# PSD Thumbnail Sorter

**Automatically sort hundreds of YouTube thumbnail PSD files into topic folders - Finance, Gaming, Travel, News, Science & Space and more - using Claude.**

Made by [Ravi Franklin](https://ravifranklin.com), YouTube thumbnail designer.

---

## The problem

After a few years of thumbnail design you end up with thousands of PSD files named after clients
(`client12a.psd`, `client12b.psd` ...). Finding "that finance thumbnail I did last year" is impossible.

## How it works

File names say nothing about the topic, so this tool looks at the thumbnails themselves:

1. **Extract** - a Python script opens every PSD, saves a small preview image and pulls out the
   text written on the thumbnail (e.g. "STOCK MARKET CRASH").
2. **Look** - Claude looks at the previews (20 at a time on a numbered contact sheet) together
   with the text, and decides the category of each one - just like a person would.
3. **Sort** - files are moved into category folders. Nothing is deleted or overwritten, and an
   `UNDO.bat` file is created that puts everything back with one double-click.

It always tests on the first 20 files and waits for your OK before moving anything.

## Use it with Claude Code

1. Install [Claude Code](https://claude.com/claude-code) and Python 3.
2. Download this repo (green **Code** button -> **Download ZIP**) and unzip it.
3. Open Claude Code in the unzipped folder and say:

   > Follow SKILL.md and sort the PSD files in `D:\My Thumbnails`

That's it. Claude installs what it needs, shows you a test result, and waits for you to say **go**.

You can also add this folder as a Claude skill so it works from anywhere.

## Run the scripts yourself

```bash
pip install -r requirements.txt

# 1. previews + text (rerun until it says DONE - it continues where it stopped)
python scripts/extract.py "D:/My Thumbnails" work

# 2. numbered contact sheets + texts.txt
python scripts/sheet.py work work/sheets

# 3. write work/plan.csv yourself (or let Claude do it):
#    index,category,confidence,reason
#    0,Finance,high,money and debt text
#    1,Gaming,high,game characters

# 4. dry run, then move
python scripts/move.py "D:/My Thumbnails" work work/plan.csv
python scripts/move.py "D:/My Thumbnails" work work/plan.csv --apply
```

## Default categories

IRL · Finance · Trading & Crypto · Business & Economy · Gym & Yoga · Travel · Vlog · Gaming ·
Tech · Education · Science & Space · Mystery & History · News & Politics · Sports ·
Entertainment & Movies · Food & Cooking · Podcast & Interview · Motivation · Kids ·
Channel Art & Banners · Other · `_Needs Review` · `_Could Not Open`

Change them in `SKILL.md` or just tell Claude your own list.

## Safe by design

- Moves only - never deletes, never overwrites (name clashes get `_2`, `_3`)
- Works on huge files: each PSD opens in its own process, so one broken 2 GB file can't crash the run
- Can be stopped and restarted any time
- `UNDO.bat` (Windows) / `undo.sh` (Mac) restores the original layout
- Your previews and file names stay on your computer

## Requirements

Python 3.9+, [psd-tools](https://github.com/psd-tools/psd-tools), Pillow.

## License

MIT
