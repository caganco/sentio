"""Get pytest test summary without Unix pipes."""
import subprocess
import sys

result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '-q'],
    capture_output=True,
    text=True,
    timeout=300,
)

# Find summary line: "474 passed, 1 skipped in 42.90s"
for line in result.stdout.split('\n'):
    if ' passed' in line and ' in ' in line:
        print(line)
        break

sys.exit(result.returncode)
