#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Manteclaw Daemon Supervisor — Keeps all earning lanes alive                 ║
# ║  Monitors: AWP mine-skill, 0xWork auto-tasker, Nookplot, Litcoiin miners    ║
# ║  Usage: ./supervisor.sh [check|status|stop-all]                              ║
# ║  Cron:  */5 * * * * /root/.openclaw/workspace/scripts/supervisor.sh cron     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ─── Paths ───────────────────────────────────────────────────────────────────
WORKSPACE="/root/.openclaw/workspace"
PID_DIR="$WORKSPACE/pids"
LOG_DIR="$WORKSPACE/logs"
SCRIPT_DIR="$WORKSPACE/scripts"
PROJECT_DIR="$WORKSPACE/projects"
LOG_FILE="$LOG_DIR/supervisor.log"

mkdir -p "$PID_DIR" "$LOG_DIR"


log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

# ─── Env Loading ─────────────────────────────────────────────────────────────
# Source .env so all daemons get API keys (cron doesn't load these automatically)
if [[ -f "$WORKSPACE/.env" ]]; then
    set -a
    source "$WORKSPACE/.env"
    set +a
    log "✅ Loaded env from $WORKSPACE/.env"
fi

is_alive() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cat "$file" 2>/dev/null | tr -d ' \n'
    fi
}

write_pid() {
    local file="$1"
    local pid="$2"
    echo "$pid" > "$file"
}

clear_pid() {
    local file="$1"
    rm -f "$file"
}

# ─── Daemon Definitions ──────────────────────────────────────────────────────
# Each daemon: name|pid_file|start_command|working_dir|env_exports|alive_cmd

declare -A DAEMON_NAME
declare -A DAEMON_PIDFILE
declare -A DAEMON_START
declare -A DAEMON_DIR
declare -A DAEMON_ENV
declare -A DAEMON_ALIVE_CMD

# 1. AWP Mine-Skill (Agent Work Protocol miner)
# NOTE: agent-start spawns run-worker in background then exits.
# We track the run-worker PID, not the wrapper PID.
DAEMON_NAME[awp]="AWP mine-skill"
DAEMON_PIDFILE[awp]="$PID_DIR/awp.pid"
DAEMON_START[awp]=". .venv/bin/activate && python scripts/run_tool.py agent-start"
DAEMON_DIR[awp]="$PROJECT_DIR/mine-skill"
DAEMON_ENV[awp]='export PLATFORM_BASE_URL=https://api.minework.net; export MINER_ID=mine-agent; export BANKR_API_KEY=${BANKR_API_KEY}; export WALLET_ADDRESS=0x03b96a9b9d0ca690ecc44bd09662550b9d776219'
DAEMON_ALIVE_CMD[awp]='pgrep -f "run_tool.py run-worker"'

# 2. 0xWork Auto-Tasker (Python one-shot poller in loop)
DAEMON_NAME[oxwork]="0xWork auto-tasker"
DAEMON_PIDFILE[oxwork]="$PID_DIR/0xwork.pid"
DAEMON_START[oxwork]="while true; do ./run-auto-tasker.sh once >> $LOG_DIR/0xwork.log 2>&1 || true; sleep 300; done"
DAEMON_DIR[oxwork]="$PROJECT_DIR/0xwork"
DAEMON_ENV[oxwork]=''
DAEMON_ALIVE_CMD[oxwork]=''

# 3. Nookplot Auto-Contributor
DAEMON_NAME[nookplot]="Nookplot auto-contributor"
DAEMON_PIDFILE[nookplot]="$PID_DIR/nookplot-auto.pid"
DAEMON_START[nookplot]="$SCRIPT_DIR/nookplot-auto.sh"
DAEMON_DIR[nookplot]="$WORKSPACE"
DAEMON_ENV[nookplot]=''
DAEMON_ALIVE_CMD[nookplot]=''

