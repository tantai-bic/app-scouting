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

Usage: python scripts/push_tracking.py [--dry-run]
"""
import csv, sys
from common import DREAM_CSV, SHEET_URL, SID, sheets

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

if "--dry-run" in sys.argv:
    for v in values[:5]: print(v)
    print(f"... tổng {len(values)-1} dòng dữ liệu")
    sys.exit(0)

svc = sheets()
meta = svc.get(spreadsheetId=SID, fields="sheets(properties,conditionalFormats)").execute()["sheets"]
tab = next((s for s in meta if s["properties"]["title"] == SHEET_NAME), None)
sheet = tab and tab["properties"]
old_rules = len(tab.get("conditionalFormats", [])) if tab else 0
if sheet is None:
    resp = svc.batchUpdate(spreadsheetId=SID, body={"requests": [
        {"addSheet": {"properties": {"title": SHEET_NAME}}}]}).execute()
    sheet = resp["replies"][0]["addSheet"]["properties"]
gid = sheet["sheetId"]

svc.values().clear(spreadsheetId=SID, range=SHEET_NAME).execute()
svc.values().update(spreadsheetId=SID, range=f"{SHEET_NAME}!A1",
                    valueInputOption="RAW", body={"values": values}).execute()
def delta_rule(formula, rgb):
    """Tô các cột ngày từ ngày thứ 2 (cột E) trở đi: so với ô ngày liền trước bên trái.
    Ô trống hoặc ngày trước trống -> để nguyên."""
    return {"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [{"sheetId": gid, "startRowIndex": 1, "startColumnIndex": 4, "endColumnIndex": len(values[0])}],
        "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]},
                        "format": {"backgroundColor": dict(zip(("red", "green", "blue"), rgb))}}}}}

svc.batchUpdate(spreadsheetId=SID, body={"requests": [
    # tab không bị xoá mỗi lần chạy -> xoá rule cũ trước, không thì rule nhân đôi mỗi ngày
    *({"deleteConditionalFormatRule": {"sheetId": gid, "index": 0}} for _ in range(old_rules)),
    delta_rule("=AND(ISNUMBER(E2),ISNUMBER(D2),E2-D2>5000)", (.72, .88, .72)),
    delta_rule("=AND(ISNUMBER(E2),ISNUMBER(D2),E2-D2<=5000)", (.96, .8, .8)),
    {"repeatCell": {"range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                 "backgroundColor": {"red": .85, "green": .89, "blue": .96}}},
        "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
    {"updateSheetProperties": {"properties": {"sheetId": gid, "gridProperties":
        {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
    {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "COLUMNS",
        "startIndex": 0, "endIndex": len(values[0])}}},
]}).execute()
print(f"OK — tab '{SHEET_NAME}': {len(values)-1} dòng\n{SHEET_URL}")
