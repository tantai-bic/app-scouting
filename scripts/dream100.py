"""Build data/Dream100.md + append data/Dream100.csv từ 1 verify_*.json.
Usage: python scripts/dream100.py --verify verify_<ngách>.json --title "<ngách>" [--all]
Tên file tương đối so với data/.
"""
import argparse, csv, datetime, json
from common import DATA, DREAM_CSV, logged_pkgs, dlday_range

p = argparse.ArgumentParser()
p.add_argument("--verify", required=True)
p.add_argument("--all", action="store_true",
               help="đưa hết app vào bảng chính kể cả FAIL (theo dõi dài hạn), không chỉ PASS")
p.add_argument("--title", default=None)
args = p.parse_args()
verify_path = DATA / args.verify
TITLE = args.title or verify_path.stem.removeprefix("verify_").replace("_", " ")

apps = {a["pkg"]: a for a in json.load(open(verify_path, encoding="utf-8"))}

def dlday(a):
    lo, hi = dlday_range(a)
    return f"{lo:,} – {hi:,}" if lo is not None else "—"

# nhóm app dùng chung tài khoản AdMob (ghi bởi check_ads_txt.py) -> cột "Cùng network"
# ponytail: optional enrichment, file network scan riêng vì chậm (fetch web mỗi app) -> không
# chạy lại mỗi lần build Dream100, chỉ đọc kết quả lần quét gần nhất nếu có.
groups_path = DATA / "ads_txt_groups.json"
groups = json.loads(groups_path.read_text(encoding="utf-8")) if groups_path.exists() else {}

def network_label(pkg):
    gid = groups.get(pkg)
    if gid is None:
        return "—"
    siblings = [apps[p]["title"] for p, g in groups.items() if g == gid and p != pkg and p in apps]
    return f"Nhóm {gid}: " + ", ".join(siblings) if siblings else f"Nhóm {gid}"

rows = list(apps.values()) if args.all else [a for a in apps.values() if a.get("verdict") == "PASS"]
rows = [a for a in rows if "error" not in a]
rows.sort(key=lambda a: -(a["realInstalls"] or 0))

verdict_col = " Verdict |" if args.all else ""
verdict_sep = "---|" if args.all else ""
out = [f"# Dream 100 — ngách {TITLE}",
       f"\n_Cập nhật {datetime.date.today()} · nguồn: AppBrain (discover) + google-play-scraper (verify) + bucket installs ÷ tuổi (download/ngày)_\n",
       "Tiêu chí PASS: `containsAds=true` · phát hành ≤ 730 ngày · download/ngày trung bình ≥ 5.000 · dev không thuộc big-company blacklist."
       + (" `--all`: bảng dưới có cả app FAIL, theo dõi dài hạn chờ đủ điều kiện." if args.all else "") + "\n",
       f"| App | Package | Dev | Phát hành | Lifetime installs | DL/ngày (TB vòng đời) | DL/ngày (bucket) | Ads | IAP | Rating | Cùng network |{verdict_col}",
       f"|---|---|---|---|---|---|---|---|---|---|---|{verdict_sep}"]
for a in rows:
    line = "| [{t}](https://play.google.com/store/apps/details?id={p}) | `{p}` | {d} | {r} | {i:,} | {x:,} | {y} | {ads} | {q} | {s} ({n:,}) | {net} |".format(
        t=a["title"], p=a["pkg"], d=a["dev"], r=a["released"], i=a["realInstalls"],
        x=a["dl_per_day_rough"], y=dlday(a), ads="✅" if a["ads"] else "—", q="✅" if a["iap"] else "—",
        s=round(a["score"] or 0, 1), n=a["ratings"] or 0, net=network_label(a["pkg"]))
    if args.all:
        line += f" {a.get('verdict','')} |"
    out.append(line)

if not args.all:
    out.append("\n## Bị loại\n")
    out.append("| App | Package | Lý do |")
    out.append("|---|---|---|")
    for a in sorted(apps.values(), key=lambda a: a.get("verdict", "")):
        if a.get("verdict") != "PASS":
            out.append(f'| {a.get("title","?")} | `{a["pkg"]}` | {a.get("verdict")} |')

(DATA / "Dream100.md").write_text("\n".join(out), encoding="utf-8")
label = "app (--all)" if args.all else "PASS"
print(f"Dream100.md: {len(rows)} {label}, {len(apps)-len(rows)} loại")

CSV_HEADER = ["Ngày", "App", "Package", "Developer", "Phát hành", "Tuổi (ngày)",
              "Lifetime installs", "DL/ngày (TB vòng đời)", "DL/ngày min (bucket)",
              "DL/ngày max (bucket)", "Ads", "IAP", "Rating", "Số đánh giá", "Cùng network"]
today = datetime.date.today().isoformat()
# CSV = lịch sử tracking: app đã từng vào Dream100 vẫn ghi tiếp dù giờ FAIL (bảng .md vẫn chỉ PASS)
seen = logged_pkgs()
csv_rows = rows + [a for a in apps.values() if a["pkg"] in seen and a not in rows and "error" not in a]
with DREAM_CSV.open("a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if f.tell() == 0:
        w.writerow(CSV_HEADER)
    for a in csv_rows:
        lo, hi = dlday_range(a)
        w.writerow([today, a["title"], a["pkg"], a["dev"], a["released"], a["age_days"],
                    a["realInstalls"], a["dl_per_day_rough"], lo, hi,
                    "Có" if a["ads"] else "Không", "Có" if a["iap"] else "Không",
                    round(a["score"] or 0, 2), a["ratings"], network_label(a["pkg"])])
print(f"Dream100.csv: +{len(csv_rows)} dòng (ngày {today})")
