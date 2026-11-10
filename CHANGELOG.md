# Changelog

Local builds and release packages are under `work/output/v<version>/`.

## Repository preview — 2026-11-10

- Used the [original Japanese PS2 front cover](https://gamesdb.launchbox-app.com/games/images/130937-sunrise-world-war) as the README preview.

## v0.8.0 — 2026-11-10 — First private release package

- Packaged the v0.3.20 test build as an xdelta patch for the original Japanese
  SLPS-25270 disc. See the [release notes](docs/releases/v0.8.0.md) for patching,
  coverage, and verification details.

## v0.3.20 — 2026-11-10 — Opening subtitle spacing

- Lowered the English line of “Destination” by 12 pixels at native resolution
  to give the romaji and English subtitles more room.

## v0.3.19 — 2026-11-10 — Romaji opening subtitles

- Added romaji above the English translation for the Japanese lines of
  “Destination,” using the existing Whisper cue timings. The lines sung in
  English appear once.
- Exported a matching English and romaji SRT. The original movie and audio
  remain intact.

## v0.3.18 — 2026-11-10 — Opening song subtitles

- Added 19 English subtitle cues to the opening movie for “Destination.” Used
  Whisper large-v3 for Japanese transcription, timing, and a draft translation,
  then reviewed and edited the English cues against the transcription.
- Added the cues to the movie player and exported the same cue sheet as an SRT.
  The original movie and audio are preserved in the disc image.

## Repository setup — 2026-11-10

- Added a project README, an ACE-style social preview and a disc preparation tool.
- Added the metadata needed to restore editable drafts from the English-only copies.

## v0.3.17 — 2026-11-10 — Equipment and Ship Info badges, Junk item name

- Replaced Equip (square item icon), Foe Units, For Ships, Use, Foe Ships,
  Built-in, and Standard with direct ImageGen edits. Verified the seven encoded
  sprites in RESOURCE pack 0002. The set now has 42 direct ImageGen sprites
  out of 269 localized sprites.
- Translated the Item Info list's half-width short name at 0x2eceb8 to Junk.
  The footer uses its full display name, Junk Parts. Verified the list's
  string and all seven sprite payloads in the packed test ISO.

## v0.3.16 — 2026-11-10 — Direct ImageGen battle-panel badges

- Replaced SP (space), GR (ground), AIR and EX with direct ImageGen edits
  based on the battle-panel screenshots, using the original sprite dimensions
  and palettes. Removed visible fragments of the Japanese lettering.
- Identified the red EX icon left of the unit type. The Japanese sprite says
  専, short for 専用 (exclusive). The battle panel draws it when the machine's
  designated-pilot field is set. The EN Cost plate already had a direct
  ImageGen edit in v0.3.15.
- Verified all four replacements in the packed ISO and at native texture
  size. There are 35 direct ImageGen sprites out of 269 localized sprites.

## v0.3.15 — 2026-11-10 — Direct ImageGen edits for Info screens

- Replaced the text on the Info menu and Pilot Info screen with direct ImageGen
  edits of the attached game screenshots. Installed 22 sprites, including four
  matching detail headers. The 269 localized sprites now include 31 direct image
  assets. The other 238 sprites still use generated letterforms.
- Own Unit (6917) had old dark outline pixels at its bevel. Support (6916) had
  old green strokes along the top and bottom. Both badges were replaced with
  clean ImageGen crops at their original sprite dimensions.
- Preserved the original texture layouts and the lower part of the EN Cost
  plate where the game draws the number. The generated frames and lettering
  differ slightly from the source. Verified all 22 encoded sprites inside the
  local test ISO. The replacement screens were reviewed in decoded previews.

## v0.3.14 — 2026-11-10 — ImageGen lettering for embedded graphics

- Replaced the lettering on all 241 previously localized sprites and added 28 sprites
  found in the RESOURCE audit. The sprite specification now contains 269 sprites and
  374 text placements. The title and Story submenu use direct ImageGen edits. Other
  labels use English wording composed from the generated letterforms, with the original
  sprite bounds, layout and palette handling.
- Newly localized artwork includes Versus menus, copyright credits, nine logo variants,
  two placeholder icons and nine tactical map sprites. The copyright screen preserves
  its original copyright marks. The maps use the existing Zakaal and Astante spellings.
  Kaisar Pass and Madaskas Island are transliterations from the artwork.
- Small or cropped tactical labels on sprites 8955, 8957 and 8962 need a clearer
  source. The audit sampled several common portrait shapes. Full movie-frame and
  model-texture coverage remains unverified.

## v0.3.13 — 2026-11-10 — full test ISO: squad names, list font redone

- Squad names: the 160 names in the squad table (saga3_ene_deck_data, char[24] at +4 of
  each 312-byte entry) translated (`work/translation/en/deck_names.json`,
  `tools/deck_names.py`). Id 2 is the player's starting squad: "1st Mech Squad". The name
  is copied into the save when a game starts, so saves made with earlier builds keep
  "第1機動部隊" (rename it in Squads, or start a new game).
- Fix: the default name of a new squad was "New Squad", but deckInitDeckName copies
  exactly 9 bytes (8 characters + NUL), so the name had no terminator. Now "Untitled".
- List font redone (10x14 ANK): Lucida Console 13 px, bold, with a drop shadow and outline,
  at the original glyph metrics (caps on rows 2-10). The v0.3.12 glyphs were 2 rows taller:
  lines touched in the Unit Info list and the battle panel cut off the bottom of "FT" /
  "Lv36". The game's symbol glyphs on ; < > \ ^ ` { | } ~ are kept.
- Correction to v0.3.12: the original Latin glyphs were not scrambled; they are a squared
  design. The scrambled look came from the first replacement being written in the wrong
  nibble order.
- Verified in PCSX2: Unit Info list (Cloud Saber, Jegan, GM III, Dragonar-1 C...) and the
  "FT Lv40" / "CAP Lv60" / "GT Lv30" labels fully visible; v0.3.13 boots to the title. Not
  seen: the starting squad name on a new save. New savestate: Prologue free play
  (`work/emulator/states/v0.3.13_prologue_freeplay.p2s`).

## v0.3.12 — 2026-11-06 — full test ISO: list font, config screens

- List font fixed (unit / pilot / weapon / skill lists, 10x14 ANK font at 0x250F78): the
  game stores these glyphs high-nibble-first, so letters drawn from data read the other
  way showed every pixel pair swapped. ASCII 0x20-0x7F are now rebuilt from the game's own
  clean 10x16 font, with outline and shade levels like the originals; "l" drawn as a plain
  stem so it no longer reads as "1" (`tools/ank_font.py`). Half-width kana unchanged.
- Config buttons (pack 2307), all one size: Reset to Default, Battle Messages, Icon
  Gauges, Vibration, Launch Scenes, Grid Points; also Battlefield, Save, Back to Title,
  Continue, Start Battle (Versus) and the "Play Sample" label.
- Verified in PCSX2: v0.3.12 fresh boot, Sound Config / Battle Config / Vibration screens
  in English; dev build in the Prologue battle, unit list "GT-A Assault / GT-B Backup" in
  the clean font.

## v0.3.11 — 2026-11-06 — full test ISO: equipment/skill names, even button sizes

- 402 more short names (field +8, half-width kana): special skills/attacks (227),
  equipment (151), skills (24); shown in the battle weapon and support/attack lists
  ("Beam Cannon Lv3", "Maintenance 1", "Ultimate Storm", "Rest", "Shield Lv2"...). Cells
  hold 14 / 13 / 11 bytes; long names abbreviated (`tools/short_names_equip.py`).
- Button text sizes: sprites of one menu now share one font size (long words squeezed
  horizontally): battle commands (Launch / Move / Support / Wait / Land / Fly...), ship
  menu, submenus, tags, panel labels (`tools/gfx_text.py` group sizing; `group` option).
- "EN Cost" plate: text in the top band only, at the original size and colours; the game
  draws the number below it.
- Gallery: "Gallery 1-3" headers and the Gallery banner (pack 2369).
- Verified in PCSX2 (dev build, fresh boot, Prologue battle): Launch/Move/Support/Wait and
  Land/Fly at one size; unit panel with the new EN Cost; unit list "GT-A Assault / GT-B
  Backup". Not seen yet: weapon and support lists with the new names (tutorial blocked
  the route), gallery headers. Savestates kept in `work/emulator/states/`.
