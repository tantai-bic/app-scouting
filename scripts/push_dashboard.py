#!/usr/bin/env python3
"""2 tab dashboard tăng trưởng, dựa trên số app + realInstalls:
  'Dashboard'       — nhóm theo ngách scouting
  'Dashboard Genre' — nhóm theo genre Play Store

- Số app quét / PASS: từ verify_*.json (trạng thái hiện tại, 1 pkg đếm 1 lần).
- Tăng/ngày: từ lịch sử Dream100.csv. Mỗi kỳ (2 lần chạy liên tiếp) chỉ cộng
  Δ installs của app có mặt ở CẢ 2 ngày rồi chia số ngày giữa 2 lần chạy ->
  không bị méo khi tập app PASS thay đổi hay bỏ ngày chạy.
Xoá + tạo lại tab mỗi lần chạy (để xoá chart cũ).

Usage: python scripts/push_dashboard.py [--dry-run]
"""
import csv, datetime, json, sys
from common import DATA, DREAM_CSV, NICHES, SHEET_URL, SID, sheets

apps = {}  # pkg -> {"niche", "genre", "pass"}; pkg nằm ở nhiều ngách -> ngách đầu tiên thắng
for vf, _, label in NICHES:
    if (DATA / vf).exists():
        for a in json.load(open(DATA / vf, encoding="utf-8")):
            if "error" not in a:
                apps.setdefault(a["pkg"], {"niche": label, "genre": a.get("genre") or "?",
                                           "pass": a.get("verdict") == "PASS"})

