import os
import requests
import subprocess

TOKEN = os.environ.get("GITHUB_TOKEN")  # set in GitHub Actions
TOP_N = 400
WORK_DIR = "work"

os.makedirs(WORK_DIR, exist_ok=True)
headers = {"Authorization": f"token {TOKEN}"}

repos = []
page = 1
while len(repos) < TOP_N:
    url = f"https://api.github.com/search/repositories?q=language:Rust&sort=stars&order=desc&per_page=100&page={page}"
    resp = requests.get(url, headers=headers).json()
    items = resp.get("items", [])
    if not items:
        break
    repos.extend(items)
    page += 1

repos = repos[:TOP_N]

for repo in repos:
    name = repo["full_name"]
    clone_path = os.path.join(WORK_DIR, name.replace("/", "_"))
    if not os.path.exists(clone_path):
        print(f"Cloning {name}...")
        subprocess.run(["git", "clone", "--depth=1", repo["clone_url"], clone_path])
