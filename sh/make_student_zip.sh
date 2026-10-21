#!/usr/bin/env bash
# 역할: 학습 배포용 프로젝트 압축본을 구성한다.
# 입력: 명령행 인자보다 아래 환경변수·프로젝트 파일 설정을 사용한다.
# 읽는 순서: 사전 확인 → 준비/실행 → 정리. 실제 명령과 기존 주의사항을 함께 확인한다.
#
# all_total_vue — 학생 배포용 zip을 만드는 스크립트.
#
# .env(실제 API 키가 들어있는 파일)는 절대 포함하지 않고, 대신 .env.example을
# 담아서 학생이 직접 `cp .env.example .env` 후 본인 키를 채우게 한다. 그 외
# .venv/__pycache__/session.db/*.log 등 로컬 실행 중 생기는 산출물도 제외한다.
#
# 실행:
#   bash sh/make_student_zip.sh
# 결과:
#   ../all_total_vue_student.zip  (단계별/ 바로 아래, all_total_vue와 같은 위치)
#
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="all_total_vue_student"
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
  --exclude='.DS_Store' \
  ./ "/tmp/${NAME}/"

( cd /tmp && zip -rq "$OLDPWD/$OUT" "${NAME}" )
rm -rf "/tmp/${NAME}"

echo "생성됨: $(cd .. && pwd)/${NAME}.zip"
echo "--- 포함된 .env* 파일 확인 ---"
unzip -l "$OUT" | grep -i "\.env" || echo "(없음)"
