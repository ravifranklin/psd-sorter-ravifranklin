"""
Step 3 - Move PSDs into category folders using a plan CSV, with a full undo.

plan CSV columns:  index,category,confidence,reason
  - index = number from files.json / the contact sheets
  - category = folder name to move into (e.g. "Finance", "_Needs Review")

Usage:
    python move.py "<psd folder>" "<work folder>" plan.csv            # dry run: only prints what would happen
    python move.py "<psd folder>" "<work folder>" plan.csv --apply    # really moves the files

Never deletes or overwrites anything. Name clashes get _2, _3 ...
Writes undo_log.csv, UNDO.bat (Windows) and undo.sh (Mac/Linux) into the PSD folder.
"""
import argparse
import csv
import json
import os
import re
from collections import Counter


def safe_folder(name):
    name = re.sub(r'[<>:"/\\|?*]', "-", name).strip(" .")
    return name or "Other"


def free_name(folder, filename):
    base, ext = os.path.splitext(filename)
    cand, n = filename, 2
    while os.path.exists(os.path.join(folder, cand)):
        cand = f"{base}_{n}{ext}"
        n += 1
    return cand


def write_undo(src, moves):
    with open(os.path.join(src, "undo_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["original", "moved_to"])
        w.writerows(moves)

    bat = ["@echo off", "chcp 65001 >nul", 'cd /d "%~dp0"',
           "echo Putting files back where they were...", ""]
    for orig, new in moves:
        o, n = orig.replace("%", "%%"), new.replace("%", "%%")
        bat.append(f'if exist "{n}" if not exist "{o}" move "{n}" "{o}" >nul')
    bat += ["", "echo Done. Empty category folders can be deleted by hand.", "pause"]
    with open(os.path.join(src, "UNDO.bat"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(bat) + "\n")

    sh = ["#!/bin/sh", 'cd "$(dirname "$0")"']
    for orig, new in moves:
        o, n = orig.replace("'", "'\\''"), new.replace("'", "'\\''").replace("\\", "/")
        sh.append(f"[ -e '{n}' ] && [ ! -e '{o}' ] && mv '{n}' '{o}'")
    sh.append('echo "Done."')
    with open(os.path.join(src, "undo.sh"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sh) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("work")
    ap.add_argument("plan")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    files = json.load(open(os.path.join(a.work, "files.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(a.plan, encoding="utf-8")))
    counts = Counter()
    moves = []
    for r in rows:
        i = int(r["index"])
        name = files[i]
        cat = safe_folder(r["category"])
        counts[cat] += 1
        here = os.path.join(a.src, name)
        if not os.path.exists(here):
            print(f"skip (not found): #{i}")
            continue
        dest_dir = os.path.join(a.src, cat)
        if not a.apply:
            continue
        os.makedirs(dest_dir, exist_ok=True)
        new_name = free_name(dest_dir, name)
        os.rename(here, os.path.join(dest_dir, new_name))
        moves.append([name, f"{cat}\\{new_name}"])

    for cat, n in counts.most_common():
        print(f"{n:6d}  {cat}")
    if a.apply:
        # keep earlier undo entries if this is a second batch
        old = os.path.join(a.src, "undo_log.csv")
        if os.path.exists(old):
            prev = list(csv.reader(open(old, encoding="utf-8")))[1:]
            moves = prev + moves
        write_undo(a.src, moves)
        print(f"MOVED. Undo file written: {os.path.join(a.src, 'UNDO.bat')}")
    else:
        print("DRY RUN - nothing moved. Add --apply to move.")


if __name__ == "__main__":
    main()
