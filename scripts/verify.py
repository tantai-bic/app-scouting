"""Verify candidate packages against Dream 100 criteria (Play Store data + verdict).
Usage: python scripts/verify.py [-o verify_<ngách>.json] com.a.b com.c.d ...
       Get-Content pool.txt | python scripts/verify.py -o verify_<ngách>.json
Output mặc định: data/verify_out.json (tên file tương đối so với data/).
"""
import argparse, datetime, json, sys
from google_play_scraper import app
from common import DATA

BIG = ("voodoo","supersonic","applovin","zynga","playtika","saygames","google","samsung",
       "adobe","canva","microsoft","meta","bytedance","outfit7","miniclip","ketchapp","homa")

def check(pkg):
    try:
        r = app(pkg, lang="en", country="us")
    except Exception as e:
        return {"pkg": pkg, "error": str(e)[:80]}
    rel = r.get("released") or ""
    # ponytail: released is a free-text date string ("Jun 3, 2024"); parse loosely, fall back to raw
    try:
        d = datetime.datetime.strptime(rel, "%b %d, %Y").date()
        age_days = (datetime.date.today() - d).days
    except ValueError:
        d, age_days = None, None
    dev = (r.get("developer") or "").lower()
    installs = r.get("realInstalls") or 0
    return {
        "pkg": pkg,
        "title": r.get("title"),
        "dev": r.get("developer"),
        "released": rel,
        "age_days": age_days,
        "realInstalls": installs,
        "minInstalls": r.get("minInstalls"),
        "dl_per_day_rough": round(installs / age_days) if age_days else None,
        "ads": r.get("containsAds"),
        "iap": r.get("offersIAP"),
        "score": r.get("score"),
        "ratings": r.get("ratings"),
        "genre": r.get("genre"),
        "big_dev": any(b in dev for b in BIG),
    }

def verdict(c):
    if "error" in c: return "ERR"
    f = []
    if c["big_dev"]: f.append("big-dev")
    if not c["ads"]: f.append("no-ads")
    if c["age_days"] is None: f.append("date?")
    elif c["age_days"] > 730: f.append("too-old")
    if (c["dl_per_day_rough"] or 0) < 5000: f.append("dl/day<5k")
    return "PASS" if not f else "FAIL:" + ",".join(f)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pkgs", nargs="*")
    ap.add_argument("-o", "--out", default="verify_out.json")
    args = ap.parse_args()
    pkgs = args.pkgs or [l.strip() for l in sys.stdin if l.strip()]
    out = []
    for p in pkgs:
        c = check(p); c["verdict"] = verdict(c); out.append(c)
        print(f'{c["verdict"]:<28} {p:<42} {c.get("title","")[:34]:<34} '
              f'{c.get("realInstalls",0):>12,} {str(c.get("released")):<14} '
              f'ads={c.get("ads")} iap={c.get("iap")}')
    out_path = DATA / args.out
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"-> {out_path}")
