#!/usr/bin/env python3
"""Sync Dream100.csv (lịch sử, 1 dòng/app/lần chạy) vào tab 'Tracking' của
spreadsheet Dream100 đã tồn tại — dạng pivot: mỗi app 1 dòng, mỗi ngày 1 cột.

Giá trị = Lifetime installs (Total Download), không phải DL/ngày asolytics:
DL/ngày là trung bình cộng dồn (tổng ÷ tuổi app) nên gần như phẳng ngày qua
ngày, không thấy được tăng trưởng thật. Lifetime installs đổi thật mỗi ngày
-> cột "Δ hôm nay" (installs mới nhất trừ lần chạy gần nhất trước đó) mới là
tín hiệu tăng trưởng thật, dùng để xem app nào đang tăng tốc/chững lại.

Các field tĩnh (Developer, Ads, Rating...) đã có sẵn ở tab Dream100 nên không
lặp lại ở đây. Ghi đè toàn bộ tab mỗi lần chạy.

Tab 'Tracking Genre' / 'Tracking Category' (category con của FOCUS_GENRES, xem
common.subcategory): mỗi nhóm 1 dòng, mỗi ngày 1 cột = installs tăng/ngày của
genre so với lần chạy trước. Chỉ cộng app có mặt ở CẢ 2 lần chạy rồi chia số
ngày giữa 2 lần -> không méo khi tập app PASS thay đổi hay bỏ ngày chạy.

Usage: python scripts/push_tracking.py [--dry-run]
"""
import csv, datetime, json, sys
from common import DATA, DREAM_CSV, FOCUS_GENRES, NICHES, SHEET_URL, SID, sheets, subcategory

SHEET_NAME = "Tracking"

with open(DREAM_CSV, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    log = list(reader)
if not log:
    sys.exit("Dream100.csv rỗng — chạy dream100.py trước")

dates = sorted({r["Ngày"] for r in log})
apps = {}          # pkg -> title (giữ tên mới nhất)
cell = {}          # (pkg, date) -> Lifetime installs, ghi đè nếu chạy nhiều lần/ngày -> lấy lần cuối
for r in log:
    apps[r["Package"]] = r["App"]
    installs = r["Lifetime installs"]
    cell[(r["Package"], r["Ngày"])] = int(installs) if installs else ""

def delta(pkg):
    """Installs ở lần chạy gần nhất trừ lần chạy gần nhất trước đó (không nhất thiết là hôm qua nếu bỏ ngày)."""
    vals = [cell[(pkg, d)] for d in dates if cell.get((pkg, d), "") != ""]
    return vals[-1] - vals[-2] if len(vals) >= 2 else ""

pkgs = sorted(apps, key=lambda p: apps[p])
values = [["App", "Package", "Δ hôm nay (installs)", *dates]]
for p in pkgs:
    values.append([apps[p], p, delta(p), *(cell.get((p, d), "") for d in dates)])

# ---- Tracking Genre / Tracking Category
info = {}  # pkg -> (genre, category), pkg ở nhiều ngách -> ngách đầu tiên thắng
for vf, niche in NICHES:
    if (DATA / vf).exists():
        for a in json.load(open(DATA / vf, encoding="utf-8")):
            info.setdefault(a["pkg"], (a.get("genre") or "?", subcategory(a.get("title"), niche)))

last = dates[-1]

def group_pivot(group_of, cols):
    """Pivot theo nhóm: group_of(pkg) -> tuple tên nhóm (None = bỏ qua app).
    Mỗi cột ngày = installs tăng/ngày so với lần chạy trước, chỉ cộng app có số ở cả 2 ngày."""
    members = {}
    for p in apps:
        g = group_of(p)
        if g is not None:
            members.setdefault(g, []).append(p)

    def growth(ps, d0, d1):
        both = [p for p in ps if cell.get((p, d0), "") != "" and cell.get((p, d1), "") != ""]
        if not both:
            return ""
        days = (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days or 1
        return round(sum(cell[(p, d1)] - cell[(p, d0)] for p in both) / days)

    rows = []
    for g, ps in members.items():
        now = [cell[(p, last)] for p in ps if cell.get((p, last), "") != ""]
        rows.append([*g, len(now), sum(now), "",  # ngày đầu không có kỳ trước
                     *(growth(ps, d0, d1) for d0, d1 in zip(dates, dates[1:]))])
    rows.sort(key=lambda r: (FOCUS_GENRES.index(r[0]) if r[0] in FOCUS_GENRES else 99, -r[len(cols) + 1]))
    return [[*cols, f"Số app ({last})", f"Tổng installs ({last})", *dates], *rows]

genre_values = group_pivot(lambda p: info.get(p, ("?",))[:1], ["Genre"])
category_values = group_pivot(lambda p: info[p] if info.get(p, ("?",))[0] in FOCUS_GENRES else None,
                              ["Genre", "Category"])

if "--dry-run" in sys.argv:
    for v in values[:5]: print(v)
    print(f"... tổng {len(values)-1} dòng dữ liệu")
    for v in genre_values: print(v)
    for v in category_values: print(v)
    sys.exit(0)

svc = sheets()
HEADER_FMT = {"repeatCell": {"range": {"startRowIndex": 0, "endRowIndex": 1},
    "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
             "backgroundColor": {"red": .85, "green": .89, "blue": .96}}},
    "fields": "userEnteredFormat(textFormat,backgroundColor)"}}

