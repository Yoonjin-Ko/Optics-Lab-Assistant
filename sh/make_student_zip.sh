#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="optics-lab-assistant"
OUT="../${NAME}.zip"

rm -f "$OUT"
rm -rf "/tmp/${NAME}"
mkdir -p "/tmp/${NAME}"

rsync -a \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='session.db' \
  --exclude='*.log' \
  --exclude='.env' \
  --include='.env.example' \
  --exclude='.env.*' \
  --exclude='.git' \
  --exclude='.DS_Store' \
  ./ "/tmp/${NAME}/"

( cd /tmp && zip -rq "$OLDPWD/$OUT" "${NAME}" )
rm -rf "/tmp/${NAME}"

echo "생성됨: $(cd .. && pwd)/${NAME}.zip"
echo "--- 포함된 .env* 파일 확인 ---"
unzip -l "$OUT" | grep -i "\.env" || echo "(없음)"
