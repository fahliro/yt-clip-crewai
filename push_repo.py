import os, re, json, pathlib, subprocess, urllib.request, urllib.error, sys

LOCAL = pathlib.Path(r"C:\Users\Robby\yt-clip-crewai")
PAT = os.environ["PAT"]
OWNER, NAME = "fahliro", "yt-clip-crewai"
H = {"Authorization": f"Bearer {PAT}", "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "cli"}

# 1) create repo (public)
try:
    r = urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{NAME}", headers=H), timeout=20)
    print("REPO SUDAH ADA:", json.loads(r.read())["html_url"])
except urllib.error.HTTPError as e:
    if e.code == 404:
        body = json.dumps({
            "name": NAME, "private": False,
            "description": "YouTube Shorts clipping pipeline powered by a CrewAI multi-agent team (same LLM stack as yt-clip-automation: Groq Whisper + OpenAI-compatible chat).",
            "has_issues": True,
        }).encode()
        req = urllib.request.Request("https://api.github.com/user/repos", data=body,
                                      headers={**H, "Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=25)
        print("CREATED:", json.loads(r.read())["html_url"])
    else:
        print("ERR", e.code, e.read()[:300].decode(errors="replace")); sys.exit(1)

# 2) git init + commit + push
os.chdir(LOCAL)
url = f"https://{PAT}@github.com/{OWNER}/{NAME}.git"
for cmd in (["git", "init", "-q"],
            ["git", "config", "user.email", "bot@github.com"],
            ["git", "config", "user.name", "clip-bot"],
            ["git", "config", "pull.rebase", "false"],
            ["git", "remote", "remove", "origin"],
            ["git", "remote", "add", "origin", url],
            ["git", "add", "-A"],
            ["git", "commit", "-q", "-m", "init: CrewAI yt-clip pipeline"],
            ["git", "branch", "-M", "main"],
            ["git", "push", "-u", "-f", "origin", "main"]):
    print("RUN", " ".join(cmd[:3]))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if out.returncode:
            print("  ->", out.stdout.strip()[:200], out.stderr.strip()[:200])
    except subprocess.TimeoutExpired as te:
        print("  TIMEOUT", te)
print("DONE")
