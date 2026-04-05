# Batman: Arkham Knight Subtitle Tool (Python)

> ⚠️ **Work In Progress** — ยังอยู่ในขั้นตอนพัฒนา / Still under development

Python port of [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**

---

## ภาษาไทย

### เกี่ยวกับโปรเจกต์นี้

เครื่องมือสำหรับแตก (export) และนำเข้า (import) ซับไตเติลจากไฟล์ `.upk` (PC) และ `.xxx` (PS4/Switch) ของเกม **Batman: Arkham Knight** พร้อม script สำหรับ decompress และ recompress ไฟล์

---

### Platform Support

| Platform | นามสกุล | Compression | game_ver | PKG_CookedForConsole |
|----------|---------|-------------|----------|----------------------|
| PC | `.upk` | LZO1X | -2132606113 | ✗ |
| PS4 | `.xxx` | LZO1X | -2132606113 | ✓ (tool set ให้อัตโนมัติ) |
| Nintendo Switch | `.xxx` | Oodle (Kraken) | -2132606112 | ❓ (ยังไม่ยืนยัน) |

---

### ไฟล์ในโปรเจกต์

| ไฟล์ | หน้าที่ | สถานะ |
|------|---------|-------|
| `batman_ak_subtitle.py` | Export / Import ซับไตเติล (ไฟล์หลัก) | ✅ พร้อมใช้ |
| `decompress_upk.py` | Wrapper สำหรับ decompress | ✅ พร้อมใช้ |
| `recompress_upk.py` | Recompress ไฟล์กลับเป็นรูปแบบเดิม | ⚠️ Switch WIP |

---

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
2. batman_ak_subtitle.py export  ← แตกซับไตเติล (จาก PC files)
3. batman_ak_subtitle.py import  ← ใส่ซับไตเติล (PS4/PC)
4. recompress_upk.py             ← recompress (LZO1X, ไม่ต้อง tool เพิ่ม)
```

**Nintendo Switch:** ⚠️ WIP
```
1. ooz.exe -d <input.xxx> <output.xxx>   ← decompress (Oodle)
2. batman_ak_subtitle.py export          ← แตกซับไตเติล
3. batman_ak_subtitle.py import          ← ใส่ซับไตเติล
4. ทดสอบด้วยไฟล์ decompressed ก่อน     ← แนะนำ
   หาก recompress จำเป็น:
   recompress_upk.py --ooz ooz.exe       ← [WIP]
```

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
- Export → `exported_subtitles.json` ข้างๆ ไฟล์/โฟลเดอร์
- Import → โฟลเดอร์ `<ชื่อ>_patched` — ไม่มีการเขียนทับไฟล์ต้นฉบับ

---

### decompress_upk.py — Decompress (PS4/PC)

Wrapper รอบ gildor's `decompress.exe` สำหรับ PS4/PC

```bash
python decompress_upk.py ./ps4_files/
python decompress_upk.py ./ps4_files/ ./ps4_decomp/ --tool tools/decompress.exe
```

> Switch ใช้ `ooz.exe -d <input> <o>` โดยตรงแทน

---

### recompress_upk.py — Recompress

Recompress ไฟล์กลับเป็นรูปแบบเดิมเพื่อให้เกมโหลดได้เร็ว

```bash
# PS4/PC (LZO1X — ไม่ต้อง tool เพิ่ม)
python recompress_upk.py ./ps4_patched/
python recompress_upk.py ./ps4_patched/ ./ps4_final/

# Nintendo Switch (Oodle — ต้อง ooz.exe) [WIP]
python recompress_upk.py ./switch_patched/ --ooz tools/ooz.exe
```

---

### ⚠️ ข้อควรระวัง

#### 1. ต้อง Decompress ก่อนเสมอ
ไฟล์ `.upk` / `.xxx` จากเกมจะอยู่ในรูปแบบ compressed — ต้อง decompress ก่อนทุกครั้งก่อนใช้ tool นี้
- PS4/PC → ใช้ `decompress_upk.py` (gildor's decompress.exe)
- Switch → ใช้ `ooz.exe -d input.xxx output.xxx`

#### 2. PKG_CookedForConsole (PS4 เท่านั้น)
`gildor's decompress.exe` จะล้าง bit `PKG_CookedForConsole` (0x20000000) ออกจาก pkg_flags — ถ้าไม่ restore ไว้จะทำให้เกมกระตุกทุก ~4 วินาที

**tool นี้ restore bit ให้อัตโนมัติ** ตอน import สำหรับ PS4 `.xxx` เท่านั้น (ไม่แตะ PC และ Switch)

#### 3. gildor's tool กับ Batman AK (LZO unsafe)
Batman AK ใช้ `lzo1x_decompress` (unsafe mode) ซึ่ง `python-lzo` ไม่รองรับ — ถ้า decompress เองด้วย Python โดยตรงจะ fail บางบล็อก ให้ใช้ `gildor's decompress.exe` แทน

#### 4. Switch — ยังไม่ได้ทดสอบ Recompress
Switch recompress ยัง **WIP** — แนะนำให้ทดสอบด้วยไฟล์ decompressed ก่อนที่จะ recompress กลับ
- `PKG_CookedForConsole` บน Switch ยังไม่ confirmed
- Oodle recompress format อาจไม่ตรงกับ original 100%

#### 5. ไฟล์ compressed ปนใน folder
ถ้า folder มีไฟล์ compressed ปนอยู่ (ยังไม่ได้ decompress) tool จะแสดง `[SKIP]` และข้ามไปโดยอัตโนมัติ ไม่ crash

---

## English

### About

A tool for exporting and importing subtitles from Batman: Arkham Knight `.upk`/`.xxx` files, with support for PC, PS4, and Nintendo Switch.

---

### Platform Support

| Platform | Extension | Compression | game_ver | PKG_CookedForConsole |
|----------|-----------|-------------|----------|----------------------|
| PC | `.upk` | LZO1X | -2132606113 | ✗ |
| PS4 | `.xxx` | LZO1X | -2132606113 | ✓ (auto-restored on import) |
| Nintendo Switch | `.xxx` | Oodle (Kraken) | -2132606112 | ❓ (unconfirmed) |

---

### Files

| File | Purpose | Status |
|------|---------|--------|
| `batman_ak_subtitle.py` | Export / Import subtitles (main tool) | ✅ Ready |
| `decompress_upk.py` | Decompress wrapper | ✅ Ready |
| `recompress_upk.py` | Recompress back to original format | ⚠️ Switch WIP |

---

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
2. batman_ak_subtitle.py export ← extract subtitles (from PC files)
3. batman_ak_subtitle.py import ← insert subtitles (PS4/PC)
4. recompress_upk.py            ← recompress (LZO1X, no extra tools needed)
```

**Nintendo Switch:** ⚠️ WIP
```
1. ooz.exe -d <input.xxx> <output.xxx>  ← decompress (Oodle)
2. batman_ak_subtitle.py export         ← extract subtitles
3. batman_ak_subtitle.py import         ← insert subtitles
4. Test with the decompressed file first (recompression may not be needed)
   If recompression is required:
   recompress_upk.py --ooz ooz.exe      ← [WIP]
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

---

### decompress_upk.py

```bash
python decompress_upk.py ./ps4_files/
python decompress_upk.py ./ps4_files/ ./out/ --tool tools/decompress.exe
```

> Switch: use `ooz.exe -d <input> <o>` directly instead.

---

### recompress_upk.py

```bash
# PS4/PC (LZO1X — no extra tools)
python recompress_upk.py ./ps4_patched/
python recompress_upk.py ./ps4_patched/ ./ps4_final/

# Switch (Oodle — requires ooz.exe) [WIP]
python recompress_upk.py ./switch_patched/ --ooz ooz.exe
```

---

### ⚠️ Warnings & Known Issues

#### 1. Files must be decompressed first
All `.upk` / `.xxx` files from the game are compressed. Always decompress before using this tool.
- PS4/PC → use `decompress_upk.py` (wraps gildor's decompress.exe)
- Switch → use `ooz.exe -d input.xxx output.xxx`

#### 2. PKG_CookedForConsole (PS4 only)
`gildor's decompress.exe` clears the `PKG_CookedForConsole` bit (0x20000000) from `pkg_flags`. Without it the game stutters every ~4 seconds.

**This tool automatically restores the bit on import** for PS4 `.xxx` files. It does not touch PC or Switch files.

#### 3. LZO unsafe mode (Batman AK quirk)
Batman AK uses `lzo1x_decompress` (unsafe) which `python-lzo` does not support — pure-Python decompression will fail on some blocks. Always use gildor's `decompress.exe` for decompression.
> Source: `UEViewer/Unreal/UnCoreCompression.cpp` — *"This situation is unusual for UE3, it happened with Alice, and Batman 3"*

#### 4. Switch recompression is WIP
Switch recompression (`recompress_upk.py --ooz`) is **experimental and untested in-game**.
- `PKG_CookedForConsole` behavior on Switch is unconfirmed
- Oodle recompress format may not exactly match the original
- Test with the decompressed file first before recompressing

#### 5. Compressed files mixed in folder
If a folder contains a mix of compressed and decompressed files, the tool will print `[SKIP]` and skip invalid files automatically — it will not crash.

---

## WIP Status

| Feature | Status | Notes |
|---------|--------|-------|
| PC export/import | ✅ Done | Fully working |
| PS4 export/import | ✅ Done | PKG_CookedForConsole auto-restored |
| PS4/PC recompress (LZO1X) | ✅ Done | No extra tools needed |
| Switch decompress | ✅ Done | Via `ooz.exe -d` |
| Switch import | ✅ Done | Decompressed files only |
| Switch recompress (Oodle) | ⚠️ WIP | Experimental, not verified in-game |
| Switch PKG_CookedForConsole | ❓ Unknown | Not yet tested |
| Thai subtitle lag/freeze | 🔍 Investigating | Binary verified OK; root cause TBD |

---

## Technical Notes

**UPK Binary Format (Batman AK / RSS branch)**
- Build `863/32995` (LicenseeVersion = 32995), game_ver = `-2132606113`
- Export table: contains extra int32 after ArchetypeIndex (RSS-specific)
- `pkg_flags` offset is **not hardcoded** — parsed dynamically from None-string position
- Property tags use `DeserializeTagByOffset()` format (int16 type + uint16 offset)

**PS4/PC Compression (custom LZO1X)**
- `comp_flag = 0x08`, `block_size = 0x20000`
- Chunk table at `0x79`: `{uncomp_size, comp_offset, comp_total, cumsum+name_off}` × N
- `PKG_StoreCompressed` bit restored on recompress

**Switch Compression (Oodle Kraken)**
- `comp_flag = 0x08`, `game_ver = -2132606112`
- Requires `ooz.exe` + `oo2core_7_win64.dll` for recompression

---

## Credits

- Original C# tool: [BatmanAK-SubtitleTool](https://github.com/rm-NoobInCoding/BatmanAK-SubtitleTool) by **NoobInCoding**
- PS4/PC Decompressor: [Unreal Package Decompressor](https://www.gildor.org/down/47/umodel/decompress.zip) by **gildor**
- Switch Decompressor: [ooz](https://github.com/powzix/ooz) by **powzix**
- UE3 format reference: [UE-Explorer/UELib](https://github.com/UE-Explorer/UE-Explorer) by **EliotVU**
- Thanks to: **fillmsn**, **celikeins**, **cousty**
