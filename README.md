# App Scouting — Dream 100

Hệ thống lọc và theo dõi app Google Play tiềm năng. Tiêu chí: ≥5.000 download/ngày, phát hành ≤2 năm, không thuộc big company, có quảng cáo (IAA/hybrid).
Kết quả đẩy lên Google Sheet: https://docs.google.com/spreadsheets/d/1TmHd9IAZ56Z98S76lnJcKnKrEmFJfMVnMv53gHcZMYw/edit

---

## 1. Cấu trúc thư mục

```
app-scouting/
├── .github/workflows/daily-tracking.yml   # GitHub Actions chạy daily tracking mỗi ngày
├── scripts/
│   ├── common.py              # CẤU HÌNH CHUNG: NICHES, Sheet ID, đường dẫn, helper asolytics/Sheets
│   ├── daily_tracking.py      # flow (B) — orchestrator chạy hằng ngày
│   ├── verify.py              # Play Store data + verdict PASS/FAIL
│   ├── run_asolytics_batch.py # download/ngày thật (asolytics), backfill 1 lần
│   ├── dream100.py            # build data/Dream100.md + append data/Dream100.csv
│   ├── push_merged.py         # -> tab Dream100
│   ├── push_tracking.py       # -> tab Tracking
│   ├── push_dashboard.py      # -> tab Dashboard, Dashboard Genre
│   └── check_ads_txt.py       # flow (C) — soi network quảng cáo
├── data/                      # dữ liệu đang dùng (Actions commit lại mỗi ngày)
│   ├── Dream100.csv           # LỊCH SỬ 1 dòng/app/ngày — không xoá
│   ├── Dream100.md
│   ├── verify_<ngách>.json
│   ├── asolytics_<ngách>.txt
│   └── ads_txt/, ads_txt_groups.json, ads_txt_report.md
├── logs/daily_tracking.log    # log từng lần chạy, dùng để debug
├── tests/fixture/             # data 1 app cho workflow test-tracking
├── archive/                   # file cũ / trung gian, không script nào đọc nữa
├── requirements.txt
├── token.json                 # BÍ MẬT, không commit (mục 3.2)
└── client_secret_*.json       # BÍ MẬT, không commit
```

**Quy ước:**
- Luôn chạy script từ thư mục gốc: `python scripts/<tên>.py`.
- Tham số tên file (ví dụ `verify_widget.json`) được hiểu **tương đối so với `data/`**.
- Thêm hoặc bớt ngách: **chỉ sửa `NICHES` trong `scripts/common.py`**.

---

## 2. Tổng quan các flow

```
 (A) Scouting 1 ngách mới  ── chạy tay, khi muốn thêm ngách
      verify.py ──> run_asolytics_batch.py ──> dream100.py ──> push_merged.py
      (Play Store)   (download/ngày thật)       (Dream100.md/csv)  (Sheet)

 (B) Daily tracking        ── tự động mỗi ngày (GitHub Actions hoặc Task Scheduler)
      daily_tracking.py = verify lại installs + asolytics + dream100.py
                          + push_tracking.py + push_merged.py + push_dashboard.py

 (C) Soi network quảng cáo ── chạy tay, thỉnh thoảng
      check_ads_txt.py ──> data/ads_txt_groups.json (dream100.py đọc để điền cột "Cùng network")
```

### Các tab trên Google Sheet

| Tab | Script ghi |
|---|---|
| `Dream100` | `push_merged.py`: gộp mọi app PASS của các ngách |
| `Tracking` | `push_tracking.py`: mỗi app một dòng, mỗi ngày một cột Lifetime installs, kèm cột Δ hôm nay |
| `Dashboard`, `Dashboard Genre` | `push_dashboard.py`: tăng trưởng theo ngách và theo genre |

