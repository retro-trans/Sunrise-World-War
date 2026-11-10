# Text inventory — Sunrise World War (SLPS-25270)

Disc: PS2 DVD, ISO9660 + UDF bridge, 2048-byte sectors. Boot ELF `SLPS_252.70` (full
`.symtab`, 9,038 symbols). Data in CRI AFS archives: `RESOURCE.AFS` (4,861 packs),
`VOICE.AFS`, `MUSIC.AFS`, `MOVIE.AFS`, `MOVIE2.AFS` (audio/video, no text).

Extraction: `py -3.11 tools/extract_text.py --write` (→ `work/source/text/*.json`, local
only). All 44 ATMB tables / 10,165 rows pass byte-identical table and codec round trips.

## Containers

| Layer | Format | Tool |
| --- | --- | --- |
| RESOURCE.AFS | `AFS\0`, count, (offset,size) TOC, data from 0x9800, 2048-aligned, contiguous | `tools/afs.py`, `tools/isobuild.py` |
| Pack (`*.pac`) | header (pack id = pfr id, member count, 0, 0) + chain of member records (rid, data offset, size, record size); data 64-byte aligned, ≥0x20 0xFF header, next record at `(data end & ~15) + 16` | `tools/packs.py` (rebuild verified byte-identical on all 4,861 packs) |
| ATMB | `ATMB`, row count, row offsets, rows | `tools/textcodec.py` |
| ELF pfr table | VA `0x2163F4 + 12*pfr id`: (name ptr, segment id, size). The game reads exactly this size | `tools/build.py` updates it |

Pack names come from the pfr table. The member `rid` is the resource id passed to
`resGetPtr` (e.g. 0x9A7 = machine library, 0x2869 = pilot library, 0x1C87 = battle lines).

## ATMB tables (44)

Japanese characters counted on unique rows, excluding control records.

| Table | Pack | Rows | Bytes | JP chars | Content |
| --- | --- | ---: | ---: | ---: | --- |
| 1271_02471 | deckmenu.pac | 345 | 178,393 | 79,669 | Library: machines (row = mch index; row 0 placeholder) |
| 1271_10345 | deckmenu.pac | 456 | 172,974 | 73,058 | Library: characters (row = chara index; row 0 narrator) |
| 2364_07303 | batlmes.pac | 8,163 | 360,211 | 90,045 | Battle lines (one short line per row) |
| 2364_10331 / 10351 | batlmes.pac | 23 / 60 | 1,065 / 908 | 298 / 120 | Battle event lines / numbered labels |
| 3960_09379 … 4821_10346 | txt_act1 … txt_act13ep | 17 tables, 471 rows | ~1.0 MB | ~231,000 | Story acts 1–13 + epilogue (one scene per row, pages split by blank lines) |
| 4822_10347 … 10736 | txt27_all.pac | 11 tables | ~145 KB | ~41,800 | World-map / faction / alliance events |
| 4857_10740 … 10742 | txt_skp_all.pac | 3 tables | ~59 KB | ~5,100 | Mission-mode texts |
| 4859_10756 | title_01_mes.pac | 157 | 8,527 | 2,518 | Title/Versus character lines |
| 0002_09386 / 10344 | sysdata.pac | 15 / 22 | 1,119 / 4,143 | 258 / 1,477 | System / intro narration |
| 2270_08344 | battle_pac.pac | 1 | 3,392 | 881 | Battle tutorial |
| 2271_06810 | staff_pac.pac | 1 | 11,106 | 5,248 | Staff credits |
| 2368_07367 | dksys_bg03.pac | 26 | 818 | 313 | BGM / song title list (some rows already English) |
| 0093_00349, 0672_*, 1270_02108 | test_mes*.pac | 2 / 9+21 / 3 | | ~16,000 | Test/debug message packs; reachability unverified — documented skip candidates |

Total ≈ 499,000 Japanese characters.

## Control grammar (GetMessagePage 0x113668, windPutText 0x161628)

Line-start header records (before any text on the line): `％`+u16, `＄`+u16, `＆ｖ`+u32+u16
(voice), `＆ｆ`+u16 id+u16 argc+argc×u32 (script function; a page holding one is a
function call). Inline: `＠ｃ`/`＠ｂ`/`＠ｖ`+u16, `＃`+one character (escape). A newline at
line start ends a page, so pages are separated by blank lines. Renderer: `%0`–`%7`
colour, `%R` newline, `%t` tab, `%z[n]` absolute x, `%b[n]` back n px. The codec keeps
all records as `{C:hex}` and other non-text bytes as `{xHH}`.

## ELF text

`tools/elf_strings.py` → `work/source/elf_strings.json`: 6,024 Shift-JIS candidates,
2,875 pointer-referenced (names, menus, help, system messages, 0x2D0000–0x2EFFFF).
Unreferenced hits in 0x216000–0x24C000 are binary false positives; 0x266000–0x2A0000
holds fixed-size name fields inside data tables (deployment names, map locations),
which need per-table handling.

Town/map scripts (v0.3.3, `tools/town_strings.py`): `efile_tbl` (0x226d38) lists 95 script
files in the ELF data area (0x284498-0x2978xx). A string argument is token `00` + NUL-
terminated text; `_exp_func` stores its address in `mdl_str_arg` (0x266128 + 4*i) and steps
over it by `strlen`, so the bytes cannot change. 563 real string arguments, 285 distinct
(`work/source/town_strings.json`; matches not followed by an argument token `18`/`ff` are
false positives), used by: house buttons (`SetHouseInfo`, strcpy into a 32-byte field),
town names (`SetTownName` -> `townName`, char[32]), exits ("To X", `SetTownGroundOutDir`,
32 bytes), and world-map marks (`SetMap*Mark`, pointer kept; label window 10 px per byte).
English: `work/translation/en/town_strings.json`, swapped in at run time by a lookup hook.
`tools/name_tables.py` → `work/source/name_tables.json`: chara 456 (full / display / short
name), mch 345, ship 256, dev 151, skill 34, key items 35.

## Graphics with text

Episode title cards (v0.3.9): sprites 9095-9123 in packs 3704-3732 (one per pack,
320x448, shown 640 wide). World-map briefing labels: 24 maps, 79 labels (v0.3.10, `tools/map_labels.py`).
Done (v0.3.5-v0.3.10): 225 text sprites in packs 0002, 0090, 1271, 1737, 2270, 2274
(`work/translation/gfx/gfx_text.json`). Movies: MOVIE.AFS (599) + MOVIE2.AFS (106), no
name table; names and sizes come from the ELF table at 0x2247E4 (12 bytes: name pointer,
size, 0), in archive order. `emv*` = episode title cards, `cmv*` = cutscenes, `bes_*` =
battle event clips, `openingh` = opening. Video is Sony IPU ("ipum") in MPEG-PS private
stream 1 (sub-header ff c0 video, ff 90 audio), not MPEG-2 video; `tools/ipu.py`
extracts it and ffmpeg 9 decodes it (`-f ipu`). Earlier notes:

Title/menu buttons (`STORY MODE` etc.) are textures that already carry English subtitles.
Other textual graphics (P3TL/PAL_ members) are not inventoried yet. Seen in PCSX2 so far:
episode title cards ("Episode 1 / Universal Century 0093" in Japanese), the copyright
screen, the Story submenu buttons (Prologue / From Episode 1) and the Japanese half of
the title-menu buttons.
