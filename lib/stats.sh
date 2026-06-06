#!/bin/bash
# stats.sh — Traffic statistics module for GoTelegram v2.5.0
# Tracks proxy (telemt port 443) and site (nginx port 8443) traffic
# Uses iptables counters + real-time snapshots + historical CSV

# Color codes (from common.sh)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STATS_DIR="/run/gotelegram"
HISTORY_FILE="/opt/gotelegram/stats_history.csv"
USER_HISTORY_FILE="/opt/gotelegram/user_stats_history.csv"
SNAPSHOTS_DIR="$STATS_DIR/snapshots"
CURRENT_SNAPSHOT="$STATS_DIR/stats_current.json"
CONFIG_FILE="/opt/gotelegram/config.json"
TELEMT_CONFIG_FILE="/etc/telemt/config.toml"
STATS_RETENTION_DAYS="${STATS_RETENTION_DAYS:-365}"
STATS_MINUTE_RETENTION_DAYS="${STATS_MINUTE_RETENTION_DAYS:-31}"
STATS_CLEANUP_INTERVAL="${STATS_CLEANUP_INTERVAL:-3600}"
STATS_CLEANUP_STAMP="$STATS_DIR/last_history_cleanup"
USER_STATS_COLLECT_STAMP="$STATS_DIR/last_user_stats_minute"

# Initialize stats infrastructure
stats_init() {
    if ! command -v iptables &>/dev/null; then
        log_warning "iptables не найден: установите пакет iptables или запустите установку зависимостей"
        return 1
    fi

    # Create runtime directory
    mkdir -p "$STATS_DIR" "$SNAPSHOTS_DIR" 2>/dev/null
    chmod 755 "$STATS_DIR" "$SNAPSHOTS_DIR" 2>/dev/null

    # Create iptables chain if not exists
    if ! iptables -L GOTELEGRAM_STATS -n >/dev/null 2>&1; then
        iptables -N GOTELEGRAM_STATS 2>/dev/null
    fi

    # Add chain to INPUT if not already present
    if ! iptables -C INPUT -j GOTELEGRAM_STATS 2>/dev/null; then
        iptables -I INPUT -j GOTELEGRAM_STATS 2>/dev/null
    fi

    # Add rule for proxy traffic (port 443, TCP)
    if ! iptables -C GOTELEGRAM_STATS -p tcp --dport 443 2>/dev/null; then
        iptables -A GOTELEGRAM_STATS -p tcp --dport 443 2>/dev/null
    fi

    # Add rule for site traffic (loopback, port 8443, TCP)
    if ! iptables -C GOTELEGRAM_STATS -i lo -p tcp --dport 8443 2>/dev/null; then
        iptables -A GOTELEGRAM_STATS -i lo -p tcp --dport 8443 2>/dev/null
    fi

    # Initialize CSV header if file doesn't exist
    if [[ ! -f "$HISTORY_FILE" ]]; then
        echo "epoch,proxy_bytes,site_bytes" > "$HISTORY_FILE" 2>/dev/null
    fi
    if [[ ! -f "$USER_HISTORY_FILE" ]]; then
        echo "epoch,user,total_octets,current_connections,active_unique_ips,recent_unique_ips" > "$USER_HISTORY_FILE" 2>/dev/null
    fi

    # Write initial snapshot
    stats_collect
}

