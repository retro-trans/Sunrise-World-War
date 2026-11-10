# Translation guide — Sunrise World War

Read `BASE_RULES.md` first; it governs everything here. This file adds the
project-specific formats and limits.

## Files

- Source (Japanese, local only): `work/source/text/<table>.json` → `rows[i].jp`.
- Drafts: `work/translation/en/<table>.json`
  `{"table": "...", "rows": [{"id": N, "jp": "<copy of source>", "en": "...", "status": "...", "notes": "..."}]}`
  Rows without `en` stay Japanese in the build. Keep `id` = source row index.
- Glossary: `work/glossary/glossary.json` (`py -3.11 tools/glossary.py lookup FILE`).
  Spellings there are binding. Missing name → report it, do not invent one.
- Committed copies: `*.en.json` written by `tools/strip_jp.py` (no Japanese script).

## Codec

Rows are text plus `{C:hex}` control records and `{xHH}` raw bytes. Every `{C:..}` must
appear in `en` in the same order (the build rejects the row otherwise). Keep `{x00}` row
terminators and `%n` colour codes. Use ASCII only in English (no curly quotes, no
full-width letters, no `…` — write `...`; use `--` for a dash). `■` and other symbols
already in the source may stay.

## Library entries (tables 1271_02471 machines, 1271_10345 characters)

Draft format — one logical line per line:

```
%4■Name■%1
Kanji
%4■Full Name■%1
Kanji Akatsuki
%4■Profile■%1
> First paragraph, written as one line.
> Second paragraph.
{x00}
```

- `> ` lines are paragraphs (Japanese paragraphs start with an ideographic space). The
  build wraps them to 309 px (22px font) and indents them two spaces. Other lines are
  kept as written and must fit 309 px on their own (about 38 characters).
- Hard limits (checked by the build): ≤ 64 lines after wrapping, ≤ 63 bytes per line.
  A 1,000-character English profile is about 30 lines.
- Header labels (keep `%4■…■%1`): 名称 Name · フルネーム Full Name · 解説 Profile (characters)
  / Description (machines) · 機体名称 Unit Name · 機種分類 Type · スペック Specs ·
  基本兵装 Standard Arms · 名前 Name · ユニット分類 Unit Type · 本名 Real Name · 通称 Known As ·
  通り名 Alias · 略称 Short Name · コードネーム Code Name · メンバー Members · 武器 Weapons ·
  分類 Class · アルター名 Alter Name · 格闘スタイル Fighting Style · 所属 Affiliation ·
  装着者 Wearer · 使用者 User. Infantry (HUF) entries use Profile for 解説.
  Unit types: HUF (Close-Combat Unit), AFV (Combat Vehicle), NON (Other).
  Spec labels: 全高 Overall Height · 全幅 Width · 本体重量 Empty Weight · 機体重量 Weight ·
  乾重量 Dry Weight · 翼幅 Wingspan · オーラ係数 Aura Coefficient · 燃料 Fuel; 詳細不明 Details unknown.
- Spec lines: `頭頂高／約９．５ｍ` → `Height: approx. 9.5 m`; `全長` Length; `重量` Weight;
  `他、詳細不明` → `Other details unknown`; a lone `他` under arms → `Others`.
- Readings in parentheses after a name (`日吉　明（ヒヨシ　アキラ）`) are dropped in English
  (`Akira Hiyoshi` — check glossary order/spelling).
- Machine codes (ＦＴ－ＺＸ７) become ASCII (FT-ZX7).

Check a table without building: `py -3.11 tools/fitcheck.py 1271_10345`.

## Short names (elf_strings.json groups `names:chara+8`, `names:mch+8`, `names:ship+8`)

The "omit" names of characters, units and ships (*GetOmitName): unit / pilot / ship lists,
shop, battle select, battle board labels. Drawn in a fixed-width font, one cell per byte,
so the limit is the longest Japanese short name of the table: characters 11, units 16,
ships 14 bytes. `py -3.11 tools/short_names.py draft` fills empty rows from the display /
full name (or the matching name word, titles dropped); numbered generics ("Fed. Sold.1")
and long names were abbreviated by hand. Keep the number of a numbered variant.

## Text graphics (`work/translation/gfx/gfx_text.json`)

One row per sprite (PAL_/IMG_/CEL_ member): `rid`, `jp`, `en` and drawing options (see
`tools/gfx_text.py`). `py -3.11 tools/gfx_text.py preview OUT.png [RID...]` shows the
original next to the encoded English; check every new row there before building.

## Town and map script strings (`work/translation/en/town_strings.json`)

One row per distinct Japanese string: `{jp, en, kinds, uses, notes, status}`. `kinds`:
`house` (location button, <= 31 bytes), `town` (town name, <= 31), `exit` ("To X", <= 31),
`map` (world-map mark, keep it about as long as the Japanese in half-width characters).
Names follow the dialogue and glossary spellings; style sheet applies ("the Cusco gate"
-> map label "Cusco gate", "Kingdom of A"). `py -3.11 tools/town_strings.py check` checks
ASCII and lengths; `dump` re-reads the scripts; `template` refreshes rows keeping English.

## Style

Encyclopedia prose: clear, neutral reference register; keep every fact, hedge
("思われる" → "is thought to", "推測の域を出ない" → "remains speculation") and evaluative
word. Do not add facts from outside knowledge. Dialogue rules are in `BASE_RULES.md`.

## Review stages

`status`: `draft` → `accuracy` → `editorial` → `proofread`. Each stage records rows
examined / edited and uncertainties in `docs/review_<batch>.md`.

## Dialogue (every other table)

Slices: `work/translation/slices/dlg_<table>_<k>.json` → rows `{id, segments: [jp...], dups}`.
Output `<slice>.out.json` → `{"rows": [{"id", "segments": [en...], "notes"}]}` — one English
string per segment, same count and order. A segment is the text of one page (a single newline = line break). The build wraps lines at 468 px (26px font, about 44 characters) and
rejects a page with more than 3 lines: condense rather than drop content, or flag it.
Merge with `py -3.11 tools/slices.py merge-dialogue "dlg_*"`.

Slice rows also carry `speakers` (one name per segment, from the page's ＄/％ header:
low 10 bits = chara index, high bits = face/pose; blank = no header) and each slice has a
`.speakers.tsv` (glossary gender/personality) and `.glossary.tsv`. `slices.py check SLICE`
validates a dialogue slice: segment count, ASCII only, no blank lines, ≤ 3 lines of 468 px
per page, control order. The translator brief and the running list of cross-slice term
decisions are in `work/translation/slices/_dialogue_brief.md`; translator reports are in
`docs/review_dialogue_draft.md`.

Renderer notes: dialogue goes through the typewriter `TextWaitPutProc` (spaces patched to
plain ASCII); location captions go through `telopMainProcess` (patched to measure pixels
and draw proportionally). Table 2368_07367 is the BGM title list; 2271_06810 is the staff
roll (credit blocks keep their line count; leading ideographic spaces become 2 spaces).

## Consistency

Cross-slice spelling decisions live in `work/glossary/term_fixes.json` and are applied by
`py -3.11 tools/term_fixes.py --write` after agent edits (BASE_RULES order).
