# Batman: Arkham Knight Subtitle Tool (Python)

> ⚠️ **Work In Progress** — ยังอยู่ในขั้นตอนพัฒนา / Still under development

Python port of [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**

---

## ภาษาไทย

### เกี่ยวกับโปรเจกต์นี้

เครื่องมือสำหรับแตก (export) และนำเข้า (import) ซับไตเติลจากไฟล์ `.upk` (PC) และ `.xxx` (PS4/Switch) ของเกม **Batman: Arkham Knight** พร้อม script สำหรับ decompress และ recompress ไฟล์

### รองรับทุก Platform

| Platform | นามสกุล | Compression | game_ver |
|----------|---------|-------------|----------|
| PC | `.upk` | LZO1X | -2132606113 |
| PS4 | `.xxx` | LZO1X | -2132606113 |
| Nintendo Switch | `.xxx` | Oodle (Kraken) | -2132606112 |

### ไฟล์ในโปรเจกต์

| ไฟล์ | หน้าที่ |
|------|---------|
| `batman_ak_subtitle.py` | Export / Import ซับไตเติล (ไฟล์หลัก) |
| `decompress_upk.py` | Wrapper สำหรับ decompress (gildor / ooz.exe) |
| `recompress_upk.py` | Recompress ไฟล์กลับเป็นรูปแบบเดิม |

### ข้อกำหนดเบื้องต้น

```bash
pip install python-lzo
# Linux ต้องติดตั้งก่อน: apt install liblzo2-dev
```

**สำหรับ PS4/PC** — ต้องการ gildor's `decompress.exe`:
- ดาวน์โหลด: https://www.gildor.org/down/47/umodel/decompress.zip

**สำหรับ Switch** — ต้องการ `ooz.exe` + `oo2core_7_win64.dll`:
- `ooz.exe`: https://github.com/powzix/ooz/releases
- `oo2core_7_win64.dll`: จากเกม **Warframe** บน Steam (ฟรี)
- วางทั้งสองไฟล์ไว้ด้วยกัน

---

### Workflow สมบูรณ์

**PS4/PC:**
```
1. decompress_upk.py             ← decompress (gildor's tool)
2. batman_ak_subtitle.py export  ← แตกซับไตเติล (PC)
3. batman_ak_subtitle.py import  ← ใส่ซับไตเติล (PS4/PC)
4. recompress_upk.py             ← recompress (LZO1X, ไม่ต้อง tool เพิ่ม)
```

**Nintendo Switch:** ⚠️ WIP
```
1. ooz.exe -d <input.xxx> <output.xxx>   ← decompress (Oodle)
2. batman_ak_subtitle.py export          ← แตกซับไตเติล
3. batman_ak_subtitle.py import          ← ใส่ซับไตเติล
4. ทดสอบด้วยไฟล์ decompressed ก่อน     ← แนะนำ (อาจไม่จำเป็นต้อง recompress)
   หาก recompress จำเป็น:
   recompress_upk.py --ooz ooz.exe       ← recompress (Oodle/Kraken) [WIP]
```

> **หมายเหตุ Switch:** ยังไม่แน่ใจว่าต้อง recompress หรือ set `PKG_CookedForConsole` หรือเปล่า แนะนำให้ทดสอบกับไฟล์ decompressed ก่อน

---

### batman_ak_subtitle.py — Export / Import

**Export** — แตกซับไตเติลออกมาเป็น JSON

```bash
python batman_ak_subtitle.py export Ace_A1.upk
python batman_ak_subtitle.py export ./ps4_files/
python batman_ak_subtitle.py e Ace_A1.xxx --lang 7
```

**Import** — นำข้อความจาก JSON ใส่กลับไปในไฟล์

```bash
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json
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
- Export: `exported_subtitles.json` ข้างๆ ไฟล์/โฟลเดอร์
- Import: โฟลเดอร์ `<ชื่อ>_patched` — ไม่มีการเขียนทับไฟล์ต้นฉบับ

---

### decompress_upk.py — Decompress (PS4/PC)

Wrapper รอบ gildor's `decompress.exe` สำหรับ PS4/PC

```bash
python decompress_upk.py ./ps4_files/
python decompress_upk.py ./ps4_files/ ./ps4_decomp/ --tool tools/decompress.exe
```

> Switch ใช้ `ooz.exe -d <input> <output>` โดยตรงแทน

---

### recompress_upk.py — Recompress

Recompress ไฟล์กลับเป็นรูปแบบเดิมเพื่อให้เกมโหลดได้เร็ว

```bash
# PS4/PC (LZO1X — ไม่ต้อง tool เพิ่ม)
python recompress_upk.py ./ps4_patched/
python recompress_upk.py ./ps4_patched/ ./ps4_final/

# Nintendo Switch (Oodle — ต้อง ooz.exe)
python recompress_upk.py ./switch_patched/ --ooz tools/ooz.exe
python recompress_upk.py ./switch_patched/ ./switch_final/ --ooz ooz.exe
```

---

## English

### About

A tool for exporting and importing subtitles from Batman: Arkham Knight `.upk`/`.xxx` files, with support for PC, PS4, and Nintendo Switch.

### Platform Support

| Platform | Extension | Compression | game_ver |
|----------|-----------|-------------|----------|
| PC | `.upk` | LZO1X | -2132606113 |
| PS4 | `.xxx` | LZO1X | -2132606113 |
| Nintendo Switch | `.xxx` | Oodle (Kraken) | -2132606112 |

### Requirements

```bash
pip install python-lzo           # PS4/PC recompression
# Linux: apt install liblzo2-dev
```

**PS4/PC decompression** — gildor's `decompress.exe`:
- Download: https://www.gildor.org/down/47/umodel/decompress.zip

**Switch decompression/recompression** — `ooz.exe` + `oo2core_7_win64.dll`:
- `ooz.exe`: https://github.com/powzix/ooz/releases
- `oo2core_7_win64.dll`: from **Warframe** on Steam (free)
- Place both files in the same directory

---

### Full Workflow

**PS4/PC:**
```
1. decompress_upk.py            ← decompress (gildor's tool)
2. batman_ak_subtitle.py export ← extract subtitles (PC)
3. batman_ak_subtitle.py import ← insert subtitles (PS4/PC)
4. recompress_upk.py            ← recompress (LZO1X, no extra tools)
```

**Nintendo Switch:** ⚠️ WIP
```
1. ooz.exe -d <input.xxx> <output.xxx>  ← decompress (Oodle)
2. batman_ak_subtitle.py export         ← extract subtitles
3. batman_ak_subtitle.py import         ← insert subtitles
4. Test with the decompressed file first — recompression may not be needed.
   If recompression is required:
   recompress_upk.py --ooz ooz.exe      ← recompress (Oodle/Kraken) [WIP]
```

---

### batman_ak_subtitle.py

```bash
# Export (alias: e)
python batman_ak_subtitle.py export Ace_A1.upk
python batman_ak_subtitle.py export ./files/ --lang 7

# Import (alias: i)
python batman_ak_subtitle.py import Ace_A1.xxx --src Ace_A1.json
python batman_ak_subtitle.py import ./ps4/ --src ./pc/ --dst-lang 0
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

### decompress_upk.py (PS4/PC only)

```bash
python decompress_upk.py ./ps4_files/
python decompress_upk.py ./ps4_files/ --tool tools/decompress.exe
```

### recompress_upk.py

```bash
# PS4/PC
python recompress_upk.py ./ps4_patched/

# Switch
python recompress_upk.py ./switch_patched/ --ooz ooz.exe
```

---

## Technical Notes

**PS4/PC Compression (custom LZO1X)**
- `comp_flag = 0x08`, `block_size = 0x20000`
- `PKG_StoreCompressed` bit restored on recompress
- `PKG_CookedForConsole` (0x20000000) restored after import for PS4 only
- Chunk table at `0x79`: `{uncomp_size, comp_offset, comp_total, cumsum+name_off}` × N

**Switch Compression (Oodle Kraken)**
- `comp_flag = 0x08`, `game_ver = -2132606112`
- Requires `ooz.exe` + `oo2core_7_win64.dll` for recompression
- `PKG_CookedForConsole` is NOT set for Switch files

**Known Limitations**
- Switch decompression must be done with `ooz.exe -d` (not gildor's tool)
- Switch recompression and `PKG_CookedForConsole` behavior are not yet confirmed — test with decompressed files first [WIP]
- Thai subtitle import causing game freeze is under investigation

---

## Credits

- Original C# tool: [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**
- PS4/PC Decompressor: [Unreal Package Decompressor](https://www.gildor.org/down/47/umodel/decompress.zip) by **gildor**
- Switch Decompressor: [ooz](https://github.com/powzix/ooz) by **powzix**
- Thanks to: **fillmsn**, **celikeins**, **cousty**
