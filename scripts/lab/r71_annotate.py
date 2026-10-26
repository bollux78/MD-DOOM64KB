#!/usr/bin/env python3
"""Print a text file as chunked GitHub workflow-command notices (the sandbox cannot download artifacts, annotations are readable).
Usage: r71_annotate.py --title T --file F [--chunk 12000] [--max 10] [--skip 0]"""
import argparse, pathlib


def enc(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True); ap.add_argument("--file", required=True)
    ap.add_argument("--chunk", type=int, default=12000); ap.add_argument("--max", type=int, default=10); ap.add_argument("--skip", type=int, default=0)
    a = ap.parse_args()
    p = pathlib.Path(a.file)
    if not p.is_file():
        print("::warning title=%s::file missing: %s" % (a.title, a.file)); return
    text = p.read_text(errors="replace")
    # split on line boundaries so listings stay readable
    chunks, cur = [], ""
    for line in text.splitlines(keepends=True):
        if len(cur) + len(line) > a.chunk and cur:
            chunks.append(cur); cur = ""
        cur += line
    if cur: chunks.append(cur)
    chunks = chunks[a.skip:a.skip + a.max]
    for i, c in enumerate(chunks):
        print("::notice title=%s (%d/%d)::%s" % (a.title, a.skip + i + 1, len(chunks) + a.skip, enc(c)))


if __name__ == "__main__":
    main()
