#!/usr/bin/env python3
"""Chạy hằng ngày (Task Scheduler local hoặc GitHub Actions): với mỗi niche đang
theo dõi, lấy lại DL/ngày thật từ asolytics, append 1 dòng/app/ngày vào
Dream100.csv, rồi sync lên Google Sheet (tab Tracking + tab Dream100 chính).

Khác run_asolytics_batch.py (backfill 1 lần, skip pkg đã có): script này LUÔN
ghi đè asolytics_<niche>.txt mỗi lần chạy vì cần số MỚI của ngày hôm nay.

Usage: python scripts/daily_tracking.py  (không cần argument, tự lặp qua common.NICHES)
       FORCE_RUN=1 python scripts/daily_tracking.py  -> bỏ qua chặn "đã chạy hôm nay"
Log: logs/daily_tracking.log (append, để xem lịch sử chạy khi không ngồi máy).
Exit code != 0 khi có bước hỏng (push lỗi, niche 0 pkg OK...) -> Actions báo đỏ.
"""
import datetime, json, os, platform, shutil, subprocess, sys, time, traceback
from common import ASO_MARKER, DATA, LOGS, NICHES, ROOT, TOKEN, logged_pkgs, run_asolytics
from verify import check, verdict as compute_verdict

SCRIPTS = ROOT / "scripts"
LOG = LOGS / "daily_tracking.log"
LAST_RUN = LOGS / ".daily_tracking_last_run"  # theo LOGS_DIR -> chạy test không chặn lần chạy thật
TODAY = datetime.date.today().isoformat()
ERRORS = []  # lỗi nghiêm trọng -> exit 1 ở cuối
LOGS.mkdir(parents=True, exist_ok=True)

def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def fail(msg):
    ERRORS.append(msg)
    log(f"[LỖI] {msg}")

# ponytail: chạy theo trigger "At log on" (mỗi lần mở máy) nên cần tự chặn
# chạy lại nếu đã chạy hôm nay; nâng cấp lên lock file nếu cần chống chạy
# chồng lấn (2 tiến trình cùng lúc).
if (not os.environ.get("FORCE_RUN") and LAST_RUN.exists()
        and LAST_RUN.read_text(encoding="utf-8").strip() == TODAY):
    log(f"[bỏ qua] đã chạy hôm nay ({TODAY}), đặt FORCE_RUN=1 để chạy lại")
    sys.exit(0)

def tool_version(cmd):
    if not shutil.which(cmd[0]):
        return "KHÔNG TÌM THẤY"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception as e:
        return f"lỗi: {e}"

def log_env():
    """Thông tin môi trường — để so sánh lần chạy local vs Actions khi có lỗi."""
    log(f"[env] host={platform.node()} os={platform.platform()} python={sys.version.split()[0]}")
    log(f"[env] utc_now={datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S} TODAY(local)={TODAY}")
    if os.environ.get("GITHUB_ACTIONS"):
        # so utc_now với giờ cron trong workflow để đo độ trễ lịch của GitHub
        log(f"[env] github event={os.environ.get('GITHUB_EVENT_NAME')} run_id={os.environ.get('GITHUB_RUN_ID')}"
            f" attempt={os.environ.get('GITHUB_RUN_ATTEMPT')} sha={os.environ.get('GITHUB_SHA', '')[:7]}")
    log(f"[env] firefox={tool_version(['firefox', '--version'])}")
    log(f"[env] geckodriver={tool_version(['geckodriver', '--version'])}")
    log(f"[env] asolytics={'có' if shutil.which('asolytics') else 'KHÔNG TÌM THẤY trong PATH'}")
    if not TOKEN.exists():
        fail("thiếu token.json — push lên Sheet sẽ hỏng (trên Actions: kiểm tra secret GOOGLE_TOKEN_JSON)")
    else:
        try:
            t = json.loads(TOKEN.read_text(encoding="utf-8"))
            # không log token, chỉ log metadata để debug hết hạn
            log(f"[env] token.json: account={t.get('account') or '?'} expiry={t.get('expiry')}"
                f" có refresh_token={'refresh_token' in t}")
        except Exception as e:
            fail(f"token.json không đọc được JSON: {e}")

# ponytail: verdict trong verify_*.json là tĩnh (dream100.py không tính lại từ
# asolytics) — too-old/no-ads/big-dev/date? không bao giờ tự hết FAIL theo ngày,
# chỉ dl/day<5k mới có cơ hội đổi. Bỏ 3 nhóm kia khỏi asolytics -> giảm ~80% call.
# App đã từng vào Dream100.csv thì luôn theo dõi tiếp, bất kể verdict hiện tại.
def _worth_tracking(a, logged=frozenset()):
    return a.get("verdict") in ("PASS", "FAIL:dl/day<5k") or a["pkg"] in logged

