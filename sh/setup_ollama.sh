#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

FAST_MODEL="${OLLAMA_FAST_MODEL:-qwen3:0.6b}"
QUALITY_MODEL="${OLLAMA_QUALITY_MODEL:-qwen3:8b}"
FORCE_REFRESH="${OLLAMA_FORCE_REFRESH:-0}"

command -v ollama >/dev/null 2>&1 \
    || { echo "ERROR: ollama가 설치되어 있지 않습니다. https://ollama.com 에서 설치 후 재실행하세요."; exit 1; }

echo "대상 모델: fast=$FAST_MODEL / quality=$QUALITY_MODEL"

if curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "기존 ollama serve가 떠 있어 종료합니다..."
    lsof -ti:11434 | xargs kill -9 2>/dev/null || true
    for _ in $(seq 1 20); do
        curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || break
        sleep 0.5
    done
fi

echo "모델 확인을 위해 ollama serve를 임시로 띄웁니다..."
nohup ollama serve > /tmp/optics_lab_ollama_setup.log 2>&1 &

cleanup() {
    echo
    echo "임시로 띄운 ollama serve를 종료합니다..."
    lsof -ti:11434 | xargs kill -9 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
    curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
done
curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 \
    || { echo "ERROR: ollama serve 기동 실패"; exit 1; }

if [ "$FORCE_REFRESH" = "1" ]; then
    for m in "$FAST_MODEL" "$QUALITY_MODEL"; do
        if ollama list | grep "^${m}" >/dev/null; then
            echo "기존 모델 삭제(OLLAMA_FORCE_REFRESH=1): $m"
            ollama rm "$m"
        fi
    done
fi

for m in "$FAST_MODEL" "$QUALITY_MODEL"; do
    if ollama list | grep "^${m}" >/dev/null; then
        echo "이미 받아져 있어 재사용: $m"
        continue
    fi
    echo
    echo "모델 받는 중: $m (크기에 따라 수 분 소요될 수 있습니다)"
    ollama pull "$m"
done

echo
cat <<EOF
 Ollama 환경 준비 완료: $FAST_MODEL / $QUALITY_MODEL

이제 ./sh/run_agent_ollma.sh 로 에이전트를 띄워 테스트할 수 있습니다.
EOF
