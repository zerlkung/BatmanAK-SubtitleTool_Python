"""
UPK/XXX Recompressor for Batman: Arkham Knight (PS4/PC)
Recompresses decompressed UPK files back to the original custom format.

Requirements:
    pip install python-lzo
    (Linux also needs: apt install liblzo2-dev)

Usage:
    python recompress_upk.py <file_or_folder> [output_folder]

Examples:
    python recompress_upk.py Ace__Ch2.xxx
    python recompress_upk.py ps4_patched/
    python recompress_upk.py ps4_patched/ ps4_final/

Format notes (reverse-engineered from PS4 Batman AK):
    0x00-0x6C  Standard UPK header (copied as-is)
    0x6D       comp_flag = 0x08  (Batman AK custom)
    0x71       chunk_count = N   (number of compressed blocks)
    0x75       name_offset from the decompressed file
    0x79       chunk table: N × 16 bytes
               entry = {uncomp_size, comp_offset, comp_total_size, cumsum_uncomp+name_off}
    0x79+N*16  block data: each block has
               magic(4) + block_size(4) + total_comp(4) + total_uncomp(4)
               + sub-block table: {comp_size(4), uncomp_size(4)} × n_sub
               + compressed sub-block data (LZO1X-1)
"""

import struct
import sys
from pathlib import Path

try:
    import lzo
except ImportError:
    print("ERROR: python-lzo not installed.  Run: pip install python-lzo")
    sys.exit(1)

# ── Constants ──────────────────────────────────────────────────────────────────
UPK_MAGIC            = 0x9E2A83C1
COMP_FLAG            = 0x08          # Batman AK custom compression flag
PKG_STORE_COMPRESSED = 0x00020000   # UE3 PKG_StoreCompressed bit in pkg_flags
BLOCK_SIZE           = 0x20000      # 131,072 bytes per sub-block
CHUNK_UNCOMP         = BLOCK_SIZE   # one sub-block per block
EXTENSIONS           = {'.upk', '.xxx'}
COMP_FLAG_OFF        = 0x6D
CHUNK_COUNT_OFF      = 0x71
NAME_OFF_FIELD       = 0x75         # stores name_offset of decompressed file
TABLE_START          = 0x79         # chunk table begins here
HEADER_END           = 0x6D         # bytes before comp_flag are copied as-is
PKG_FLAGS_OFF        = 0x16         # offset of pkg_flags in UPK header


# ── LZO helpers ───────────────────────────────────────────────────────────────
def _compress_raw(data: bytes) -> bytes:
    """LZO1X-1 compress → raw bytes (strips the 5-byte python-lzo header)."""
    return lzo.compress(data, 1)[5:]


def _build_block(uncomp_data: bytes) -> bytes:
    """
    Build one UE3/Batman-AK chunk block.

    Structure:
        magic(4) + block_size(4) + total_comp(4) + total_uncomp(4)
        + [comp_size(4) + uncomp_size(4)] × n_sub_blocks
        + compressed sub-block data…
    """
    sub_blocks = []
    for i in range(0, len(uncomp_data), BLOCK_SIZE):
        block = uncomp_data[i:i + BLOCK_SIZE]
        sub_blocks.append((_compress_raw(block), len(block)))

    total_comp   = sum(len(c) for c, _ in sub_blocks)
    total_uncomp = len(uncomp_data)

    header = struct.pack('<IIII', UPK_MAGIC, BLOCK_SIZE, total_comp, total_uncomp)
    table  = b''.join(struct.pack('<II', len(c), u) for c, u in sub_blocks)
    data   = b''.join(c for c, _ in sub_blocks)
    return header + table + data


# ── Header parsing ─────────────────────────────────────────────────────────────
def _read_name_off(raw: bytes) -> int:
    """Return name_offset from a decompressed UPK header."""
    pos = 4 + 4 + 4           # magic + ver + header_size
    slen = struct.unpack_from('<i', raw, pos)[0]; pos += 4 + slen
    pos += 4                  # pkg_flags
    pos += 4                  # name_count
    return struct.unpack_from('<i', raw, pos)[0]


