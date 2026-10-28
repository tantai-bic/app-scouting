#!/usr/bin/env python3
"""Theo dõi THỊ TRƯỜNG ngách, so sánh công bằng: mỗi ngách (common.CLUSTERS) và mỗi category Play
lấy đúng TOP_N app, xếp theo độ phủ Top Free 200 của 8 nước (data/hotmap/top_free.json, tạo bởi
`node scripts/hotmap_list.mjs`), scrape installs hằng ngày rồi chấm điểm "nên làm".

Khác Dream100 (chỉ app PASS = đã lọc sẵn người thắng): đây là MẪU THỊ TRƯỜNG cùng cỡ cho mọi ngách.

Điểm 0-100 = trung bình có trọng số của hạng phần trăm giữa các nhóm cùng cấp
(trọng số theo docs/tieu-chi-chon-ngach.md, "nhân đôi" = ×2):
  Cầu        ×1  median tăng installs/ngày mỗi app (30 ngày; lịch sử < 7 ngày thì TB vòng đời installs ÷ tuổi)
  Toàn cầu   ×1  số nước trung bình mỗi app lọt Top Free 200 (trên 8 nước)
  App thắng  ×2  số app < 2 năm, có ads, không big dev, tăng >= 5k/ngày ("số app thắng lặp lại")
  Thói quen  ×2  median % review nhắc dùng hằng ngày ("retention đối thủ", review EN/US)
  IAA        ×1  % app có ads
Ngách rớt nhóm B (common.POLICY_OUT) vẫn theo dõi nhưng không chấm điểm.

Ghi: data/market.csv (lịch sử 1 dòng/app/ngày), data/market.md, data/market_reviews.json (cache 7 ngày),
Postgres scouting.market_app + scouting.market_group (nếu có DATABASE_URL).
Usage: python scripts/market.py
"""
import csv, datetime, json, re, socket, statistics
from concurrent.futures import ThreadPoolExecutor
from google_play_scraper import Sort, reviews
from common import DATA, POLICY_OUT, cluster, pg_replace
from verify import check

socket.setdefaulttimeout(20)  # ponytail: scraper không có timeout, 1 request treo là kẹt cả batch
TOP_N = 10
WEIGHTS = {"demand": 1, "global": 1, "winners": 2, "habit": 2, "iaa": 1}
HM = DATA / "hotmap"
CSV_F = DATA / "market.csv"
REV_F = DATA / "market_reviews.json"
TODAY = datetime.date.today().isoformat()
HABIT = re.compile(r"\b(every ?day|daily|every (night|morning)|all the time|use it (a lot|often)"
                   r"|for (months|years)|since \d{4})\b", re.I)
COLS = ["Ngày", "Package", "App", "Developer", "Ngách", "Phát hành", "Tuổi (ngày)", "Installs",
        "Ads", "Big dev", "Rating", "Số đánh giá", "Số nước", "Độ phủ chart"]

# --- 1. mẫu: top N mỗi nhóm theo độ phủ chart (lọt top nhiều nước + hạng cao -> điểm lớn)
title, countries, cats, presence = {}, {}, {}, {}
for r in json.loads((HM / "top_free.json").read_text(encoding="utf-8")):
    p = r["appId"]
    title[p] = r["title"]
    countries.setdefault(p, set()).add(r["country"])
    cats.setdefault(p, set()).add(r["cat"])
    presence[p] = presence.get(p, 0) + (201 - r["rank"]) / 200
groups = {}
for p in presence:
    if (c := cluster(title[p])) != "Khác":
        groups.setdefault(("Ngách", c), []).append(p)
    for cat in cats[p]:
        groups.setdefault(("Category", cat), []).append(p)
groups = {k: sorted(v, key=lambda p: -presence[p])[:TOP_N] for k, v in groups.items()}
selected = sorted({p for v in groups.values() for p in v})

# --- 2. installs hôm nay
with ThreadPoolExecutor(8) as ex:
    det = {c["pkg"]: c for c in ex.map(check, selected) if "error" not in c and c.get("realInstalls")}
print(f"{len(groups)} nhóm, {len(selected)} app, scrape OK {len(det)}")


def row(d, p, a):
    return [d, p, a["title"], a["dev"], cluster(a["title"]), a["released"], a["age_days"], a["realInstalls"],
            "Có" if a["ads"] else "Không", "Có" if a["big_dev"] else "Không", round(a["score"] or 0, 2),
            a["ratings"], len(countries.get(p, ())), round(presence.get(p, 0), 2)]


