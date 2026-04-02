# Batman: Arkham Knight Subtitle Tool (Python)

> ⚠️ **Work In Progress** — ยังอยู่ในขั้นตอนพัฒนา / Still under development

Python port of [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**

---

## ภาษาไทย

### เกี่ยวกับโปรเจกต์นี้

เครื่องมือสำหรับแตก (export) และนำเข้า (import) ซับไตเติลจากไฟล์ `.upk` (PC) และ `.xxx` (PS4) ของเกม **Batman: Arkham Knight** พร้อม script สำหรับ decompress และ recompress ไฟล์

Port มาจากโปรเจกต์ต้นฉบับที่เขียนด้วย C# โดย NoobInCoding พร้อมแก้ไข bug หลายจุดและเพิ่มความสามารถ cross-platform (PC ↔ PS4)

### ไฟล์ในโปรเจกต์

| ไฟล์ | หน้าที่ |
|------|---------|
| `batman_ak_subtitle.py` | Export / Import ซับไตเติล (ไฟล์หลัก) |
| `decompress_upk.py` | Wrapper สำหรับ gildor's decompress.exe |
| `recompress_upk.py` | Recompress ไฟล์กลับเป็นรูปแบบเดิม (LZO1X) |

### ความแตกต่างจากของเดิม

- ใช้ **object name เป็น key** ในการ match แทน line number → ไม่มีปัญหา subtitle ผิด slot
- **Import แบบ in-place** แทนการ append ต่อท้ายไฟล์
- Output เป็น **JSON** → match key ระหว่าง PC กับ PS4 ได้ตรงๆ
- รองรับ **batch processing** ทั้งโฟลเดอร์
- จัดการ **object name ซ้ำ** ด้วย key `Name#1`, `Name#2` อัตโนมัติ
- ตรวจสอบ **compressed file** และแจ้งเตือนแทนที่จะ crash

### ข้อกำหนดเบื้องต้น

```bash
pip install python-lzo
# Linux ต้องติดตั้งก่อน: apt install liblzo2-dev
```

ต้องการ **gildor's decompress.exe** สำหรับ decompress:
- ดาวน์โหลด: https://www.gildor.org/down/47/umodel/decompress.zip
- วางไว้ในโฟลเดอร์เดียวกับ script หรือระบุ path ด้วย `--tool`

---

### Workflow สมบูรณ์

```
1. decompress_upk.py             ← decompress ไฟล์ต้นฉบับ
2. batman_ak_subtitle.py export  ← แตกซับไตเติล (PC)
3. batman_ak_subtitle.py import  ← ใส่ซับไตเติล (PS4)
4. recompress_upk.py             ← recompress กลับสู่รูปแบบเดิม
```

---

### batman_ak_subtitle.py — Export / Import

**Export** — แตกซับไตเติลออกมาเป็น JSON

```bash
# Export ไฟล์เดียว (default: slot 0 = English)
python batman_ak_subtitle.py export Ace_A1.upk

# Export ทั้งโฟลเดอร์
python batman_ak_subtitle.py export ./pc_files/

# ระบุ slot ภาษา (alias: e)
python batman_ak_subtitle.py e Ace_A1.upk --lang 7
```

**Import** — นำข้อความจาก JSON ใส่กลับไปในไฟล์

```bash
# Import เข้าไฟล์ PS4 (ทับ slot 0 = English)
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json

# Import ทั้งโฟลเดอร์ (alias: i)
python batman_ak_subtitle.py i ./ps4_files/ --src ./pc_files/ --dst-lang 0
```

**ตาราง Language Index**

| Index | ภาษา | Index | ภาษา |
|-------|------|-------|------|
| 0 | English (default) | 6 | Portuguese |
| 1 | French | 7 | Japanese |
| 2 | Italian | 8 | Korean |
| 3 | German | 9 | Russian |
| 4 | Spanish (ES) | 10 | Polish |
| 5 | Spanish (MX) | | |

**Output**
- Export: `.json` ข้างๆ ไฟล์ต้นฉบับ หรือ `exported_subtitles.json` ถ้า export ทั้งโฟลเดอร์
- Import: โฟลเดอร์ `<ชื่อ>_patched` — **ไม่มีการเขียนทับไฟล์ต้นฉบับ**

---

### decompress_upk.py — Decompress

Wrapper รอบ gildor's `decompress.exe` พร้อม auto-detect ว่าไฟล์ compressed หรือเปล่า

```bash
# Decompress ไฟล์เดียว
python decompress_upk.py Ace.xxx

# Decompress ทั้งโฟลเดอร์
python decompress_upk.py ./ps4_files/

# ระบุ output folder
python decompress_upk.py ./ps4_files/ ./ps4_decomp/

# ระบุ path ของ decompress.exe
python decompress_upk.py ./ps4_files/ --tool tools/decompress.exe
```

- ข้ามไฟล์ที่ decompress แล้วโดยอัตโนมัติ
- ข้ามไฟล์ที่ไม่ใช่ UPK/XXX

---

### recompress_upk.py — Recompress

Recompress ไฟล์ที่ผ่านการ decompress กลับเป็นรูปแบบเดิมด้วย LZO1X เพื่อให้เกมโหลดได้เร็ว

```bash
# Recompress ไฟล์เดียว
python recompress_upk.py Ace.xxx

# Recompress ทั้งโฟลเดอร์
python recompress_upk.py ./ps4_patched/

# ระบุ output folder
python recompress_upk.py ./ps4_patched/ ./ps4_final/
```

- ข้ามไฟล์ที่ compressed แล้วโดยอัตโนมัติ
- ข้ามไฟล์ที่ไม่ใช่ UPK/XXX
- ต้องติดตั้ง `python-lzo` ก่อนใช้งาน

---

## English

### About

A tool for exporting and importing subtitles from `.upk` (PC) and `.xxx` (PS4) files in **Batman: Arkham Knight**, plus scripts for decompressing and recompressing package files.

### Files

| File | Purpose |
|------|---------|
| `batman_ak_subtitle.py` | Export / Import subtitles (main tool) |
| `decompress_upk.py` | Wrapper for gildor's decompress.exe |
| `recompress_upk.py` | Recompress files back to original format (LZO1X) |

### Requirements

```bash
pip install python-lzo
# Linux also needs: apt install liblzo2-dev
```

**gildor's decompress.exe** is required for decompression:
- Download: https://www.gildor.org/down/47/umodel/decompress.zip
- Place it in the same folder as the scripts, or specify with `--tool`

---

### Full Workflow

```
1. decompress_upk.py            ← decompress original files
2. batman_ak_subtitle.py export ← extract subtitles (PC)
3. batman_ak_subtitle.py import ← insert subtitles (PS4)
4. recompress_upk.py            ← recompress back to original format
```

---

### batman_ak_subtitle.py — Export / Import

```bash
# Export single file (alias: e)
python batman_ak_subtitle.py export Ace_A1.upk
python batman_ak_subtitle.py export ./pc_files/ --lang 7

# Import single file (alias: i)
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json
python batman_ak_subtitle.py import ./ps4_files/ --src ./pc_files/ --dst-lang 0
```

**Language Index**

| Index | Language | Index | Language |
|-------|----------|-------|----------|
| 0 | English (default) | 6 | Portuguese |
| 1 | French | 7 | Japanese |
| 2 | Italian | 8 | Korean |
| 3 | German | 9 | Russian |
| 4 | Spanish (ES) | 10 | Polish |
| 5 | Spanish (MX) | | |

### decompress_upk.py — Decompress

```bash
python decompress_upk.py ./ps4_files/
python decompress_upk.py ./ps4_files/ ./ps4_decomp/ --tool tools/decompress.exe
```

### recompress_upk.py — Recompress

```bash
python recompress_upk.py ./ps4_patched/
python recompress_upk.py ./ps4_patched/ ./ps4_final/
```

---

## Technical Notes

**File Format**
- PC uses `.upk`, PS4 uses `.xxx` — same binary format, different extension
- Magic: `0x9E2A83C1`, game version: `-2132606113`
- Must be decompressed before editing

**Compression (Batman AK custom LZO1X)**
- `comp_flag = 0x08`, block size: `0x20000`
- `PKG_StoreCompressed` bit set in `pkg_flags`
- Chunk table at `0x79`: `{uncomp_size, comp_offset, comp_total, cumsum+name_off}` × N

**Known Limitations**
- Recompressed files may have slight stutter (LZO vs original compression ratio)
- Thai subtitle import causing game freeze is under investigation

---

## Credits

- Original C# tool: [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**
- Decompressor: [Unreal Package Decompressor](https://www.gildor.org/down/47/umodel/decompress.zip) by **gildor**
- Thanks to: **fillmsn**, **celikeins**, **cousty**
