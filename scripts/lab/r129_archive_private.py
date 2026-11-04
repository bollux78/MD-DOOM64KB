#!/usr/bin/env python3
"""R129: prepare a LOCAL private ROM/ELF archive (never uploads any file).

Intentionally no GitHub API, git push, tokens, or artifact upload.
Destination must be outside the public repository checkout and outside source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_within(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def git_root() -> Path:
    return Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()

    root = git_root()
    source = args.run_dir.resolve(strict=True)
    stage = args.stage_dir.resolve(strict=False)
    if not source.is_dir():
        parser.error("run-dir must be an existing directory")
    if is_within(stage, root) or is_within(stage, source) or is_within(source, stage):
        parser.error("stage-dir must be outside public git checkout and source tree")
    if args.attempt < 1 or not args.run_id.isdecimal():
        parser.error("run-id must be numeric and attempt >= 1")
    if not (7 <= len(args.source_commit) <= 40
            and all(c in "0123456789abcdefABCDEF" for c in args.source_commit)):
        parser.error("source-commit must be a hexadecimal git SHA")

    files: list[Path] = []
    for variant in sorted(source.iterdir()):
        if variant.is_symlink():
            raise ValueError(f"symlink variant forbidden: {variant}")
        if not variant.is_dir() or not variant.name.startswith("c-"):
            continue
        for item in sorted(variant.iterdir()):
            if item.is_symlink():
                raise ValueError(f"symlink asset forbidden: {item}")
            if item.is_file() and (item.suffix.lower() in (".bin", ".elf")
                                   or item.name == "MANIFEST.json"):
                files.append(item)
    if not any(p.suffix.lower() == ".bin" for p in files):
        raise RuntimeError("No ROM .bin files found: refusing an empty archive")

    # Make no claims about remote persistence: this is just a safe local stage.
    stage.mkdir(parents=True, exist_ok=True)
    records = []
    for item in files:
        relative = item.relative_to(source)
        dst = stage / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        original_hash = sha256(item)
        if dst.exists():
            if dst.is_symlink() or not dst.is_file() or sha256(dst) != original_hash:
                raise RuntimeError(f"Existing destination mismatch: {dst}")
        else:
            shutil.copy2(item, dst)
        if sha256(dst) != original_hash:
            raise RuntimeError(f"SHA256 mismatch after copy: {dst}")
        records.append({
            "path": relative.as_posix(),
            "bytes": item.stat().st_size,
            "sha256": original_hash,
        })

    manifest = {
        "schema": "md-doom-private-archive-v1",
        "source_repo": "bollux78/MD-DOOM64KB",
        "source_commit": args.source_commit,
        "workflow": args.workflow,
        "run_id": args.run_id,
        "attempt": args.attempt,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "remote_backup_verified": False,
        "files": records,
    }
    manifest_path = stage / "MANIFEST-PRIVATE.json"
    if manifest_path.is_symlink():
        raise RuntimeError("Manifest may not be a symlink")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Prepared {len(records)} files in local staging: {stage}")
    print("Remote backup NOT performed or verified.")


if __name__ == "__main__":
    main()
