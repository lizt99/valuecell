#!/bin/bash
set -Eeuo pipefail

# Simple project launcher with auto-install for bun and uv
# - macOS: use Homebrew to install missing tools
# - other OS: print guidance

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PY_DIR="$SCRIPT_DIR/python"

BACKEND_PID=""
FRONTEND_PID=""
POLLING_PID=""

info()  { echo "[INFO]  $*"; }
success(){ echo "[ OK ]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERR ]  $*" 1>&2; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

ensure_brew_on_macos() {
  if [[ "${OSTYPE:-}" == darwin* ]]; then
    if ! command_exists brew; then
      error "Homebrew is not installed. Please install Homebrew: https://brew.sh/"
      error "Example install: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
      exit 1
    fi
  fi
}

ensure_tool() {
  local tool_name="$1"; shift
  local brew_formula="$1"; shift || true

  if command_exists "$tool_name"; then
    success "$tool_name is installed ($($tool_name --version 2>/dev/null | head -n1 || echo version unknown))"
    return 0
  fi

  case "$(uname -s)" in
    Darwin)
      ensure_brew_on_macos
      info "Installing $tool_name via Homebrew..."
      brew install "$brew_formula"
      ;;
    Linux)
      info "Detected Linux, auto-installing $tool_name..."
      if [[ "$tool_name" == "bun" ]]; then
        curl -fsSL https://bun.sh/install | bash
        # Add Bun default install dir to PATH (current process only)
        if ! command_exists bun && [[ -x "$HOME/.bun/bin/bun" ]]; then
          export PATH="$HOME/.bun/bin:$PATH"
        fi
      elif [[ "$tool_name" == "uv" ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv default install dir to PATH (current process only)
        if ! command_exists uv && [[ -x "$HOME/.local/bin/uv" ]]; then
          export PATH="$HOME/.local/bin:$PATH"
        fi
      else
        warn "Unknown tool: $tool_name"
      fi
      ;;
    *)
      warn "$tool_name not installed. Auto-install is not provided on this OS. Please install manually and retry."
      exit 1
      ;;
  esac

  if command_exists "$tool_name"; then
    success "$tool_name installed successfully"
  else
    error "$tool_name installation failed. Please install manually and retry."
    exit 1
  fi
}

compile() {
  # Backend deps
  if [[ -d "$PY_DIR" ]]; then
    info "Sync Python dependencies (uv sync)..."
    (cd "$PY_DIR" && bash scripts/prepare_envs.sh && uv run valuecell/server/db/init_db.py)
    success "Python dependencies synced"
  else
    warn "Backend directory not found: $PY_DIR. Skipping"
  fi

  # Frontend deps
  if [[ -d "$FRONTEND_DIR" ]]; then
    info "Install frontend dependencies (bun install)..."
    (cd "$FRONTEND_DIR" && bun install)
    success "Frontend dependencies installed"
  else
    warn "Frontend directory not found: $FRONTEND_DIR. Skipping"
  fi
}

start_polling_service() {
  if [[ ! -d "$PY_DIR" ]]; then
    warn "Backend directory not found; skipping polling service start"
    return 0
  fi
  
  info "Starting TradingView Polling Service..."
  
  # Load environment variables from .env file
  local env_file="$SCRIPT_DIR/.env"
  if [[ -f "$env_file" ]]; then
    # Export Svix credentials
    export $(grep -v '^#' "$env_file" | grep SVIX | xargs) 2>/dev/null || true
  fi
  
  # Check if credentials are set
  if [[ -z "${SVIX_API_TOKEN:-}" ]] || [[ -z "${SVIX_CONSUMER_ID:-}" ]]; then
    warn "Svix API credentials not found in .env file"
    warn "Polling service may not work correctly"
    warn "Please set SVIX_API_TOKEN and SVIX_CONSUMER_ID in .env"
  fi
  
  # Create logs directory
  mkdir -p "$SCRIPT_DIR/logs"
  
  # Start polling service in background
  (
    cd "$PY_DIR" && \
    nohup uv run --env-file "$env_file" \
      -m valuecell.agents.tradingview_signal_agent.polling_service \
      > "$SCRIPT_DIR/logs/polling_service.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/logs/polling_service.pid"
  )
  
  # Read PID
  sleep 1
  if [[ -f "$SCRIPT_DIR/logs/polling_service.pid" ]]; then
    POLLING_PID=$(cat "$SCRIPT_DIR/logs/polling_service.pid")
    if kill -0 "$POLLING_PID" 2>/dev/null; then
      success "Polling service started (PID: $POLLING_PID)"
      info "  Logs: $SCRIPT_DIR/logs/polling_service.log"
      info "  Polling interval: 3 minutes"
    else
      warn "Polling service failed to start (check logs/polling_service.log)"
      POLLING_PID=""
    fi
  fi
}

