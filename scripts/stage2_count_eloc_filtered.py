import os
import csv
import subprocess
import json
import time

WORK_DIR = "work"
OUTPUT_CSV = "rust_loc_results.csv"
RUST_PERCENT_THRESHOLD = 80  # Only keep repos with Rust > 80%

rows = []

for repo_dir in os.listdir(WORK_DIR):
    repo_path = os.path.join(WORK_DIR, repo_dir)
    if not os.path.isdir(repo_path):
        continue

    print(f"🧮 Analyzing {repo_dir}...")
    result = subprocess.run(["tokei", repo_path, "--output", "json"], capture_output=True, text=True)
    if not result.stdout.strip():
        print(f"⚠️ Empty Tokei output for {repo_dir}, skipping.")
        continue

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON from Tokei for {repo_dir}, skipping.")
        continue

    rust_data = data.get("Rust", {})
    total_rust = rust_data.get("code", 0)
    comments = rust_data.get("comments", 0)
    blanks = rust_data.get("blanks", 0)
    rust_files = rust_data.get("files", 0)

    total_code = sum(lang.get("code", 0) for lang in data.values() if isinstance(lang, dict))
    rust_percent = (total_rust / total_code * 100) if total_code > 0 else 0

    if rust_percent >= RUST_PERCENT_THRESHOLD:
        rows.append({
            "repo": repo_dir,
            "rust_files": rust_files,
            "rust_code": total_rust,
            "rust_comments": comments,
            "rust_blanks": blanks,
            "rust_percent": round(rust_percent, 2)
        })
    else:
        print(f"🚫 Skipping {repo_dir}: Rust {rust_percent:.2f}% < {RUST_PERCENT_THRESHOLD}%")

    time.sleep(0.5)

with open(OUTPUT_CSV, 'w', newline='') as f:
    fieldnames = ["repo", "rust_files", "rust_code", "rust_comments", "rust_blanks", "rust_percent"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Results saved to {OUTPUT_CSV} ({len(rows)} repos kept).")
