#!/bin/sh
# Close out: double-click this file (macOS opens it in a Terminal window of its own). It runs
# scripts/fos_close.py unchanged, so the script's own safeguards still apply.
# No AI is involved. Nothing here sends anything anywhere.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "Python 3 was not found on this computer. Install it, then double-click this file again."
  printf 'Press Return to close this window. '
  read -r _
  exit 127
fi
"$PY" scripts/fos_close.py
status=$?
echo
printf 'Press Return to close this window. '
read -r _
exit $status
