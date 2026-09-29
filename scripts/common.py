"""Cấu hình + helper dùng chung cho mọi script. Thêm ngách mới: chỉ sửa NICHES ở đây."""
import os, pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")  # ponytail: Windows console mặc định cp1252, vỡ tiếng Việt

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
TOKEN = ROOT / "token.json"          # bí mật, không commit (xem README mục 2.2)
DREAM_CSV = DATA / "Dream100.csv"    # lịch sử 1 dòng/app/ngày — mọi tab tăng trưởng đọc từ đây

SID = "1TmHd9IAZ56Z98S76lnJcKnKrEmFJfMVnMv53gHcZMYw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SID}/edit"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file"]

# (verify file, asolytics file, tên ngách) — tên file tương đối so với DATA
# ponytail: ngách tracker (habit/water/mood/sleep) bỏ 2026-09-23 — 0/71 app PASS,
# subscription-dominated không hợp IAA. File cũ nằm trong archive/.
NICHES = [
    ("verify_widget.json", "asolytics_widget.txt", "Widget / Control Panel"),
    ("verify_keyboard.json", "asolytics_keyboard.txt", "Keyboard Theme"),
    ("verify_content.json", "asolytics_content.txt", "Sticker/Quote/Ringtone Maker"),
    ("verify_content2.json", "asolytics_content2.txt", "Wallpaper/Coloring/Collage/GIF Maker"),
    ("verify_content3.json", "asolytics_content3.txt", "Font/Icon Pack/Video Status Maker"),
]

# asolytics in tiếng Ukraina: "Середня кількість завантажень на добу: від X до Y"
# (= download trung bình/ngày: từ X đến Y). Thiếu dòng này = asolytics hỏng dù exit 0.
ASO_MARKER = "Середня кількість завантажень на добу"
_DLDAY_RE = re.compile(r"на добу:\s*від\s*(\d+)\s*до\s*(\d+)")


def read_asolytics(path):
    """-> {pkg: raw block} từ file asolytics_*.txt (format '===== <pkg>' mỗi app)."""
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    blocks = {}
    for chunk in path.read_text(encoding="utf-8", errors="replace").split("===== ")[1:]:
        pkg, _, body = chunk.partition("\n")
        blocks[pkg.strip()] = body.strip()
    return blocks


def dlday_range(block):
    """-> (min, max) download/ngày từ 1 block asolytics, (None, None) nếu không có."""
    m = _DLDAY_RE.search(block or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def run_asolytics(pkg, timeout=90):
    """Chạy `asolytics --average` cho 1 app. -> CompletedProcess (raise TimeoutExpired nếu treo)."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    return subprocess.run(["asolytics", "--average", pkg, "--gl", "US", "--hl", "en"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=timeout)


def sheets():
    """Google Sheets service (import lazy để --dry-run không cần google libs/token)."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()