Cả ba script đều **ghi đè toàn bộ tab** mỗi lần chạy. Sửa tay trên Sheet sẽ mất ở lần chạy sau. Mọi script `push_*.py` đều có `--dry-run` để xem trước dữ liệu mà không gọi Google.

---

## 3. Setup máy local (Windows)

### 3.1 Cài phần mềm

1. **Python 3.12+** (máy dev đang dùng 3.14): https://www.python.org/downloads/ — tick "Add to PATH".
2. **Firefox**: https://www.mozilla.org/firefox/ — asolytics điều khiển Firefox chạy ẩn. Không cần tự tải geckodriver, `webdriver_manager` sẽ tự tải.
3. Clone repo và cài thư viện:
   ```powershell
   gh repo clone tantai-bic/app-scouting D:\app-scouting
   cd D:\app-scouting
   pip install -r requirements.txt
   pip install --no-deps -r requirements-asolytics.txt   # asolytics ghim numpy cũ, không cài deps của nó
   ```
4. Kiểm tra:
   ```powershell
   asolytics --average com.whatsapp --gl US --hl en
   ```
   Chạy đúng thì output có dòng `Середня кількість завантажень на добу: від X до Y`. asolytics in ra tiếng Ukraina, dòng này nghĩa là "download trung bình/ngày: từ X đến Y".

### 3.2 Tạo `token.json` (quyền ghi Google Sheet)

Chỉ làm 1 lần, hoặc làm lại khi token hết hạn.

1. Cần file OAuth client `client_secret_*.json` (loại **Desktop app**), đặt ở thư mục gốc. File này không nằm trong repo; lấy từ người quản lý, hoặc tạo ở Google Cloud Console → APIs & Services → Credentials.
2. Chạy lệnh dưới đây. Trình duyệt sẽ mở ra, đăng nhập tài khoản **có quyền sửa Sheet** ở trên.
   ```powershell
   python -c "from google_auth_oauthlib.flow import InstalledAppFlow as F; import glob; c=F.from_client_secrets_file(glob.glob('client_secret_*.json')[0], ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive.file']).run_local_server(port=0); open('token.json','w').write(c.to_json())"
   ```
3. Kiểm tra: chạy `python scripts/push_tracking.py` (không dry-run). Phải in ra `OK — tab 'Tracking': N dòng`.

> ⚠️ **Token hết hạn sau 7 ngày** nếu OAuth consent screen của project Google Cloud đang ở trạng thái **Testing**. Cách sửa: vào Google Cloud Console → OAuth consent screen → **Publish app** (chuyển sang In production). Sau đó tạo lại token theo bước 2.

---

## 4. Flow (B) — Daily tracking

### 4.1 Chạy tay

```powershell
cd D:\app-scouting
python scripts/daily_tracking.py                     # mỗi ngày chỉ chạy được 1 lần
$env:FORCE_RUN=1; python scripts/daily_tracking.py   # ép chạy lại trong cùng ngày
```

- Chạy mất khoảng **60–70 phút**. asolytics chậm, mất khoảng 20–40 giây mỗi app.
- Chỉ theo dõi app có verdict `PASS` hoặc `FAIL:dl/day<5k`. Các lý do FAIL khác (quá cũ, không có ads, big dev) là cố định, không bao giờ tự hết.
- Chạy thành công thì trả exit code 0 và ghi ngày vào `logs/.daily_tracking_last_run`. Có lỗi thì trả exit code 1, cuối log có dòng `=== xong với N lỗi: ... ===`.

### 4.2 Chạy tự động trên máy (Task Scheduler)

Task `AppScoutingDailyTracking` chạy lúc **log on**. Mỗi lần mở máy nó chạy, nhưng script tự bỏ qua nếu hôm đó đã chạy rồi.

```powershell
Get-ScheduledTask AppScoutingDailyTracking           # xem trạng thái
Start-ScheduledTask AppScoutingDailyTracking         # chạy ngay
Disable-ScheduledTask AppScoutingDailyTracking       # tắt (khi đã chuyển sang GitHub Actions)
```

