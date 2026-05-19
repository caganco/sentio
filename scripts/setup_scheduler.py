"""Windows Task Scheduler kurulumu — Görev Zamanlayıcı'ya günlük 09:00 görevi ekler.

ÖNEMLI: `create` komutu **Administrator PowerShell**'den çalıştırılmalıdır
(`schtasks /Create /RL HIGHEST` yükseltilmiş izin gerektirir). Çalıştırıldığında
mevcut Windows kullanıcısının **hesap şifresi sorulacaktır** (getpass — gizli
giriş, ekrana yazılmaz). Şifre yalnızca schtasks'a subprocess argümanı olarak
geçer; hiçbir log, print veya hata çıktısında açık görünmez (maskelenir).
"""
import getpass
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
PYTHON = sys.executable
SCRIPT = ROOT / "scripts" / "daily_update.py"
TASK_NAME = "BIST_DailyUpdate"

# Sentinel used when rendering the schtasks command for diagnostics so the
# real password is never written to stdout/stderr/logs.
_PW_MASK = "****"


def _mask_cmd(cmd: list[str]) -> list[str]:
    """Return a copy of the schtasks argv with the /RP value replaced by a mask."""
    masked = list(cmd)
    try:
        rp_idx = masked.index("/RP")
        masked[rp_idx + 1] = _PW_MASK
    except (ValueError, IndexError):
        pass
    return masked


def create_task() -> None:
    """Register the daily task to run as the current user (service mode).

    Run this from an **Administrator PowerShell** — `/RL HIGHEST` needs
    elevation. The current user's Windows account password is requested
    interactively via getpass (hidden input). It is never stored, logged,
    or echoed; only passed to schtasks and masked in any diagnostic output.
    """
    run_as_user = getpass.getuser()
    print(f"Gorev '{TASK_NAME}' kullanici '{run_as_user}' altinda olusturulacak.")
    print("Bu komut Administrator PowerShell'den calistirilmalidir.")
    password = getpass.getpass(
        f"'{run_as_user}' Windows hesap sifresi (giris gizli): "
    )
    if not password:
        print("HATA: Sifre bos — gorev olusturulamadi.")
        sys.exit(1)

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
        "/RU", run_as_user,
        "/RP", password,
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
        # Never let the password reach a traceback — re-raise with masked argv.
        print("HATA: schtasks calistirilamadi:", exc.strerror or str(exc))
        sys.exit(1)
    finally:
        # Drop the plaintext password from memory as soon as the call returns.
        del password
        cmd[cmd.index("/RP") + 1] = _PW_MASK

    if result.returncode == 0:
        print(f"Gorev olusturuldu: {TASK_NAME}")
        print(f"  Kullanici : {run_as_user}")
        print(f"  Python    : {PYTHON}")
        print(f"  Script    : {SCRIPT}")
        print(f"  Zaman     : Her gun 09:00 (service mode, /RL HIGHEST)")
    else:
        # stderr from schtasks does not echo the /RP value; still, only print
        # the masked command for context — never the raw argv.
        stderr_text = result.stderr or ""
        print("HATA:", stderr_text.strip())
        print("  Komut (maskeli):", " ".join(_mask_cmd(cmd)))
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
