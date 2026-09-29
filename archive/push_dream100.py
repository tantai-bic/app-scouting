#!/usr/bin/env python3
"""Tạo spreadsheet Dream100 mới (owner = tài khoản ADC) và ghi bảng app vào đó.

Usage: python push_dream100.py <oauth_client_secret.json> [--dry-run]
Đọc: verify_out.json (google-play-scraper) + asolytics_widget.txt (download/ngày).
"""
import json, re, sys, datetime, pathlib
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file"]
TOKEN = "token.json"   # refresh token, tạo 1 lần -> các lần sau không phải mở browser
TITLE = f"Dream 100 — Widget / Control Panel ({datetime.date.today()})"

apps = {a["pkg"]: a for a in json.load(open("verify_out.json", encoding="utf-8"))}
raw = pathlib.Path("asolytics_widget.txt").read_text(encoding="utf-8", errors="replace")
blocks = {}
for chunk in raw.split("===== ")[1:]:
    pkg, _, body = chunk.partition("\n")
    blocks[pkg.strip()] = body

def dlday(pkg):
    """asolytics in tiếng Ukraina: 'Середня кількість завантажень на добу: від X до Y'."""
    m = re.search(r"на добу:\s*від\s*(\d+)\s*до\s*(\d+)", blocks.get(pkg, ""))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

rows = sorted((a for a in apps.values() if a.get("verdict") == "PASS"),
              key=lambda a: -(dlday(a["pkg"])[0] or 0))

HEADER = ["#", "App", "Package", "Developer", "Play Store", "Phát hành", "Tuổi (ngày)",
          "Lifetime installs", "DL/ngày (TB vòng đời)", "DL/ngày min (asolytics)",
          "DL/ngày max (asolytics)", "Đạt ≥5k/ngày", "Ads", "IAP", "Monetize",
          "Rating", "Số đánh giá", "Category", "Theo dõi"]

def row(i, a):
    lo, hi = dlday(a["pkg"])
    return [i, a["title"], a["pkg"], a["dev"],
            f'https://play.google.com/store/apps/details?id={a["pkg"]}',
            a["released"], a["age_days"], a["realInstalls"], a["dl_per_day_rough"],
            lo if lo is not None else "", hi if hi is not None else "",
            "ĐẠT" if (lo or 0) >= 5000 else ("CHƯA" if lo is not None else "?"),
            "Có" if a["ads"] else "Không", "Có" if a["iap"] else "Không",
            "Hybrid (IAA+IAP)" if a["ads"] and a["iap"] else ("IAA" if a["ads"] else "—"),
            a["score"], a["ratings"], a["genre"], ""]

values = [
    [TITLE], [],
    ["Nguồn: AppBrain + google-play-scraper search (discover) · google-play-scraper app() (verify) · asolytics --average (download/ngày)"],
    ["Tiêu chí PASS: containsAds=true · phát hành ≤730 ngày · DL/ngày ≥5.000 · developer không thuộc big-company blacklist"],
    [f"Sinh tự động {datetime.datetime.now():%Y-%m-%d %H:%M} từ thư mục app-scouting"], [],
    HEADER,
] + [row(i, a) for i, a in enumerate(rows, 1)]

if "--dry-run" in sys.argv:
    for r in values: print(r)
    sys.exit(0)

creds = Credentials.from_authorized_user_file(TOKEN, SCOPES) if pathlib.Path(TOKEN).exists() else None
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
if not creds or not creds.valid:
    key = next((a for a in sys.argv[1:] if a.endswith(".json")), None)
    if not key:
        sys.exit("Thiếu đường dẫn OAuth client secret .json")
    creds = InstalledAppFlow.from_client_secrets_file(key, SCOPES).run_local_server(port=0)
    pathlib.Path(TOKEN).write_text(creds.to_json(), encoding="utf-8")
svc = build("sheets", "v4", credentials=creds).spreadsheets()
# sheetId của tab mới KHÔNG phải 0 -> phải lấy từ response, đừng hardcode
new = svc.create(body={"properties": {"title": TITLE},
                       "sheets": [{"properties": {"title": "Dream100"}}]},
                 fields="spreadsheetId,sheets.properties.sheetId").execute()
sid, gid = new["spreadsheetId"], new["sheets"][0]["properties"]["sheetId"]
svc.values().update(spreadsheetId=sid, range="Dream100!A1",
                    valueInputOption="RAW", body={"values": values}).execute()
hdr = len(values) - len(rows)          # dòng header (1-based) = số dòng trước bảng
svc.batchUpdate(spreadsheetId=sid, body={"requests": [
    {"repeatCell": {"range": {"sheetId": gid, "startRowIndex": hdr - 1, "endRowIndex": hdr},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                             "backgroundColor": {"red": .85, "green": .89, "blue": .96}}},
                    "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
    {"updateSheetProperties": {"properties": {"sheetId": gid, "gridProperties":
                               {"frozenRowCount": hdr}}, "fields": "gridProperties.frozenRowCount"}},
    {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "COLUMNS",
                              "startIndex": 0, "endIndex": len(HEADER)}}},
]}).execute()
print(f"OK — {len(rows)} app\nhttps://docs.google.com/spreadsheets/d/{sid}/edit")
