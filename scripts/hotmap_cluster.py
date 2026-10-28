"""Hot Map bước 1b: gom app mới (data/hotmap/hotmap_apps.csv) theo ngách con bằng từ khoá tên,
lọc ads + không big dev + >=5k dl/ngày -> data/hotmap/clusters.md. Chạy: python scripts/hotmap_cluster.py
Danh sách ngách con: common.CLUSTERS."""
import csv, collections
from common import DATA, cluster

rows = list(csv.DictReader((DATA / "hotmap/hotmap_apps.csv").open(encoding="utf-8")))
ok = [r for r in rows if r["ads"] == "True" and r["big_dev"] == "False" and int(r["dl_day"] or 0) >= 5000]
g = collections.defaultdict(list)
for r in ok: g[cluster(r["title"])].append(r)
md = [f"# Ngách con: app mới <=24 tháng, >=3 nước, có ads, không big dev, >=5k dl/ngày ({len(ok)}/{len(rows)})\n",
      "| ngách con | app | 8 nước | <12 tháng | median dl/ngày | top 3 (dl/ngày) |", "|---|---|---|---|---|---|"]
for n, l in sorted(g.items(), key=lambda x: -len(x[1])):
    l.sort(key=lambda r: -int(r["dl_day"]))
    med = sorted(int(r["dl_day"]) for r in l)[len(l) // 2]
    md.append(f'| {n} | {len(l)} | {sum(int(r["n_occ"]) >= 8 for r in l)} | {sum(int(r["age_days"]) <= 365 for r in l)} | {med:,} | '
              + "; ".join(f'[{r["title"][:30]}](https://play.google.com/store/apps/details?id={r["pkg"]}) ({int(r["dl_day"])//1000}k)' for r in l[:3]) + " |")
md += ["\n## Chi tiết từng ngách con\n"]
for n, l in sorted(g.items(), key=lambda x: -len(x[1])):
    if n == "Khác": continue
    md += [f"### {n}\n", "| app | dev | released | dl/ngày | iap | nước |", "|---|---|---|---|---|---|"]
    md += [f'| [{r["title"]}](https://play.google.com/store/apps/details?id={r["pkg"]}) | {r["dev"]} | {r["released"]} | {int(r["dl_day"]):,} | {r["iap"]} | {r["n_occ"]} |' for r in l]
    md.append("")
(DATA / "hotmap/clusters.md").write_text("\n".join(md), encoding="utf-8")
print("->", DATA / "hotmap/clusters.md")