inst = {}  # (date, pkg) -> installs, lần chạy cuối trong ngày thắng
with open(DREAM_CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if r["Package"] in apps and r["Lifetime installs"]:
            inst[(r["Ngày"], r["Package"])] = int(r["Lifetime installs"])
dates = sorted({d for d, _ in inst})
periods = list(zip(dates, dates[1:]))
per_labels = [f"{a[5:]}→{b[5:]}" for a, b in periods]


def build_values(key, name):
    """-> (values, meta) cho 1 tab, nhóm app theo apps[pkg][key]."""
    def on(d, l):
        return {p: v for (dd, p), v in inst.items() if dd == d and apps[p][key] == l}

    def growth(d0, d1, l):
        a, b = on(d0, l), on(d1, l)
        both = a.keys() & b.keys()
        days = (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days
        return (round(sum(b[p] - a[p] for p in both) / days), len(both)) if both else ("", 0)

    scanned, passed = {}, {}
    for a in apps.values():
        scanned[a[key]] = scanned.get(a[key], 0) + 1
        passed[a[key]] = passed.get(a[key], 0) + a["pass"]
    labels = [l for _, _, l in NICHES if l in scanned] if key == "niche" else \
        sorted(scanned, key=lambda l: (-passed[l], -scanned[l]))
    tracked = [l for l in labels if any(apps[p][key] == l for _, p in inst)]  # nhóm có lịch sử -> vào chart xu hướng
    g = {(l, p): growth(*p, l) for l in labels for p in periods}

    rows = [["Tăng/ngày = Δ Lifetime installs của các app có mặt ở cả 2 lần chạy ÷ số ngày giữa 2 lần chạy"],
            [name, "Số app quét", "Số app PASS", "Tổng installs (PASS, mới nhất)",
             "Tăng/ngày (kỳ gần nhất)", "Tăng/ngày / app", "% tăng/ngày"]]
    for l in labels:
        last = g[(l, periods[-1])] if periods else ("", 0)
        total = sum(on(dates[-1], l).values()) if dates else 0
        rows.append([l, scanned[l], passed[l], total, last[0],
                     round(last[0] / last[1]) if last[1] else "",
                     f"{last[0] / total:.2%}" if total and last[0] != "" else ""])
    # bảng xu hướng xoay ngang: hàng = kỳ/ngày, cột = nhóm (API chart không có "switch rows/cols")
    s2 = len(rows) + 4  # 1-based dòng header bảng tăng/ngày (+1 dòng title tab, + blank + title bảng + header)
    rows += [[], ["Tăng installs/ngày theo kỳ"], ["Kỳ", *tracked]]
    rows += [[pl, *(g[(l, p)][0] for l in tracked)] for pl, p in zip(per_labels, periods)]
    s3 = len(rows) + 4
    rows += [[], ["Số app PASS theo dõi theo ngày"], ["Ngày", *tracked]]
    rows += [[d, *(len(on(d, l)) for l in tracked)] for d in dates]
    values = [[f"Dashboard tăng trưởng theo {name.lower()} — cập nhật {datetime.datetime.now():%Y-%m-%d %H:%M}"]] + rows
    return values, {"n": len(labels), "m": len(tracked), "s1": 3, "s2": s2, "s3": s3, "end": len(values)}


TABS = [("Dashboard", "niche", "Ngách"), ("Dashboard Genre", "genre", "Genre")]
built = [(t, *build_values(k, n)) for t, k, n in TABS]

if "--dry-run" in sys.argv:
    for t, values, m in built:
        print(f"--- {t} {m}")
        for v in values: print(v)
    sys.exit(0)

svc = sheets()
BLUE = {"red": .85, "green": .89, "blue": .96}
NUM = {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}

for idx, (title, values, m) in enumerate(built):
    meta = svc.get(spreadsheetId=SID, fields="sheets.properties").execute()["sheets"]
    old = next((s["properties"]["sheetId"] for s in meta if s["properties"]["title"] == title), None)
    reqs = [{"deleteSheet": {"sheetId": old}}] if old is not None else []
    reqs.append({"addSheet": {"properties": {"title": title, "index": idx}}})
    gid = svc.batchUpdate(spreadsheetId=SID, body={"requests": reqs}).execute()["replies"][-1]["addSheet"]["properties"]["sheetId"]
    svc.values().update(spreadsheetId=SID, range=f"{title}!A1", valueInputOption="USER_ENTERED",
                        body={"values": values}).execute()

    def rng(r0, r1, c0, c1):  # 0-based, end-exclusive
        return {"sheetId": gid, "startRowIndex": r0, "endRowIndex": r1,
                "startColumnIndex": c0, "endColumnIndex": c1}

    def fmt(r0, r1, c0, c1, f):
        return {"repeatCell": {"range": rng(r0, r1, c0, c1), "cell": {"userEnteredFormat": f},
                               "fields": "userEnteredFormat(" + ",".join(f) + ")"}}

    def line(t, header, nrows, ytitle, row, c):
        """Line chart: domain = cột A (kỳ/ngày), mỗi cột nhóm 1 đường."""
        r0 = header - 1
        return {"addChart": {"chart": {"spec": {"title": t, "basicChart": {
            "chartType": "LINE", "legendPosition": "RIGHT_LEGEND", "headerCount": 1,
            "axis": [{"position": "LEFT_AXIS", "title": ytitle}],
            "domains": [{"domain": {"sourceRange": {"sources": [rng(r0, r0 + 1 + nrows, 0, 1)]}}}],
            "series": [{"series": {"sourceRange": {"sources": [rng(r0, r0 + 1 + nrows, c, c + 1)]}},
                        "targetAxis": "LEFT_AXIS", "lineStyle": {"width": 3},
                        "pointStyle": {"shape": "CIRCLE", "size": 6}} for c in range(1, 1 + m["m"])]}},
            "position": {"overlayPosition": {"anchorCell": {"sheetId": gid, "rowIndex": row, "columnIndex": c},
                                             "widthPixels": 720, "heightPixels": 360}}}}}

    n, s1, s2, s3 = m["n"], m["s1"], m["s2"], m["s3"]
    d0 = s1  # 0-based dòng data đầu của bảng tổng quan
    reqs = [fmt(0, 1, 0, 1, {"textFormat": {"bold": True, "fontSize": 14}}),
            *(fmt(r - 1, r, 0, 30, {"textFormat": {"bold": True}, "backgroundColor": BLUE}) for r in (s1, s2, s3)),
            *(fmt(r - 2, r - 1, 0, 1, {"textFormat": {"bold": True}}) for r in (s2, s3)),
            fmt(d0, d0 + n, 3, 6, NUM),
            fmt(s2, s2 + len(periods), 1, 1 + m["m"], NUM),
            # tô màu cột Tăng/ngày: đỏ thấp -> xanh cao
            {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [rng(d0, d0 + n, 4, 5)],
                "gradientRule": {"minpoint": {"color": {"red": .96, "green": .8, "blue": .8}, "type": "MIN"},
                                 "maxpoint": {"color": {"red": .72, "green": .88, "blue": .72}, "type": "MAX"}}}}},
            {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "COLUMNS",
                                                     "startIndex": 0, "endIndex": 7}}},
            # bubble: X = số app PASS, Y = tăng/ngày, size = tổng installs -> góc trên-phải = đông app + tăng mạnh
            {"addChart": {"chart": {"spec": {
                "title": "Số app PASS (X) vs tăng installs/ngày (Y), bóng = tổng installs",
                "bubbleChart": {"legendPosition": "RIGHT_LEGEND",
                    "domain": {"sourceRange": {"sources": [rng(d0, d0 + n, 2, 3)]}},
                    "series": {"sourceRange": {"sources": [rng(d0, d0 + n, 4, 5)]}},
                    "bubbleLabels": {"sourceRange": {"sources": [rng(d0, d0 + n, 0, 1)]}},
                    "groupIds": {"sourceRange": {"sources": [rng(d0, d0 + n, 0, 1)]}},
                    "bubbleSizes": {"sourceRange": {"sources": [rng(d0, d0 + n, 3, 4)]}},
                    "bubbleOpacity": 0.6}},
                "position": {"overlayPosition": {"anchorCell": {"sheetId": gid, "rowIndex": 0, "columnIndex": 8},
                                                 "widthPixels": 720, "heightPixels": 360}}}}}]
    if m["m"] and periods:
        reqs.append(line("Xu hướng: tăng installs/ngày theo kỳ", s2, len(periods), "installs/ngày", 19, 8))
    if m["m"] and dates:
        reqs.append(line("Xu hướng: số app PASS theo dõi", s3, len(dates), "số app", 38, 8))
    svc.batchUpdate(spreadsheetId=SID, body={"requests": reqs}).execute()
    print(f"OK — tab '{title}': {n} nhóm ({m['m']} có lịch sử), {len(periods)} kỳ — "
          f"{SHEET_URL}#gid={gid}")