def refresh_installs(verify_path, pkgs):
    """Re-scrape realInstalls/age/verdict qua Google Play — nếu không, Lifetime
    installs đứng yên mãi (verify_*.json chỉ tạo 1 lần) và cột Δ hôm nay của
    push_tracking.py luôn ra 0. Lỗi scrape 1 pkg -> giữ số cũ, không xoá."""
    data = json.load(open(verify_path, encoding="utf-8"))
    by_pkg = {a["pkg"]: a for a in data}
    errs, changed, t0 = 0, 0, time.monotonic()
    for pkg in pkgs:
        t = time.monotonic()
        c = check(pkg)
        dt = time.monotonic() - t
        if "error" in c:
            errs += 1
            log(f"  [installs] lỗi scrape {pkg} ({dt:.1f}s): {c['error']} — giữ số cũ")
            continue
        old = by_pkg.get(pkg, {})
        c["verdict"] = compute_verdict(c)
        if old.get("realInstalls") != c.get("realInstalls") or old.get("verdict") != c["verdict"]:
            changed += 1
        log(f"  [installs] {pkg} ({dt:.1f}s): {old.get('realInstalls')} -> {c.get('realInstalls')}"
            f" verdict {old.get('verdict')} -> {c['verdict']}")
        by_pkg[pkg] = c
    json.dump(list(by_pkg.values()), open(verify_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log(f"  [installs] tổng: {len(pkgs)} pkg, {errs} lỗi, {changed} đổi số, {time.monotonic() - t0:.0f}s")
    # nhiều lỗi cùng lúc thường là Google Play chặn/giới hạn IP (hay gặp trên IP datacenter)
    if pkgs and errs == len(pkgs):
        fail(f"{verify_path.name}: 100% pkg scrape lỗi — nghi Google Play chặn IP")
    elif pkgs and errs / len(pkgs) > 0.3:
        log(f"  [CẢNH BÁO] {errs}/{len(pkgs)} pkg scrape lỗi — có thể đang bị rate limit")

def refresh_asolytics(aso_path, pkgs):
    aso_path.write_text("", encoding="utf-8")  # ghi đè fresh mỗi ngày
    ok, t0 = 0, time.monotonic()
    for pkg in pkgs:
        t = time.monotonic()
        try:
            r = run_asolytics(pkg)
            body = r.stdout or r.stderr
            dt = time.monotonic() - t
            if ASO_MARKER in r.stdout:
                ok += 1
                log(f"  [asolytics] {pkg} OK ({dt:.1f}s)")
            else:
                # in đuôi stdout/stderr — traceback selenium/geckodriver nằm ở đây
                tail = " | ".join((r.stderr or r.stdout).strip().splitlines()[-5:])
                log(f"  [asolytics] {pkg} HỎNG rc={r.returncode} ({dt:.1f}s): {tail[:600]}")
        except subprocess.TimeoutExpired:
            body = "lỗi: timeout 90s"
            log(f"  [asolytics] {pkg} TIMEOUT 90s")
        except Exception as e:
            body = f"lỗi: {e}"
            log(f"  [asolytics] {pkg} EXCEPTION: {e!r}")
        with aso_path.open("a", encoding="utf-8") as f:
            f.write(f"===== {pkg}\n{body.strip()}\n")
    log(f"  [asolytics] tổng: {ok}/{len(pkgs)} OK, {time.monotonic() - t0:.0f}s")
    return len(pkgs), ok

def run_script(cmd, label):
    t = time.monotonic()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout.strip() + ("\n[stderr] " + r.stderr.strip() if r.stderr.strip() else "")).strip()
    log(f"{label} rc={r.returncode} ({time.monotonic() - t:.1f}s) -> {out}")
    if r.returncode != 0:
        if "invalid_grant" in out:
            fail(f"{label}: refresh token hết hạn/bị thu hồi (invalid_grant) — tạo lại token.json"
                 " (OAuth app ở chế độ Testing thì token chỉ sống 7 ngày)")
        else:
            fail(f"{label}: exit {r.returncode}")

def main():
    t0 = time.monotonic()
    log("=== bắt đầu daily_tracking ===")
    log_env()
    for verify_file, aso_file, title in NICHES:
        if not (DATA / verify_file).exists():
            log(f"[bỏ qua] thiếu {verify_file}")
            continue
        log(f"--- {title} ---")
        logged = logged_pkgs()
        pkgs = [a["pkg"] for a in json.load(open(DATA / verify_file, encoding="utf-8"))
                if "error" not in a and _worth_tracking(a, logged)]
        log(f"{title}: {len(pkgs)} pkg cần theo dõi")
        refresh_installs(DATA / verify_file, pkgs)
        total, ok = refresh_asolytics(DATA / aso_file, pkgs)
        log(f"{title}: asolytics {ok}/{total} pkg OK")
        if total and ok == 0:
            fail(f"{title}: asolytics 0/{total} OK — kiểm tra firefox/geckodriver ở [env]")
        run_script([sys.executable, SCRIPTS / "dream100.py", aso_file, "--verify", verify_file, "--title", title],
                   f"{title}: dream100.py")

    for script in ["push_tracking.py", "push_merged.py", "push_dashboard.py"]:
        run_script([sys.executable, SCRIPTS / script], script)
    log(f"tổng thời gian: {(time.monotonic() - t0) / 60:.1f} phút")

try:
    main()
except Exception:
    fail("exception không bắt được:\n" + traceback.format_exc())

if ERRORS:
    log(f"=== xong với {len(ERRORS)} lỗi: {' ; '.join(e.splitlines()[0] for e in ERRORS)} ===\n")
    sys.exit(1)
LAST_RUN.write_text(TODAY, encoding="utf-8")
log("=== xong ===\n")
