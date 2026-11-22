"""
Step 1 - Read every PSD/PSB in a folder: save a small preview JPG and pull out
the text layers + layer names. Results go into a separate work folder, never
into the PSD folder.

Each file is opened in its own child process, so one huge or broken PSD can't
crash the whole run (it falls back to the tiny embedded thumbnail, then to
"could not open"). Safe to stop and restart: finished files are skipped.

Usage:
    python extract.py "<psd folder>" "<work folder>" [--start 0] [--end 999999] [--max-minutes 0]
"""
import argparse
import json
import os
import subprocess
import sys
import time

EXTS = (".psd", ".psb")


def worker(path, idx, work, mode):
    from psd_tools import PSDImage

    info = {"file": os.path.basename(path)}
    psd = PSDImage.open(path)
    img = psd.topil() if mode == "full" else None
    if img is None:
        img = psd.thumbnail()
        info["small_preview"] = True
    if img is not None:
        img = img.convert("RGB")
        img.thumbnail((480, 480))
        img.save(os.path.join(work, "prev", f"{idx}.jpg"), quality=70)
    texts, names = [], []
    for layer in psd.descendants():
        names.append(layer.name)
        if layer.kind == "type":
            try:
                texts.append(layer.text.strip().replace("\r", " "))
            except Exception:
                pass
    info["text"] = texts
    info["layers"] = names[:40]
    with open(os.path.join(work, f"info_{idx}.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False)


def list_files(src):
    return sorted(
        f for f in os.listdir(src)
        if f.lower().endswith(EXTS) and os.path.isfile(os.path.join(src, f))
    )


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        worker(*sys.argv[2:6])
        return

    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("work")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10**9)
    ap.add_argument("--max-minutes", type=float, default=0,
                    help="stop after this many minutes (0 = no limit); rerun to continue")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per file")
    a = ap.parse_args()

    os.makedirs(os.path.join(a.work, "prev"), exist_ok=True)
    files = list_files(a.src)
    with open(os.path.join(a.work, "files.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, ensure_ascii=False)

    deadline = time.time() + a.max_minutes * 60 if a.max_minutes else None
    done = 0
    for i in range(a.start, min(a.end, len(files))):
        idx = f"{i:05d}"
        if os.path.exists(os.path.join(a.work, f"info_{idx}.json")):
            continue
        if deadline and time.time() > deadline:
            print(f"PAUSED at {i} of {len(files)} - run again to continue")
            return
        path = os.path.join(a.src, files[i])
        ok = False
        for mode in ("full", "thumb"):
            try:
                r = subprocess.run(
                    [sys.executable, os.path.abspath(__file__), "--one", path, idx, a.work, mode],
                    timeout=a.timeout, capture_output=True,
                )
                if r.returncode == 0:
                    ok = True
                    break
            except subprocess.TimeoutExpired:
                pass
        if not ok:
            with open(os.path.join(a.work, f"info_{idx}.json"), "w", encoding="utf-8") as f:
                json.dump({"file": files[i], "error": "could not open"}, f)
        done += 1
    print(f"DONE - {len(files)} files total, {done} processed this run")


if __name__ == "__main__":
    main()
