#!/usr/bin/env python3
"""Gộp nhiều ngách vào 1 tab Dream100 của spreadsheet đã tồn tại.

Usage: python scripts/push_merged.py [--dry-run]
Nguồn mỗi ngách: common.NICHES (verify_<x>.json, asolytics_<x>.txt, nhãn ngách).
"""
import datetime, json, sys
from common import DATA, NICHES, SHEET_URL, SID, dlday_range, read_asolytics, sheets

rows = []
for vf, af, label in NICHES:
    if not (DATA / vf).exists():
        print(f"[bỏ qua] chưa có {vf}"); continue
    day = {pkg: dlday_range(b) for pkg, b in read_asolytics(DATA / af).items()}
    for a in json.load(open(DATA / vf, encoding="utf-8")):
        if a.get("verdict") != "PASS":
            continue
        lo, hi = day.get(a["pkg"], (None, None))
        rows.append((lo or 0, [label, a["title"], a["pkg"], a["dev"],
            f'https://play.google.com/store/apps/details?id={a["pkg"]}',
            a["released"], a["age_days"], a["realInstalls"], a["dl_per_day_rough"],
            lo if lo is not None else "", hi if hi is not None else "",
            "ĐẠT" if (lo or 0) >= 5000 else ("CHƯA" if lo is not None else "?"),
            "Có" if a["ads"] else "Không", "Có" if a["iap"] else "Không",
            "Hybrid (IAA+IAP)" if a["ads"] and a["iap"] else ("IAA" if a["ads"] else "—"),
            round(a["score"] or 0, 2), a["ratings"], a["genre"], ""]))
rows.sort(key=lambda r: -r[0])

HEADER = ["#", "Ngách", "App", "Package", "Developer", "Play Store", "Phát hành", "Tuổi (ngày)",
          "Lifetime installs", "DL/ngày (TB vòng đời)", "DL/ngày min (asolytics)",
          "DL/ngày max (asolytics)", "Đạt ≥5k/ngày", "Ads", "IAP", "Monetize",
          "Rating", "Số đánh giá", "Category", "Theo dõi"]
values = [
    ["Dream 100 — App Content (IAA / hybrid)"], [],
    ["Nguồn: AppBrain + google-play-scraper search (discover) · google-play-scraper app() (verify) · asolytics --average (download/ngày)"],
    ["Tiêu chí PASS: containsAds=true · phát hành ≤730 ngày · DL/ngày ≥5.000 · developer không thuộc big-company blacklist"],
    [f"Ngách: {' · '.join(n[2] for n in NICHES)}"],
    [f"Cập nhật {datetime.datetime.now():%Y-%m-%d %H:%M}"], [],
    HEADER,
] + [[i] + r[1] for i, r in enumerate(rows, 1)]
HDR = len(values) - len(rows)

if "--dry-run" in sys.argv:
    for v in values[:12]: print(v)
    print(f"... tổng {len(rows)} app")
    sys.exit(0)

svc = sheets()
meta = svc.get(spreadsheetId=SID, fields="sheets.properties").execute()["sheets"]
gid = next(s["properties"]["sheetId"] for s in meta if s["properties"]["title"] == "Dream100")
svc.values().clear(spreadsheetId=SID, range="Dream100").execute()
svc.values().update(spreadsheetId=SID, range="Dream100!A1", valueInputOption="RAW",
                    body={"values": values}).execute()
svc.batchUpdate(spreadsheetId=SID, body={"requests": [
    {"repeatCell": {"range": {"sheetId": gid, "startRowIndex": HDR-1, "endRowIndex": HDR},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                 "backgroundColor": {"red": .85, "green": .89, "blue": .96},
                 "wrapStrategy": "WRAP"}},
        "fields": "userEnteredFormat(textFormat,backgroundColor,wrapStrategy)"}},
    {"repeatCell": {"range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 14}}},
        "fields": "userEnteredFormat.textFormat"}},
    {"updateSheetProperties": {"properties": {"sheetId": gid, "gridProperties":
        {"frozenRowCount": HDR, "frozenColumnCount": 3}},
        "fields": "gridProperties(frozenRowCount,frozenColumnCount)"}},
    {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "COLUMNS",
        "startIndex": 0, "endIndex": len(HEADER)}}},
]}).execute()
print(f"OK — {len(rows)} app\n{SHEET_URL}")
