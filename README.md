# Batman: Arkham Knight Subtitle Tool (Python)

> ⚠️ **Work In Progress** — ยังอยู่ในขั้นตอนพัฒนา / Still under development

Python port of [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**

---

## ภาษาไทย

### เกี่ยวกับโปรเจกต์นี้

เครื่องมือสำหรับแตก (export) และนำเข้า (import) ซับไตเติลจากไฟล์ `.upk` (PC) และ `.xxx` (PS4) ของเกม **Batman: Arkham Knight**

Port มาจากโปรเจกต์ต้นฉบับที่เขียนด้วย C# โดย NoobInCoding พร้อมแก้ไข bug หลายจุดและเพิ่มความสามารถ cross-platform (PC ↔ PS4)

### ความแตกต่างจากของเดิม

- ใช้ **object name เป็น key** ในการ match แทน line number → ไม่มีปัญหา subtitle ผิด slot
- **Import แบบ in-place** แทนการ append ต่อท้ายไฟล์ → ไฟล์ไม่บวมขึ้นโดยไม่จำเป็น
- Output เป็น **JSON** → match key ระหว่าง PC กับ PS4 ได้ตรงๆ
- รองรับ **batch processing** ทั้งโฟลเดอร์
- ตรวจ platform อัตโนมัติจาก magic bytes

### ข้อกำหนดเบื้องต้น

- Python 3.8+
- ไฟล์ต้อง **decompress ก่อน** โดยใช้ [Unreal Package Decompressor](https://www.gildor.org/down/47/umodel/decompress.zip) (by gildor)

### การใช้งาน

**Export** — แตกซับไตเติลออกมาเป็น JSON

```bash
# Export ไฟล์เดียว (default: slot 0 = English)
python batman_ak_subtitle.py export Ace_A1.upk

# Export ทั้งโฟลเดอร์
python batman_ak_subtitle.py export ./pc_files/

# ระบุ slot ภาษา
python batman_ak_subtitle.py export Ace_A1.upk --lang 7   # Japanese
```

**Import** — นำข้อความจาก JSON ใส่กลับไปในไฟล์

```bash
# Import เข้าไฟล์ PS4 (ทับ slot 0 = English)
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json

# Import ทั้งโฟลเดอร์
python batman_ak_subtitle.py import ./ps4_files/ --src ./pc_files/ --dst-lang 0
```

### ตาราง Language Index

| Index | ภาษา |
|-------|------|
| 0 | English (default) |
| 1 | French |
| 2 | Italian |
| 3 | German |
| 4 | Spanish (ES) |
| 5 | Spanish (MX) |
| 6 | Portuguese |
| 7 | Japanese |
| 8 | Korean |
| 9 | Russian |
| 10 | Polish |

### Output

- ไฟล์ export จะถูกบันทึกเป็น `.json` ข้างๆ ไฟล์ต้นฉบับ (หรือชื่อ `exported_subtitles.json` ถ้า export ทั้งโฟลเดอร์)
- ไฟล์ที่ผ่านการ import จะอยู่ในโฟลเดอร์ `<ชื่อโฟลเดอร์>_patched` — **ไม่มีการเขียนทับไฟล์ต้นฉบับ**

---

## English

### About

A tool for exporting and importing subtitles from `.upk` (PC) and `.xxx` (PS4) files in **Batman: Arkham Knight**.

Ported from the original C# project by NoobInCoding, with several bug fixes and added cross-platform support (PC ↔ PS4).

### Differences from the original

- Uses **object name as key** instead of line numbers → no subtitle slot mismatch
- **In-place import** instead of appending data to end of file → no unnecessary file size growth
- **JSON output** → easy key matching between PC and PS4 files
- **Batch processing** support for entire folders
- Auto-detects platform from magic bytes

### Requirements

- Python 3.8+
- Files must be **decompressed first** using [Unreal Package Decompressor](https://www.gildor.org/down/47/umodel/decompress.zip) (by gildor)

### Usage

**Export** — extract subtitles to JSON

```bash
# Export single file (default: slot 0 = English)
python batman_ak_subtitle.py export Ace_A1.upk

# Export entire folder
python batman_ak_subtitle.py export ./pc_files/

# Specify language slot
python batman_ak_subtitle.py export Ace_A1.upk --lang 7   # Japanese
```

**Import** — write text from JSON back into files

```bash
# Import into PS4 file (overwrite slot 0 = English)
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json

# Batch import entire folder
python batman_ak_subtitle.py import ./ps4_files/ --src ./pc_files/ --dst-lang 0
```

### Language Index

| Index | Language |
|-------|----------|
| 0 | English (default) |
| 1 | French |
| 2 | Italian |
| 3 | German |
| 4 | Spanish (ES) |
| 5 | Spanish (MX) |
| 6 | Portuguese |
| 7 | Japanese |
| 8 | Korean |
| 9 | Russian |
| 10 | Polish |

### Output

- Exported files are saved as `.json` next to the source file (or `exported_subtitles.json` for folder exports)
- Imported files are written to a `<folder>_patched` directory — **original files are never overwritten**

---

## Credits

- Original C# tool: [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**
- Thanks to: **fillmsn**, **celikeins**, **cousty**
