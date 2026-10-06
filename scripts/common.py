"""Cấu hình + helper dùng chung cho mọi script. Thêm ngách mới: chỉ sửa NICHES ở đây."""
import os, pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")  # ponytail: Windows console mặc định cp1252, vỡ tiếng Việt

ROOT = pathlib.Path(__file__).resolve().parent.parent
# DATA_DIR / LOGS_DIR / SHEET_ID: override khi chạy test (xem .github/workflows/test-tracking.yml)
DATA = pathlib.Path(os.environ.get("DATA_DIR") or ROOT / "data")
LOGS = pathlib.Path(os.environ.get("LOGS_DIR") or ROOT / "logs")
TOKEN = ROOT / "token.json"          # bí mật, không commit (xem README mục 2.2)
DREAM_CSV = DATA / "Dream100.csv"    # lịch sử 1 dòng/app/ngày — mọi tab tăng trưởng đọc từ đây



def logged_pkgs():
    """Package đã từng có dòng trong Dream100.csv -> tiếp tục theo dõi dù sau đó FAIL
    (vd DL/ngày TB vòng đời tụt dưới 5k chỉ vì app già thêm), biết đâu lại đi lên."""
    import csv
    if not DREAM_CSV.exists():
        return set()
    with DREAM_CSV.open(encoding="utf-8", newline="") as f:
        return {r["Package"] for r in csv.DictReader(f)}


SID = os.environ.get("SHEET_ID") or "1TmHd9IAZ56Z98S76lnJcKnKrEmFJfMVnMv53gHcZMYw"
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
    ("verify_coloring.json", "asolytics_coloring.txt", "Coloring / Color by Number"),
]

# Genre Play Store được đi sâu theo category con (tab Tracking Category / Dashboard Category)
FOCUS_GENRES = ("Personalization", "Photography", "Casual")

# Play Store không có category con -> phân loại theo từ khoá trong tên app, khớp đầu tiên thắng
# (thứ tự quan trọng: "Emoji Font Keyboard" phải vào Keyboard trước Font).
# ponytail: heuristic theo title; app bị xếp sai thì thêm/đổi thứ tự từ khoá ở đây.
SUBCATEGORIES = [
    ("Keyboard", ("keyboard",)),
    ("Control Center", ("control", "panel")),
    ("Lock Screen", ("lock screen", "lockscreen")),
    ("Battery / Charging", ("battery", "charging")),
    ("Sticker", ("sticker",)),
    ("Coloring", ("color by", "coloring", "paint by")),
    ("Video / Status Maker", ("video", "status")),
    ("Theme Kit (Icons & Widgets)", ("widget", "icon", "launcher")),
    ("Wallpaper", ("wallpaper",)),
    ("Font", ("font",)),
    ("Ringtone", ("ringtone",)),
    ("Collage / Photo Editor", ("collage", "photo")),
]


def subcategory(title, niche=""):
    """Khớp từ khoá theo tên app trước, không có thì theo tên ngách scouting, cuối cùng 'Khác'."""
    for text in ((title or "").lower(), niche.lower()):
        for name, kws in SUBCATEGORIES:
            if any(k in text for k in kws):
                return name
    return "Khác"


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
