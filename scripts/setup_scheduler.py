"""Windows Task Scheduler kurulumu — Görev Zamanlayıcı'ya günlük 09:00 görevi ekler.

"Run only when user is logged on" modu: `/RU` ve `/RP` verilmez; görev mevcut
oturum açmış kullanıcı bağlamında çalışır, **şifre gerekmez**. Microsoft Account
ortamlarında yerel hesap şifresi olmadığından bu mod zorunludur. `/RL HIGHEST`
korunur (en yüksek yetkiyle çalışır); kurulum yine de Administrator
PowerShell'den yapılmalıdır.
"""
import subprocess
import sys
from pathlib import Path

# schtasks emits localized (Turkish) text; the default Windows console codec
# (cp1254) can't encode the U+FFFD replacement chars that errors="replace"
# produces, crashing every print on the failure path. Force UTF-8 output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).parent.parent.resolve()
PYTHON = sys.executable
SCRIPT = ROOT / "scripts" / "daily_update.py"
TASK_NAME = "BIST_DailyUpdate"


def create_task() -> None:
    """Register the daily task in "run only when user is logged on" mode.

    No `/RU` / `/RP` is passed — schtasks registers the task under the current
    interactive user with no stored credentials, so **no password is
    requested**. Required for Microsoft Account environments (no local account
    password exists). `/RL HIGHEST` is kept; run from an Administrator
    PowerShell so the highest-privilege registration succeeds.
    """
    print(f"Gorev '{TASK_NAME}' olusturuluyor (run-only-when-logged-on, sifresiz).")
    print("Bu komut Administrator PowerShell'den calistirilmalidir.")

    # Pin the task's working directory to the project root. Task Scheduler
    # otherwise launches in %SystemRoot%\System32, where relative paths
    # (config.yaml, positions.yaml, parquet snapshots) resolve wrong and the
    # run fails. `cmd /c cd /d "<root>" && ...` fixes the CWD before Python
    # starts. Paths are quoted to tolerate spaces.
    tr_value = (
        f'cmd /c cd /d "{ROOT}" && '
        f'"{PYTHON}" "{SCRIPT}" --scan --generate-report'
    )

    cmd = [
        "schtasks", "/Create", "/F",
        "/TN", TASK_NAME,
        "/TR", tr_value,
        "/SC", "DAILY",
        "/ST", "09:00",
        "/RL", "HIGHEST",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        print("HATA: schtasks calistirilamadi:", exc.strerror or str(exc))
        sys.exit(1)

    if result.returncode == 0:
        print(f"Gorev olusturuldu: {TASK_NAME}")
        print(f"  Python    : {PYTHON}")
        print(f"  Script    : {SCRIPT}")
        print(f"  Mod       : Run only when user is logged on (sifresiz)")
        print(f"  Zaman     : Her gun 09:00 (/RL HIGHEST)")
    else:
        stderr_text = result.stderr or ""
        print("HATA:", stderr_text.strip())
        print("  Komut:", " ".join(cmd))
        print("  Not: Administrator PowerShell'den calistirildigindan emin olun.")
        sys.exit(1)


def delete_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        print(f"Gorev silindi: {TASK_NAME}")
    else:
        stderr_text = result.stderr or ""
        print("HATA:", stderr_text.strip())


def query_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        print(result.stdout or "")
    else:
        print(f"Gorev bulunamadi: {TASK_NAME}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BIST Task Scheduler Kurulumu")
    parser.add_argument("action", choices=["create", "delete", "query"], default="create", nargs="?")
    args = parser.parse_args()

    if args.action == "create":
        create_task()
    elif args.action == "delete":
        delete_task()
    else:
        query_task()
