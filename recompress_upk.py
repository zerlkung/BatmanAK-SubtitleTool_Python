"""
UPK/XXX Recompressor for Batman: Arkham Knight (PC/PS4)
Recompresses decompressed UPK files back to LZO1X format.

Requirements:
    pip install python-lzo

Usage:
    python recompress_upk.py <file_or_folder> [output_folder]

    If output_folder is omitted, writes to <folder>_recompressed/

Examples:
    python recompress_upk.py Ace__Ch2.xxx
    python recompress_upk.py ps4_patched/
    python recompress_upk.py ps4_patched/ ps4_final/

Notes:
    - Input must be decompressed first (gildor's decompress.exe)
    - Already-compressed files are skipped automatically
    - Output files are safe to copy back into the game
"""

import struct
import sys
from pathlib import Path

try:
    import lzo
except ImportError:
    print("ERROR: python-lzo not installed. Run: pip install python-lzo")
    print("       You may also need: apt install liblzo2-dev  (Linux)")
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

UPK_MAGIC       = 0x9E2A83C1
LZO_FLAG        = 0x02           # UE3 compression flag for LZO
BLOCK_SIZE      = 0x20000        # 131,072 bytes per sub-block (same as original)
CHUNK_UNCOMP    = BLOCK_SIZE * 4 # 512 KB per chunk entry in table
EXTENSIONS      = {'.upk', '.xxx'}
COMP_FLAGS_OFF  = 0x6D           # offset of compression_flags in UPK header


# ── LZO helpers ───────────────────────────────────────────────────────────────

def _compress_raw(data: bytes) -> bytes:
    """LZO1X-1 compress, returning raw bytes (no python-lzo 5-byte header)."""
    return lzo.compress(data, 1)[5:]


def _build_chunk(uncomp_data: bytes) -> bytes:
    """
    Build one UE3 chunk block from uncompressed data.

    Structure:
        magic(4) + block_size(4) + total_comp(4) + total_uncomp(4)
        + [comp_size(4) + uncomp_size(4)] * n_sub_blocks
        + compressed sub-block data ...
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


# ── Main recompress ───────────────────────────────────────────────────────────

def recompress_upk(input_path: Path, output_path: Path) -> bool:
    """
    Recompress a decompressed UPK/XXX file.
    Returns True on success, False if file was skipped.
    """
    raw = bytearray(input_path.read_bytes())

    # Validate magic
    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        print(f"  [SKIP] {input_path.name}: not a UPK/XXX file")
        return False

    # Skip already-compressed files
    if struct.unpack_from('<I', raw, COMP_FLAGS_OFF)[0] != 0:
        print(f"  [SKIP] {input_path.name}: already compressed")
        return False

    # Find name_offset (start of payload to compress)
    pos = 4 + 4 + 4  # magic + ver + header_size
    slen = struct.unpack_from('<i', raw, pos)[0]; pos += 4 + slen
    pos += 4  # pkg_flags
    pos += 4  # name_count
    name_off = struct.unpack_from('<i', raw, pos)[0]

    HEADER_END = 0x75  # end of standard header fields

    payload = bytes(raw[name_off:])

    # Build chunk list
    chunks_data = []
    for i in range(0, len(payload), CHUNK_UNCOMP):
        uncomp = payload[i:i + CHUNK_UNCOMP]
        chunks_data.append((len(uncomp), _build_chunk(uncomp)))

    # Build new header (copy original, set compression flag)
    new_header = bytearray(raw[:HEADER_END])
    struct.pack_into('<I', new_header, COMP_FLAGS_OFF, LZO_FLAG)

    # Build chunk table
    chunk_table_size = 4 + len(chunks_data) * 16
    chunk_data_start = len(new_header) + chunk_table_size

    chunk_table = bytearray(struct.pack('<I', len(chunks_data)))
    file_offset = chunk_data_start
    mem_offset  = name_off
    for uncomp_size, chunk_bytes in chunks_data:
        chunk_table.extend(struct.pack('<IIII',
                                       file_offset, len(chunk_bytes),
                                       mem_offset,  uncomp_size))
        file_offset += len(chunk_bytes)
        mem_offset  += uncomp_size

    # Assemble output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = bytes(new_header) + bytes(chunk_table)
    for _, chunk_bytes in chunks_data:
        out += chunk_bytes
    output_path.write_bytes(out)

    ratio = len(out) / len(raw) * 100
    print(f"  ✓ {input_path.name}: {len(raw):,} → {len(out):,} bytes ({ratio:.1f}%)")
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src_path = Path(sys.argv[1])
    if not src_path.exists():
        print(f"ERROR: {src_path} not found")
        sys.exit(1)

    # Collect input files
    if src_path.is_file():
        files = [src_path] if src_path.suffix.lower() in EXTENSIONS else []
        if not files:
            print(f"ERROR: {src_path.name} is not a .upk/.xxx file")
            sys.exit(1)
        out_dir = (Path(sys.argv[2]) if len(sys.argv) > 2
                   else src_path.parent / (src_path.stem + '_recompressed'))
    else:
        files = [p for p in src_path.rglob('*') if p.suffix.lower() in EXTENSIONS]
        if not files:
            print(f"No .upk/.xxx files found in {src_path}")
            sys.exit(1)
        out_dir = (Path(sys.argv[2]) if len(sys.argv) > 2
                   else src_path.parent / (src_path.name + '_recompressed'))

    print(f"Recompressing {len(files)} file(s) → {out_dir}/\n")

    ok = 0
    for f in files:
        out_file = out_dir / f.name
        if recompress_upk(f, out_file):
            ok += 1

    print(f"\nDone. {ok}/{len(files)} file(s) recompressed to: {out_dir}")


if __name__ == '__main__':
    main()
