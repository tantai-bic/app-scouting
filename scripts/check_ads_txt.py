#!/usr/bin/env python3
"""Quét app-ads.txt (IAB standard) của từng app trong verify_out.json để tìm app
nào dùng CHUNG publisher/seller ID (AdMob pub-xxx, AppLovin id...) -> tín hiệu
cùng 1 network/studio đứng sau dù Play Store hiện tên developer khác nhau.

Nguồn website: field developerWebsite của google-play-scraper (app-ads.txt luôn
nằm ở root domain, không phải path bất kỳ). Không phải app nào cũng có file này
(dev nhỏ lẻ, hoặc site không host) -> bỏ qua, không coi là lỗi.

Usage: python scripts/check_ads_txt.py verify_<ngách>.json   (tương đối so với data/)
Ghi data/ads_txt/<pkg>.txt (raw), data/ads_txt_report.md, data/ads_txt_groups.json.
"""
import json, sys
from urllib.parse import urlparse
import requests
from google_play_scraper import app as gp_app

from common import DATA

SRC = sys.argv[1] if len(sys.argv) > 1 else "verify_out.json"
OUT_DIR = DATA / "ads_txt"
OUT_DIR.mkdir(exist_ok=True)

apps = [a for a in json.load(open(DATA / SRC, encoding="utf-8")) if a.get("verdict") == "PASS"]

def fetch_app_ads(pkg):
    try:
        site = gp_app(pkg, lang="en", country="us").get("developerWebsite")
    except Exception as e:
        return None, f"lookup lỗi: {e}"
    if not site:
        return None, "không có developerWebsite"
    root = urlparse(site)
    url = f"{root.scheme}://{root.netloc}/app-ads.txt"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        return None, f"fetch lỗi: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code} tại {url}"
    return r.text, None

# entries[key] = [(pkg, title, relationship), ...]   key = (network_domain, publisher_id)
entries = {}
skipped = []
for a in apps:
    pkg = a["pkg"]
    text, err = fetch_app_ads(pkg)
    if err:
        skipped.append((pkg, a["title"], err))
        continue
    (OUT_DIR / f"{pkg}.txt").write_text(text, encoding="utf-8")
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        domain, pub_id, rel = parts[0].lower(), parts[1], parts[2].upper()
        entries.setdefault((domain, pub_id), []).append((pkg, a["title"], rel))

titles = {a["pkg"]: a["title"] for a in apps}
shared = {k: {pkg for pkg, _, _ in v} for k, v in entries.items() if len({pkg for pkg, _, _ in v}) > 1}

# ponytail: RESELLER lines are boilerplate most ad SDKs bundle for every client app regardless
# of who actually uses them -> matching there is weak/noisy. A DIRECT google.com (AdMob) pub-id
# is Google-verified per account, so 2+ apps BOTH declaring it DIRECT is the one strong "same
# real owner" signal — a pub-id showing up as RESELLER elsewhere means mediation routing through
# that account, not co-ownership, so it must NOT count toward the same group.
admob_direct = {}
for (domain, pub), rows in entries.items():
    if domain != "google.com":
        continue
    direct_pkgs = {pkg for pkg, _, rel in rows if rel == "DIRECT"}
    if len(direct_pkgs) > 1:
        admob_direct[pub] = direct_pkgs

# gộp các app nối nhau qua bất kỳ pub-id chung nào thành 1 cụm (union-find đơn giản)
parent = {pkg: pkg for pkgs in admob_direct.values() for pkg in pkgs}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
for pkgs in admob_direct.values():
    pkgs = list(pkgs)
    for p in pkgs[1:]:
        union(pkgs[0], p)
clusters = {}
for pkg in parent:
    clusters.setdefault(find(pkg), set()).add(pkg)
clusters = [c for c in clusters.values() if len(c) > 1]

print(f"Quét {len(apps)} app, {len(apps) - len(skipped)} có app-ads.txt, {len(skipped)} bỏ qua.\n")
if clusters:
    print(f"=== {len(clusters)} nhóm app dùng CHUNG tài khoản AdMob (DIRECT) — tín hiệu mạnh nhất ===")
    for i, cluster in enumerate(clusters, 1):
        print(f"\nNhóm {i}:")
        for pkg in sorted(cluster):
            print(f"  - {titles[pkg]} ({pkg})")
else:
    print("Không app nào chung tài khoản AdMob DIRECT.")

other = len(shared) - len(admob_direct)
if other:
    print(f"\n({other} publisher ID khác cũng trùng giữa nhiều app, nhưng phần lớn là dòng RESELLER"
          f" — boilerplate do chung SDK/mediation, không chắc là cùng chủ. Full raw trong data/ads_txt/*.txt)")

if skipped:
    print(f"\n=== Bỏ qua ({len(skipped)}) ===")
    for pkg, title, why in skipped:
        print(f"  {title} ({pkg}): {why}")

report = [f"# Ads.txt shared-account check ({SRC})\n",
          f"Quét {len(apps)} app, {len(apps) - len(skipped)} có app-ads.txt.\n"]
for i, cluster in enumerate(clusters, 1):
    report.append(f"## Nhóm {i} — chung tài khoản AdMob (DIRECT)\n")
    for pkg in sorted(cluster):
        report.append(f"- {titles[pkg]} (`{pkg}`)")
    report.append("")
(DATA / "ads_txt_report.md").write_text("\n".join(report), encoding="utf-8")

# pkg -> group id, dùng để dream100.py join vào cột "Cùng network"
groups = {pkg: i for i, cluster in enumerate(clusters, 1) for pkg in cluster}
(DATA / "ads_txt_groups.json").write_text(json.dumps(groups, indent=1), encoding="utf-8")
print(f"\nBáo cáo: data/ads_txt_report.md, data/ads_txt_groups.json")
