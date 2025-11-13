#!/usr/bin/env bash
#
# 通用一键停止脚本（POSIX sh/bash）
#
# 功能：
# - 尝试按端口和进程模式终止后端（uvicorn）与前端（vite）进程
#
# 使用：
#   bash ./scripts/stop_all.sh
#
# 可选环境变量：
#   BACKEND_PORT   后端端口（默认 8000）
#   FRONTEND_PORT  前端端口（默认 3000）
#
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() { printf "[stop_all] %s\n" "$*"; }

kill_port() {
  local port="$1"
  log "按端口终止进程：${port}"
  if command -v lsof >/dev/null 2>&1; then
    lsof -t -i:"${port}" | xargs -r kill -9 || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" || true
  else
    # Windows (Git Bash/MSYS) 兜底：使用 netstat + taskkill
    local uname_s="$(uname -s 2>/dev/null || echo unknown)"
    case "${uname_s}" in
      MINGW*|MSYS*|CYGWIN*|Windows_NT)
        if command -v netstat >/dev/null 2>&1; then
          # 查找该端口的 LISTENING 进程PID
          local pids
          pids=$(netstat -ano | grep ":${port}" | grep -i LISTEN | awk '{print $NF}' | sort -u)
          if [[ -n "${pids}" ]]; then
            log "检测到PID: ${pids}，执行 taskkill /F"
            for pid in ${pids}; do
              taskkill /PID "${pid}" /F >/dev/null 2>&1 || true
            done
          else
            log "未检测到端口 ${port} 的PID。"
          fi
        else
          log "未找到 lsof/fuser/netstat，跳过端口杀进程。"
        fi
        ;;
      *)
        log "未找到 lsof/fuser，跳过端口杀进程。"
        ;;
    esac
  fi
}

kill_pattern() {
  local pattern="$1"
  log "按模式终止进程：${pattern}"
  if command -v pkill >/dev/null 2>&1; then
    pkill -f "${pattern}" || true
  else
    # 兼容部分环境：手动筛选并kill
    if command -v ps >/dev/null 2>&1; then
      ps aux | grep -E "${pattern}" | grep -v grep | awk '{print $2}' | xargs -r kill -9 || true
    fi
  fi
}

log "项目根目录：${REPO_ROOT}"

# 优先按端口杀进程
kill_port "${BACKEND_PORT}" || true
kill_port "${FRONTEND_PORT}" || true

# 兜底：按典型模式杀进程
kill_pattern "uvicorn .*app\.main:app" || true
kill_pattern "vite" || true
kill_pattern "npm.*run.*dev" || true
kill_pattern "node.*vite" || true

log "一键停止完成。"