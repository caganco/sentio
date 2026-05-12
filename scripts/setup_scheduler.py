"""Windows Task Scheduler kurulumu — Görev Zamanlayıcı'ya günlük 09:00 görevi ekler."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYTHON = sys.executable
SCRIPT = ROOT / "scripts" / "daily_update.py"
TASK_NAME = "BIST_DailyUpdate"


def create_task() -> None:
    cmd = [
        "schtasks", "/Create", "/F",
        "/TN", TASK_NAME,
        "/TR", f'"{PYTHON}" "{SCRIPT}" --scan --generate-report',
        "/SC", "DAILY",
        "/ST", "09:00",
        "/RL", "HIGHEST",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Gorev olusturuldu: {TASK_NAME}")
        print(f"  Python : {PYTHON}")
        print(f"  Script : {SCRIPT}")
        print(f"  Zaman  : Her gun 09:00")
    else:
        print("HATA:", result.stderr.strip())
        sys.exit(1)


def delete_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"Gorev silindi: {TASK_NAME}")
    else:
        print("HATA:", result.stderr.strip())


def query_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
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