# Collect current traffic statistics from iptables
stats_collect() {
    local proxy_bytes=0 proxy_pkts=0 site_bytes=0 site_pkts=0
    local ts=$(date +%s)
    local temp_file=$(mktemp)

    if ! command -v iptables &>/dev/null; then
        mkdir -p "$STATS_DIR" 2>/dev/null
        echo "{\"ts\":$ts,\"proxy_bytes\":0,\"proxy_pkts\":0,\"site_bytes\":0,\"site_pkts\":0,\"error\":\"iptables_missing\"}" > "$CURRENT_SNAPSHOT" 2>/dev/null
        rm -f "$temp_file" 2>/dev/null
        return 1
    fi

    # Parse iptables output: format is "pkts bytes target"
    # We need to extract bytes (2nd column) for each rule
    local iptables_output=$(iptables -L GOTELEGRAM_STATS -v -n -x 2>/dev/null)

    # Extract counters for port 443 (proxy)
    proxy_bytes=$(echo "$iptables_output" | grep "dpt:443" | grep -v "lo" | awk '{print $2}')
    proxy_pkts=$(echo "$iptables_output" | grep "dpt:443" | grep -v "lo" | awk '{print $1}')

    # Extract counters for port 8443 on loopback (site)
    site_bytes=$(echo "$iptables_output" | grep "dpt:8443" | awk '{print $2}')
    site_pkts=$(echo "$iptables_output" | grep "dpt:8443" | awk '{print $1}')

    # Default to 0 if not found
    proxy_bytes=${proxy_bytes:-0}
    proxy_pkts=${proxy_pkts:-0}
    site_bytes=${site_bytes:-0}
    site_pkts=${site_pkts:-0}

    # Write current snapshot as JSON
    if command -v jq &>/dev/null; then
        echo "{\"ts\":$ts,\"proxy_bytes\":$proxy_bytes,\"proxy_pkts\":$proxy_pkts,\"site_bytes\":$site_bytes,\"site_pkts\":$site_pkts}" > "$CURRENT_SNAPSHOT" 2>/dev/null
    else
        cat > "$CURRENT_SNAPSHOT" 2>/dev/null <<EOF
{"ts":$ts,"proxy_bytes":$proxy_bytes,"proxy_pkts":$proxy_pkts,"site_bytes":$site_bytes,"site_pkts":$site_pkts}
EOF
    fi

    # Save snapshot for rate calculation (one per minute)
    local minute_key
    minute_key=$(date +%Y%m%d%H%M 2>/dev/null)
    local snapshot_file="$SNAPSHOTS_DIR/snap_${minute_key}.json"
    cp "$CURRENT_SNAPSHOT" "$snapshot_file" 2>/dev/null

    # Append to history CSV (once per minute, check if last entry is fresh)
    # Auto-recreate the file with header if it was deleted — otherwise the
    # collector would silently stop writing history after any wipe (v2.4.1 fix).
    if [[ ! -f "$HISTORY_FILE" ]]; then
        mkdir -p "$(dirname "$HISTORY_FILE")" 2>/dev/null
        echo "epoch,proxy_bytes,site_bytes" > "$HISTORY_FILE" 2>/dev/null
    fi

    if [[ -f "$HISTORY_FILE" ]]; then
        local last_ts
        last_ts=$(grep -E '^[0-9]' "$HISTORY_FILE" 2>/dev/null | tail -1 | cut -d, -f1)
        last_ts="${last_ts:-0}"
        local current_minute=$((ts - (ts % 60)))

        if [[ "$last_ts" -eq 0 ]] || [[ $((current_minute - last_ts)) -ge 60 ]]; then
            echo "$current_minute,$proxy_bytes,$site_bytes" >> "$HISTORY_FILE" 2>/dev/null

            # Cleanup/compact history at most once per hour.
            stats_cleanup_history
        fi
    fi

    stats_collect_users "$ts"

    rm -f "$temp_file" 2>/dev/null
}

