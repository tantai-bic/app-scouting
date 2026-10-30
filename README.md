# App Scouting — Dream 100

Hệ thống lọc và theo dõi app Google Play tiềm năng. Tiêu chí: ≥5.000 download/ngày, phát hành ≤2 năm, không thuộc big company, có quảng cáo (IAA/hybrid).
Kết quả đẩy lên Google Sheet (cấu hình qua biến môi trường `SHEET_ID`).

---

## 1. Cấu trúc thư mục

```
app-scouting/
├── .github/workflows/daily-tracking.yml   # GitHub Actions chạy daily tracking mỗi ngày
├── scripts/
│   ├── common.py              # CẤU HÌNH CHUNG: NICHES, Sheet ID, đường dẫn, helper DL/ngày/Sheets
│   ├── daily_tracking.py      # flow (B) — orchestrator chạy hằng ngày
│   ├── verify.py              # Play Store data + verdict PASS/FAIL
│   ├── dream100.py            # build data/Dream100.md + append data/Dream100.csv
│   ├── push_merged.py         # -> tab Dream100
│   ├── push_tracking.py       # -> tab Tracking
│   ├── push_dashboard.py      # -> tab Dashboard, Dashboard Genre
│   └── check_ads_txt.py       # flow (C) — soi network quảng cáo
├── data/                      # dữ liệu đang dùng (Actions commit lại mỗi ngày)
│   ├── Dream100.csv           # LỊCH SỬ 1 dòng/app/ngày — không xoá
│   ├── Dream100.md
│   ├── verify_<ngách>.json
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
      verify.py ──> dream100.py ──> push_merged.py
      (Play Store)   (Dream100.md/csv)  (Sheet)

 (B) Daily tracking        ── tự động mỗi ngày (GitHub Actions hoặc Task Scheduler)
      daily_tracking.py = verify lại installs + dream100.py
                          + push_tracking.py + push_merged.py + push_dashboard.py

 (C) Soi network quảng cáo ── chạy tay, thỉnh thoảng
      check_ads_txt.py ──> data/ads_txt_groups.json (dream100.py đọc để điền cột "Cùng network")
```

### Các tab trên Google Sheet

| Tab | Script ghi |
|---|---|
| `Dream100` | `push_merged.py`: gộp mọi app PASS của các ngách |
| `Tracking` | `push_tracking.py`: mỗi app một dòng, mỗi ngày một cột Lifetime installs, kèm cột Δ hôm nay |
| `Tracking Genre` | `push_tracking.py`: mỗi genre một dòng, mỗi ngày một cột = installs **tăng/ngày** so với lần chạy trước |
| `Tracking Category` | `push_tracking.py`: như trên, nhưng tách theo category con của Personalization / Photography / Casual |
| `Dashboard`, `Dashboard Genre`, `Dashboard Category` | `push_dashboard.py`: tăng trưởng + chart theo ngách / genre / category con |
| `Data` | `push_dashboard.py`: dữ liệu thô cho **Looker Studio**, 1 dòng = 1 app × 1 ngày (có Ngách/Genre/Category, Tăng/ngày). Tab này chỉ ghi đè giá trị, không xoá/tạo lại, để giữ gid mà Looker đang kết nối |
| `Window` | `push_dashboard.py`: số tính sẵn cho heatmap Looker, 1 dòng = Mốc (7 ngày / 30 ngày / Lifetime) × Cấp (App / Ngách / Genre / Category) × Nhóm. Mỗi app so với lần chạy gần nhất của chính nó cách ≥ N ngày; cột `Số ngày` < N nghĩa là nhóm đó chưa đủ lịch sử. Giữ gid như tab `Data` |

**Category con:** Play Store không có cấp dưới genre, nên category con được phân loại theo **từ khoá trong tên app** (`SUBCATEGORIES` trong `scripts/common.py`). Tên app không khớp từ khoá nào thì dò theo tên ngách; vẫn không khớp thì xếp vào "Khác". Khi thấy app bị xếp sai, thêm từ khoá hoặc đổi thứ tự ở đó (khớp đầu tiên thắng). Muốn đi sâu thêm genre khác thì thêm vào `FOCUS_GENRES`.

Giá trị tăng/ngày chỉ cộng các app có mặt ở **cả 2** lần chạy, rồi chia cho số ngày giữa 2 lần chạy. Nhờ vậy số không bị nhảy khi tập app PASS thay đổi.

