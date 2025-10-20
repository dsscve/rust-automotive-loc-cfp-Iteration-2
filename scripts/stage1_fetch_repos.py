import os
import requests
import subprocess
import sys
import time

TOKEN = os.environ.get("GITHUB_TOKEN")  # set in GitHub Actions
if not TOKEN:
    print("❌ ERROR: GITHUB_TOKEN not found in environment.")
    sys.exit(1)

TOP_N = 400
WORK_DIR = "work"
os.makedirs(WORK_DIR, exist_ok=True)

headers = {"Authorization": f"token {TOKEN}"}
repos = []
page = 1

print(f"🔍 Fetching top {TOP_N} Rust repositories by stars...")

while len(repos) < TOP_N:
    url = f"https://api.github.com/search/repositories?q=language:Rust&sort=stars&order=desc&per_page=100&page={page}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"⚠️ GitHub API returned {resp.status_code}: {resp.text}")
        break

    items = resp.json().get("items", [])
    if not items:
        break

    repos.extend(items)
    print(f"📦 Page {page} fetched ({len(repos)} total)")
    page += 1
    time.sleep(1)  # be nice to the API

repos = repos[:TOP_N]

for repo in repos:
    name = repo["full_name"]
    clone_path = os.path.join(WORK_DIR, name.replace("/", "_"))
    if os.path.exists(clone_path):
        print(f"⏩ Skipping {name} (already cloned)")
        continue
    print(f"⬇️ Cloning {name}...")
    subprocess.run(["git", "clone", "--depth=1", repo["clone_url"], clone_path], check=False)