# --- 3. lịch sử: ghi lại cả file, bỏ dòng hôm nay cũ -> chạy lại trong ngày an toàn
hist = list(csv.reader(CSV_F.open(encoding="utf-8", newline="")))[1:] if CSV_F.exists() else []
if not hist and (HM / "details.json").exists():
    # ponytail: lần đầu lấy mốc từ cache Hot Map (details.json) -> có tăng trưởng ngay từ hôm nay,
    # ngày mốc = ngày sửa file cache
    seed = datetime.date.fromtimestamp((HM / "details.json").stat().st_mtime).isoformat()
    cache = json.loads((HM / "details.json").read_text(encoding="utf-8"))
    hist = [row(seed, p, cache[p]) for p in selected
            if seed != TODAY and p in cache and cache[p].get("realInstalls") and "title" in cache[p]]
hist = [r for r in hist if r[0] != TODAY] + [row(TODAY, p, a) for p, a in det.items()]
with CSV_F.open("w", encoding="utf-8", newline="") as f:
    csv.writer(f).writerows([COLS] + hist)

inst, runs = {}, {}
for r in sorted(hist):
    inst[(r[0], r[1])] = int(r[7])
    runs.setdefault(r[1], []).append(r[0])


def rate(p, n):
    """-> (installs tăng/ngày, số ngày) so với lần chạy gần nhất cách >= n ngày (thiếu thì lần đầu)."""
    cutoff = (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=n)).isoformat()
    d0 = max((d for d in runs[p] if d <= cutoff), default=runs[p][0])
    days = (datetime.date.fromisoformat(TODAY) - datetime.date.fromisoformat(d0)).days
    return ((inst[(TODAY, p)] - inst[(d0, p)]) / days, days) if days else (None, 0)


# --- 4. thói quen từ review (cache 7 ngày: review đổi chậm, đỡ ~300 request/ngày)
rev = json.loads(REV_F.read_text(encoding="utf-8")) if REV_F.exists() else {}
week_ago = (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=7)).isoformat()


def habit(p):
    try:
        rs, _ = reviews(p, lang="en", country="us", sort=Sort.MOST_RELEVANT, count=200)
    except Exception:
        rs = []
    return p, {"date": TODAY, "n": len(rs),
               "habit": round(sum(bool(HABIT.search(r["content"] or "")) for r in rs) / len(rs), 4) if rs else None}


with ThreadPoolExecutor(8) as ex:
    rev.update(ex.map(habit, [p for p in det if rev.get(p, {}).get("date", "") <= week_ago]))
REV_F.write_text(json.dumps(rev, ensure_ascii=False, indent=0), encoding="utf-8")

# --- 5. chỉ số từng nhóm
med = lambda xs: statistics.median(xs) if xs else None
out = []
for (lvl, name), ps in sorted(groups.items()):
    ps = [p for p in ps if p in det]
    if not ps:
        continue
    r7, r30 = {p: rate(p, 7) for p in ps}, {p: rate(p, 30) for p in ps}
    life = {p: det[p]["realInstalls"] / det[p]["age_days"] for p in ps if det[p]["age_days"]}
    # ponytail: lịch sử < 7 ngày thì Δ installs gần như 0 (Play không cập nhật realInstalls mỗi ngày cho
    # mọi app) -> tạm dùng TB vòng đời (installs ÷ tuổi), tự chuyển sang số thật khi đủ 7 ngày
    cur = {p: r30[p][0] if r30[p][1] >= 7 else life.get(p, 0) for p in ps}
    winners = [p for p in ps if (det[p]["age_days"] or 9999) <= 730 and det[p]["ads"] and not det[p]["big_dev"]
               and cur[p] >= 5000]
    out.append({"level": lvl, "grp": name, "apps": len(ps), "days": min(r30[p][1] for p in ps),
                "g7": med([r7[p][0] for p in ps if r7[p][0] is not None]),
                "demand": med(list(cur.values())),
                "lifetime": med(list(life.values())),
                "global": sum(len(countries[p]) for p in ps) / len(ps),
                "winners": len(winners), "iaa": sum(bool(det[p]["ads"]) for p in ps) / len(ps),
                "habit": med([rev[p]["habit"] for p in ps if rev.get(p, {}).get("habit") is not None]),
                "rating": med([det[p]["score"] for p in ps if det[p]["score"]]),
                "new_share": sum((det[p]["age_days"] or 9999) <= 730 for p in ps) / len(ps),
                "policy": POLICY_OUT.get(name, "") if lvl == "Ngách" else "",
                "top": ", ".join(f'{det[p]["title"][:28]} ({cur[p] / 1000:.0f}k)'
                                 for p in sorted(ps, key=lambda p: -cur[p])[:3])})