start_backend() {
  if [[ ! -d "$PY_DIR" ]]; then
    warn "Backend directory not found; skipping backend start"
    return 0
  fi
  info "Starting backend (uv run scripts/launch.py)..."
  cd "$PY_DIR" && uv run --with questionary scripts/launch.py
}

start_frontend() {
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    warn "Frontend directory not found; skipping frontend start"
    return 0
  fi
  info "Starting frontend dev server (bun run dev)..."
  (
    cd "$FRONTEND_DIR" && bun run dev
  ) & FRONTEND_PID=$!
  info "Frontend PID: $FRONTEND_PID"
}

cleanup() {
  echo
  info "Stopping services..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$POLLING_PID" ]] && kill -0 "$POLLING_PID" 2>/dev/null; then
    info "Stopping polling service..."
    kill "$POLLING_PID" 2>/dev/null || true
  fi
  # Also try to stop polling service by PID file
  if [[ -f "$SCRIPT_DIR/logs/polling_service.pid" ]]; then
    local pid=$(cat "$SCRIPT_DIR/logs/polling_service.pid")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$SCRIPT_DIR/logs/polling_service.pid"
  fi
  success "Stopped"
}

trap cleanup EXIT INT TERM

print_usage() {
  cat <<'EOF'
Usage: ./start.sh [options]

Description:
  - Checks whether bun and uv are installed; on macOS, missing tools will be auto-installed via Homebrew.
  - Then installs backend and frontend dependencies and starts services.
  - Automatically starts TradingView Polling Service for data collection.

Services Started:
  - TradingView Polling Service (background, every 3 minutes)
  - Frontend (bun dev server on port 1420)
  - Backend (API server and agents)

Options:
  --no-frontend      Start backend only
  --no-backend       Start frontend only
  --no-polling       Skip polling service (not recommended)
  -h, --help         Show help

Environment Variables:
  Required in .env file for polling service:
    SVIX_API_TOKEN      - Svix API token for polling
    SVIX_CONSUMER_ID    - Svix consumer ID

Logs:
  - Polling Service: logs/polling_service.log
  - Backend/Agents: logs/<timestamp>/
EOF
}

main() {
  local start_frontend_flag=1
  local start_backend_flag=1
  local start_polling_flag=1

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-frontend) start_frontend_flag=0; shift ;;
      --no-backend)  start_backend_flag=0; shift ;;
      --no-polling)  start_polling_flag=0; shift ;;
      -h|--help)     print_usage; exit 0 ;;
      *) error "Unknown argument: $1"; print_usage; exit 1 ;;
    esac
  done

  # Ensure tools
  ensure_tool bun oven-sh/bun/bun
  ensure_tool uv uv

  compile

  # Start polling service first (independent background service)
  if (( start_polling_flag )); then
    start_polling_service
  fi

  if (( start_frontend_flag )); then
    start_frontend
  fi
  sleep 5  # Give frontend a moment to start

  if (( start_backend_flag )); then
    start_backend
  fi

  # Wait for background jobs
  wait
}

main "$@"