# ── Main recompress ───────────────────────────────────────────────────────────
def recompress_upk(input_path: Path, output_path: Path) -> bool:
    """
    Recompress a decompressed UPK/XXX file.
    Returns True on success, False if skipped.
    """
    raw = bytearray(input_path.read_bytes())

    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        print(f"  [SKIP] {input_path.name}: not a UPK/XXX file")
        return False

    if struct.unpack_from('<I', raw, COMP_FLAG_OFF)[0] != 0:
        print(f"  [SKIP] {input_path.name}: already compressed")
        return False

    name_off = _read_name_off(bytes(raw))

    # ── Build compressed blocks ───────────────────────────────────────────────
    payload  = bytes(raw[name_off:])   # everything from name table to EOF
    blocks   = []                      # list of (uncomp_size, block_bytes)
    for i in range(0, len(payload), CHUNK_UNCOMP):
        chunk = payload[i:i + CHUNK_UNCOMP]
        blocks.append((len(chunk), _build_block(chunk)))

    # ── Assemble output ───────────────────────────────────────────────────────
    # Header bytes 0x00-0x6C (copied from decompressed, with pkg_flags patched)
    new_header = bytearray(raw[:HEADER_END])

    # Set PKG_StoreCompressed bit in pkg_flags (gildor's tool clears this on decompress)
    pf = struct.unpack_from('<I', new_header, PKG_FLAGS_OFF)[0]
    struct.pack_into('<I', new_header, PKG_FLAGS_OFF, pf | PKG_STORE_COMPRESSED)

    # comp_flag + pad + chunk_count + name_off_dup
    new_header.extend(struct.pack('<I', COMP_FLAG))        # 0x6D comp_flag
    new_header.extend(struct.pack('<I', len(blocks)))      # 0x71 chunk_count
    new_header.extend(struct.pack('<I', name_off))         # 0x75 name_offset dup

    # Chunk table: TABLE_START = 0x79
    # Blocks will be placed immediately after the chunk table
    chunk_table_size = len(blocks) * 16
    block_data_start = len(new_header) + chunk_table_size  # absolute file offset

    chunk_table = bytearray()
    cumsum_uncomp = 0
    file_offset   = block_data_start
    for uncomp_size, block_bytes in blocks:
        comp_total = len(block_bytes)
        cumsum_uncomp += uncomp_size
        entry = struct.pack('<IIII',
                            uncomp_size,
                            file_offset,
                            comp_total,
                            cumsum_uncomp + name_off)
        chunk_table.extend(entry)
        file_offset += comp_total

    # Assemble final file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = bytes(new_header) + bytes(chunk_table)
    for _, block_bytes in blocks:
        out += block_bytes
    output_path.write_bytes(out)

    ratio = len(out) / len(raw) * 100
    print(f"  ✓ {input_path.name}: {len(raw):,} → {len(out):,} bytes ({ratio:.1f}%)")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src_path = Path(sys.argv[1])
    if not src_path.exists():
        print(f"ERROR: {src_path} not found"); sys.exit(1)

    if src_path.is_file():
        files   = [src_path] if src_path.suffix.lower() in EXTENSIONS else []
        out_dir = (Path(sys.argv[2]) if len(sys.argv) > 2
                   else src_path.parent / (src_path.stem + '_recompressed'))
    else:
        files   = [p for p in src_path.rglob('*') if p.suffix.lower() in EXTENSIONS]
        out_dir = (Path(sys.argv[2]) if len(sys.argv) > 2
                   else src_path.parent / (src_path.name + '_recompressed'))

    if not files:
        print(f"No .upk/.xxx files found at {src_path}"); sys.exit(1)

    print(f"Recompressing {len(files)} file(s) → {out_dir}/\n")
    ok = sum(recompress_upk(f, out_dir / f.name) for f in files)
    print(f"\nDone. {ok}/{len(files)} file(s) recompressed to: {out_dir}")


if __name__ == '__main__':
    main()