# 4. Litcoiin Hybrid Miner (v4 + multi-provider)
DAEMON_NAME[litcoin]="Litcoiin hybrid miner"
DAEMON_PIDFILE[litcoin]="$PID_DIR/litcoin.pid"
DAEMON_START[litcoin]=". venv/bin/activate && python3 miner-hybrid.py"
DAEMON_DIR[litcoin]="$PROJECT_DIR/litcoin"
DAEMON_ENV[litcoin]='export BANKR_API_KEY=${BANKR_API_KEY}; export BANKR_API_KEY_OLD=${BANKR_API_KEY_OLD}; export GROQ_API_KEY=${GROQ_API_KEY}; export SAMBANOVA_API_KEY=${SAMBANOVA_API_KEY}'
DAEMON_ALIVE_CMD[litcoin]=''

# ─── Core Functions ─────────────────────────────────────────────────────────

daemon_is_alive() {
    local key="$1"
    local pidfile="${DAEMON_PIDFILE[$key]}"
    local alive_cmd="${DAEMON_ALIVE_CMD[$key]}"
    local pid

    # If a custom alive command is defined, use it
    if [[ -n "$alive_cmd" ]]; then
        eval "$alive_cmd" > /dev/null 2>&1
        return $?
    fi

    # Default: check PID file
    pid=$(read_pid "$pidfile")
    is_alive "$pid"
}

get_daemon_pid() {
    local key="$1"
    local alive_cmd="${DAEMON_ALIVE_CMD[$key]}"

    # If custom alive command exists, try to get PID from it
    if [[ -n "$alive_cmd" ]]; then
        local found_pid
        found_pid=$(eval "$alive_cmd" | head -1)
        if [[ -n "$found_pid" ]]; then
            echo "$found_pid"
            return
        fi
    fi

    # Fallback to PID file
    read_pid "${DAEMON_PIDFILE[$key]}"
}

check_daemon() {
    local key="$1"
    local name="${DAEMON_NAME[$key]}"
    local pidfile="${DAEMON_PIDFILE[$key]}"
    local start_cmd="${DAEMON_START[$key]}"
    local workdir="${DAEMON_DIR[$key]}"
    local env_exports="${DAEMON_ENV[$key]}"
    local alive_cmd="${DAEMON_ALIVE_CMD[$key]}"
    local pid

    pid=$(get_daemon_pid "$key")

    if daemon_is_alive "$key"; then
        # Update PID file if we found a living process via alive_cmd
        if [[ -n "$alive_cmd" ]] && [[ "$pid" != "$(read_pid "$pidfile")" ]]; then
            write_pid "$pidfile" "$pid"
        fi
        log "✅ $name — alive (PID: $pid)"
        return 0
    fi

    # Dead or missing
    if [[ -n "$pid" ]]; then
        log "💀 $name — PID $pid dead. Clearing stale PID file."
        clear_pid "$pidfile"
    else
        log "⚠️  $name — not running (no PID file)."
    fi

    # Restart
    log "🚀 $name — RESTARTING..."

    # Build a small wrapper script to ensure correct cwd + env
    local wrapper="$PID_DIR/.${key}_start.sh"
    cat > "$wrapper" <<'WRAPPER'
#!/bin/bash
# Source .env for all API keys
cd "${workdir}" || exit 1
if [[ -f "/root/.openclaw/workspace/.env" ]]; then
    set -a
    source "/root/.openclaw/workspace/.env"
    set +a
fi
WRAPPER
    if [[ -n "$env_exports" ]]; then
        echo "$env_exports" >> "$wrapper"
    fi
    echo "eval \"$start_cmd\"" >> "$wrapper"
    chmod +x "$wrapper"

    # Launch in background and capture actual PID
    nohup bash "$wrapper" >> "$LOG_DIR/${key}.log" 2>&1 &
    local new_pid=$!

    # For AWP: agent-start exits after spawning run-worker.
    # Wait a moment, then find the actual worker PID.
    if [[ "$key" == "awp" ]]; then
        sleep 3
        local worker_pid
        worker_pid=$(pgrep -f "run_tool.py run-worker" | head -1)
        if [[ -n "$worker_pid" ]] && is_alive "$worker_pid"; then
            write_pid "$pidfile" "$worker_pid"
            log "✅ $name — restarted (worker PID: $worker_pid)"
            return 0
        else
            log "❌ $name — restart failed (no worker process found)"
            "$SCRIPT_DIR/alert.sh" daemon-failed "$key" 2>/dev/null || true
            clear_pid "$pidfile"
            return 1
        fi
    fi

    if is_alive "$new_pid"; then
        write_pid "$pidfile" "$new_pid"
        log "✅ $name — restarted (new PID: $new_pid)"
    else
        log "❌ $name — restart failed (PID $new_pid not alive)"
        "$SCRIPT_DIR/alert.sh" daemon-failed "$key" 2>/dev/null || true
        clear_pid "$pidfile"
    fi
}