# --- 6. điểm: hạng phần trăm trong cùng cấp, bỏ ngách rớt chính sách
for lvl in {g["level"] for g in out}:
    ok = [g for g in out if g["level"] == lvl and not g["policy"]]
    for g in ok:
        s = 0
        for k, w in WEIGHTS.items():
            vals = [x[k] or 0 for x in ok]
            v = g[k] or 0
            s += w * (sum(x < v for x in vals) + 0.5 * sum(x == v for x in vals)) / len(vals)
        g["score"] = round(100 * s / sum(WEIGHTS.values()), 1)
out.sort(key=lambda g: (g["level"], -g.get("score", -1)))

# --- 7. xuất
fmt = lambda v, f: "—" if v is None else format(v, f)
md = [f"# Thị trường ngách — top {TOP_N} app mỗi nhóm × Top Free 200 của 8 nước ({TODAY})\n",
      "Điểm 0-100: Cầu ×1, Toàn cầu ×1, App thắng ×2, Thói quen ×2, IAA ×1 (xem docstring scripts/market.py).",
      "`Lịch sử` = số ngày ngắn nhất dùng để tính tăng trưởng trong nhóm: < 7 thì cột Cầu là TB vòng đời"
      " (installs ÷ tuổi), từ 7 ngày là tăng installs/ngày thật (tối đa 30 ngày).\n"]
for lvl in ("Ngách", "Category"):
    md += [f"\n## {lvl}\n", "| # | Nhóm | Điểm | Cầu: median DL/ngày/app | Lịch sử | Số nước TB | App thắng | % review thói quen"
           " | % ads | % app <2 năm | Rating | Top 3 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate([g for g in out if g["level"] == lvl], 1):
        md.append(f'| {i} | {g["grp"]} | {g["score"] if "score" in g else "loại: " + g["policy"]} | '
                  f'{fmt(g["demand"], ",.0f")} | {g["days"]} | {g["global"]:.1f} | {g["winners"]}/{g["apps"]} | '
                  f'{fmt(g["habit"], ".1%")} | {g["iaa"]:.0%} | {g["new_share"]:.0%} | {fmt(g["rating"], ".2f")} | {g["top"]} |')
(DATA / "market.md").write_text("\n".join(md), encoding="utf-8")

prev = {}
app_rows = []
for r in sorted(hist):  # tăng/ngày của từng app so với lần chạy trước của chính nó
    d, p, v = r[0], r[1], int(r[7])
    g = None
    if p in prev:
        days = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(prev[p][0])).days
        g = round((v - prev[p][1]) / days) if days else None
    prev[p] = (d, v)
    app_rows.append([d, p, r[2], r[3], r[4], r[6] or None, v, g, r[8] == "Có", r[9] == "Có",
                     float(r[10]) if r[10] else None, int(r[11]) if r[11] else None, int(r[12]), float(r[13])])
DDL = """
create schema if not exists scouting;
drop table if exists scouting.market_app, scouting.market_group;
create table scouting.market_app (date date, pkg text, app text, developer text, niche text, age_days int,
  installs bigint, growth int, ads bool, big_dev bool, rating real, ratings int, countries int, presence real);
create table scouting.market_group (level text, grp text, score real, apps int, days int, g7 real, demand real,
  lifetime real, global real, winners int, iaa real, habit real, rating real, new_share real, policy text, top text);
"""
keys = ["level", "grp", "score", "apps", "days", "g7", "demand", "lifetime", "global", "winners", "iaa", "habit",
        "rating", "new_share", "policy", "top"]
if pg_replace(DDL, {"scouting.market_app": app_rows, "scouting.market_group": [[g.get(k) for k in keys] for g in out]}):
    print(f"OK — Postgres scouting.market_app: {len(app_rows)} dòng, market_group: {len(out)} nhóm")
print(f"OK — data/market.md: {len(out)} nhóm, data/market.csv +{len(det)} dòng ({TODAY})")