- Open: the small badge drawn over the bottom-left of some pilot portraits (Kanji, Kaine;
  not the Claudian soldier) is not identified yet.

## v0.3.10 — 2026-11-04 — full test ISO: world-map briefing labels in English

- 24 briefing maps (sprites 9000-9020, 9155-9160; packs 3609-3629, 3764-3769), 79
  labels: Claudia campaign maps (Alex Port, Fiex Peninsula, Arid Zone / Breadbasket /
  Cold Zone, Monak, Astante Fortress, Nargou Region, Cecil Island, Cecibel Base, Taruk
  Peninsula / 3rd Army Base) and the Terra Realm maps (Terra Realm Map, Asia, Gaia,
  Pentagona, Iberia, Byston Well, Grados Supply Line, Paradigm City, North Base, Hoshimi
  (GEAR HQ), East Base (Resistance Base), Bazaar Point, Cusco, Grados City).
- `tools/map_labels.py`: each label is defined once and found on every map by template
  matching (score >= 0.85), so repeated and greyed-out copies are handled. Greyed labels
  keep their dim colours; current ones use the game's cream. `write` regenerates the map
  rows of `work/translation/gfx/gfx_text.json`.
- `tools/gfx_text.py`: `labels` (several texts per sprite), `plate_tint` (rebuild a
  translucent label plate), `protect` (keep location markers inside a box).
