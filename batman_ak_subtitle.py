"""
Batman: Arkham Knight Subtitle Tool (Python port)
Supports PC (.upk) and PS4 (.xxx) — same binary format, different extension.

Usage:
  Export:  python batman_ak_subtitle.py export <file_or_folder> [--lang N]
  Import:  python batman_ak_subtitle.py import <target_file_or_folder> --src <json_or_folder> [--dst-lang N]

Aliases: 'export' = 'e', 'import' = 'i'

Language index (0–10):
  0=English  1=French   2=Italian   3=German    4=Spanish(ES)
  5=Spanish(MX)  6=Portuguese  7=Japanese  8=Korean  9=Russian  10=Polish

Notes:
  - Files must be decompressed first (use Unreal Package Decompressor by gildor).
  - Import writes to a new '_patched' folder, never overwrites the original.
  - Cross-platform: export Thai from PC slot[0], import into PS4 slot[0].
"""

import argparse
import json
import struct
import shutil
import sys
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

UPK_MAGIC   = 0x9E2A83C1
GAME_VER    = -2132606113
EXTENSIONS  = {'.upk', '.xxx'}
LANG_NAMES  = [
    'English', 'French', 'Italian', 'German',
    'Spanish(ES)', 'Spanish(MX)', 'Portuguese',
    'Japanese', 'Korean', 'Russian', 'Polish',
]

# ── Low-level binary helpers ──────────────────────────────────────────────────

def read_i16(data, pos):  return struct.unpack_from('<h', data, pos)[0], pos + 2
def read_i32(data, pos):  return struct.unpack_from('<i', data, pos)[0], pos + 4
def read_u32(data, pos):  return struct.unpack_from('<I', data, pos)[0], pos + 4
def read_u64(data, pos):  return struct.unpack_from('<Q', data, pos)[0], pos + 8

def write_i16(buf, pos, v): struct.pack_into('<h', buf, pos, v); return pos + 2
def write_i32(buf, pos, v): struct.pack_into('<i', buf, pos, v); return pos + 4
def write_u32(buf, pos, v): struct.pack_into('<I', buf, pos, v); return pos + 4


def read_tstring(data, pos):
    """Read a UE3 TString (length-prefixed, ASCII or UTF-16LE)."""
    length, pos = read_i32(data, pos)
    if length > 0:
        s = data[pos:pos + length - 1].decode('ascii', errors='replace')
        pos += length
    elif length < 0:
        byte_len = (-length) * 2
        s = data[pos:pos + byte_len - 2].decode('utf-16-le', errors='replace')
        pos += byte_len
    else:
        s = ''
    return s, pos


