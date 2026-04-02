"""
UPK/XXX Decompressor for Batman: Arkham Knight (PS4/PC)
Wraps gildor's decompress.exe — handles the custom chunk table format.

Requirements:
    decompress.exe (gildor's Unreal Package Decompressor)
    placed in the same folder as this script OR specified with --tool

Usage:
    python decompress_upk.py <file_or_folder> [output_folder] [--tool path/to/decompress.exe]

Examples:
    python decompress_upk.py Ace.xxx
    python decompress_upk.py ps4_files/
    python decompress_upk.py ps4_files/ ps4_decomp/ --tool tools/decompress.exe

Notes:
    - Skips files that are already decompressed (comp_flag == 0)
    - Output goes to <folder>_decompressed/ by default
    - decompress.exe can be downloaded from: https://www.gildor.org/down/47/umodel/decompress.zip
"""

import struct
import sys
import shutil
import subprocess
from pathlib import Path

EXTENSIONS    = {'.upk', '.xxx'}
COMP_FLAG_OFF = 0x6D
UPK_MAGIC     = 0x9E2A83C1


def is_compressed(raw: bytes) -> bool:
    if len(raw) < 0x72:
        return False
    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        return False
    return struct.unpack_from('<I', raw, COMP_FLAG_OFF)[0] != 0


def find_decompress_exe(hint: Path | None) -> Path | None:
    """Search for decompress.exe: hint → script dir → PATH."""
    candidates = []
    if hint:
        candidates.append(hint)
    script_dir = Path(__file__).parent
    candidates += [
        script_dir / 'decompress.exe',
        script_dir / 'tools' / 'decompress.exe',
    ]
    for p in candidates:
        if p.exists():
            return p
    # try PATH
    found = shutil.which('decompress.exe') or shutil.which('decompress')
    return Path(found) if found else None


def decompress_file(input_path: Path, output_path: Path, decompress_exe: Path) -> bool:
    """Decompress one file using gildor's tool. Returns True on success."""
    raw = input_path.read_bytes()

    if struct.unpack_from('<I', raw, 0)[0] != UPK_MAGIC:
        print(f"  [SKIP] {input_path.name}: not a UPK/XXX file")
        return False

    if not is_compressed(raw):
        print(f"  [SKIP] {input_path.name}: already decompressed")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # gildor's tool decompresses in-place or to the same folder
    # we copy to a temp location, decompress, then move
    tmp = output_path.parent / (input_path.stem + '_tmp' + input_path.suffix)
    shutil.copy2(input_path, tmp)

    try:
        result = subprocess.run(
            [str(decompress_exe), str(tmp)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  [FAIL] {input_path.name}: decompress.exe returned {result.returncode}")
            if result.stderr:
                print(f"         {result.stderr.strip()}")
            tmp.unlink(missing_ok=True)
            return False

        # gildor's tool writes output as <name>_decomp.<ext> or similar
        # try common output names
        possible = [
            tmp.parent / (tmp.stem + '_decomp' + tmp.suffix),
            tmp.parent / (tmp.stem + '.decomp' + tmp.suffix),
            tmp,  # some versions overwrite in-place
        ]
        out_file = None
        for p in possible:
            if p.exists() and p != tmp:
                out_file = p
                break
        if out_file is None:
            # check if tmp itself was modified (in-place decomp)
            tmp_raw = tmp.read_bytes()
            if not is_compressed(tmp_raw):
                out_file = tmp

        if out_file is None:
            print(f"  [FAIL] {input_path.name}: could not find decompressed output")
            tmp.unlink(missing_ok=True)
            return False

        shutil.move(str(out_file), str(output_path))
        if tmp.exists():
            tmp.unlink()

        orig_size = len(raw)
        new_size  = output_path.stat().st_size
        print(f"  ✓ {input_path.name}: {orig_size:,} → {new_size:,} bytes ({new_size/orig_size*100:.0f}%)")
        return True

    except subprocess.TimeoutExpired:
        print(f"  [FAIL] {input_path.name}: decompress.exe timed out")
        tmp.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"  [FAIL] {input_path.name}: {e}")
        tmp.unlink(missing_ok=True)
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target', help='File or folder to decompress')
    parser.add_argument('output', nargs='?', help='Output folder (default: <folder>_decompressed)')
    parser.add_argument('--tool', help='Path to decompress.exe')
    args = parser.parse_args()

    src_path = Path(args.target)
    if not src_path.exists():
        print(f"ERROR: {src_path} not found"); sys.exit(1)

    tool_hint = Path(args.tool) if args.tool else None
    decomp_exe = find_decompress_exe(tool_hint)
    if not decomp_exe:
        print("ERROR: decompress.exe not found.")
        print("  Download from: https://www.gildor.org/down/47/umodel/decompress.zip")
        print("  Place it in the same folder as this script, or use --tool path/to/decompress.exe")
        sys.exit(1)
    print(f"Using: {decomp_exe}")

    # Collect files
    if src_path.is_file():
        files = [src_path]
        out_dir = Path(args.output) if args.output else src_path.parent / (src_path.stem + '_decompressed')
    else:
        files = [p for p in src_path.rglob('*') if p.suffix.lower() in EXTENSIONS]
        out_dir = Path(args.output) if args.output else src_path.parent / (src_path.name + '_decompressed')

    if not files:
        print(f"No .upk/.xxx files found at {src_path}"); sys.exit(1)

    print(f"Decompressing {len(files)} file(s) → {out_dir}/\n")
    ok = sum(decompress_file(f, out_dir / f.name, decomp_exe) for f in files)
    print(f"\nDone. {ok}/{len(files)} file(s) decompressed to: {out_dir}")


if __name__ == '__main__':
    main()
