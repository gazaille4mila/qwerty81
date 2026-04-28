source /home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/.reva_env.sh
rm -f /home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/.reva_env.sh
#!/usr/bin/env bash
set -o pipefail
_timeout() {
    # Usage: _timeout SECONDS COMMAND [ARGS...]
    local secs=$1; shift
    "$@" &
    local pid=$!
    (
        exec >/dev/null 2>&1 <&-
        sleep "$secs"
        kill -TERM "$pid" 2>/dev/null
        sleep 10
        kill -KILL "$pid" 2>/dev/null
    ) &
    local watcher=$!
    wait "$pid"
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
}

_load_agent_env() {
    if [ -f .env ]; then
        set -a
        . ./.env
        set +a
    fi
    if [ -f .api_key ]; then
        COALESCENCE_API_KEY=$(tr -d '\r\n' < .api_key)
        export COALESCENCE_API_KEY
    fi
    export GITHUB_REPO_URL="https://github.com/gazaille4mila/qwerty81"
}

TIMEOUT=17880
SESSION_TIMEOUT=1800
START=$(date +%s)

while true; do
    ELAPSED=$(( $(date +%s) - START ))
    [ $ELAPSED -ge $TIMEOUT ] && echo "[reva] duration reached, stopping." && break
    REMAINING=$((TIMEOUT - ELAPSED))
    # cap each invocation at SESSION_TIMEOUT so idle backends get cycled
    PER_RUN=$((REMAINING < SESSION_TIMEOUT ? REMAINING : SESSION_TIMEOUT))

    _load_agent_env
    if [ -f .reva_has_run ]; then
        _timeout "${PER_RUN}" claude --continue -p "$(cat initial_prompt.txt)" --model claude-sonnet-4-6 --dangerously-skip-permissions --output-format stream-json --verbose --mcp-config '{"mcpServers":{"paperlantern":{"type":"http","url":"https://mcp.paperlantern.ai/chat/mcp?key=pl_cd1099cd5b35f6c193f9"},"koala":{"type":"http","url":"https://koala.science/mcp","headers":{"Authorization":"Bearer '"$COALESCENCE_API_KEY"'"}}}}' 2>&1 | tee -a agent.log
    else
        _timeout "${PER_RUN}" claude -p "$(cat initial_prompt.txt)" --model claude-sonnet-4-6 --dangerously-skip-permissions --output-format stream-json --verbose --mcp-config '{"mcpServers":{"paperlantern":{"type":"http","url":"https://mcp.paperlantern.ai/chat/mcp?key=pl_cd1099cd5b35f6c193f9"},"koala":{"type":"http","url":"https://koala.science/mcp","headers":{"Authorization":"Bearer '"$COALESCENCE_API_KEY"'"}}}}' 2>&1 | tee -a agent.log
        touch .reva_has_run
    fi
    EXIT_CODE=$?
    echo "[reva] agent exited ($EXIT_CODE), restarting in 5s..."
    sleep 5
done
