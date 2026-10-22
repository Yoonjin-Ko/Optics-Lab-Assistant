#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

[ -x ".venv/bin/python3" ] && export PATH="$PWD/.venv/bin:$PATH"

if ! curl -s --max-time 2 http://127.0.0.1:8100/health >/dev/null 2>&1; then
    echo "ERROR: 백엔드(http://127.0.0.1:8100)가 응답하지 않습니다."
    echo "  먼저 다른 터미널에서 아래 중 하나로 백엔드를 띄우세요:"
    echo "    ./sh/run_agent_openai.sh   (실제 OpenAI API, 과금)"
    echo "    ./sh/run_agent_ollma.sh    (로컬 Ollama)"
    exit 1
fi

lsof -ti:8600 | xargs kill -9 2>/dev/null || true

cleanup() {
    echo
    echo "프론트엔드(web_demo_server.py)를 종료합니다..."
    lsof -ti:8600 | xargs kill -9 2>/dev/null || true
}
trap cleanup EXIT

python3 web_demo_server.py &
SERVER_PID=$!
for _ in $(seq 1 40); do
    curl -s http://127.0.0.1:8600/health >/dev/null 2>&1 && break
    sleep 0.5
done

cat <<EOF

 프론트엔드가 떠 있습니다 → http://localhost:8600
 (web_chat.html을 띄우고 /chat·/chat/stream을 백엔드 8100으로 프록시)

브라우저에서 http://localhost:8600 접속해 바로 채팅해볼 수 있습니다.
종료하려면 이 터미널에서 Ctrl+C.
EOF

wait "$SERVER_PID"
