"""Hot Map bước 1: từ data/hotmap/top_free.json lấy chi tiết app (cache details.json),
lọc app phát hành <=730 ngày, dựng bảng nước × category -> data/hotmap/hotmap.md + hotmap_apps.csv.
Chạy: python scripts/hotmap.py
"""
import csv, json, collections, socket
socket.setdefaulttimeout(20)  # ponytail: scraper không có timeout, 1 request treo là kẹt cả batch
from concurrent.futures import ThreadPoolExecutor
from common import DATA
from verify import check

HM = DATA / "hotmap"
MAX_AGE = 730
rows = json.loads((HM / "top_free.json").read_text(encoding="utf-8"))
cache_f = HM / "details.json"
details = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
todo = sorted({r["appId"] for r in rows} - details.keys())
print("fetch", len(todo))
with ThreadPoolExecutor(8) as ex:
    for i, c in enumerate(ex.map(check, todo), 1):
        details[c["pkg"]] = c
        if i % 200 == 0:
            cache_f.write_text(json.dumps(details), encoding="utf-8"); print(i, flush=True)
cache_f.write_text(json.dumps(details), encoding="utf-8")

new = {p for p, d in details.items() if d.get("age_days") is not None and d["age_days"] <= MAX_AGE}
cnt = collections.Counter((r["country"], r["cat"]) for r in rows if r["appId"] in new)
countries = sorted({r["country"] for r in rows}); cats = sorted({r["cat"] for r in rows})
md = ["# Hot Map: số app mới (<=24 tháng) trong Top Free 200\n",
      "| cat / nước | " + " | ".join(countries) + " | tổng |", "|---|" + "---|" * (len(countries) + 1)]
for c in cats:
    vals = [cnt[(k, c)] for k in countries]
    md.append(f"| {c} | " + " | ".join(map(str, vals)) + f" | {sum(vals)} |")
md.append("| tổng | " + " | ".join(str(sum(cnt[(k, c)] for c in cats)) for k in countries) + f" | {sum(cnt.values())} |")

# app mới xuất hiện ở nhiều nước nhất, kèm chi tiết
by_app = collections.defaultdict(list)
for r in rows:
    if r["appId"] in new: by_app[r["appId"]].append(f'{r["country"]}:{r["cat"]}#{r["rank"]}')
md += ["\n## App mới lọt top ở >=3 nước\n", "| app | dev | released | installs | dl/day | ads | iap | big | xuất hiện |", "|---|---|---|---|---|---|---|---|---|"]
for p, occ in sorted(by_app.items(), key=lambda x: -len(x[1])):
    if len(occ) < 3: break
    d = details[p]
    md.append(f'| [{d["title"]}](https://play.google.com/store/apps/details?id={p}) | {d["dev"]} | {d["released"]} | {d["realInstalls"]:,} | {d["dl_per_day_rough"]:,} | {d["ads"]} | {d["iap"]} | {d["big_dev"]} | {len(occ)}: {" ".join(occ)} |')
(HM / "hotmap.md").write_text("\n".join(md), encoding="utf-8")
with (HM / "hotmap_apps.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["pkg", "title", "dev", "released", "age_days", "installs", "dl_day", "ads", "iap", "big_dev", "genre", "n_occ", "occ"])
    for p, occ in sorted(by_app.items(), key=lambda x: -len(x[1])):
        d = details[p]; w.writerow([p, d["title"], d["dev"], d["released"], d["age_days"], d["realInstalls"], d["dl_per_day_rough"], d["ads"], d["iap"], d["big_dev"], d["genre"], len(occ), " ".join(occ)])
print("new apps", len(new), "-> data/hotmap/hotmap.md")