Nếu cần tạo lại task:
```powershell
$a = New-ScheduledTaskAction -Execute "C:\Python314\python.exe" -Argument '"D:\app-scouting\scripts\daily_tracking.py"' -WorkingDirectory "D:\app-scouting"
Register-ScheduledTask AppScoutingDailyTracking -Action $a -Trigger (New-ScheduledTaskTrigger -AtLogOn)
```

### 4.3 Chạy tự động trên GitHub Actions

File workflow: `.github/workflows/daily-tracking.yml`. Workflow chạy lúc **08:00 giờ VN** (01:00 UTC), mỗi lần làm các bước:

1. Checkout repo. Dữ liệu của lần chạy trước trong `data/` nằm sẵn trong repo.
2. Cài Python và thư viện. Runner Ubuntu đã có sẵn Firefox và geckodriver.
3. Ghi `token.json` từ secret `GOOGLE_TOKEN_JSON`.
4. Chạy `scripts/daily_tracking.py`.
5. **Luôn chạy, kể cả khi bước 4 lỗi**: commit `data/` và `logs/` rồi push lại repo cho lần chạy sau.
6. Upload `logs/daily_tracking.log` thành artifact, giữ 30 ngày.

#### Setup lần đầu

1. Repo: https://github.com/tantai-bic/app-scouting (**private**).
2. **Thêm secret token** (cần có `token.json` từ mục 3.2):
   ```powershell
   gh secret set GOOGLE_TOKEN_JSON --repo tantai-bic/app-scouting < token.json
   ```
   Hoặc làm trên web: Repo → Settings → Secrets and variables → Actions → New repository secret, tên `GOOGLE_TOKEN_JSON`, dán toàn bộ nội dung `token.json`.
3. **Cho phép Actions push**: Repo → Settings → Actions → General → Workflow permissions → chọn **Read and write permissions**.
4. **Chạy thử bằng tay**: tab Actions → `daily-tracking` → **Run workflow**. Hoặc dùng lệnh:
   ```powershell
   gh workflow run daily-tracking
   gh run watch                 # xem tiến độ
   gh run view --log-failed     # xem log bước lỗi
   ```
5. Chạy thử OK (xanh, có commit `daily tracking YYYY-MM-DD`) thì **tắt Task Scheduler trên máy** (mục 4.2). Nếu để cả hai cùng chạy, máy local sẽ ghi CSV riêng, lệch với repo.
6. Từ giờ, trước khi sửa code hoặc chạy tay trên máy thì `git pull` để lấy dữ liệu mới nhất.

#### Test trước khi chạy thật (`test-tracking`)

File `.github/workflows/test-tracking.yml` **chỉ chạy tay**. Workflow chạy toàn bộ `daily_tracking.py` với **1 app** (`tests/fixture/verify_widget.json`) và ghi vào **Sheet test riêng**:
https://docs.google.com/spreadsheets/d/1rJ7ZwJIwb-yCor6UWbzJXbo2GHAV51hLPoSeQ6Vuuko/edit

- Mất khoảng 3–5 phút. Không đụng `data/` thật, không commit, không ghi Sheet thật.
- Pass khi asolytics ra số download/ngày và `Dream100.csv` có dữ liệu. Log và data test được upload thành artifact.
- Nên chạy mỗi khi sửa `scripts/` hoặc `requirements.txt`, hoặc khi vừa đổi token.

```powershell
gh workflow run test-tracking --repo tantai-bic/app-scouting
gh run watch --repo tantai-bic/app-scouting
```

