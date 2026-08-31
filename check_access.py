import re, json, pathlib, urllib.request, urllib.error
cfg = pathlib.Path(r"C:\Users\Robby\AppData\Local\hermes\config.yaml").read_text()
TOKEN = re.search(r"GITHUB_PERSONAL_ACCESS_TOKEN=([^\s\"]+)", cfg).group(1)
TOKEN = TOKEN if "..." not in TOKEN else "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"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "cli"}
OWNER, NAME = "fahliro", "yt-clip-crewai"

# 1) exists?
try:
    r = urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{NAME}", headers=H), timeout=20)
    d = json.loads(r.read())
    print("REPO EXISTS:", d["html_url"], "| private:", d.get("private"))
    print("ACTION: siap git push (remote add origin)")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("REPO BELUM ADA (404). Coba create...")
        body = json.dumps({"name": NAME, "private": False}).encode()
        req = urllib.request.Request("https://api.github.com/user/repos", data=body,
                                      headers={**H, "Content-Type": "application/json"}, method="POST")
        try:
            r = urllib.request.urlopen(req, timeout=20)
            print("CREATED:", json.loads(r.read())["html_url"])
        except urllib.error.HTTPError as e2:
            print("CREATE GAGAL:", e2.code, e2.read()[:200].decode(errors="replace"))
    else:
        print("GET ERR", e.code, e.read()[:200].decode(errors="replace"))
