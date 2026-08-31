import re, json, pathlib, urllib.request, sys

cfg = pathlib.Path(r"C:\Users\Robby\AppData\Local\hermes\config.yaml").read_text()
TOKEN = re.search(r"GITHUB_PERSONAL_ACCESS_TOKEN=([^\s\"]+)", cfg).group(1)
if "..." in TOKEN:
    TOKEN = "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"

H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "cli"}
OWNER = "fahliro"
NAME = "yt-clip-crewai"

# already exists?
try:
    r = urllib.request.urlopen(urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{NAME}", headers=H), timeout=25)
    print("REPO EXISTS:", json.loads(r.read())["html_url"]); sys.exit(0)
except urllib.error.HTTPError as e:
    if e.code != 404:
        print("ERR", e.code, e.read()[:300]); sys.exit(1)

body = json.dumps({
    "name": NAME, "private": False,
    "description": "YouTube Shorts clipping pipeline powered by a CrewAI multi-agent team (download -> analyze -> cut -> caption -> review -> upload). Same LLM stack as yt-clip-automation (Groq Whisper + OpenAI-compatible chat).",
    "auto_init": False, "has_issues": True,
}).encode()
req = urllib.request.Request("https://api.github.com/user/repos", data=body,
                              headers={**H, "Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=25)
print("CREATED:", json.loads(r.read())["html_url"])
