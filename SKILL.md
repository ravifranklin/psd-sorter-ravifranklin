---
name: psd-thumbnail-sorter
description: Sort a folder of YouTube thumbnail PSD/PSB files into category folders (Finance, Gaming, Travel, News, etc.) by looking at each thumbnail. Use when the user asks to sort, organise or categorise PSD thumbnail files.
---

# PSD Thumbnail Sorter

Sorts YouTube thumbnail PSD files into topic folders. File names are often client
names, so **never sort by file name** - decide from the preview image and the text
layers inside each PSD.

The user may be a beginner: do all technical work yourself, explain results in
plain, simple English, and never ask technical questions.

## Privacy rule
Thumbnails and file names belong to the user's clients. Never upload, publish,
commit or share previews, file names, text layers or the plan anywhere. Keep all
work files on the user's own machine (or in this session only).

## Default categories
IRL, Finance, Trading & Crypto, Business & Economy, Gym & Yoga, Travel, Vlog,
Gaming, Tech, Education, Science & Space, Mystery & History, News & Politics,
Sports, Entertainment & Movies, Food & Cooking, Podcast & Interview, Motivation,
Kids, Channel Art & Banners, Other

Special folders: `_Needs Review` (unsure / blank / low confidence),
`_Could Not Open` (broken files).

Only create a folder when at least one file goes in it. A new category is fine
if 3+ files clearly share a topic none of the above covers. If the user gives
their own list, use theirs.

## Steps

1. **Setup.** `pip install psd-tools pillow` (add `--break-system-packages` if pip
   refuses). Pick a work folder *outside* the PSD folder (e.g. a temp folder).

2. **Extract** previews + text (safe to rerun; skips finished files):
   ```
   python scripts/extract.py "<psd folder>" "<work>" --max-minutes 25
   ```
   Big folders: keep rerunning until it prints `DONE`. Roughly 1-3 s per file.

3. **Contact sheets:**
   ```
   python scripts/sheet.py "<work>" "<work>/sheets"
   ```
   Each sheet shows 20 numbered previews; `texts.txt` lists each number's text layers.

4. **Classify.** Open the sheets one by one (Read tool) together with `texts.txt`.
   Write `<work>/plan.csv` with columns `index,category,confidence,reason`.
   Hints: charts/candlesticks = Trading & Crypto; money, debt, salary, savings =
   Finance; countries' economies = Business & Economy; person talking to camera in
   a street/public place = IRL; family/daily life = Vlog; space, planets, aliens,
   probes = Science & Space; ghost ships, lost history, unsolved cases = Mystery &
   History; politicians, elections, social debates = News & Politics; movie or
   celebrity = Entertainment & Movies; YouTube banners = Channel Art & Banners.
   Blank or unclear = `_Needs Review` with confidence `low`.

5. **Test first.** Do steps 2-4 for the first 20 files only (`--end 20`), show the
   user a simple table (what each thumbnail shows -> folder) and the counts.
   **Wait for the user to say go.** Adjust categories if they ask.

6. **Dry run, then move:**
   ```
   python scripts/move.py "<psd folder>" "<work>" "<work>/plan.csv"           # preview counts
   python scripts/move.py "<psd folder>" "<work>" "<work>/plan.csv" --apply   # move
   ```
   Moves only (same drive = instant), never deletes or overwrites (clashes get
   `_2`, `_3`). Writes `undo_log.csv`, `UNDO.bat` and `undo.sh` into the PSD
   folder - double-clicking `UNDO.bat` puts everything back.

7. **Report** in plain English: how many files went into each folder, how many
   need review, and where the UNDO file is. Delete the work folder.

## Variant: export JPGs into 50 niche folders
If the user wants JPG copies sorted into numbered niche folders instead of moving the PSDs, use
`scripts/psdsort.py` (steps `init`, `export`, `sheets`, `apply`; see README). Run `export` in short foreground
chunks if long processes get killed. It resumes by itself. Classify from the sheets into a map file
(`range:category`, numbers from `categories.txt`), then `apply`. Same privacy rule: work files never leave the
user's machine.
