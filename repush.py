import os, subprocess, pathlib, sys

LOCAL = pathlib.Path(r"C:\Users\Robby\yt-clip-crewai")
PAT = os.environ["PAT"]
OWNER, NAME = "fahliro", "yt-clip-crewai"
os.chdir(LOCAL)

def run(cmd):
    print("RUN", " ".join(cmd[:3]))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode:
        print("  ->", r.stdout.strip()[:200], r.stderr.strip()[:200])
        return r.returncode
    return 0

# 1) add .gitignore fix, then untrack everything already tracked, re-add respecting gitignore
run(["git", "rm", "-r", "--cached", "--quiet", "."])          # untrack all
run(["git", "add", "-A"])                                     # re-add (gitignore now excludes .venv etc)
run(["git", "commit", "-q", "-m", "chore: drop .venv + helper scripts from repo (gitignore)"])
url = f"https://{PAT}@github.com/{OWNER}/{NAME}.git"
run(["git", "remote", "remove", "origin"])
run(["git", "remote", "add", "origin", url])
run(["git", "push", "-u", "-f", "origin", "main"])
print("DONE")
