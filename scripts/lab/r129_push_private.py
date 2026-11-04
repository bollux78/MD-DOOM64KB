#!/usr/bin/env python3
"""R129: push a staged private archive (from r129_archive_private.py) to bollux78/MD-DOOM-PRIVATE and verify it.

Fail-closed rules:
  - the target repository must NOT be publicly visible: an unauthenticated GitHub API request must return 404
    (a 200 means public -> abort before any push);
  - authentication only through a deploy key file outside the public checkout ($R129_KEY, default
    ~/.ssh/md_doom_private_deploy, mode 0600); nothing secret is printed or written to the workspace;
  - after the push, the remote is fetched again and every file's git blob id on origin must equal the local
    file's; only then MANIFEST-PRIVATE.json gets remote_backup_verified=true (in the private repo and stage).
Never deletes the local originals or the stage.
Usage: r129_push_private.py --stage DIR --clone DIR --dest builds/r126b/run-41882892479-1 [--catalog OUT.json]
"""
import argparse, json, os, pathlib, shutil, stat, subprocess, sys, urllib.error, urllib.request

REPO = "bollux78/MD-DOOM-PRIVATE"
URL = "git@github.com:%s.git" % REPO


def run(cmd, cwd=None, env=None, capture=False):
    r = subprocess.run(cmd, cwd=cwd, env=env, check=True, text=True, capture_output=capture)
    return r.stdout.strip() if capture else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=pathlib.Path, required=True); ap.add_argument("--clone", type=pathlib.Path, required=True)
    ap.add_argument("--dest", required=True); ap.add_argument("--catalog", type=pathlib.Path)
    a = ap.parse_args()
    dest = pathlib.PurePosixPath(a.dest)
    assert not dest.is_absolute() and ".." not in dest.parts and dest.parts[0] == "builds", dest
    stage = a.stage.resolve(strict=True); man = json.loads((stage / "MANIFEST-PRIVATE.json").read_text())
    ws = os.environ.get("GITHUB_WORKSPACE")
    for p in (stage, a.clone.resolve()):
        if ws and (p == pathlib.Path(ws).resolve() or pathlib.Path(ws).resolve() in p.parents):
            sys.exit("R129: stage/clone must be outside the public checkout")
    # 1. Visibility: anonymous API must NOT see the repository.
    try:
        urllib.request.urlopen("https://api.github.com/repos/" + REPO, timeout=20)
        sys.exit("R129 ABORT: %s is publicly visible (anonymous API 200). Nothing pushed." % REPO)
    except urllib.error.HTTPError as e:
        if e.code != 404: sys.exit("R129 ABORT: visibility check returned HTTP %d. Nothing pushed." % e.code)
    except Exception as e:
        sys.exit("R129 ABORT: visibility check failed (%s). Nothing pushed." % type(e).__name__)
    # 2. Deploy key.
    key = pathlib.Path(os.environ.get("R129_KEY", str(pathlib.Path.home() / ".ssh/md_doom_private_deploy")))
    if not key.is_file(): sys.exit("R129 ABORT: deploy key not found (set R129_KEY). Nothing pushed.")
    if stat.S_IMODE(key.stat().st_mode) & 0o077: sys.exit("R129 ABORT: deploy key permissions must be 0600.")
    env = dict(os.environ, GIT_SSH_COMMAND="ssh -i %s -o IdentitiesOnly=yes -o BatchMode=yes" % key, GIT_TERMINAL_PROMPT="0")
    # 3. Clone/update.
    if not (a.clone / ".git").is_dir():
        a.clone.parent.mkdir(parents=True, exist_ok=True); run(["git", "clone", "-q", URL, str(a.clone)], env=env)
    branch = run(["git", "symbolic-ref", "--short", "HEAD"], cwd=a.clone, capture=True)
    run(["git", "pull", "-q", "--ff-only", "origin", branch], cwd=a.clone, env=env)
    run(["git", "config", "user.name", "md-doom-runner"], cwd=a.clone); run(["git", "config", "user.email", "md-doom-runner@users.noreply.github.com"], cwd=a.clone)
    # 4. Copy (never overwrite a different file).
    target = a.clone / dest
    for rec in man["files"]:
        src = stage / rec["path"]; dst = target / rec["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if run(["git", "hash-object", str(dst)], capture=True) != run(["git", "hash-object", str(src)], capture=True):
                sys.exit("R129 ABORT: %s already archived with different content." % (dest / rec["path"]))
        else:
            shutil.copy2(src, dst)
    shutil.copy2(stage / "MANIFEST-PRIVATE.json", target / "MANIFEST-PRIVATE.json")
    run(["git", "add", "--", str(dest)], cwd=a.clone)
    if run(["git", "status", "--porcelain", "--", str(dest)], cwd=a.clone, capture=True):
        run(["git", "commit", "-q", "-m", "Archive %s (%s run %s-%s, %s)" % (dest, man["workflow"], man["run_id"], man["attempt"], man["source_commit"][:12])], cwd=a.clone)
        run(["git", "push", "-q", "origin", branch], cwd=a.clone, env=env)
    # 5. Verify against a fresh fetch of the remote.
    run(["git", "fetch", "-q", "origin", branch], cwd=a.clone, env=env)
    bad = []
    for rec in man["files"]:
        rp = "%s/%s" % (dest, rec["path"])
        try:
            remote = run(["git", "rev-parse", "origin/%s:%s" % (branch, rp)], cwd=a.clone, capture=True)
        except subprocess.CalledProcessError:
            remote = None
        if remote != run(["git", "hash-object", str(stage / rec["path"])], capture=True): bad.append(rp)
    if bad: sys.exit("R129 VERIFY FAILED (%d files): %s" % (len(bad), bad[:5]))
    man["remote_backup_verified"] = True; man["remote"] = {"repo": REPO, "branch": branch, "path": str(dest),
                                                          "commit": run(["git", "rev-parse", "origin/" + branch], cwd=a.clone, capture=True)}
    txt = json.dumps(man, indent=2, ensure_ascii=False) + "\n"
    (stage / "MANIFEST-PRIVATE.json").write_text(txt); (target / "MANIFEST-PRIVATE.json").write_text(txt)
    run(["git", "add", "--", str(dest / "MANIFEST-PRIVATE.json")], cwd=a.clone)
    if run(["git", "status", "--porcelain"], cwd=a.clone, capture=True):
        run(["git", "commit", "-q", "-m", "Verified %s" % dest], cwd=a.clone); run(["git", "push", "-q", "origin", branch], cwd=a.clone, env=env)
    if a.catalog:   # public-safe: hashes and ids only, no local paths
        a.catalog.write_text(json.dumps({"dest": str(dest), "source_commit": man["source_commit"], "workflow": man["workflow"],
                                         "run_id": man["run_id"], "attempt": man["attempt"], "private_commit": man["remote"]["commit"],
                                         "files": [{"path": r["path"], "bytes": r["bytes"], "sha256": r["sha256"]} for r in man["files"]],
                                         "remote_backup_verified": True}, indent=1) + "\n")
    print("R129 archived and verified: %s (%d files, private commit %s)" % (dest, len(man["files"]), man["remote"]["commit"][:12]))


if __name__ == "__main__":
    main()
