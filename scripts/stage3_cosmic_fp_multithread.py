import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tree_sitter import Language, Parser

# --- Load Rust parser ---
RUST_LANGUAGE = Language('build/my-languages.so', 'rust')
parser = Parser()
parser.set_language(RUST_LANGUAGE)

def get_code_snippet(node, code_bytes):
    return code_bytes[node.start_byte:node.end_byte].decode('utf-8')

def collect_fps(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    code_bytes = bytes(code, 'utf-8')
    tree = parser.parse(code_bytes)
    root = tree.root_node
    fps = {}

    def visit(node):
        if node.type == 'function_item' and 'pub' in get_code_snippet(node, code_bytes):
            fp_name = get_code_snippet(node, code_bytes).split('{')[0].strip()
            fps[fp_name] = node
        if node.type == 'impl_item':
            struct_node = next((c for c in node.children if c.type == 'type_identifier'), None)
            if struct_node:
                for child in node.children:
                    if child.type == 'function_item':
                        fp_name = f"{get_code_snippet(struct_node, code_bytes)}::{get_code_snippet(child, code_bytes).split('{')[0].strip()}"
                        fps[fp_name] = child
        for child in node.children:
            visit(child)

    visit(root)
    return fps, code_bytes

def analyze_fp(node, code_bytes, fp_names):
    E = X = R = W = 0
    param_nodes = [c for c in node.children if c.type == 'parameters']
    for params in param_nodes:
        E += len([p for p in params.children if p.type == 'parameter'])
    if any(c.type == 'type' for c in node.children):
        X += 1
    block_node = next((c for c in node.children if c.type == 'block'), None)
    if block_node:
        stack = [block_node]
        while stack:
            n = stack.pop()
            snippet = get_code_snippet(n, code_bytes)
            if n.type == 'macro_invocation' and 'println' in snippet:
                X += 1
            if any(r in snippet for r in ['std::fs::read', 'File::open']):
                R += 1
            if any(w in snippet for w in ['std::fs::write', 'write_all', 'BufWriter']):
                W += 1
            if any(db in snippet for db in ['sqlx::query!', 'diesel::insert_into', 'diesel::load']):
                if 'insert' in snippet or 'update' in snippet:
                    W += 1
                else:
                    R += 1
            if any(net in snippet for net in ['reqwest::get', 'reqwest::post', 'TcpStream']):
                E += 1
                X += 1
            stack.extend(n.children)
    return E, X, R, W

def process_rs_file(rs_file):
    fps_dict, code_bytes = collect_fps(rs_file)
    fp_names = set(fps_dict.keys())
    e_total = x_total = r_total = w_total = 0
    for fp_node in fps_dict.values():
        e, x, r, w = analyze_fp(fp_node, code_bytes, fp_names)
        e_total += e
        x_total += x
        r_total += r
        w_total += w
    return e_total, x_total, r_total, w_total

input_csv = "rust_loc_results.csv"
output_csv = "rust_loc_results_with_fp_multithread.csv"

total_eloc = total_cfp = 0

with open(input_csv) as infile, open(output_csv, 'w', newline='') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ["Entry", "Exit", "Read", "Write", "CFP", "eLOC_per_CFP"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        repo = row["repo"]
        repo_dir = os.path.join("work", repo.replace("/", "_"))
        e_total = x_total = r_total = w_total = 0

        if os.path.exists(repo_dir):
            rs_files = [
                os.path.join(root, f)
                for root, _, files in os.walk(repo_dir)
                for f in files if f.endswith(".rs")
            ]

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(process_rs_file, rs_file): rs_file for rs_file in rs_files}
                for future in as_completed(futures):
                    e, x, r, w = future.result()
                    e_total += e
                    x_total += x
                    r_total += r
                    w_total += w

        cfp = e_total + x_total + r_total + w_total
        eloc = int(row.get("rust_code", 0) or 0)
        ratio = round(eloc / cfp, 2) if cfp > 0 else 0

        total_eloc += eloc
        total_cfp += cfp

        row.update({
            "Entry": e_total,
            "Exit": x_total,
            "Read": r_total,
            "Write": w_total,
            "CFP": cfp,
            "eLOC_per_CFP": ratio
        })
        writer.writerow(row)

    avg_ratio = round(total_eloc / total_cfp, 2) if total_cfp > 0 else 0
    writer.writerow({
        "repo": "TOTAL SUMMARY",
        "rust_files": "",
        "rust_code": total_eloc,
        "rust_comments": "",
        "rust_blanks": "",
        "Entry": "",
        "Exit": "",
        "Read": "",
        "Write": "",
        "CFP": total_cfp,
        "eLOC_per_CFP": avg_ratio
    })

print(f"✅ Results written to {output_csv}")
