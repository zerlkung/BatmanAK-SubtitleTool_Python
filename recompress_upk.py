"""
UPK/XXX Recompressor for Batman: Arkham Knight (PS4/PC + Nintendo Switch)

PS4/PC:  Recompresses using LZO1X (built-in, no extra tools needed)
Switch:  Recompresses using Oodle Kraken via ooz.exe (must be provided)

Requirements:
    pip install python-lzo          (PS4/PC only)
    ooz.exe + oo2core_7_win64.dll   (Switch only — see Notes)

Usage:
    python recompress_upk.py <file_or_folder> [output_folder] [--ooz path/to/ooz.exe]

Examples:
    python recompress_upk.py ps4_patched/
    python recompress_upk.py switch_patched/ --ooz tools/ooz.exe
    python recompress_upk.py Ace.xxx ./out/ --ooz ooz.exe

Notes:
    Switch Oodle recompression requires:
      - ooz.exe  (open-source: https://github.com/powzix/ooz)
      - oo2core_7_win64.dll  (from Warframe on Steam — free game)
    Place both files in the same folder, then pass --ooz path/to/ooz.exe

PS4/PC Format (LZO1X, reverse-engineered from PS4 Batman AK):
    0x6D  comp_flag = 0x08
    0x71  chunk_count = N
    0x75  name_offset of decompressed file
    0x79  chunk table: N × 16 bytes {uncomp_size, comp_offset, comp_total, cumsum+name_off}
          followed by LZO1X chunk blocks
"""

import struct
import sys
import subprocess
import tempfile
from pathlib import Path

# ── PS4/PC LZO support ────────────────────────────────────────────────────────
try:
    import lzo
    _HAS_LZO = True
except ImportError:
    _HAS_LZO = False

# ── Constants ──────────────────────────────────────────────────────────────────
UPK_MAGIC            = 0x9E2A83C1
GAME_VER_PS4_PC      = -2132606113
GAME_VER_SWITCH      = -2132606112
COMP_FLAG            = 0x08
PKG_STORE_COMPRESSED = 0x00020000
PKG_STORE_AGAIN      = 0x00800000
BLOCK_SIZE           = 0x20000        # 131,072 bytes
CHUNK_UNCOMP         = BLOCK_SIZE
EXTENSIONS           = {'.upk', '.xxx'}
COMP_FLAG_OFF        = 0x6D
CHUNK_COUNT_OFF      = 0x71
NAME_OFF_FIELD       = 0x75
TABLE_START          = 0x79
HEADER_END           = 0x6D
PKG_FLAGS_OFF        = 0x16


# ── Helpers ────────────────────────────────────────────────────────────────────
def _read_game_ver(raw: bytes) -> int:
    if len(raw) < 8:
        return 0
    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        return 0
    return struct.unpack_from('<i', raw, 4)[0]


def _read_name_off(raw: bytes) -> int:
    pos = 4 + 4 + 4
    slen = struct.unpack_from('<i', raw, pos)[0]; pos += 4 + slen
    pos += 4 + 4
    return struct.unpack_from('<i', raw, pos)[0]


def _compress_lzo_raw(data: bytes) -> bytes:
    return lzo.compress(data, 1)[5:]


def _build_lzo_block(uncomp_data: bytes) -> bytes:
    sub_blocks = []
    for i in range(0, len(uncomp_data), BLOCK_SIZE):
        block = uncomp_data[i:i + BLOCK_SIZE]
        sub_blocks.append((_compress_lzo_raw(block), len(block)))
    total_comp   = sum(len(c) for c, _ in sub_blocks)
    total_uncomp = len(uncomp_data)
    header = struct.pack('<IIII', UPK_MAGIC, BLOCK_SIZE, total_comp, total_uncomp)
    table  = b''.join(struct.pack('<II', len(c), u) for c, u in sub_blocks)
    data   = b''.join(c for c, _ in sub_blocks)
    return header + table + data


# ── PS4/PC recompress (LZO1X) ─────────────────────────────────────────────────
def _recompress_lzo(raw: bytearray, input_path: Path, output_path: Path) -> bool:
    if not _HAS_LZO:
        print(f"  [SKIP] {input_path.name}: python-lzo not installed — run: pip install python-lzo")
        return False

    name_off = _read_name_off(bytes(raw))
    payload  = bytes(raw[name_off:])
    blocks   = []
    for i in range(0, len(payload), CHUNK_UNCOMP):
        chunk = payload[i:i + CHUNK_UNCOMP]
        blocks.append((len(chunk), _build_lzo_block(chunk)))

    new_header = bytearray(raw[:HEADER_END])
    pf = struct.unpack_from('<I', new_header, PKG_FLAGS_OFF)[0]
    struct.pack_into('<I', new_header, PKG_FLAGS_OFF, pf | PKG_STORE_COMPRESSED)
    new_header.extend(struct.pack('<I', COMP_FLAG))
    new_header.extend(struct.pack('<I', len(blocks)))
    new_header.extend(struct.pack('<I', name_off))

    chunk_table_size = len(blocks) * 16
    block_data_start = len(new_header) + chunk_table_size

    chunk_table    = bytearray()
    cumsum_uncomp  = 0
    file_offset    = block_data_start
    for uncomp_size, block_bytes in blocks:
        comp_total    = len(block_bytes)
        cumsum_uncomp += uncomp_size
        chunk_table.extend(struct.pack('<IIII',
                                       uncomp_size, file_offset,
                                       comp_total, cumsum_uncomp + name_off))
        file_offset += comp_total

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = bytes(new_header) + bytes(chunk_table)
    for _, block_bytes in blocks:
        out += block_bytes
    output_path.write_bytes(out)

    ratio = len(out) / len(raw) * 100
    print(f"  ✓ {input_path.name}: {len(raw):,} → {len(out):,} bytes ({ratio:.1f}%)  [LZO1X]")
    return True