Cả ba script đều **ghi đè toàn bộ tab** mỗi lần chạy. Sửa tay trên Sheet sẽ mất ở lần chạy sau. Mọi script `push_*.py` đều có `--dry-run` để xem trước dữ liệu mà không gọi Google.

---

## 3. Setup máy local (Windows)

### 3.1 Cài phần mềm

1. **Python 3.12+** (máy dev đang dùng 3.14): https://www.python.org/downloads/ — tick "Add to PATH".
2. Clone repo và cài thư viện:
   ```powershell
   gh repo clone tantai-bic/app-scouting D:\app-scouting
   cd D:\app-scouting
   pip install -r requirements.txt
   ```
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

- Chạy mất khoảng **1–2 phút** (~0,3 giây/app). DL/ngày min/max tính từ bucket installs của Play Store ("10M+") ÷ tuổi app — đúng con số asolytics từng lấy, nhưng không cần mở Firefox (trước đây 55 phút).
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
2. Cài Python và thư viện.
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
(ID lấy từ repo variable `TEST_SHEET_ID`)

- Mất khoảng 3–5 phút. Không đụng `data/` thật, không commit, không ghi Sheet thật.
- Pass khi `Dream100.csv` có dữ liệu. Log và data test được upload thành artifact.
- Nên chạy mỗi khi sửa `scripts/` hoặc `requirements.txt`, hoặc khi vừa đổi token.

```powershell
gh workflow run test-tracking --repo tantai-bic/app-scouting
gh run watch --repo tantai-bic/app-scouting
```

Chạy test ngay trên máy (cùng cơ chế; `logs/.daily_tracking_last_run` thật không bị ảnh hưởng):
```powershell
$env:SHEET_ID="<id-sheet-test>"; $env:DATA_DIR="$env:TEMP\scout-test\data"; $env:LOGS_DIR="$env:TEMP\scout-test\logs"; $env:FORCE_RUN=1
New-Item -ItemType Directory -Force $env:DATA_DIR | Out-Null; Copy-Item tests\fixture\* $env:DATA_DIR
python scripts/daily_tracking.py
Remove-Item Env:SHEET_ID, Env:DATA_DIR, Env:LOGS_DIR, Env:FORCE_RUN   # QUAN TRỌNG: xoá biến để lần sau không ghi nhầm
```

Biến môi trường dùng để override (định nghĩa trong `scripts/common.py`): `SHEET_ID` (Sheet đích), `DATA_DIR` (thay `data/`), `LOGS_DIR` (thay `logs/`), `FORCE_RUN=1` (bỏ chặn 1 lần/ngày).

#### Giới hạn

- Repo private có **2.000 phút Actions miễn phí/tháng**. Job này tốn khoảng 2–3 phút × 30 ngày ≈ 90 phút/tháng.
- Lịch cron của GitHub có thể **trễ 15–60 phút** và đôi khi bị bỏ qua vào giờ cao điểm.
- Job tối đa 30 phút (`timeout-minutes`).

---

## 5. Đọc log & xử lý lỗi

Mỗi lần chạy trong `logs/daily_tracking.log` bắt đầu bằng `=== bắt đầu daily_tracking ===`. Lần chạy trên Actions có thể xem trong log của bước "Chạy daily_tracking", hoặc tải artifact về.

Tìm nhanh các dòng lỗi:
```powershell
Select-String -Path logs\daily_tracking.log -Pattern "LỖI|CẢNH BÁO|HỎNG|TIMEOUT"
```