def write_tab(name, rows, rules):
    """Ghi đè tab `name` (tạo nếu chưa có). rules(gid) -> list conditional format request."""
    meta = svc.get(spreadsheetId=SID, fields="sheets(properties,conditionalFormats)").execute()["sheets"]
    tab = next((s for s in meta if s["properties"]["title"] == name), None)
    if tab:
        gid, old_rules = tab["properties"]["sheetId"], len(tab.get("conditionalFormats", []))
    else:
        gid, old_rules = svc.batchUpdate(spreadsheetId=SID, body={"requests": [
            {"addSheet": {"properties": {"title": name}}}]}).execute()["replies"][0]["addSheet"]["properties"]["sheetId"], 0
    svc.values().clear(spreadsheetId=SID, range=name).execute()
    svc.values().update(spreadsheetId=SID, range=f"{name}!A1",
                        valueInputOption="RAW", body={"values": rows}).execute()
    header = json.loads(json.dumps(HEADER_FMT))
    header["repeatCell"]["range"]["sheetId"] = gid
    svc.batchUpdate(spreadsheetId=SID, body={"requests": [
        # tab không bị xoá mỗi lần chạy -> xoá rule cũ trước, không thì rule nhân đôi mỗi ngày
        *({"deleteConditionalFormatRule": {"sheetId": gid, "index": 0}} for _ in range(old_rules)),
        *rules(gid),
        header,
        {"updateSheetProperties": {"properties": {"sheetId": gid, "gridProperties":
            {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
        {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "COLUMNS",
            "startIndex": 0, "endIndex": len(rows[0])}}},
    ]}).execute()
    print(f"OK — tab '{name}': {len(rows)-1} dòng")

def app_rules(gid):
    """Tô các cột ngày từ ngày thứ 2 (cột E) trở đi: so với ô ngày liền trước bên trái.
    Ô trống hoặc ngày trước trống -> để nguyên."""
    def rule(formula, rgb):
        return {"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [{"sheetId": gid, "startRowIndex": 1, "startColumnIndex": 4, "endColumnIndex": len(values[0])}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]},
                            "format": {"backgroundColor": dict(zip(("red", "green", "blue"), rgb))}}}}}
    return [rule("=AND(ISNUMBER(E2),ISNUMBER(D2),E2-D2>5000)", (.72, .88, .72)),
            rule("=AND(ISNUMBER(E2),ISNUMBER(D2),E2-D2<=5000)", (.96, .8, .8))]

def gradient_rules(rows, first_date_col):
    """Gradient đỏ (tăng ít) -> xanh (tăng nhiều) trên các cột ngày."""
    return lambda gid: [{"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [{"sheetId": gid, "startRowIndex": 1, "startColumnIndex": first_date_col, "endColumnIndex": len(rows[0])}],
        "gradientRule": {"minpoint": {"color": {"red": .96, "green": .8, "blue": .8}, "type": "MIN"},
                         "maxpoint": {"color": {"red": .72, "green": .88, "blue": .72}, "type": "MAX"}}}}}]

write_tab(SHEET_NAME, values, app_rules)
write_tab("Tracking Genre", genre_values, gradient_rules(genre_values, 3))
write_tab("Tracking Category", category_values, gradient_rules(category_values, 4))
print(SHEET_URL)