- New names chosen here (no dialogue spelling exists): Fiex Peninsula, Nargou Region,
  Cecil Island, Taruk Peninsula. Flagged for the accuracy reviewers.
- Verified: preview of every map (before/after). In PCSX2 (v0.3.10, fresh boot): the
  Prologue title card in English; the briefing maps themselves not yet reached in game
  (same image format and packs as the verified episode cards).

## v0.3.9 — 2026-11-04 — full test ISO: episode title cards in English

- Correction to v0.3.8: the episode title cards are not movies. They are 320x448 sprites
  shown twice as wide (packs 3704-3717 and 3732, members 9095-9108 / 9123: Prologue,
  Episodes 1-13, Epilogue; packs 3718-3729, members 9109-9120: the 12 Mission Mode
  chapter cards). Found by scanning the card-state RAM for image blocks.
- All 27 cards redrawn: story cards use the existing English titles ("Episode 1 /
  Universal Century 0093"); Mission Mode chapters translated here ("Omens of Battle", "The
  Jet-Black Sea", ... "Death Struggle at Zaxel"; `work/translation/gfx/gfx_text.json`).
- `tools/gfx_text.py`: `hstretch` (draw for the stretched display), `shadow` (erase the
  drop shadow), `line_align`, `gap`, `keep_palette` (pictures keep their own palette and
  pixels; only changed pixels are remapped; the title buttons use it too).
- `tools/ipu.py`: lists the 705 movies and extracts the IPU video stream (private stream 1,
  sub-header ff c0 = video, ff 90 = audio); ffmpeg 9 decodes it (`-f ipu`). Movies have no
  text found so far; no encoder was needed.
- `tools/gfx_find.py` probes a varied window, so mostly dark images are found.
- Verified in PCSX2 (dev build, fresh boot): the Episode 1 card shows "Episode 1 /
  Universal Century 0093" with correct proportions through its fade. v0.3.9 boots to the
  English title menu. Other cards checked in the preview only.
- Still Japanese (done in v0.3.10): world-map sprites with place labels.

## v0.3.8 — 2026-11-04 — full test ISO: title menu in English

- Title menu buttons (Story, Mission, Load, Versus, Gallery; the English subtitles kept)
  and the Story submenu (Prologue, From Episode 1, Epilogue) redrawn: pack 0090. The
  artwork under the Japanese is rebuilt by inpainting (OpenCV, `bg: "inpaint"` in
  `tools/gfx_text.py`), the English uses the original gradient and outline.
- Fix: dev builds (`--dev`) only rewrote packs with AFS slack, so graphics changes in
  packs 0090, 1737 and 2274 were missing from dev ISOs (full ISOs had them). Dev builds
  now also rewrite every changed pack that fits its slot.
- Verified in PCSX2: title menu and Story submenu (dev v0.3.7); v0.3.8 shows the English
  title menu.
- (Wrong, see v0.3.9) Found: episode title cards ("Episode 1 / U.C. 0093") are movies: 17 `emv*.pss` in
  MOVIE2.AFS (705 movies in MOVIE.AFS + MOVIE2.AFS, names from the table at 0x2247E4).
  They are Sony IPU streams ("ipum" in private stream 1), which ffmpeg cannot decode;
  changing them needs an IPU decoder/encoder. Not done. The SWW logo (katakana reading,
  "From サンライズ英雄譚") is left as the game's logo.

## v0.3.6 — 2026-11-04 — full test ISO: short names in English

- 892 short ("omit") names of characters, units and ships (name tables field +8, half-
  width kana) translated: unit / pilot / ship lists, shop, battle select, battle labels.
  693 come from the display or full English name (or the matching name word, titles
  dropped), 199 were abbreviated by hand ("Fed. Sold.1", "Deathscythe H", "Grados Shuttle")
  to fit the fixed-width list cells: characters 11, units 16, ships 14 bytes
  (`tools/short_names.py`).
- Ship panel: "ﾁｬｰｼﾞ" after "EN" -> "Regen" (5 cells; "Charge" was cut); the "Units" and
  "Equip" labels are drawn narrower so two-digit counts no longer run into them.
- Safety: the string builder no longer moves a `.sdata` string that code reaches gp-
  relative (that reference cannot be rewritten); none of the current strings needed it.
- Verified in PCSX2 (dev build, fresh boot): Unit Info list (Cloud Saber, Jegan, GM III,
  Dragonar-1 C...), Pilot Info list (Kanji, Amuro, Fed. Offcr1, LB Pilot 1...), Ship Info
  list (Salamis-class), memory-card format prompt fully English. v0.3.6 boots to the title.
  Not seen yet: the Regen label and narrowed labels in place, shop and battle-select lists.

## v0.3.5 — 2026-11-04 — full test ISO: menu and battle graphics in English

- 166 text sprites redrawn in English (`work/translation/gfx/gfx_text.json`,
  `tools/gfx_text.py`; packs 0002, 1271, 1737, 2270, 2274): ship menu, Squads / Shop /
  Info / Config submenus, list tabs and labels, memory-card slots, battle commands
  (Launch / Move / Support / Wait...), unit panel (Onboard, Units, Equip, Command, Max
  Sortie, Move, Size, EN Cost, SP/GR/AIR), target/range tags, results bonuses, training
  screens, world-map realm/continent banners, Critical Attack / Talent Activated banners.
  Sprites keep their size, pieces and palette size (requantised).
- Two memory-card messages the string catalogue had missed (0x27F858, `mcout_mes`).
- Tools: `tools/gfx.py` (P3TL/P3TX textures; PAL_/IMG_/CEL_ sprites, composed from their
  cells), `tools/gfx_find.py` (members loaded in a savestate), `tools/gfx_gallery.py`,
  `tools/dbg/gfx_hot.py` (write redrawn sprites into a running game).
- Verified in PCSX2 (dev v0.3.4, fresh boot): ship menu; RAM preview: Info submenu, unit
  info screen, memory-card slots; fresh boot: combat drill launch menu and unit panel.
  v0.3.5 itself built but not booted.
- Still Japanese (short names fixed in v0.3.6): unit/character/ship short names (~890
  strings: unit lists, battle labels); "ENﾁｬｰｼﾞ" (0x2DD368); title-menu buttons and episode
  title cards (large P3TL textures).

## v0.3.4 — 2026-11-04 (dev)

- First sprite build (v0.3.3 + graphics); tested by fresh boot.

## v0.3.3 — 2026-11-04 — full test ISO: town screens in English

- Town and world-map script text translated: 285 distinct strings (563 uses) from the 95
  town/map scripts: location buttons, town names, "To X" exits, map marks
  (`work/translation/en/town_strings.json`, `tools/town_strings.py`). The scripts step over
  each string by its length, so the bytes stay; a hook in the script argument parser
  (`_exp_func` 0x17FB14 -> 0x210700) looks the text up (djb2 hash, binary search, 2,280-byte
  table) and passes the English instead. English strings go to free executable space.
- Location buttons are right-aligned on their pixel width (they assumed 11 px per byte).
- Fix (present since v0.1.7): the executable-string builder treated zeros after a string
  in writable `.data`/`.sdata` as free space. It had put "Cima Fleet Officer" inside the
  32-byte `townName` buffer (overwritten by any town name over 12 characters) and
  "Poseidal Regular Army Soldier" over the script interpreter's token byte. Strings in
  writable sections now keep their own size (`townName` 32; `.sdata` literals up to the
  next referenced address) and lend no space. Two strings shortened to fit: "Switch"
  (乗換), "No details" (詳細不明).
- Spelling: "Kingdom of A", lowercase "gate" on map labels (project style sheet).
- Verified in PCSX2 (dev build v0.3.2, fresh boot): Side 1 Londenion town screen. Town
  name, current place and every button are in English; moving between places, going back
  to the ship and returning to town all work; moved strings intact in RAM. v0.3.3 boots to
  the title. Not yet seen on screen: world-map marks and exits.
- Found: battle unit panel labels (搭載, 機体, 装備, 指揮, 最大出撃数, 移動, ENチャージ) and the
  ship menu (外出, 部隊, ショップ, 情報, 設定, セーブ, 出港) are graphics, not executable text.
- Tooling: `tools/dbg/hotpatch.py` writes a newer build's executable changes into a running
  game; town-screen route in `docs/debug_tools.md`.

## v0.3.2 — 2026-11-04 (dev)

- v0.3.1 plus the writable-section fix and pixel-width button alignment.

## v0.3.1 — 2026-11-04 (dev)

- First town-string hook build; tested by hot patch into a v0.3.0 savestate.

## v0.3.0 — 2026-11-01 — full test ISO: reviewed script (accuracy, editorial, proofread)

- All three BASE_RULES review stages run over the library, every dialogue table and the
  non-name executable strings (98 units, `tools/review.py`): accuracy 376 edits / 912 flags,
  editorial 1,411 edits / 361 flags, proofread 160 edits / 180 flags; 24,500+ items examined
  per stage. Reports: `docs/review_accuracy.md`, `docs/review_editorial.md`,
  `docs/review_proofread.md`. Draft status is now `proofread` on every reviewed row.
- Scripted passes between stages: rank ladder (Ensign / Lieutenant JG / Lieutenant / Major /
  Lieutenant Colonel / Colonel), Rie's "Lun", style sheet (stutter capitals, "?!", "All right",
  punctuation inside quotes), "/" and literal "
