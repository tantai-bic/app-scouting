#!/usr/bin/env python3
"""3 tab dashboard tăng trưởng, dựa trên số app + realInstalls:
  'Dashboard'          — nhóm theo ngách scouting
  'Dashboard Genre'    — nhóm theo genre Play Store
  'Dashboard Category' — category con của FOCUS_GENRES (common.subcategory)

- Số app quét / PASS: từ verify_*.json (trạng thái hiện tại, 1 pkg đếm 1 lần).
- Tăng/ngày: từ lịch sử Dream100.csv. Mỗi kỳ (2 lần chạy liên tiếp) chỉ cộng
  Δ installs của app có mặt ở CẢ 2 ngày rồi chia số ngày giữa 2 lần chạy ->
  không bị méo khi tập app PASS thay đổi hay bỏ ngày chạy.
Xoá + tạo lại tab mỗi lần chạy (để xoá chart cũ).

Usage: python scripts/push_dashboard.py [--dry-run]
"""
import csv, datetime, json, sys
from common import DATA, DREAM_CSV, FOCUS_GENRES, NICHES, SHEET_URL, SID, sheets, subcategory

apps = {}  # pkg -> {"niche", "genre", "category", "pass"}; pkg nằm ở nhiều ngách -> ngách đầu tiên thắng
for vf, label in NICHES:
    if (DATA / vf).exists():
        for a in json.load(open(DATA / vf, encoding="utf-8")):
            if "error" not in a:
                genre = a.get("genre") or "?"
                apps.setdefault(a["pkg"], {"niche": label, "genre": genre, "pass": a.get("verdict") == "PASS",
                    "sub": subcategory(a.get("title"), label),
                    # None = genre ngoài FOCUS_GENRES -> không vào tab Category
                    "category": f"{genre} › {subcategory(a.get('title'), label)}" if genre in FOCUS_GENRES else None})

inst = {}  # (date, pkg) -> installs, lần chạy cuối trong ngày thắng
raw = {}   # (date, pkg) -> dòng CSV, cho tab Data
with open(DREAM_CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        raw[(r["Ngày"], r["Package"])] = r
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
        if a[key] is None:
            continue
        scanned[a[key]] = scanned.get(a[key], 0) + 1
        passed[a[key]] = passed.get(a[key], 0) + a["pass"]
    labels = [l for _, l in NICHES if l in scanned] if key == "niche" else \
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


TABS = [("Dashboard", "niche", "Ngách"), ("Dashboard Genre", "genre", "Genre"),
        ("Dashboard Category", "category", "Category")]
built = [(t, *build_values(k, n)) for t, k, n in TABS]


def num(v):
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return ""


def build_data():
    """Tab 'Data' cho Looker Studio: long format, 1 dòng = 1 app × 1 ngày, giữ số dạng number.
    Tăng/ngày = Δ installs so với lần chạy trước của CHÍNH app đó ÷ số ngày (dòng đầu của app để trống)."""
    cols = ["Phát hành", "Tuổi (ngày)", "Lifetime installs", "DL/ngày (TB vòng đời)",
            "DL/ngày min (bucket)", "DL/ngày max (bucket)", "Rating", "Số đánh giá"]
    out = [["Ngày", "App", "Package", "Developer", "Ngách", "Genre", "Category", "PASS hiện tại",
            "Tăng/ngày", "Ads", "IAP", *cols]]
    prev = {}  # pkg -> (date, installs)
    for (d, p), r in sorted(raw.items()):
        a = apps.get(p, {})
        cur = num(r["Lifetime installs"])
        g = ""
        if p in prev and cur != "":
            days = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(prev[p][0])).days
            g = round((cur - prev[p][1]) / days) if days else ""
        if cur != "":
            prev[p] = (d, cur)
        out.append([d, r["App"], p, r["Developer"], a.get("niche", "?"), a.get("genre", "?"), a.get("sub", "Khác"),
                    "Có" if a.get("pass") else "Không", g, r["Ads"], r["IAP"],
                    r["Phát hành"], *(num(r[c]) for c in cols[1:])])
    return out


