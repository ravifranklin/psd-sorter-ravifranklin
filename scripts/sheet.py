"""
Step 2 - Build numbered contact sheets (default 20 previews each) so Claude can
look at many thumbnails at once, plus a text summary of each file's text layers.

Usage:
    python sheet.py "<work folder>" "<output folder for sheets>" [--per-sheet 20]

Creates sheet_00000.jpg, sheet_00020.jpg, ... and texts.txt.
The red number on each tile is the file's index in files.json.
"""
import argparse
import glob
import json
import os

from PIL import Image, ImageDraw, ImageFont

W, H, COLS = 400, 225, 4


def font():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, 20)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--per-sheet", type=int, default=20)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    files = json.load(open(os.path.join(a.work, "files.json"), encoding="utf-8"))
    f = font()
    lines = []
    for start in range(0, len(files), a.per_sheet):
        ids = [i for i in range(start, min(start + a.per_sheet, len(files)))
               if os.path.exists(os.path.join(a.work, "prev", f"{i:05d}.jpg"))]
        if ids:
            rows = (len(ids) + COLS - 1) // COLS
            sheet = Image.new("RGB", (W * COLS, (H + 28) * rows), "white")
            d = ImageDraw.Draw(sheet)
            for k, i in enumerate(ids):
                im = Image.open(os.path.join(a.work, "prev", f"{i:05d}.jpg"))
                im.thumbnail((W, H))
                x, y = (k % COLS) * W, (k // COLS) * (H + 28)
                sheet.paste(im, (x, y + 28))
                d.text((x + 5, y + 3), str(i), fill="red", font=f)
            sheet.save(os.path.join(a.out, f"sheet_{start:05d}.jpg"), quality=75)

    for i, name in enumerate(files):
        p = os.path.join(a.work, f"info_{i:05d}.json")
        if not os.path.exists(p):
            lines.append(f"{i}\t(not extracted yet)")
            continue
        info = json.load(open(p, encoding="utf-8"))
        if info.get("error"):
            lines.append(f"{i}\tERROR: {info['error']}")
        else:
            lines.append(f"{i}\t" + " / ".join(info.get("text", []))[:200])
    with open(os.path.join(a.out, "texts.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"Sheets and texts.txt written to {a.out}")


if __name__ == "__main__":
    main()