" line-break defects fixed (401 pages) and
  now rejected by the checkers, 40+ new spelling decisions in `term_fixes.json` (now matching
  names split across line breaks).
- 18 executable strings the reference scanner had missed (no data/code pointer found, e.g.
  "Save complete.", "End Squad Setup?", " will be unlocked.") translated in place.
- Verified in PCSX2: boots, story-select line, English UI in a town screen. Found: town
  location buttons are still Japanese -- they are inline strings in town-script bytecode
  (0x266000-0x2A0000, ~700 distinct) and cannot change length; needs a runtime lookup hook.

- Owner decision: 大尉 = "Lieutenant" (Amuro; same rank for Kanji, Quattro, Min): 40 lines.
- Delegated decisions: 勇 (Brain Powerd) "You" -> "Yu" (Yu Isami, Yu Brain); ポセイダル様 ->
  "Lord Poseidal"; 勇者特急隊 -> "the Brave Express Team". Applied via
  `work/glossary/term_fixes.json` and the glossary research file.

## v0.2.2 — 2026-11-01 — full test ISO: every script table in English (draft)

- Same text as v0.2.0, plus two renderer fixes found in PCSX2:
  - Dialogue typewriter (`TextWaitPutProc`) replaced each ASCII space with the string at
    0x2ED4D0 (two half-width "｡", blank in the Japanese font), so English spaces showed
    as two small rings and were ~30 px wide. The string is now a plain space.
  - Location captions (`telopMainProcess`) drew two bytes per fixed 26 px cell, centred
    on 27 px per pair and dropped the last byte of odd-length text ("L ondeni on"
    Spacepor). Captions are now measured in pixels (26px widths) and each step redraws
    the growing prefix proportionally (`tools/vwf.py` TELOP_W / TELOP_DRAW).
