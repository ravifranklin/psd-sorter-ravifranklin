#!/usr/bin/env python3
"""
psdsort — export Photoshop files (PSD/PSB) to high-quality JPGs and sort them
into niche/category folders.

Steps:
  1. init     Create the numbered category folders in the output folder.
  2. export   Find every PSD/PSB in one or more source folders and export each
              one to a full-size JPG (quality 95), plus a small preview.
  3. sheets   Build numbered contact sheets from the previews so a person
              (or an AI with vision) can decide each file's category.
  4. apply    Read a map file ("index:category" lines) and move each JPG into
              its category folder. Duplicate names get 1, 2, 3... added.

Run `python psdsort.py <step> --help` for the options of each step.
"""
import argparse
import os
import struct
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
PSD_EXT = (".psd", ".psb")
GIANT_PIXELS = 150_000_000      # above this, read the file in a streaming, downscaled way
GIANT_TARGET_WIDTH = 4000


# --------------------------------------------------------------------------- helpers

def load_categories(path):
    with open(path, encoding="utf-8") as f:
        cats = [l.strip() for l in f if l.strip()]
    # Windows folder names cannot contain these characters
    bad = '<>:"/\\|?*'
    return ["".join("-" if ch in bad else ch for ch in c) for c in cats]


def category_dirs(out, categories):
    return {i + 1: f"{i + 1:02d} {c}" for i, c in enumerate(categories)}


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if l.strip()]


def parse_map(path):
    """Lines like '12:7' or '100-140:24'. Later lines override earlier ones."""
    m = {}
    for n, line in enumerate(read_lines(path), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            rng, cat = line.split(":")
            a, _, b = rng.partition("-")
            a, b = int(a), int(b or a)
            for i in range(a, b + 1):
                m[i] = int(cat)
        except ValueError:
            sys.exit(f"{path} line {n}: can't read '{line}' (expected like 10-20:7)")
    return m


# --------------------------------------------------------------------------- PSD reading

def psd_header(path):
    with open(path, "rb") as f:
        h = f.read(26)
    if len(h) < 26 or h[:4] != b"8BPS":
        raise ValueError("not a PSD/PSB file")
    ver = struct.unpack(">H", h[4:6])[0]
    ch, height, width, depth, mode = struct.unpack(">HIIHH", h[12:26])
    return ver, ch, height, width, depth, mode


def _seek_to_image_data(f, ver):
    f.seek(26)
    for _ in range(2):                      # color mode data, image resources
        n = struct.unpack(">I", f.read(4))[0]
        f.seek(n, 1)
    n = struct.unpack(">Q", f.read(8))[0] if ver == 2 else struct.unpack(">I", f.read(4))[0]
    f.seek(n, 1)                            # layer & mask info
    return struct.unpack(">H", f.read(2))[0]


def _to_rgb_array(a, depth):
    if depth == 16:
        return (a >> 8).astype("u1")
    if depth == 32:
        return (np.clip(a, 0, 1) ** (1 / 2.2) * 255).astype("u1")
    return a


def _array_to_image(a, mode):
    if mode == 3:                                           # RGB
        im = Image.fromarray(np.ascontiguousarray(np.stack(a[:3], -1)), "RGB")
        if a.shape[0] >= 4 and a[3].min() < 255:            # transparent: put on white
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=Image.fromarray(np.ascontiguousarray(a[3]), "L"))
            im = bg
        return im
    if mode == 4:                                           # CMYK (stored inverted)
        return Image.fromarray(np.ascontiguousarray(255 - np.stack(a[:4], -1)), "CMYK").convert("RGB")
    if mode in (1, 8):                                      # grayscale / duotone
        return Image.fromarray(np.ascontiguousarray(a[0]), "L").convert("RGB")
    raise ValueError(f"unsupported color mode {mode}")


