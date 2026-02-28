#!/bin/bash
# start.sh — Ansung Vision Inspection 개발 서버 실행
# 사용법: ./start.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================="
echo "  Ansung Vision Inspection"
echo "=============================="

# ── 0) 기존 프로세스 정리 ────────────────────────────────────────────────
echo ""
echo "[0/2] 기존 프로세스 정리 중..."
lsof -ti :8000 | xargs kill -9 2>/dev/null && echo "  port 8000 해제" || true
lsof -ti :5173 | xargs kill -9 2>/dev/null && echo "  port 5173 해제" || true
sleep 1

# ── 1) FastAPI 백엔드 ────────────────────────────────────────────────────
echo "[1/2] FastAPI 백엔드 시작 (port 8000)..."
cd "$ROOT_DIR"
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# ── 2) React 프론트엔드 ──────────────────────────────────────────────────
echo "[2/2] React 프론트엔드 시작 (port 5173)..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "-------------------------------"
echo "  로컬:    http://localhost:5173"
echo "  외부IP:  http://{YOUR_IP}:5173"
echo "  백엔드:  http://localhost:8000"
echo "  API 문서: http://localhost:8000/docs"
echo "-------------------------------"
echo "  종료: Ctrl+C"
echo ""

# 브라우저 자동 오픈 (프론트엔드 준비 대기)
sleep 3
echo "🌐 브라우저 열기..."
open -a "Google Chrome" "http://localhost:5173" 2>/dev/null || \
  xdg-open "http://localhost:5173" 2>/dev/null || \
  start "http://localhost:5173" 2>/dev/null || \
  echo "⚠️  브라우저 자동 시작 실패. 수동으로 http://localhost:5173 접속하세요."

# Ctrl+C 시 자식 프로세스 정리
trap "echo ''; echo '종료 중...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