def encode_tstring(s, force_unicode=False):
    """Encode a string as UE3 TString bytes (length header + content)."""
    if not s:
        return struct.pack('<i', 0)
    if force_unicode or _needs_unicode(s):
        encoded = s.encode('utf-16-le') + b'\x00\x00'
        length  = -(len(encoded) // 2)          # negative = UTF-16
        return struct.pack('<i', length) + encoded
    else:
        encoded = s.encode('ascii') + b'\x00'
        return struct.pack('<i', len(encoded)) + encoded


def _needs_unicode(s):
    try:
        s.encode('ascii')
        return False
    except UnicodeEncodeError:
        return True


# ── UPK parser ────────────────────────────────────────────────────────────────

class UpkFile:
    """Parse a decompressed UPK/XXX file and expose its tables."""

    def __init__(self, path: Path):
        self.path = path
        self.raw  = bytearray(path.read_bytes())
        self._parse()

    def _parse(self):
        raw = self.raw
        pos = 0

        magic, pos  = read_u32(raw, pos)
        if magic != UPK_MAGIC:
            raise ValueError(f"{self.path.name}: Invalid UPK magic 0x{magic:08X}")

        game_ver, pos = read_i32(raw, pos)
        if game_ver != GAME_VER:
            raise ValueError(f"{self.path.name}: Unsupported game version {game_ver}")

        self.header_size, pos = read_i32(raw, pos)

        # "None" string
        _, pos = read_tstring(raw, pos)

        self.pkg_flags,    pos = read_u32(raw, pos)
        self.name_count,   pos = read_i32(raw, pos)
        self.name_offset,  pos = read_i32(raw, pos)
        self.export_count, pos = read_i32(raw, pos)
        self.export_offset,pos = read_i32(raw, pos)
        self.import_count, pos = read_i32(raw, pos)
        self.import_offset,pos = read_i32(raw, pos)

        # Detect compressed file: offsets must be within file bounds
        file_size = len(raw)
        if (self.name_offset   <= 0 or self.name_offset   >= file_size or
                self.export_offset <= 0 or self.export_offset >= file_size or
                self.import_offset <= 0 or self.import_offset >= file_size):
            raise ValueError(
                f"{self.path.name}: File appears to be compressed — "
                "please decompress it first using Unreal Package Decompressor."
            )

        self._parse_names()
        self._parse_imports()
        self._parse_exports()

    def _parse_names(self):
        self.names = []
        pos = self.name_offset
        for _ in range(self.name_count):
            name, pos = read_tstring(self.raw, pos)
            pos += 8   # u64 flags
            self.names.append(name)

    def _parse_imports(self):
        # Each import entry is 7 × i32 = 28 bytes
        # Layout: packageName(4) packageNameOrd(4) className(4) classNameOrd(4)
        #         outerObj(4) objName(4) objNameOrd(4)
        self.imports = []
        pos = self.import_offset
        for _ in range(self.import_count):
            fields = list(struct.unpack_from('<7i', self.raw, pos))
            pos += 28
            self.imports.append({
                'packageName': fields[0],
                'className':   fields[2],
                'outerObj':    fields[4],
                'objName':     fields[5],   # ← confirmed from TImport.cs
            })

    def _parse_exports(self):
        self.exports = []
        pos = self.export_offset
        for _ in range(self.export_count):
            classObj,    pos = read_i32(self.raw, pos)
            _,           pos = read_i32(self.raw, pos)  # superObj
            _,           pos = read_i32(self.raw, pos)  # outerObj
            objName,     pos = read_i32(self.raw, pos)
            _,           pos = read_i32(self.raw, pos)  # objNameOrder
            _,           pos = read_i32(self.raw, pos)  # objArchetype
            _,           pos = read_u64(self.raw, pos)  # objFlags
            _,           pos = read_i32(self.raw, pos)  # objFlagsExt
            size,        pos = read_i32(self.raw, pos)
            offset = 0
            if size > 0:
                offset, pos = read_i32(self.raw, pos)
            pos += 4 + 16 + 4 + 4   # exportFlags + GUID + pkgFlags + pkgFlagsExt
            self.exports.append({
                'classObj': classObj,
                'objName':  objName,
                'size':     size,
                'offset':   offset,
                '_pos':     pos,    # position after this export entry (for patching)
            })

    def resolve_class(self, idx):
        """Resolve a classObj index to a class name string."""
        try:
            if idx < 0:
                return self.names[self.imports[-idx - 1]['objName']]
            elif idx > 0:
                return self.names[self.exports[idx - 1]['objName']]
        except (IndexError, KeyError):
            pass
        return 'null'

    @property
    def dt_name_index(self):
        """Name-table index of 'DialogueText'."""
        if not hasattr(self, '_dt_idx'):
            self._dt_idx = next(
                (i for i, n in enumerate(self.names) if n == 'DialogueText'), None
            )
        return self._dt_idx

    def ak_dialogue_exports(self):
        """Yield (export_index, export_dict) for every AkDialogueEvent export."""
        for i, e in enumerate(self.exports):
            if self.resolve_class(e['classObj']) == 'AkDialogueEvent' and e['size'] > 0:
                yield i, e


# ── DialogueText array parser ─────────────────────────────────────────────────

def parse_dialogue_array(data, dt_idx):
    """
    Scan object data for the DialogueText ArrayProperty and return
    (array_end_pos, arr_size_pos, slots) where:
      array_end_pos  = position of the first byte AFTER the last slot
      arr_size_pos     = position of the arr_size i32 field (for patching)
      slots            = list of (slot_str, slot_start_pos) for every slot
    Returns None if not found.
    """
    data_len = len(data)
    p = 0
    while p < data_len - 16:
        key = struct.unpack_from('<h', data, p)[0]
        if key == 9:  # ArrayProperty
            idx1 = struct.unpack_from('<i', data, p + 4)[0]
            if idx1 == dt_idx:
                # key(2) + sub(2) + idx1(4) + unk(4) = 12 bytes to arr_size
                p2 = p + 12

                # bounds: need 12 bytes for arr_size(4) + padding(4) + count(4)
                if p2 + 12 > data_len:
                    p += 1
                    continue

                arr_size_pos = p2
                arr_size, p2 = read_i32(data, p2)
                _,        p2 = read_i32(data, p2)   # zero/padding
                count,    p2 = read_i32(data, p2)

                # sanity: UE3 has 11 language slots max, reject garbage counts
                if count <= 0 or count > 20:
                    p += 1
                    continue

                slots = []
                ok = True
                for _ in range(count):
                    slot_start = p2

                    # need at least 4 bytes for the length prefix
                    if p2 + 4 > data_len:
                        ok = False
                        break

                    # peek the length to validate before reading
                    length = struct.unpack_from('<i', data, p2)[0]
                    if length > 0:
                        # ASCII: length includes null terminator
                        if p2 + 4 + length > data_len:
                            ok = False
                            break
                    elif length < 0:
                        # UTF-16LE: byte_len = (-length) * 2, includes null terminator
                        byte_len = (-length) * 2
                        if p2 + 4 + byte_len > data_len:
                            ok = False
                            break
                    # length == 0 is an empty string, always safe

                    s, p2 = read_tstring(data, p2)
                    slots.append((s, slot_start))

                if ok and len(slots) == count:
                    return p2, arr_size_pos, slots

                # if validation failed, keep scanning from next byte
        p += 1
    return None


# ── Export ────────────────────────────────────────────────────────────────────

def export_file(upk: UpkFile, lang: int):
    """
    Extract all AkDialogueEvent subtitles from lang slot.
    Returns list of (key, text) to preserve order and handle duplicate names.
    Keys are 'ObjName' or 'ObjName#N' for duplicates (N = occurrence index).
    Empty slots are included as empty string to preserve line count.
    """
    result = []      # list of (key, text)
    name_count = {}  # track how many times each name has appeared
    dt_idx = upk.dt_name_index
    if dt_idx is None:
        return result

    for _, e in upk.ak_dialogue_exports():
        obj_name  = upk.names[e['objName']]
        obj_start = e['offset']

        # Read from obj_start to end-of-file so that relocated objects
        # (where Thai UTF-16 data extends beyond the original e['size'])
        # are read fully.  parse_dialogue_array stops as soon as it finds
        # the valid DialogueText array and returns, so the extra bytes are
        # never misinterpreted.
        data   = bytes(upk.raw[obj_start:])
        parsed = parse_dialogue_array(data, dt_idx)
        if parsed is None:
            continue
        _, _, slots = parsed

        # Build unique key for duplicate names
        count = name_count.get(obj_name, 0)
        name_count[obj_name] = count + 1
        key = obj_name if count == 0 else f'{obj_name}#{count}'

        text = slots[lang][0] if lang < len(slots) else ''
        result.append((key, text))

    return result


# ── Import (in-place patch) ───────────────────────────────────────────────────

def import_file(target: UpkFile, texts, dst_lang: int):
    """
    Patch target in-place: for each AkDialogueEvent replace slot[dst_lang].
    texts can be:
      - list of (key, text)  — from export_file (preserves order + duplicates)
      - dict {key: text}     — legacy JSON format
    Keys use 'ObjName' or 'ObjName#N' for duplicates.
    """
    dt_idx = target.dt_name_index
    if dt_idx is None:
        print("  [WARN] 'DialogueText' not found in name table — nothing to import.")
        return

    # Normalise texts to dict keyed by unique key
    if isinstance(texts, list):
        texts_dict = dict(texts)
    else:
        texts_dict = texts

    patched = 0
    skipped = 0
    name_count = {}  # track occurrences to build same keys as export

    for exp_i, e in target.ak_dialogue_exports():
        obj_name = target.names[e['objName']]

        # Build the same unique key used during export
        count = name_count.get(obj_name, 0)
        name_count[obj_name] = count + 1
        key = obj_name if count == 0 else f'{obj_name}#{count}'

        new_text = texts_dict.get(key)
        if new_text is None:
            skipped += 1
            continue

        # Skip empty translations (preserve original)
        if not new_text:
            skipped += 1
            continue

        obj_start = e['offset']
        # e['size'] may be stale (from before a previous relocation).
        # Read from obj_start to end-of-file so parse_dialogue_array always
        # sees the complete object, then slice to actual parsed length.
        data = bytearray(target.raw[obj_start:])

        parsed = parse_dialogue_array(bytes(data), dt_idx)
        if parsed is None:
            print(f"  [WARN] {key}: DialogueText array not found, skipping.")
            skipped += 1
            continue

        array_end_pos, arr_size_pos, slots = parsed

        # Derive the true current size of this object from the parsed data.
        # array_end_pos is the byte right after the last slot — that IS the
        # effective end of the DialogueText array.  For safety we use
        # max(e['size'], array_end_pos) so we never truncate.
        true_size = max(e['size'], array_end_pos)
        obj_end   = obj_start + true_size
        data      = bytearray(target.raw[obj_start:obj_end])

        if dst_lang >= len(slots):
            print(f"  [WARN] {key}: lang slot {dst_lang} doesn't exist (only {len(slots)} slots), skipping.")
            skipped += 1
            continue

        old_str, slot_pos = slots[dst_lang]
        if not old_str:
            # empty slot — nothing to replace
            skipped += 1
            continue

        # Encode old and new
        old_encoded = encode_tstring(old_str)
        new_encoded = encode_tstring(new_text, force_unicode=True)
        delta = len(new_encoded) - len(old_encoded)

        # Build new object data
        new_data = (
            data[:slot_pos] +
            bytearray(new_encoded) +
            data[slot_pos + len(old_encoded):]
        )

        # Fix arr_size field
        old_arr_size = struct.unpack_from('<i', new_data, arr_size_pos)[0]
        struct.pack_into('<i', new_data, arr_size_pos, old_arr_size + delta)

        # Write new object back into raw
        if delta == 0:
            target.raw[obj_start:obj_end] = new_data
        else:
            new_offset = len(target.raw)
            target.raw.extend(new_data)
            # Zero out old slot using true_size (not stale e['size'])
            target.raw[obj_start:obj_end] = b'\x00' * true_size
            _patch_export_entry(target, exp_i, new_offset, len(new_data))

        patched += 1
        print(f"  ✓ {key}")
        if delta != 0:
            print(f"    (size changed by {delta:+d} bytes, relocated to 0x{new_offset:X})")

    print(f"\n  Patched: {patched}  Skipped: {skipped}")


def _patch_export_entry(upk: UpkFile, exp_i: int, new_offset: int, new_size: int):
    """
    Re-parse the export table entry for exp_i and patch its offset and size fields.
    """
    raw = upk.raw
    pos = upk.export_offset
    for i in range(upk.export_count):
        entry_start = pos
        classObj, pos = read_i32(raw, pos)
        pos += 4 + 4   # superObj + outerObj
        pos += 4 + 4   # objName + objNameOrder
        pos += 4       # objArchetype
        pos += 8       # objFlags
        pos += 4       # objFlagsExt
        size_pos = pos
        size, pos = read_i32(raw, pos)
        offset_pos = pos
        if size > 0:
            _, pos = read_i32(raw, pos)
        pos += 4 + 16 + 4 + 4  # exportFlags + GUID + pkgFlags + pkgFlagsExt

        if i == exp_i:
            struct.pack_into('<i', raw, size_pos,   new_size)
            struct.pack_into('<i', raw, offset_pos, new_offset)
            return


# ── File & folder helpers ─────────────────────────────────────────────────────

def collect_files(path: Path):
    if path.is_file():
        return [path] if path.suffix.lower() in EXTENSIONS else []
    return [p for p in path.rglob('*') if p.suffix.lower() in EXTENSIONS]


def output_path_for(src: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / src.name


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_export(args):
    src_path = Path(args.target)
    files = collect_files(src_path)
    if not files:
        print(f"No .upk/.xxx files found at: {src_path}")
        sys.exit(1)

    lang = args.lang
    print(f"Exporting lang slot [{lang}] ({LANG_NAMES[lang] if lang < len(LANG_NAMES) else '?'}) from {len(files)} file(s)...\n")

    all_texts = {}
    for f in files:
        print(f"  Reading {f.name}...")
        try:
            upk = UpkFile(f)
        except ValueError as e:
            print(f"    [SKIP] {e}")
            continue
        pairs = export_file(upk, lang)  # list of (key, text)
        if pairs:
            # Store as dict — duplicate keys get '#N' suffix so no loss
            all_texts[f.stem] = dict(pairs)
            print(f"    → {len(pairs)} subtitle(s) extracted")
        else:
            print(f"    → no subtitles found")

    if not all_texts:
        print("\nNothing exported.")
        return

    # Output JSON
    if src_path.is_dir():
        out_file = src_path / 'exported_subtitles.json'
    else:
        out_file = src_path.with_suffix('.json')

    out_file.write_text(
        json.dumps(all_texts, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    total = sum(len(v) for v in all_texts.values())
    print(f"\nDone. {total} subtitle(s) written to: {out_file}")


def cmd_import(args):
    dst_path = Path(args.target)
    src_path = Path(args.src)

    dst_files = collect_files(dst_path)
    if not dst_files:
        print(f"No .upk/.xxx files found at target: {dst_path}")
        sys.exit(1)

    # Load source texts from JSON
    if src_path.suffix.lower() == '.json':
        json_path = src_path
    elif src_path.is_dir():
        json_path = src_path / 'exported_subtitles.json'
    else:
        json_path = src_path.with_suffix('.json')

    if not json_path.exists():
        print(f"Source JSON not found: {json_path}")
        print("Run export first to generate the JSON file.")
        sys.exit(1)

    all_texts = json.loads(json_path.read_text(encoding='utf-8'))

    dst_lang = args.dst_lang
    print(f"Importing into lang slot [{dst_lang}] ({LANG_NAMES[dst_lang] if dst_lang < len(LANG_NAMES) else '?'})")
    print(f"Target: {dst_path}  ({len(dst_files)} file(s))")
    print(f"Source JSON: {json_path}\n")

    # Output to _patched folder
    if dst_path.is_dir():
        out_dir = dst_path.parent / (dst_path.name + '_patched')
    else:
        out_dir = dst_path.parent / (dst_path.stem + '_patched')

    patched_files = 0
    for f in dst_files:
        texts = all_texts.get(f.stem)
        if not texts:
            print(f"  [SKIP] {f.name} — no matching entry in JSON")
            continue

        print(f"  Processing {f.name}...")

        # Copy to output dir first, then patch the copy
        out_file = output_path_for(f, out_dir)
        shutil.copy2(f, out_file)

        try:
            upk = UpkFile(out_file)
        except ValueError as e:
            print(f"  [SKIP] {e}")
            out_file.unlink(missing_ok=True)
            continue

        import_file(upk, texts, dst_lang)

        # Write patched bytes back
        out_file.write_bytes(upk.raw)
        patched_files += 1

    print(f"\nDone. {patched_files} file(s) written to: {out_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Batman: Arkham Knight Subtitle Tool (Python)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest='cmd')

    # Export
    exp = sub.add_parser('export', aliases=['e'], help='Export subtitles to JSON')
    exp.add_argument('target', help='File or folder to export from')
    exp.add_argument('--lang', type=int, default=0,
                     help='Language slot to export (0=English, default=0)')

    # Import
    imp = sub.add_parser('import', aliases=['i'], help='Import subtitles from JSON into target files')
    imp.add_argument('target', help='Target file or folder (PS4 .xxx or PC .upk)')
    imp.add_argument('--src', required=True,
                     help='Source: folder containing exported_subtitles.json, or direct .json path')
    imp.add_argument('--dst-lang', type=int, default=0,
                     help='Destination language slot to overwrite (default=0 = English)')

    args = parser.parse_args()

    if args.cmd in ('export', 'e'):
        cmd_export(args)
    elif args.cmd in ('import', 'i'):
        cmd_import(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