| Dòng log | Nghĩa | Cách xử lý |
|---|---|---|
| `[LỖI] thiếu token.json` | Chưa tạo token (local) hoặc chưa đặt secret (Actions) | Mục 3.2 / 4.3 bước 2 |
| `[env] token.json: ... expiry=...` | Thời điểm hết hạn của access token. Access token hết hạn là bình thường, refresh token sẽ tự cấp lại | — |
| `[LỖI] ... invalid_grant` | **Refresh token hết hạn** (thường gặp sau 7 ngày khi app ở chế độ Testing) | Publish OAuth app, tạo lại `token.json` (3.2), cập nhật secret (4.3 bước 2) |
| `[installs] lỗi scrape <pkg>` | Không lấy được dữ liệu Play Store cho app đó. App đó giữ số cũ | App bị gỡ khỏi store thì lỗi này là bình thường |
| `[CẢNH BÁO] x/N pkg scrape lỗi` / `[LỖI] 100% pkg scrape lỗi` | Có thể **Google Play đang chặn IP** (hay gặp với IP datacenter của GitHub) | Chạy lại sau vài giờ; nếu lỗi kéo dài trên Actions thì quay về chạy bằng Task Scheduler |
| `[env] utc_now=...` | Giờ bắt đầu thực tế | So với 01:00 UTC để biết GitHub cron bị trễ bao lâu |
| `push_*.py rc=1 ... [stderr] ...` | Ghi Sheet lỗi | Đọc stderr: `invalid_grant` là lỗi token; `403` là tài khoản không có quyền sửa Sheet; `429` là vượt quota, chạy lại sau |
| `tổng thời gian: X phút` | Tổng thời lượng chạy | Tăng dần theo số app, cần để ý quota phút Actions |

Chạy lại chỉ phần push (sau khi đã sửa token), không cần scrape lại:
```powershell
python scripts/push_tracking.py; python scripts/push_merged.py; python scripts/push_dashboard.py
```

---

## 5a. Thị trường ngách (`market.py`) — so sánh ngách công bằng

Dream100 chỉ theo dõi app **PASS**, tức là app đã lọt qua bộ lọc (mới, có ads, ≥5k/ngày). Vì vậy số app mỗi ngách lệch nhau rất nhiều (từ 1 đến 17), và nó chỉ đo "app mới nào đang thắng" chứ không đo được nhu cầu của ngách. `market.py` lấy một **mẫu thị trường có cỡ bằng nhau** cho mọi ngách:

1. `node scripts/hotmap_list.mjs`: lấy Top Free 200 của 8 nước (US, BR, IN, ID, MX, DE, JP, VN) × 10 category, khoảng 80 request, mất chừng 1 phút.
2. Mỗi **ngách** (`CLUSTERS` trong `common.py`, phân loại theo từ khoá thói quen trong tên app) và mỗi **category** lấy đúng `TOP_N = 10` app có **độ phủ chart** cao nhất (lọt top ở nhiều nước, hạng cao).
3. Scrape installs hằng ngày, ghi vào `data/market.csv`. Lấy review mỗi 7 ngày, cache ở `data/market_reviews.json`.
4. Chấm điểm 0–100. Mỗi chỉ số được quy về hạng phần trăm giữa các nhóm cùng cấp, trọng số lấy từ `docs/tieu-chi-chon-ngach.md`:

| Chỉ số | Trọng số | Đo bằng | Trả lời câu hỏi |
|---|---|---|---|
| Cầu | ×1 | median tăng installs/ngày mỗi app. Lịch sử < 7 ngày thì dùng TB vòng đời | Có nhiều người tải không |
| Toàn cầu | ×1 | số nước trung bình mỗi app lọt Top 200 (trên 8 nước) | User toàn cầu hay chỉ một nước |
| App thắng | ×2 | số app < 2 năm, có ads, không big dev, ≥5k/ngày | App mới có cửa thắng không |
| Thói quen | ×2 | median % review nhắc "every day / daily / for months..." | Có thành thói quen hằng ngày không |
| IAA | ×1 | % app có ads | Có kiếm tiền bằng ads được không |

Ngách rớt nhóm B (`POLICY_OUT` trong `common.py`: AI gen, short drama, VPN, cleaner...) vẫn được theo dõi nhưng **không chấm điểm**. Kết quả nằm ở `data/market.md` và phần "Thị trường ngách" trên Grafana.

**Giới hạn cần biết:**
- Chỉ có dữ liệu Android/Google Play. `realInstalls` là số toàn cầu, nhưng Play không chia theo nước. Độ phủ theo nước lấy từ top chart.
- Review chỉ lấy tiếng Anh, store US. Tín hiệu thói quen là proxy (WhatsApp/Duolingo ~9%, keyboard theme 0–2%), không thay được retention thật.
- Ngách nhận diện bằng từ khoá trong tên app. App bị xếp sai thì sửa `CLUSTERS`. Ngách có ít hơn 10 app trong chart (Font, Find phone) sẽ hiện số app thật ở cột `Số app`.

## 5b. Dashboard Grafana + Supabase