Chạy test ngay trên máy (cùng cơ chế; `logs/.daily_tracking_last_run` thật không bị ảnh hưởng):
```powershell
$env:SHEET_ID="1rJ7ZwJIwb-yCor6UWbzJXbo2GHAV51hLPoSeQ6Vuuko"; $env:DATA_DIR="$env:TEMP\scout-test\data"; $env:LOGS_DIR="$env:TEMP\scout-test\logs"; $env:FORCE_RUN=1
New-Item -ItemType Directory -Force $env:DATA_DIR | Out-Null; Copy-Item tests\fixture\* $env:DATA_DIR
python scripts/daily_tracking.py
Remove-Item Env:SHEET_ID, Env:DATA_DIR, Env:LOGS_DIR, Env:FORCE_RUN   # QUAN TRỌNG: xoá biến để lần sau không ghi nhầm
```

Biến môi trường dùng để override (định nghĩa trong `scripts/common.py`): `SHEET_ID` (Sheet đích), `DATA_DIR` (thay `data/`), `LOGS_DIR` (thay `logs/`), `FORCE_RUN=1` (bỏ chặn 1 lần/ngày).

#### Giới hạn

- Repo private có **2.000 phút Actions miễn phí/tháng**. Job này tốn khoảng 65 phút × 30 ngày ≈ 1.950 phút, rất sát giới hạn. Xem mức dùng ở GitHub → Settings → Billing. Nếu thiếu, đổi cron thành 2 ngày một lần (`0 1 */2 * *`).
- Lịch cron của GitHub có thể **trễ 15–60 phút** và đôi khi bị bỏ qua vào giờ cao điểm.
- Job tối đa 180 phút (`timeout-minutes`).

---

## 5. Đọc log & xử lý lỗi

Mỗi lần chạy trong `logs/daily_tracking.log` bắt đầu bằng `=== bắt đầu daily_tracking ===`. Lần chạy trên Actions có thể xem trong log của bước "Chạy daily_tracking", hoặc tải artifact về.

Tìm nhanh các dòng lỗi:
```powershell
Select-String -Path logs\daily_tracking.log -Pattern "LỖI|CẢNH BÁO|HỎNG|TIMEOUT"
```

| Dòng log | Nghĩa | Cách xử lý |
|---|---|---|
| `[env] firefox=KHÔNG TÌM THẤY` | Máy không có Firefox trong PATH. Trên Windows dòng này thường vẫn hiện dù đã cài Firefox, không sao | Chỉ quan tâm nếu đi kèm lỗi asolytics 0/N |
| `[LỖI] thiếu token.json` | Chưa tạo token (local) hoặc chưa đặt secret (Actions) | Mục 3.2 / 4.3 bước 2 |
| `[env] token.json: ... expiry=...` | Thời điểm hết hạn của access token. Access token hết hạn là bình thường, refresh token sẽ tự cấp lại | — |
| `[LỖI] ... invalid_grant` | **Refresh token hết hạn** (thường gặp sau 7 ngày khi app ở chế độ Testing) | Publish OAuth app, tạo lại `token.json` (3.2), cập nhật secret (4.3 bước 2) |
| `[asolytics] <pkg> HỎNG rc=... : <traceback>` | asolytics chạy xong nhưng không ra số | Đọc traceback. `WebDriverException` là lỗi Firefox/geckodriver; `rate limit` là lỗi GitHub API khi tải geckodriver |
| `[asolytics] <pkg> TIMEOUT 90s` | Firefox bị treo hoặc mạng chậm | Thỉnh thoảng gặp thì bỏ qua; gặp hàng loạt thì kiểm tra mạng |
| `[LỖI] <ngách>: asolytics 0/N OK` | asolytics hỏng toàn bộ | Chạy tay `asolytics --average com.whatsapp --gl US --hl en` để xem lỗi |
| `[installs] lỗi scrape <pkg>` | Không lấy được dữ liệu Play Store cho app đó. App đó giữ số cũ | App bị gỡ khỏi store thì lỗi này là bình thường |
| `[CẢNH BÁO] x/N pkg scrape lỗi` / `[LỖI] 100% pkg scrape lỗi` | Có thể **Google Play đang chặn IP** (hay gặp với IP datacenter của GitHub) | Chạy lại sau vài giờ; nếu lỗi kéo dài trên Actions thì quay về chạy bằng Task Scheduler |
| `[env] utc_now=...` | Giờ bắt đầu thực tế | So với 01:00 UTC để biết GitHub cron bị trễ bao lâu |
| `push_*.py rc=1 ... [stderr] ...` | Ghi Sheet lỗi | Đọc stderr: `invalid_grant` là lỗi token; `403` là tài khoản không có quyền sửa Sheet; `429` là vượt quota, chạy lại sau |
| `tổng thời gian: X phút` | Tổng thời lượng chạy | Tăng dần theo số app, cần để ý quota phút Actions |