# Print active telemt usernames from [access.users]. Usernames are restricted by
# goTelegram to A-Z/a-z/0-9/_.- so they are safe in URLs and CSV fields.
stats_active_users() {
    [[ -f "$TELEMT_CONFIG_FILE" ]] || return 0
    awk '
        /^\[access\.users\]$/ { in_users=1; next }
        in_users && /^\[/ { exit }
        in_users && /^[[:space:]]*#/ { next }
        in_users && /=/ {
            key=$1
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
            gsub(/^"|"$/, "", key)
            if (key ~ /^[A-Za-z0-9_.-]{1,48}$/) print key
        }
    ' "$TELEMT_CONFIG_FILE" 2>/dev/null
}

stats_collect_users() {
    local ts="${1:-$(date +%s)}"
    local current_minute=$((ts - (ts % 60)))

    mkdir -p "$(dirname "$USER_HISTORY_FILE")" 2>/dev/null
    if [[ ! -f "$USER_HISTORY_FILE" ]]; then
        echo "epoch,user,total_octets,current_connections,active_unique_ips,recent_unique_ips" > "$USER_HISTORY_FILE" 2>/dev/null
    fi

    command -v curl &>/dev/null || return 0
    command -v jq &>/dev/null || return 0

    if [[ -f "$USER_STATS_COLLECT_STAMP" ]] && [[ "$(cat "$USER_STATS_COLLECT_STAMP" 2>/dev/null)" == "$current_minute" ]]; then
        return 0
    fi

    local existing_users=""
    existing_users=$(awk -F, -v ts="$current_minute" '$1 == ts { print $2 }' "$USER_HISTORY_FILE" 2>/dev/null || true)

    local user payload total conns active_ips recent_ips
    while IFS= read -r user; do
        [[ -n "$user" ]] || continue
        if printf '%s\n' "$existing_users" | grep -Fxq "$user"; then
            continue
        fi

        payload=$(curl -sS --max-time 2 "http://127.0.0.1:9091/v1/users/${user}" 2>/dev/null || true)
        [[ -n "$payload" ]] || continue
        total=$(echo "$payload" | jq -r '.data.total_octets // .total_octets // 0' 2>/dev/null)
        conns=$(echo "$payload" | jq -r '.data.current_connections // .current_connections // 0' 2>/dev/null)
        active_ips=$(echo "$payload" | jq -r '.data.active_unique_ips // .active_unique_ips // 0' 2>/dev/null)
        recent_ips=$(echo "$payload" | jq -r '.data.recent_unique_ips // .recent_unique_ips // 0' 2>/dev/null)
        [[ "$total" =~ ^[0-9]+$ ]] || total=0
        [[ "$conns" =~ ^[0-9]+$ ]] || conns=0
        [[ "$active_ips" =~ ^[0-9]+$ ]] || active_ips=0
        [[ "$recent_ips" =~ ^[0-9]+$ ]] || recent_ips=0
        echo "$current_minute,$user,$total,$conns,$active_ips,$recent_ips" >> "$USER_HISTORY_FILE" 2>/dev/null
    done < <(stats_active_users)

    echo "$current_minute" > "$USER_STATS_COLLECT_STAMP" 2>/dev/null || true
    stats_cleanup_user_history
}

# Read current snapshot as JSON
stats_read_current() {
    if [[ -f "$CURRENT_SNAPSHOT" ]]; then
        cat "$CURRENT_SNAPSHOT"
    else
        echo "{}"
    fi
}

# Extract value from JSON (fallback if jq not available)
json_get() {
    local json="$1"
    local key="$2"

    if command -v jq &>/dev/null; then
        echo "$json" | jq -r ".${key}" 2>/dev/null || echo "0"
    else
        echo "$json" | grep -o "\"$key\":[^,}]*" | cut -d: -f2 | tr -d ' "' || echo "0"
    fi
}

# Convert bytes to human-readable format
format_bytes() {
    local bytes=$1

    if (( bytes < 1024 )); then
        printf "%.0f B" "$bytes"
    elif (( bytes < 1024 * 1024 )); then
        printf "%.1f KB" "$(echo "scale=1; $bytes / 1024" | bc 2>/dev/null || echo "$((bytes / 1024))")"
    elif (( bytes < 1024 * 1024 * 1024 )); then
        printf "%.1f MB" "$(echo "scale=1; $bytes / 1024 / 1024" | bc 2>/dev/null || echo "$((bytes / 1024 / 1024))")"
    elif (( bytes < 1024 * 1024 * 1024 * 1024 )); then
        printf "%.1f GB" "$(echo "scale=1; $bytes / 1024 / 1024 / 1024" | bc 2>/dev/null || echo "$((bytes / 1024 / 1024 / 1024))")"
    else
        printf "%.1f TB" "$(echo "scale=1; $bytes / 1024 / 1024 / 1024 / 1024" | bc 2>/dev/null || echo "$((bytes / 1024 / 1024 / 1024 / 1024))")"
    fi
}

# Convert bytes/sec to human-readable rate
format_rate() {
    local bytes_per_sec=$1

    if (( bytes_per_sec < 1024 )); then
        printf "%.0f B/s" "$bytes_per_sec"
    elif (( bytes_per_sec < 1024 * 1024 )); then
        printf "%.1f KB/s" "$(echo "scale=1; $bytes_per_sec / 1024" | bc 2>/dev/null || echo "$((bytes_per_sec / 1024))")"
    elif (( bytes_per_sec < 1024 * 1024 * 1024 )); then
        printf "%.1f MB/s" "$(echo "scale=1; $bytes_per_sec / 1024 / 1024" | bc 2>/dev/null || echo "$((bytes_per_sec / 1024 / 1024))")"
    else
        printf "%.1f GB/s" "$(echo "scale=1; $bytes_per_sec / 1024 / 1024 / 1024" | bc 2>/dev/null || echo "$((bytes_per_sec / 1024 / 1024 / 1024))")"
    fi
}

# Safely convert value to integer (returns 0 for empty/non-numeric)
_to_int() {
    local val="${1:-0}"
    # Strip non-numeric chars, default to 0
    val="${val//[^0-9]/}"
    echo "${val:-0}"
}

# Calculate diff safely (never negative, never crashes on empty)
_safe_diff() {
    local a=$(_to_int "$1")
    local b=$(_to_int "$2")
    local d=$((a - b))
    (( d < 0 )) && d=0
    echo "$d"
}

# Calculate traffic rates and totals from history
stats_calculate_rates() {
    local traffic_type="$1"  # "proxy" or "site"
    local col_idx=2  # proxy_bytes is column 2
    [[ "$traffic_type" == "site" ]] && col_idx=3

    local now
    now=$(date +%s)

    # Get latest data line (skip header with grep -E '^[0-9]')
    local bytes_now
    bytes_now=$(_to_int "$(grep -E '^[0-9]' "$HISTORY_FILE" 2>/dev/null | tail -1 | cut -d, -f"$col_idx")")

    local periods="60 300 3600 86400 604800 2592000 31536000"
    local results=""

    for secs in $periods; do
        local target_ts=$((now - secs))
        # Find closest entry at or after target timestamp (skip header)
        local old_val
        old_val=$(_to_int "$(awk -F, -v ts="$target_ts" '$1 ~ /^[0-9]/ && $1 <= ts' "$HISTORY_FILE" 2>/dev/null | tail -1 | cut -d, -f"$col_idx")")

        local diff
        diff=$(_safe_diff "$bytes_now" "$old_val")
        local rate=$(( secs > 0 ? diff / secs : 0 ))

        local bytes_fmt rate_fmt
        bytes_fmt=$(format_bytes "$diff")
        rate_fmt=$(format_rate "$rate")

        if [ -z "$results" ]; then
            results="${bytes_fmt}|${rate_fmt}"
        else
            results="${results}|${bytes_fmt}|${rate_fmt}"
        fi
    done

    echo "$results"
}

# Main display function for traffic statistics
show_traffic_stats() {
    # Ensure stats are collected
    stats_collect

    # Get current counters
    local current_json=$(stats_read_current)
    local proxy_pkts=$(json_get "$current_json" "proxy_pkts")
    local site_pkts=$(json_get "$current_json" "site_pkts")

    # Calculate rates for proxy
    local proxy_rates=$(stats_calculate_rates "proxy")
    IFS='|' read -r p1m p1mr p5m p5mr p60m p60mr p1d p1dr p7d p7dr p30d p30dr p365d p365dr <<< "$proxy_rates"

    # Calculate rates for site
    local site_rates=$(stats_calculate_rates "site")
    IFS='|' read -r s1m s1mr s5m s5mr s60m s60mr s1d s1dr s7d s7dr s30d s30dr s365d s365dr <<< "$site_rates"

    # Display proxy stats
    {
        echo ""
        echo -e "${BLUE}  Proxy (telemt, порт 443):${NC}"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        echo -e "${BLUE}  Период     │ Входящий      │ Скорость${NC}"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        printf "   %-9s │ %14s │ %s\n" "1 мин" "$p1m" "$p1mr"
        printf "   %-9s │ %14s │ %s\n" "5 мин" "$p5m" "$p5mr"
        printf "   %-9s │ %14s │ %s\n" "60 мин" "$p60m" "$p60mr"
        printf "   %-9s │ %14s │ %s\n" "1 день" "$p1d" "$p1dr"
        printf "   %-9s │ %14s │ %s\n" "7 дней" "$p7d" "$p7dr"
        printf "   %-9s │ %14s │ %s\n" "30 дней" "$p30d" "$p30dr"
        printf "   %-9s │ %14s │ %s\n" "365 дней" "$p365d" "$p365dr"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        printf "  Пакетов: %d\n\n" "$proxy_pkts"

        echo -e "${BLUE}  Сайт (nginx, порт 8443):${NC}"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        echo -e "${BLUE}  Период     │ Входящий      │ Скорость${NC}"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        printf "   %-9s │ %14s │ %s\n" "1 мин" "$s1m" "$s1mr"
        printf "   %-9s │ %14s │ %s\n" "5 мин" "$s5m" "$s5mr"
        printf "   %-9s │ %14s │ %s\n" "60 мин" "$s60m" "$s60mr"
        printf "   %-9s │ %14s │ %s\n" "1 день" "$s1d" "$s1dr"
        printf "   %-9s │ %14s │ %s\n" "7 дней" "$s7d" "$s7dr"
        printf "   %-9s │ %14s │ %s\n" "30 дней" "$s30d" "$s30dr"
        printf "   %-9s │ %14s │ %s\n" "365 дней" "$s365d" "$s365dr"
        echo -e "${BLUE}  ─────────────────────────────────────────${NC}"
        printf "  Пакетов: %d\n" "$site_pkts"
        echo ""
    } >&2
}

_stats_positive_int() {
    local value="${1:-0}"
    [[ "$value" =~ ^[0-9]+$ ]] && [[ "$value" -gt 0 ]] && echo "$value" || echo "$2"
}

stats_should_cleanup() {
    local stamp="$1"
    local now last interval
    mkdir -p "$STATS_DIR" 2>/dev/null || true
    now=$(date +%s)
    interval=$(_stats_positive_int "$STATS_CLEANUP_INTERVAL" 3600)
    last=$(cat "$stamp" 2>/dev/null || echo 0)
    [[ "$last" =~ ^[0-9]+$ ]] || last=0
    if (( now - last < interval )); then
        return 1
    fi
    echo "$now" > "$stamp" 2>/dev/null || true
    return 0
}

stats_retention_cutoffs() {
    local now retention_days minute_days
    now=$(date +%s)
    retention_days=$(_stats_positive_int "$STATS_RETENTION_DAYS" 365)
    minute_days=$(_stats_positive_int "$STATS_MINUTE_RETENTION_DAYS" 31)
    if (( minute_days > retention_days )); then
        minute_days="$retention_days"
    fi
    echo "$((now - retention_days * 86400)) $((now - minute_days * 86400))"
}

# Keep history for at most one year. Recent points stay per-minute; older
# points are compacted to one last cumulative snapshot per hour.
stats_cleanup_history() {
    if [[ ! -f "$HISTORY_FILE" ]]; then
        return
    fi

    stats_should_cleanup "$STATS_CLEANUP_STAMP" || return 0

    local retention_cutoff minute_cutoff temp_file
    read -r retention_cutoff minute_cutoff <<< "$(stats_retention_cutoffs)"
    temp_file=$(mktemp)

    {
        head -1 "$HISTORY_FILE"
        awk -F, -v keep="$retention_cutoff" -v minute="$minute_cutoff" '
            BEGIN { OFS="," }
            NR == 1 { next }
            $1 !~ /^[0-9]+$/ { next }
            $1 < keep { next }
            $1 >= minute { print $1, $2, $3; next }
            {
                bucket = int($1 / 3600)
                compact[bucket] = $1 OFS $2 OFS $3
            }
            END {
                for (bucket in compact) print compact[bucket]
            }
        ' "$HISTORY_FILE" | sort -t, -k1,1n
    } > "$temp_file" 2>/dev/null

    mv "$temp_file" "$HISTORY_FILE" 2>/dev/null
}

stats_cleanup_user_history() {
    if [[ ! -f "$USER_HISTORY_FILE" ]]; then
        return
    fi

    stats_should_cleanup "${STATS_CLEANUP_STAMP}.users" || return 0

    local retention_cutoff minute_cutoff temp_file
    read -r retention_cutoff minute_cutoff <<< "$(stats_retention_cutoffs)"
    temp_file=$(mktemp)

    {
        head -1 "$USER_HISTORY_FILE"
        awk -F, -v keep="$retention_cutoff" -v minute="$minute_cutoff" '
            BEGIN { OFS="," }
            NR == 1 { next }
            $1 !~ /^[0-9]+$/ { next }
            $1 < keep { next }
            $1 >= minute { print $1, $2, $3, $4, $5, $6; next }
            {
                bucket = $2 SUBSEP int($1 / 3600)
                compact[bucket] = $1 OFS $2 OFS $3 OFS $4 OFS $5 OFS $6
            }
            END {
                for (bucket in compact) print compact[bucket]
            }
        ' "$USER_HISTORY_FILE" | sort -t, -k1,1n -k2,2
    } > "$temp_file" 2>/dev/null

    mv "$temp_file" "$USER_HISTORY_FILE" 2>/dev/null
}

# Toggle stats collection on/off
toggle_stats() {
    local current_state="false"

    # Read current state from config
    if [[ -f "$CONFIG_FILE" ]] && command -v jq &>/dev/null; then
        current_state=$(jq -r '.stats_enabled // false' "$CONFIG_FILE" 2>/dev/null)
    fi

    # Toggle
    if [[ "$current_state" == "true" ]]; then
        # Disable stats
        if [[ -f "$CONFIG_FILE" ]]; then
            if command -v jq &>/dev/null; then
                jq '.stats_enabled = false' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" 2>/dev/null
                mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
            fi
        fi

        # Remove iptables rules
        iptables -D INPUT -j GOTELEGRAM_STATS 2>/dev/null
        iptables -F GOTELEGRAM_STATS 2>/dev/null
        iptables -X GOTELEGRAM_STATS 2>/dev/null

        # Clean up directories
        rm -rf "$STATS_DIR" 2>/dev/null

        echo "Сбор статистики ОТКЛЮЧЕН" >&2
    else
        # Enable stats
        if [[ -f "$CONFIG_FILE" ]]; then
            if command -v jq &>/dev/null; then
                jq '.stats_enabled = true' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" 2>/dev/null
                mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
            fi
        fi

        # Initialize stats collection
        stats_init

        echo "Сбор статистики ВКЛЮЧЕН" >&2
    fi
}

# Install systemd service for stats collection
install_stats_collector() {
    local service_file="/etc/systemd/system/gotelegram-stats.service"

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        echo "Требуется root для установки сервиса" >&2
        return 1
    fi

    if ! command -v iptables &>/dev/null; then
        log_info "Установка iptables для подсчёта трафика..."
        install_pkg "$(apt_pkg_for_cmd iptables)" || {
            echo "Не удалось установить iptables" >&2
            return 1
        }
    fi

    # Get script directory (resolve symlinks)
    local script_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
    local lib_dir=$(dirname "$script_dir")

    # Create systemd service file
    cat > "$service_file" <<'EOF'
[Unit]
Description=goTelegram Pro Traffic Stats Collector
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c 'source /opt/gotelegram/lib/common.sh; source /opt/gotelegram/lib/stats.sh; stats_init; while true; do stats_collect; sleep 1; done'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "$service_file"
    systemctl daemon-reload
    systemctl enable gotelegram-stats.service
    systemctl restart gotelegram-stats.service

    if [[ -f "$CONFIG_FILE" ]] && command -v jq &>/dev/null; then
        local tmp
        tmp=$(mktemp)
        if jq '.stats_enabled = true' "$CONFIG_FILE" > "$tmp" 2>/dev/null; then
            mv "$tmp" "$CONFIG_FILE"
            chmod 600 "$CONFIG_FILE" 2>/dev/null || true
        else
            rm -f "$tmp" 2>/dev/null
        fi
    fi

    echo "Сервис gotelegram-stats установлен и запущен" >&2
}

# Remove stats collector service
remove_stats_collector() {
    if [[ $EUID -ne 0 ]]; then
        echo "Требуется root для удаления сервиса" >&2
        return 1
    fi

    systemctl stop gotelegram-stats.service 2>/dev/null
    systemctl disable gotelegram-stats.service 2>/dev/null
    rm -f /etc/systemd/system/gotelegram-stats.service
    systemctl daemon-reload

    # Remove iptables rules
    iptables -D INPUT -j GOTELEGRAM_STATS 2>/dev/null
    iptables -F GOTELEGRAM_STATS 2>/dev/null
    iptables -X GOTELEGRAM_STATS 2>/dev/null

    # Clean up directories and files
    rm -rf "$STATS_DIR" 2>/dev/null
    rm -f "$HISTORY_FILE" "$USER_HISTORY_FILE" 2>/dev/null

    echo "Сервис статистики удалён" >&2
}

# Export functions for external use
export -f stats_init stats_collect stats_collect_users stats_active_users stats_read_current stats_calculate_rates
export -f show_traffic_stats format_bytes format_rate toggle_stats
export -f stats_cleanup_history stats_cleanup_user_history stats_should_cleanup stats_retention_cutoffs install_stats_collector remove_stats_collector
export -f json_get
