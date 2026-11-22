---
name: psd-thumbnail-sorter
description: Export a large folder of YouTube thumbnail PSD/PSB files to high-quality JPGs and sort them into 50 niche folders (Finance, Gaming, Travel, etc.) by looking at each thumbnail. Use when the user asks to export, sort or categorise PSD thumbnails.
---

# PSD to JPG thumbnail sorter

Exports every PSD/PSB in the user's folders to a full-size JPG (quality 95) and files
each JPG into one of 50 numbered niche folders listed in `categories.txt`. The PSDs
are never changed. File names are often client names, so **never decide the niche
from the file name**. Look at the thumbnail.

The user may be a beginner: do all technical work yourself and explain results in
plain, simple English.

## Privacy rule
Thumbnails and file names belong to the user's clients. Never upload, publish,
commit or share previews, file names, map files or logs anywhere. Keep the work
folder on the user's own machine.

## Steps
1. **Setup.** `pip install -r requirements.txt` (add `--break-system-packages` if pip refuses).
2. **Folders.** `python psdsort.py init --out "<output folder>"`
3. **Export.** `python psdsort.py export "<source folder>" [more folders] --out "<output>" --work "<output>/_work"`
   Use `--exclude` for folders to skip. If long commands get cut off, run it in short chunks.
   It resumes by itself. Repeat until every file is done, then check `export_log.txt` for errors.
4. **Sheets.** `python psdsort.py sheets --work "<output>/_work" --skip-prefilled`
   Files already in a subfolder named like a category are sorted automatically.
5. **Decide.** Look at each numbered sheet (48 thumbnails each) and write a map file,
   one line per number or range: `0-14:7` (category numbers = line numbers in
   `categories.txt`). Judge the main subject. Banners, logos, blank canvases and
   print designs go to the last category unless clearly in a niche. Save the map as you go.
6. **Apply.** `python psdsort.py apply --out "<output>" --work "<output>/_work" --map map.txt`
   Duplicate names get 1, 2, 3... added and are listed in `renamed.txt`.

## Report back
How many were exported and sorted, how many were renamed as duplicates, which files
failed or were skipped, the biggest folders, and ask whether to delete the leftover
`_exported` and `_work` folders.