# ── Switch recompress (Oodle via ooz.exe) ─────────────────────────────────────
def _recompress_oodle(raw: bytearray, input_path: Path, output_path: Path,
                      ooz_exe: Path) -> bool:
    """
    Recompress a Switch UPK using ooz.exe (Oodle Kraken).
    ooz.exe operates on raw payload bytes, not the full UPK file.
    We extract the payload, compress it, then rebuild the UPK header.
    """
    name_off = _read_name_off(bytes(raw))
    payload  = bytes(raw[name_off:])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_in  = Path(tmp) / 'payload.bin'
        tmp_out = Path(tmp) / 'payload.kraken'
        tmp_in.write_bytes(payload)

        try:
            result = subprocess.run(
                [str(ooz_exe), '-z', '--kraken', str(tmp_in), str(tmp_out)],
                capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired:
            print(f"  [FAIL] {input_path.name}: ooz.exe timed out")
            return False
        except FileNotFoundError:
            print(f"  [FAIL] {input_path.name}: ooz.exe not found at {ooz_exe}")
            return False

        if result.returncode != 0 or not tmp_out.exists():
            print(f"  [FAIL] {input_path.name}: ooz.exe failed (rc={result.returncode})")
            if result.stderr:
                print(f"         {result.stderr.strip()[:120]}")
            return False

        compressed_payload = tmp_out.read_bytes()

    # Build single-chunk UPK: header + 1 chunk block (no sub-block split for Oodle)
    # The chunk block header still uses UPK_MAGIC + BLOCK_SIZE convention
    total_comp   = len(compressed_payload)
    total_uncomp = len(payload)
    n_sub        = (total_uncomp + BLOCK_SIZE - 1) // BLOCK_SIZE

    # Sub-block sizes: last block may be smaller
    sub_sizes = []
    # ooz compressed the whole payload as one stream; we treat it as 1 sub-block
    sub_table = struct.pack('<II', total_comp, total_uncomp)
    chunk_block = (struct.pack('<IIII', UPK_MAGIC, BLOCK_SIZE, total_comp, total_uncomp)
                   + sub_table
                   + compressed_payload)

    new_header = bytearray(raw[:HEADER_END])
    pf = struct.unpack_from('<I', new_header, PKG_FLAGS_OFF)[0]
    struct.pack_into('<I', new_header, PKG_FLAGS_OFF, pf | PKG_STORE_COMPRESSED)
    new_header.extend(struct.pack('<I', COMP_FLAG))
    new_header.extend(struct.pack('<I', 1))        # chunk_count = 1
    new_header.extend(struct.pack('<I', name_off))

    block_data_start = len(new_header) + 16  # 1 entry × 16 bytes
    chunk_table = struct.pack('<IIII',
                               total_uncomp,
                               block_data_start,
                               len(chunk_block),
                               total_uncomp + name_off)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = bytes(new_header) + chunk_table + chunk_block
    output_path.write_bytes(out)

    ratio = len(out) / len(raw) * 100
    print(f"  ✓ {input_path.name}: {len(raw):,} → {len(out):,} bytes ({ratio:.1f}%)  [Oodle/Kraken]")
    return True


# ── Main entry ────────────────────────────────────────────────────────────────
def recompress_upk(input_path: Path, output_path: Path,
                   ooz_exe: Path | None = None) -> bool:
    raw = bytearray(input_path.read_bytes())

    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        print(f"  [SKIP] {input_path.name}: not a UPK/XXX file")
        return False

    if struct.unpack_from('<I', raw, COMP_FLAG_OFF)[0] != 0:
        print(f"  [SKIP] {input_path.name}: already compressed")
        return False

    game_ver = struct.unpack_from('<i', raw, 4)[0]
    is_switch = (game_ver == GAME_VER_SWITCH)

    if is_switch:
        if ooz_exe is None:
            print(f"  [SKIP] {input_path.name}: Switch file — use --ooz path/to/ooz.exe")
            return False
        print(f"  [WIP]  {input_path.name}: Switch recompression is experimental.")
        print(f"         It is recommended to test with the decompressed file first.")
        print(f"         PKG_CookedForConsole behavior on Switch is not yet confirmed.")
        return _recompress_oodle(raw, input_path, output_path, ooz_exe)
    else:
        return _recompress_lzo(raw, input_path, output_path)


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target', help='File or folder to recompress')
    parser.add_argument('output', nargs='?', help='Output folder')
    parser.add_argument('--ooz', help='Path to ooz.exe (required for Switch files)')
    args = parser.parse_args()

    src_path = Path(args.target)
    if not src_path.exists():
        print(f"ERROR: {src_path} not found"); sys.exit(1)

    ooz_exe = Path(args.ooz) if args.ooz else None

    if src_path.is_file():
        files   = [src_path] if src_path.suffix.lower() in EXTENSIONS else []
        out_dir = (Path(args.output) if args.output
                   else src_path.parent / (src_path.stem + '_recompressed'))
    else:
        files   = [p for p in src_path.rglob('*') if p.suffix.lower() in EXTENSIONS]
        out_dir = (Path(args.output) if args.output
                   else src_path.parent / (src_path.name + '_recompressed'))

    if not files:
        print(f"No .upk/.xxx files found at {src_path}"); sys.exit(1)

    print(f"Recompressing {len(files)} file(s) → {out_dir}/\n")
    ok = sum(recompress_upk(f, out_dir / f.name, ooz_exe) for f in files)
    print(f"\nDone. {ok}/{len(files)} file(s) recompressed to: {out_dir}")


if __name__ == '__main__':
    main()