def build_window():
    """Tab 'Window' cho heatmap Looker: 1 dòng = Mốc (7 ngày / 30 ngày / Lifetime) × Cấp (App / Ngách /
    Genre / Category) × Nhóm. Mốc N ngày: mỗi app so lần chạy mới nhất với lần chạy GẦN NHẤT của chính
    app đó cách >= N ngày (app theo dõi chưa đủ N ngày thì lấy lần chạy đầu của nó) -> ngách mới thêm vẫn
    có số. Tăng/ngày nhóm = Σ tốc độ từng app; "Số ngày" = độ dài ngắn nhất trong nhóm (< N = chưa đủ lịch sử);
    "% tăng trong kỳ" quy về đúng N ngày. Lifetime: installs ÷ tuổi app (DL/ngày TB vòng đời)."""
    if not dates:
        return [[]]
    d1 = dates[-1]
    last = {p: v for (d, p), v in inst.items() if d == d1}
    levels = [("App", None), ("Ngách", "niche"), ("Genre", "genre"), ("Category", "sub")]

    def group(p, key):
        return f'{raw[(d1, p)]["App"]} ({p})' if key is None else apps[p][key]

    out = [["Mốc", "Cấp", "Nhóm", "Ngách", "Category", "Từ ngày", "Đến ngày", "Số ngày", "Số app",
            "Tăng/ngày", "Tăng/ngày / app", "% tăng trong kỳ", "Tổng installs"]]
    runs = {}  # pkg -> các ngày có số installs
    for d, p in sorted(inst):
        runs.setdefault(p, []).append(d)

    windows = []  # (label, N, {pkg: (tốc độ/ngày, installs gốc, ngày gốc, số ngày)})
    for n in (7, 30):
        cutoff = (datetime.date.fromisoformat(d1) - datetime.timedelta(days=n)).isoformat()
        w = {}
        for p in last:
            d0 = max((d for d in runs[p] if d <= cutoff), default=runs[p][0])
            days = (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days
            if days:
                w[p] = ((last[p] - inst[(d0, p)]) / days, inst[(d0, p)], d0, days)
        windows.append((f"{n} ngày", n, w))
    windows.append(("Lifetime", None, {p: (last[p] / num(raw[(d1, p)]["Tuổi (ngày)"]), 0, "", "")
                                       for p in last if num(raw[(d1, p)]["Tuổi (ngày)"])}))

    for label, n, w in windows:
        for lvl, key in levels:
            g = {}
            for p in w:
                g.setdefault(group(p, key), []).append(p)
            for name, ps in sorted(g.items()):
                r, b = sum(w[p][0] for p in ps), sum(w[p][1] for p in ps)
                one = ps[0] if key is None else None
                out.append([label, lvl, name, apps[one]["niche"] if one else (name if key == "niche" else ""),
                            apps[one]["sub"] if one else (name if key == "sub" else ""),
                            min(w[p][2] for p in ps) if n else "", d1, min(w[p][3] for p in ps) if n else "",
                            len(ps), round(r), round(r / len(ps)),
                            round(r * n / b, 4) if n and b else "", sum(last[p] for p in ps)])
    return out


data_values = build_data()
window_values = build_window()

if "--dry-run" in sys.argv:
    for t, values, m in built:
        print(f"--- {t} {m}")
        for v in values: print(v)
    for t, vals in (("Data", data_values), ("Window", window_values)):
        print(f"--- {t}: {len(vals) - 1} dòng")
        for v in vals[:3] + vals[-2:]: print(v)
    sys.exit(0)

svc = sheets()


def write_looker_tab(title, values, date_cols):
    """Tab cho Looker Studio: KHÔNG xoá/tạo lại (Looker bám theo gid) -> chỉ clear + ghi đè giá trị.
    Ghi RAW (tên app bắt đầu bằng "=" / "+" không bị hiểu thành công thức), rồi ghi lại các cột ngày
    bằng USER_ENTERED -> Sheets parse thành date thật, Looker nhận đúng kiểu Date."""
    meta = svc.get(spreadsheetId=SID, fields="sheets.properties").execute()["sheets"]
    gid = next((s["properties"]["sheetId"] for s in meta if s["properties"]["title"] == title), None)
    if gid is None:
        gid = svc.batchUpdate(spreadsheetId=SID, body={"requests": [{"addSheet": {"properties": {"title": title}}}]}
                              ).execute()["replies"][0]["addSheet"]["properties"]["sheetId"]
    svc.values().clear(spreadsheetId=SID, range=title).execute()
    svc.values().update(spreadsheetId=SID, range=f"{title}!A1", valueInputOption="RAW", body={"values": values}).execute()
    for c in date_cols:
        col = chr(ord("A") + c)
        svc.values().update(spreadsheetId=SID, range=f"{title}!{col}2", valueInputOption="USER_ENTERED",
                            body={"values": [[r[c]] for r in values[1:]]}).execute()
    print(f"OK — tab '{title}' (Looker Studio): {len(values) - 1} dòng — {SHEET_URL}#gid={gid}")


write_looker_tab("Data", data_values, [0])
write_looker_tab("Window", window_values, [5, 6])
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