`push_dashboard.py` ghi 2 bảng vào Postgres (schema `scouting`), sau đó Grafana đọc từ đó:
- `scouting.app_daily`: giống tab `Data`, 1 dòng = 1 app × 1 ngày.
- `scouting.app_window`: giống tab `Window`, dùng cho heatmap 7 ngày / 30 ngày / Lifetime.

Mỗi lần chạy, 2 bảng này bị drop rồi tạo lại trong 1 transaction, vì chúng là dữ liệu dẫn xuất từ `Dream100.csv`. Dashboard được lưu dưới dạng code trong `grafana/dashboard.json`.

### Setup lần đầu

1. **Supabase** (https://supabase.com, gói free): tạo project. Vào **SQL Editor** và chạy đoạn dưới (đổi mật khẩu) để tạo role chỉ-đọc cho Grafana:
   ```sql
   create schema if not exists scouting;
   create role grafana_ro login password 'ĐỔI_MẬT_KHẨU';
   grant usage on schema scouting to grafana_ro;
   alter default privileges in schema scouting grant select on tables to grafana_ro;
   ```
2. Lấy connection string: **Connect → Session pooler** (dạng IPv4; GitHub Actions và Grafana Cloud không gọi được host IPv6 trực tiếp). Kết quả có dạng
   `postgresql://postgres.<project-ref>:<mật-khẩu>@aws-0-<region>.pooler.supabase.com:5432/postgres`. Đặt nó làm secret:
   ```powershell
   gh secret set DATABASE_URL --repo tantai-bic/app-scouting   # dán connection string khi được hỏi
   ```
3. **Grafana Cloud** (https://grafana.com, gói free): vào Connections → Add new connection → **PostgreSQL**, điền:
   - Host: `aws-0-<region>.pooler.supabase.com:5432`, Database: `postgres`
   - User: `grafana_ro.<project-ref>` (khi đi qua pooler, user phải có hậu tố `.<project-ref>`), Password: mật khẩu ở bước 1
   - TLS/SSL Mode: `require`
4. Vào Dashboards → New → **Import** → upload `grafana/dashboard.json` → chọn data source vừa tạo.

Sửa dashboard: sửa trên Grafana, rồi chọn **Export → Export as JSON (Export for sharing externally)** và ghi đè `grafana/dashboard.json` để lưu lại vào repo.

Chạy thử trên máy (cần Docker), không cần Supabase:
```powershell
docker run -d --name scout-pg -e POSTGRES_PASSWORD=pw -p 55432:5432 postgres:17
$env:DATABASE_URL="postgresql://postgres:pw@localhost:55432/postgres"; python scripts/push_dashboard.py; Remove-Item Env:DATABASE_URL
```

---

## 6. Flow (A) — Thêm ngách mới

Ví dụ thêm ngách "ringtone2":

1. **Lấy danh sách package** của ngách, dùng skill `aso-app-scouting`, AppBrain hoặc search Play Store, rồi lưu vào `pool_ringtone2.txt` (mỗi dòng một package).
2. **Verify với Play Store**. Kết quả ghi ra `data/verify_ringtone2.json`:
   ```powershell
   Get-Content pool_ringtone2.txt | python scripts/verify.py -o verify_ringtone2.json
   ```
3. **Build Dream 100** (thêm dòng vào `data/Dream100.csv` và `data/Dream100.md`):
   ```powershell
   python scripts/dream100.py --verify verify_ringtone2.json --title "Ringtone 2"
   ```
   Thêm `--all` nếu muốn đưa cả app FAIL vào bảng.
4. **Đưa ngách vào theo dõi hằng ngày**: thêm một dòng vào `NICHES` trong `scripts/common.py`:
   ```python
   ("verify_ringtone2.json", "Ringtone 2"),
   ```
5. Đẩy lên Sheet: `python scripts/push_merged.py`. Sau đó commit và push (`git add data scripts; git commit; git push`).

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
| `asolytics_*.txt` | Output asolytics cũ, không dùng nữa từ 2026-10-28 (DL/ngày tính từ bucket installs) |
| `verify_tracker.json`, `asolytics_tracker.txt` | Ngách tracker đã bỏ theo dõi từ 2026-09-23 (0/71 app PASS) |
| `pool_*.txt`, `*_pass.txt`, `verify_*.txt`, `verify_out.json`, … | Output trung gian của các lần scouting cũ |