stop_daemon() {
    local key="$1"
    local name="${DAEMON_NAME[$key]}"
    local pidfile="${DAEMON_PIDFILE[$key]}"
    local alive_cmd="${DAEMON_ALIVE_CMD[$key]}"
    local pid

    # For AWP, also kill the actual worker process
    if [[ "$key" == "awp" ]]; then
        local worker_pid
        worker_pid=$(pgrep -f "run_tool.py run-worker" | head -1)
        if [[ -n "$worker_pid" ]]; then
            kill "$worker_pid" 2>/dev/null || true
            sleep 1
            kill -9 "$worker_pid" 2>/dev/null || true
            log "🛑 $name — stopped worker (PID: $worker_pid)"
        fi
    fi

    pid=$(read_pid "$pidfile")
    if [[ -n "$pid" ]] && is_alive "$pid"; then
        kill "$pid" 2>/dev/null || true
        sleep 1
        if is_alive "$pid"; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        log "🛑 $name — stopped wrapper (PID: $pid)"
    fi
    clear_pid "$pidfile"
}

status_all() {
    log "══════════ Daemon Status ══════════"
    for key in awp oxwork nookplot litcoin; do
        local name="${DAEMON_NAME[$key]}"
        local pid=$(get_daemon_pid "$key")
        if daemon_is_alive "$key"; then
            log "🟢 $name — RUNNING (PID: $pid)"
        else
            log "🔴 $name — STOPPED"
        fi
    done
    log "═══════════════════════════════════"
}

# ─── Main ────────────────────────────────────────────────────────────────────

CMD="${1:-check}"

case "$CMD" in
    check|cron)
        log "══════ Supervisor Check ══════"
        for key in awp oxwork nookplot litcoin; do
            check_daemon "$key"
        done
        log "══════ Check Complete ══════"
        ;;

    status)
        status_all
        ;;

    restart)
        log "══════ Supervisor Restart ══════"
        for key in awp oxwork nookplot litcoin; do
            stop_daemon "$key"
            sleep 1
            check_daemon "$key"
        done
        log "══════ Restart Complete ══════"
        ;;

    stop)
        log "══════ Supervisor Stop All ══════"
        for key in awp oxwork nookplot litcoin; do
            stop_daemon "$key"
        done
        log "══════ All Daemons Stopped ══════"
        ;;

    *)
        echo "Manteclaw Daemon Supervisor"
        echo ""
        echo "Usage: $0 {check|cron|status|restart|stop}"
        echo ""
        echo "  check   — Check all daemons, restart dead ones (default)"
        echo "  cron    — Same as check, intended for crontab"
        echo "  status  — Show status of all daemons"
        echo "  restart — Stop and restart all daemons"
        echo "  stop    — Stop all daemons"
        echo ""
        echo "Crontab setup (every 5 min):"
        echo '  */5 * * * * /root/.openclaw/workspace/scripts/supervisor.sh cron'
        echo ""
        echo "Monitored daemons:"
        echo "  • AWP mine-skill         ($PROJECT_DIR/mine-skill)"
        echo "  • 0xWork auto-tasker     ($PROJECT_DIR/0xwork)"
        echo "  • Nookplot auto-contrib  ($SCRIPT_DIR/nookplot-auto.sh)"
        echo "  • Litcoiin hybrid miner  ($PROJECT_DIR/litcoin)"
        echo ""
        echo "Logs: $LOG_FILE"
        exit 1
        ;;
esac
