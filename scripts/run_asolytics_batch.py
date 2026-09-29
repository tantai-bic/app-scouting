#!/usr/bin/env python3
"""Chạy `asolytics --average` tuần tự cho mọi pkg trong 1 verify_*.json, ghi kết
quả theo đúng format "===== pkg" mà dream100.py đang parse (asolytics_*.txt).

Ghi ngay sau mỗi app (không đợi xong hết) -> lỡ bị ngắt giữa chừng vẫn giữ được
kết quả đã chạy. Bỏ qua app đã có sẵn trong file output (chạy lại an toàn).

Usage: python scripts/run_asolytics_batch.py verify_<ngách>.json asolytics_<ngách>.txt
Tên file tương đối so với data/.
"""
import json, sys
from common import DATA, read_asolytics, run_asolytics

verify_file, out_file = sys.argv[1], sys.argv[2]
pkgs = [a["pkg"] for a in json.load(open(DATA / verify_file, encoding="utf-8")) if "error" not in a]

out_path = DATA / out_file
existing = set(read_asolytics(out_path))
todo = [p for p in pkgs if p not in existing]
print(f"{len(pkgs)} pkg, {len(existing)} đã có, {len(todo)} cần chạy")

for i, pkg in enumerate(todo, 1):
    print(f"[{i}/{len(todo)}] {pkg}")
    try:
        r = run_asolytics(pkg)
        body = r.stdout or r.stderr
    except Exception as e:
        body = f"lỗi: {e}"
    with out_path.open("a", encoding="utf-8") as f:
        f.write(f"===== {pkg}\n{body.strip()}\n")

print("Xong.")
