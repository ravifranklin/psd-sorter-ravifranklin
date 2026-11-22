# psd-sorter

Export thousands of Photoshop files (PSD and PSB) to high-quality JPGs and sort them into niche folders, such as Gaming, Finance & Investing or Travel & Adventure.

Built by [Ravi Franklin](https://ravifranklin.com) to organise a 13-year archive of YouTube thumbnail designs (over 23,000 files) with the help of Claude.

## What it does

1. **Creates 50 category folders** (`01 Podcast & Interviews` … `50 Other - General Content`). Edit `categories.txt` to change them.
2. **Exports every PSD/PSB** found in your folders and subfolders to a full-size JPG at quality 95. Your original files are never changed. It also:
   - opens 16-bit and 32-bit PSDs quickly,
   - handles giant canvases (tested on a 14 GB, 32,000 px PSB) by saving them at 4,000 px wide,
   - skips macOS `._` junk files,
   - can be stopped and restarted. It picks up where it left off,
   - lists any corrupted files in a log instead of stopping.
3. **Makes numbered preview sheets** (48 thumbnails per image) so you can decide each file's niche quickly.
4. **Moves each JPG into its folder** from a simple map file. If a name is already used, it adds 1, 2, 3… (`design.jpg`, `design1.jpg`, `design2.jpg`), so nothing is overwritten.

Files that already sit inside a subfolder named like a category (for example `.../Gaming/file.psd`) are sorted into that category automatically.

## Install

You need [Python 3.9+](https://www.python.org/downloads/). Then, in this folder:

```
pip install -r requirements.txt
```

## Use

Windows example. Use your own drive letters.

```
python psdsort.py init   --out "F:\THUMBNAILS"
python psdsort.py export "E:\My PSDs" "D:\More PSDs" --out "F:\THUMBNAILS" --work "F:\THUMBNAILS\_work"
python psdsort.py sheets --work "F:\THUMBNAILS\_work" --skip-prefilled
```

Open the sheets in `_work\sheets`. Every thumbnail has a yellow number. Write a map file (any name, like `map.txt`) with one line per number or range, using the category numbers from `categories.txt`:

```
# number(s) : category
0-14:7        # Finance & Investing
15:24         # Real Estate & Architecture
16-40:3       # Gaming
```

Then move everything into place:

```
python psdsort.py apply --out "F:\THUMBNAILS" --work "F:\THUMBNAILS\_work" --map map.txt
```

Any file not in your map stops the run and is listed, so nothing gets lost. Add `--other` to send unmapped files to the last folder instead.

Renamed duplicates are listed in `_work\renamed.txt`.

## Sorting with AI

The deciding step is done by looking at the sheets. That can be you, or an AI model that can see images. Ravi used Claude to read the sheets and write the map files. Any vision-capable assistant can do the same: give it `categories.txt` and the sheets, and ask for a map file in the format above.

## Privacy

The `work` folder holds your file names, previews and logs. **Keep it private and never commit it.** If your designs belong to clients, their file names count as client information too. The `.gitignore` blocks images, PSDs and work folders from being committed by accident.

## Options

Run `python psdsort.py <step> --help` for all options, for example:

- `--exclude FOLDER` to skip a folder (can repeat)
- `--workers N` to set the number of files exported at once (lower it if your PC runs out of memory)
- `--rescan` to search the source folders again after adding new files

## License

MIT. See [LICENSE](LICENSE).