- Verified in PCSX2: title/story-select voice line, first story scene dialogue, location
  caption spacing and centring (dev build v0.2.1 and replayed state). Not yet seen on
  screen: choice menus, staff credits, battle lines, BGM titles, mission mode.

## v0.2.1 — 2026-11-01 (dev)

- Dev ISO with the space and caption fixes (caption width was measured with the wrong
  font type; fixed before v0.2.2).

## v0.2.0 — 2026-11-01 — dialogue draft (superseded by v0.2.2)

- All dialogue translated by 51 slice translators (86 slices): story acts 1–13 and
  epilogue, world-map/faction events, battle lines (8,163 rows), mission mode,
  title/versus lines, system text, battle tutorial, staff credits, BGM titles, test packs.
  Script tables: 100% of 444,540 Japanese characters have English; 9,815 rows built,
  0 layout problems (3 lines x 468 px per page). **Draft stage**: the BASE_RULES
  accuracy, editorial and proofreading passes have not run.
- Tooling: `slices.py check` validates dialogue slices (segment count, ASCII, page fit,
  control order); `slices.py speakers` labels each segment with the speaking character
  (page header ＄/％ + u16, low 10 bits = chara index); speaker sheets with glossary
  gender/personality; `term_fixes.py` also fixes dialogue segments; `strip_jp.py` strips
  segment Japanese and Japanese quoted in notes.