Chạy lại chỉ phần push (sau khi đã sửa token), không cần chạy lại asolytics:
```powershell
python scripts/push_tracking.py; python scripts/push_merged.py; python scripts/push_dashboard.py
```

---

## 6. Flow (A) — Thêm ngách mới

Ví dụ thêm ngách "ringtone2":

1. **Lấy danh sách package** của ngách, dùng skill `aso-app-scouting`, AppBrain hoặc search Play Store, rồi lưu vào `pool_ringtone2.txt` (mỗi dòng một package).
2. **Verify với Play Store**. Kết quả ghi ra `data/verify_ringtone2.json`:
   ```powershell
   Get-Content pool_ringtone2.txt | python scripts/verify.py -o verify_ringtone2.json
   ```
3. **Lấy download/ngày thật** (chạy lâu; ngắt giữa chừng thì chạy lại lệnh cũ, script tự bỏ qua app đã có):
   ```powershell
   python scripts/run_asolytics_batch.py verify_ringtone2.json asolytics_ringtone2.txt
   ```
4. **Build Dream 100** (thêm dòng vào `data/Dream100.csv` và `data/Dream100.md`):
   ```powershell
   python scripts/dream100.py asolytics_ringtone2.txt --verify verify_ringtone2.json --title "Ringtone 2"
   ```
   Thêm `--all` nếu muốn đưa cả app FAIL vào bảng.
5. **Đưa ngách vào theo dõi hằng ngày**: thêm một dòng vào `NICHES` trong `scripts/common.py`:
   ```python
   ("verify_ringtone2.json", "asolytics_ringtone2.txt", "Ringtone 2"),
   ```
6. Đẩy lên Sheet: `python scripts/push_merged.py`. Sau đó commit và push (`git add data scripts; git commit; git push`).

---

## 7. Flow (C) — Soi network quảng cáo (app-ads.txt)

Tìm các app PASS dùng chung publisher ID (AdMob `pub-xxx`, …). Đây là dấu hiệu cùng một studio đứng sau dù tên developer khác nhau.

```powershell
python scripts/check_ads_txt.py verify_widget.json
```
Script ghi `data/ads_txt/<pkg>.txt`, `data/ads_txt_groups.json` và `data/ads_txt_report.md`. Lần sau chạy `dream100.py` sẽ tự điền cột "Cùng network". Chạy khá chậm vì phải fetch website của từng app, nên chỉ chạy khi cần, không chạy hằng ngày.

---

## 8. `archive/`

File cũ, không script nào đọc nữa. Giữ lại để tham khảo:

| File | Ghi chú |
|---|---|
| `push_dream100.py` | Script tạo **spreadsheet mới**, chỉ dùng lần đầu. Hiện đã có Sheet cố định |
| `Dream100_snapshot_*.csv` | Bản sao lưu trước các lần đổi cấu trúc CSV |
| `verify_tracker.json`, `asolytics_tracker.txt` | Ngách tracker đã bỏ theo dõi từ 2026-09-23 (0/71 app PASS) |
| `pool_*.txt`, `*_pass.txt`, `verify_*.txt`, `verify_out.json`, … | Output trung gian của các lần scouting cũ |
