#!/usr/bin/env bash
#
# 通用一键启动脚本（POSIX sh/bash）
#
# 功能：
# - 释放后端与前端默认端口占用（尽力尝试）
# - 启动后端 Uvicorn（热重载），启动前端 Vite（--host）
# - 后端默认使用 Conda 的 aitt-py311 环境；可通过环境变量覆盖
#
# 使用：
#   bash ./scripts/start_all.sh
#
# 可选环境变量：
#   BACKEND_PORT   后端端口（默认 8000）
#   FRONTEND_PORT  前端端口（默认 3000）
#   PYTHON_BIN     指定 python 解释器（绝对路径或在 PATH 中）
#   CONDA_ENV_NAME 指定 conda 环境名（如 aitt-py311），需系统已安装 conda
#
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PYTHON_BIN="${PYTHON_BIN:-}"
# 默认使用 aitt-py311 环境（可通过导出 CONDA_ENV_NAME 覆盖）
CONDA_ENV_NAME="${CONDA_ENV_NAME:-aitt-py311}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"

log() { printf "[start_all] %s\n" "$*"; }

kill_port() {
  local port="$1"
  log "尝试释放端口 ${port} 占用..."
  if command -v lsof >/dev/null 2>&1; then
    lsof -t -i:"${port}" | xargs -r kill -9 || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" || true
  else
    log "未找到 lsof/fuser，跳过端口释放。"
  fi
}

start_backend() {
  cd "${BACKEND_DIR}"
  local host="127.0.0.1"
  log "启动后端（端口 ${BACKEND_PORT}，热重载）..."
  if command -v conda >/dev/null 2>&1; then
    # 先尝试使用 Conda 指定环境（默认 aitt-py311）
    log "使用 Conda 环境 '${CONDA_ENV_NAME}' 启动后端..."
    # 预检：打印解释器版本，帮助定位环境不可用问题
    if ! conda run -n "${CONDA_ENV_NAME}" python -V >/dev/null 2>&1; then
      log "警告：Conda 环境 '${CONDA_ENV_NAME}' 不可用或未创建，回退到系统 Python。"
      if [[ -n "${PYTHON_BIN}" ]]; then
        nohup "${PYTHON_BIN}" -m uvicorn app.main:app --host "${host}" --port "${BACKEND_PORT}" --log-level info --reload \
          > "${LOG_DIR}/backend_dev.log" 2>&1 &
      else
        nohup python -m uvicorn app.main:app --host "${host}" --port "${BACKEND_PORT}" --log-level info --reload \
          > "${LOG_DIR}/backend_dev.log" 2>&1 &
      fi
    else
      nohup conda run -n "${CONDA_ENV_NAME}" uvicorn app.main:app --host "${host}" --port "${BACKEND_PORT}" --log-level info --reload \
        > "${LOG_DIR}/backend_dev.log" 2>&1 &
    fi
  else
    log "未检测到 conda，使用系统 Python 启动后端。"
    if [[ -n "${PYTHON_BIN}" ]]; then
      nohup "${PYTHON_BIN}" -m uvicorn app.main:app --host "${host}" --port "${BACKEND_PORT}" --log-level info --reload \
        > "${LOG_DIR}/backend_dev.log" 2>&1 &
    else
      nohup python -m uvicorn app.main:app --host "${host}" --port "${BACKEND_PORT}" --log-level info --reload \
        > "${LOG_DIR}/backend_dev.log" 2>&1 &
    fi
  fi
}

start_frontend() {
  cd "${FRONTEND_DIR}"
  log "启动前端 Vite（端口 ${FRONTEND_PORT}，--host）..."
  nohup npm run dev -- --host > "${LOG_DIR}/frontend_dev.log" 2>&1 &
}

log "项目根目录：${REPO_ROOT}"
kill_port "${BACKEND_PORT}" || true
kill_port "${FRONTEND_PORT}" || true

start_backend
start_frontend

log "后端已启动： http://127.0.0.1:${BACKEND_PORT}/"
log "前端已启动： http://localhost:${FRONTEND_PORT}/"
log "日志文件： ${LOG_DIR}/backend_dev.log, ${LOG_DIR}/frontend_dev.log"
log "如需指定 64 位解释器：导出 PYTHON_BIN 或设置 CONDA_ENV_NAME 后执行脚本。"