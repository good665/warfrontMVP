"""Download the official portable client and verify GitHub's asset SHA-256."""
import hashlib
import json
from pathlib import Path
import platform
import urllib.request

TOOLS = Path(__file__).resolve().parents[1] / ".tools"
RELEASE = "https://api.github.com/repos/cloudflare/cloudflared/releases/latest"


def install():
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("This portable installer supports Windows x64")
    headers = {"User-Agent": "Warfront-Test-Server", "Accept": "application/vnd.github+json"}
    with urllib.request.urlopen(urllib.request.Request(RELEASE, headers=headers), timeout=30) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == "cloudflared-windows-amd64.exe")
    digest = asset.get("digest", "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise RuntimeError("Official release has no verifiable SHA-256 digest; refusing to execute an unverified client")
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/cloudflare/cloudflared/releases/download/"):
        raise RuntimeError("Unexpected release download source")
    TOOLS.mkdir(exist_ok=True)
    target = TOOLS / "cloudflared.exe"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Warfront-Test-Server"}), timeout=60) as response:
        data = response.read(100_000_001)
    if len(data) > 100_000_000 or hashlib.sha256(data).hexdigest() != digest[7:]:
        raise RuntimeError("Release digest mismatch")
    target.write_bytes(data)
    metadata = {"version": release["tag_name"], "sha256": digest[7:], "source": url}
    (TOOLS / "cloudflared.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"installed": str(target), "version": release["tag_name"], "sha256_verified": True}))


if __name__ == "__main__":
    install()