- 33 cross-slice spelling decisions added to `work/glossary/term_fixes.json`; canon
  genders for 11 well-known characters (`work/glossary/research_dialogue_gender.json`).
- Known bugs (fixed in v0.2.2): spaces in dialogue drawn as two rings; captions spaced
  in pairs.

## v0.1.9 — 2026-10-31 — first full test ISO with the English library and UI

- Full ISO (not dev): same content as v0.1.8, without the library preview hook.
- Text: all 801 library entries (456 characters, 345 machines/units) drafted by ten
  slice translators, 0 layout problems; 2,462 executable strings (names from the
  glossary, menus, help, battle captions, special attacks, items, skills, memory card).
  Library and executable strings are **draft stage**: accuracy, editorial and
  proofreading passes are still to do. Story, battle and event dialogue remain Japanese.

## v0.1.8 — 2026-10-31 (dev)

- 126 executable strings that the name-table dump had mis-filed (skill table over-run
  into the title-menu help table, equipment/skill/item descriptions) translated.
  Title menu and Story submenu help verified in English in PCSX2.

## v0.1.7 — 2026-10-31 (dev)

- ELF string relocation (`tools/elfstrings_build.py`): in place when it fits, otherwise
  moved to freed slack or unused library code with every data pointer (and, for
  code-referenced strings, the `addiu`/`ori` low halves) rewritten. 2,336 strings, none
  without space. Title menu boots and renders with relocated strings.

## v0.1.6 — 2026-10-31 (dev)

- Complete library draft merged; consistency fixes (`work/glossary/term_fixes.json`).
  deckmenu.pac grows 719,456 → 785,824 bytes; it still loads (library opened for
  characters 100/300 and machines 150/300). Glossary: 2,016 entries from eight research
  batches (`docs/glossary.md`).

## v0.1.5 — 2026-10-31 — library preview + first English entries (dev)

- Library preview heartbeat (`LIBBOX+24`); `tools/dbg/library.py goto` retries from any
  point of the boot flow. Two self-translated library entries (character 1 Kanji
  Akatsuki, machine 1 Impulse 7) render in the game's own window with the VWF; all
  lines fit the measured 309 px. Draft-stage only (not yet reviewed).

## v0.1.4 — 2026-10-31 — first translated rows (dev)

- Library auto-wrap at build time (`tools/layout.py`): 309 px, ≤ 64 lines, ≤ 63 bytes.
- Driver did not start reliably from the boot flow (fixed in v0.1.5).

## v0.1.3 — 2026-10-31 — library preview (dev)

- Preview driver hooked on the title menu's Story entry (jump table 0x2DDCE0[0]); the
  Gallery hook of v0.1.1 could not be reached reliably because the menu drops short
  input pulses. Measured the library window from RAM: 22px font, right limit 309 px,
  font space 0.
- Builds refuse to patch the dev ISO while the emulator holds it open.

## v0.1.2 — failed

- Dev ISO was locked by the running emulator; nothing was written (`FAILED.txt`).

## v0.1.1 — 2026-10-31 — dev base ISO

- AFS slack layout: every pack with text and the font pack get a fixed TOC slot of
  2× size + 64 KiB; MUSIC.AFS / VOICE.AFS shifted after RESOURCE.AFS. Later dev builds
  patch the ELF and those packs in place (`--dev`).
- First library preview hook (Gallery).

## v0.1.0 — 2026-10-31 — VWF + debug monitor

- Proportional ASCII for the 22px and 26px ROM fonts (Noto Sans JP, 0–4 coverage
  levels like the original glyphs); `GetRomFontDispSizeX` returns per-glyph advances;
  nibble-accurate 4bpp blitter replaces the byte-snapping originals.
- Pad monitor in `ReadPad` (input injection, frame clock) for `tools/dbg`.
- Boots, title, menus, Versus mode intro dialogue verified in PCSX2; Japanese text
  renders unchanged through the new blitter; ASCII in help text uses the new font.

## Tooling — 2026-10-31

- ISO9660/AFS/pack/ATMB readers and writers, all verified by byte-identical rebuilds.
- Text extraction (44 ATMB tables, 10,165 rows), ELF string catalog, ELF name tables,
  glossary seeding from the sibling Sunrise Eiyuutan projects, symbol-aware
  disassembler / xrefs / dead-code finder, portable muted PCSX2 with PINE 28027.