def read_merged_fast(path):
    """Read the flattened (composite) image Photoshop stores at the end of the file.
    Handles 8/16/32-bit, which Pillow alone can't."""
    from psd_tools.compression import decompress
    from psd_tools.constants import Compression
    ver, ch, h, w, depth, mode = psd_header(path)
    with open(path, "rb") as f:
        comp = _seek_to_image_data(f, ver)
        data = f.read()
    raw = decompress(data, Compression(comp), w, h * ch, depth, ver)
    dt = {8: "u1", 16: ">u2", 32: ">f4"}[depth]
    a = np.frombuffer(raw, dtype=dt)[: ch * h * w].reshape(ch, h, w)
    return _array_to_image(_to_rgb_array(a, depth), mode)


def read_giant_streaming(path, target_width=GIANT_TARGET_WIDTH):
    """For huge canvases: read row by row and keep every Nth pixel, so memory
    stays small. Output is downscaled to about target_width pixels wide."""
    from psd_tools.compression import decode_rle
    ver, ch, h, w, depth, mode = psd_header(path)
    if depth != 8:
        raise ValueError("streaming reader supports 8-bit files only")
    step = max(1, w // target_width)
    out = np.zeros((ch, (h + step - 1) // step, (w + step - 1) // step), "u1")
    with open(path, "rb") as f:
        comp = _seek_to_image_data(f, ver)
        if comp == 1:                                       # RLE
            cw = 4 if ver == 2 else 2
            counts = np.frombuffer(f.read(ch * h * cw), ">u4" if cw == 4 else ">u2")
            for c in range(ch):
                for r in range(h):
                    b = f.read(int(counts[c * h + r]))
                    if r % step == 0:
                        row = np.frombuffer(decode_rle(b, w, 1, 8, ver), "u1")
                        out[c, r // step] = row[::step]
        elif comp == 0:                                     # raw
            for c in range(ch):
                for r in range(h):
                    b = f.read(w)
                    if r % step == 0:
                        out[c, r // step] = np.frombuffer(b, "u1")[::step]
        else:
            raise ValueError(f"streaming reader can't handle compression {comp}")
    return _array_to_image(out, mode)


def open_psd(path):
    """Try the fastest reader first, fall back to slower ones."""
    _, _, h, w, _, _ = psd_header(path)
    if w * h > GIANT_PIXELS:
        return read_giant_streaming(path), "giant"
    try:
        im = Image.open(path)
        im.load()
        return im, "pillow"
    except Exception:
        pass
    try:
        return read_merged_fast(path), "fast"
    except Exception:
        pass
    from psd_tools import PSDImage
    im = PSDImage.open(path).topil()
    if im is None:
        raise ValueError("file has no stored composite image")
    return im, "psd-tools"


def to_rgb(im):
    if im.mode in ("RGBA", "LA", "P", "PA"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        return bg
    return im.convert("RGB")


# --------------------------------------------------------------------------- step: init

def cmd_init(args):
    cats = load_categories(args.categories)
    for d in category_dirs(args.out, cats).values():
        os.makedirs(os.path.join(args.out, d), exist_ok=True)
    print(f"Created {len(cats)} category folders in {args.out}")


# --------------------------------------------------------------------------- step: export

def _export_one(job):
    i, src, out_dir, small_dir, quality = job
    out = os.path.join(out_dir, f"{i:05d}.jpg")
    small = os.path.join(small_dir, f"{i:05d}.jpg")
    if os.path.exists(out) and os.path.exists(small):
        return i, "SKIP", ""
    t = time.time()
    try:
        im, how = open_psd(src)
        im = to_rgb(im)
        blank = max(ImageStat.Stat(im.resize((64, 36))).stddev) < 2
        im.save(out, "JPEG", quality=quality, subsampling=0)
        s = im.copy()
        s.thumbnail((320, 320))
        s.save(small, "JPEG", quality=80)
        note = f"{how} {im.size[0]}x{im.size[1]} {time.time() - t:.1f}s" + (" BLANK" if blank else "")
        return i, "OK", note
    except Exception as e:
        return i, "ERR", repr(e)[:200]


def cmd_export(args):
    work = os.path.abspath(args.work)
    out_dir = os.path.join(args.out, "_exported")
    small_dir = os.path.join(work, "small")
    for d in (work, out_dir, small_dir):
        os.makedirs(d, exist_ok=True)

    list_path = os.path.join(work, "list.txt")
    if os.path.exists(list_path) and not args.rescan:
        files = read_lines(list_path)
        print(f"Resuming with {len(files)} files from {list_path} (use --rescan to search again)")
    else:
        excludes = [os.path.abspath(e) for e in args.exclude]
        files = []
        for src in args.sources:
            for root, dirs, names in os.walk(src):
                if any(os.path.abspath(root).startswith(e) for e in excludes):
                    dirs[:] = []
                    continue
                for n in sorted(names):
                    if n.startswith("._"):          # macOS junk files, not real PSDs
                        continue
                    if n.lower().endswith(PSD_EXT):
                        files.append(os.path.abspath(os.path.join(root, n)))
        files.sort(key=str.lower)
        with open(list_path, "w", encoding="utf-8") as f:
            f.write("\n".join(files) + "\n")
        print(f"Found {len(files)} PSD/PSB files")

    # Pre-sort: files already inside a subfolder named like a category keep it
    cats = load_categories(args.categories)
    lookup = {c.lower(): n for n, c in enumerate(cats, 1)}
    with open(os.path.join(work, "prefill.txt"), "w", encoding="utf-8") as f:
        for i, p in enumerate(files):
            parent = os.path.basename(os.path.dirname(p)).lower()
            if parent in lookup:
                f.write(f"{i}:{lookup[parent]}\n")

    jobs = [(i, p, out_dir, small_dir, args.quality) for i, p in enumerate(files)]
    log_path = os.path.join(work, "export_log.txt")
    ok = err = 0
    with open(log_path, "a", encoding="utf-8") as log, \
         Pool(args.workers, maxtasksperchild=25) as pool:
        for n, (i, status, note) in enumerate(pool.imap_unordered(_export_one, jobs), 1):
            if status != "SKIP":
                log.write(f"{status}\t{i}\t{files[i]}\t{note}\n")
                log.flush()
            ok += status in ("OK", "SKIP")
            err += status == "ERR"
            if n % 100 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)} done, {err} errors", flush=True)
    print(f"Exported {ok} of {len(files)}. Errors are listed in {log_path}")


# --------------------------------------------------------------------------- step: sheets

def cmd_sheets(args):
    work = os.path.abspath(args.work)
    small_dir = os.path.join(work, "small")
    sheet_dir = os.path.join(work, "sheets")
    os.makedirs(sheet_dir, exist_ok=True)
    prefilled = set(parse_map(os.path.join(work, "prefill.txt"))) if args.skip_prefilled and \
        os.path.exists(os.path.join(work, "prefill.txt")) else set()
    ids = sorted(int(n[:5]) for n in os.listdir(small_dir) if n.endswith(".jpg"))
    ids = [i for i in ids if i not in prefilled]

    C, R, W, H = args.cols, args.rows, 240, 135
    per = C * R
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except OSError:
        try:
            font = ImageFont.truetype("arialbd.ttf", 18)
        except OSError:
            font = ImageFont.load_default()
    count = 0
    for s in range(0, len(ids), per):
        sheet = Image.new("RGB", (C * W, R * H), "black")
        d = ImageDraw.Draw(sheet)
        for j, i in enumerate(ids[s:s + per]):
            im = Image.open(os.path.join(small_dir, f"{i:05d}.jpg")).convert("RGB")
            im.thumbnail((W - 4, H - 4))
            x, y = (j % C) * W, (j // C) * H
            sheet.paste(im, (x + 2, y + 2))
            t = str(i)
            d.rectangle([x + 2, y + 2, x + 8 + 11 * len(t), y + 24], fill="yellow")
            d.text((x + 5, y + 3), t, fill="black", font=font)
        sheet.save(os.path.join(sheet_dir, f"sheet_{s // per:03d}.jpg"), quality=80)
        count += 1
    print(f"Made {count} sheets ({len(ids)} images) in {sheet_dir}")
    print("Write your decisions in a map file, one line per range, e.g.  0-12:7  or  13:24")


# --------------------------------------------------------------------------- step: apply

def cmd_apply(args):
    work = os.path.abspath(args.work)
    files = read_lines(os.path.join(work, "list.txt"))
    out_dir = os.path.join(args.out, "_exported")
    dirs = category_dirs(args.out, load_categories(args.categories))

    cat = {}
    prefill = os.path.join(work, "prefill.txt")
    if os.path.exists(prefill):
        cat.update(parse_map(prefill))
    for m in args.map:
        cat.update(parse_map(m))

    missing = [i for i in range(len(files))
               if os.path.exists(os.path.join(out_dir, f"{i:05d}.jpg")) and i not in cat]
    if missing and not args.other:
        sys.exit(f"{len(missing)} exported files have no category yet, e.g. {missing[:10]}. "
                 "Add them to your map file, or use --other to put them in the last folder.")

    taken = set()
    for d in dirs.values():
        p = os.path.join(args.out, d)
        os.makedirs(p, exist_ok=True)
        taken.update(n.lower() for n in os.listdir(p))

    moved = renamed = 0
    with open(os.path.join(work, "renamed.txt"), "a", encoding="utf-8") as log:
        for i, src_psd in enumerate(files):
            src = os.path.join(out_dir, f"{i:05d}.jpg")
            if not os.path.exists(src):
                continue
            c = cat.get(i, max(dirs))
            if c not in dirs:
                sys.exit(f"File {i} has category {c}, but only 1-{max(dirs)} exist")
            stem = os.path.splitext(os.path.basename(src_psd))[0]
            name, n = f"{stem}.jpg", 0
            while name.lower() in taken:            # duplicate: add 1, 2, 3...
                n += 1
                name = f"{stem}{n}.jpg"
            taken.add(name.lower())
            os.replace(src, os.path.join(args.out, dirs[c], name))
            moved += 1
            if n:
                renamed += 1
                log.write(f"{src_psd}\t->\t{dirs[c]}/{name}\n")
    print(f"Moved {moved} images ({renamed} renamed because the name was already used)")


# --------------------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    default_cats = os.path.join(HERE, "..", "categories.txt")

    s = sub.add_parser("init", help="create the category folders")
    s.add_argument("--out", required=True, help="output folder, e.g. F:\\THUMBNAILS")
    s.add_argument("--categories", default=default_cats)
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("export", help="export PSD/PSB files to JPG")
    s.add_argument("sources", nargs="+", help="one or more folders to search (subfolders included)")
    s.add_argument("--out", required=True, help="output folder")
    s.add_argument("--work", default="work", help="folder for lists, previews and logs (keep it private)")
    s.add_argument("--exclude", action="append", default=[], help="folder to skip (can repeat)")
    s.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    s.add_argument("--quality", type=int, default=95)
    s.add_argument("--rescan", action="store_true", help="search the source folders again")
    s.add_argument("--categories", default=default_cats)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("sheets", help="make numbered preview sheets")
    s.add_argument("--work", default="work")
    s.add_argument("--cols", type=int, default=8)
    s.add_argument("--rows", type=int, default=6)
    s.add_argument("--skip-prefilled", action="store_true",
                   help="leave out files already sorted by their source subfolder name")
    s.set_defaults(func=cmd_sheets)

    s = sub.add_parser("apply", help="move JPGs into category folders using map file(s)")
    s.add_argument("--out", required=True)
    s.add_argument("--work", default="work")
    s.add_argument("--map", action="append", default=[], help="map file (can repeat)")
    s.add_argument("--other", action="store_true", help="unmapped files go to the last category")
    s.add_argument("--categories", default=default_cats)
    s.set_defaults(func=cmd_apply)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
