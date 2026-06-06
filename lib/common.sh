#!/bin/bash
# PCAtelegram_web v2.5.0 — common utilities
# Colors, logging, spinner, system helpers, v1 compat, i18n-aware

# ── Version ───────────────────────────────────────────────────────────────────
PCATELEGRAM_WEB_VERSION="2.5.0"
PCATELEGRAM_WEB_NAME="PCAtelegram_web"

# ── Пути ──────────────────────────────────────────────────────────────────────
PCATELEGRAM_WEB_DIR="/opt/pcatelegram_web"
PCATELEGRAM_WEB_CONFIG="$PCATELEGRAM_WEB_DIR/config.json"
TELEMT_CONFIG="/etc/telemt/config.toml"
TELEMT_BIN="/usr/local/bin/telemt"
TELEMT_SERVICE="telemt"
NGINX_SITE_CONF="/etc/nginx/sites-available/pcatelegram_web"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/pcatelegram_web"
WEBSITE_ROOT="/var/www/pcatelegram_web-site"
BACKUP_DIR="$PCATELEGRAM_WEB_DIR/backups"
LOG_FILE="/var/log/pcatelegram_web.log"
BOT_DIR="/opt/pcatelegram_web-bot"
ADMIN_WEB_DIR="/opt/pcatelegram_web-admin"
ADMIN_WEB_SERVICE="pcatelegram_web-admin"
ADMIN_WEB_HOST="0.0.0.0"
ADMIN_WEB_PORT="1984"
ADMIN_WEB_AUTH_FILE="/root/pcatelegram_web-admin.password"

# ── V1 совместимость ─────────────────────────────────────────────────────────
V1_CONTAINER_NAME="mtproto-proxy"
V1_CONFIG_FILE="/opt/pcatelegram_web-bot/proxy.json"
V1_SERVICE_NAME="pcatelegram_web-bot"

# ── Цвета ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Логирование ──────────────────────────────────────────────────────────────
log_info()    { echo -e "  ${CYAN}ℹ${NC} $*" >&2; }
log_success() { echo -e "  ${GREEN}✓${NC} $*" >&2; }
log_warning() { echo -e "  ${YELLOW}⚠${NC} $*" >&2; }
log_error()   { echo -e "  ${RED}✗${NC} $*" >&2; }
log_step()    { echo -e "\n${BOLD}${WHITE}  $*${NC}" >&2; }
log_dim()     { echo -e "  ${DIM}$*${NC}" >&2; }

log_to_file() {
    local ts; ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $*" >> "$LOG_FILE" 2>/dev/null
}

# ── Spinner ──────────────────────────────────────────────────────────────────
_spin_pid=""
spinner_start() {
    local default_msg
    default_msg=$(type t &>/dev/null && t wait || echo "Please wait...")
    local msg="${1:-$default_msg}"
    (
        local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
        local i=0
        while true; do
            printf "\r  ${CYAN}${frames[$i]}${NC} ${msg}" >&2
            i=$(( (i+1) % ${#frames[@]} ))
            sleep 0.1
        done
    ) &
    _spin_pid=$!
}

spinner_stop() {
    [ -n "$_spin_pid" ] && kill "$_spin_pid" 2>/dev/null && wait "$_spin_pid" 2>/dev/null
    _spin_pid=""
    printf "\r\033[K" >&2
}

# ── Прогресс-бар ─────────────────────────────────────────────────────────────
progress_bar() {
    local current="$1" total="$2" label="${3:-}"
    local pct=$(( current * 100 / total ))
    local filled=$(( pct / 2 ))
    local empty=$(( 50 - filled ))
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    printf "\r  ${GREEN}[${bar}]${NC} ${pct}%% ${label}" >&2
    [ "$current" -eq "$total" ] && echo "" >&2
}

# ── Выполнение с индикатором ─────────────────────────────────────────────────
run_with_spinner() {
    local label="$1"; shift
    local err_file="/tmp/.pcatelegram_web_spinner_err_$$"
    spinner_start "$label"
    "$@" >/dev/null 2>"$err_file"
    local rc=$?
    spinner_stop
    if [ $rc -eq 0 ]; then
        log_success "$label"
    else
        local err_label
        err_label=$(type t &>/dev/null && t error || echo "error")
        log_error "$label ${RED}(${err_label}, code: $rc)${NC}"
        if [ -s "$err_file" ]; then
            log_dim "  $(head -3 "$err_file")"
        fi
    fi
    rm -f "$err_file"
    return $rc
}

# ── Banner ───────────────────────────────────────────────────────────────────
show_banner() {
    local line
    line=$(printf '━%.0s' $(seq 1 60))
    echo ""
    echo -e "${CYAN}${line}${NC}"
    if type tf &>/dev/null; then
        echo -e "  ${BOLD}${WHITE}🚀 $(tf banner_title "$PCATELEGRAM_WEB_VERSION")${NC}"
        echo -e "  ${DIM}$(t banner_subtitle)${NC}"
        echo -e "  ${DIM}$(t banner_features)${NC}"
    else
        echo -e "  ${BOLD}${WHITE}🚀 PCAtelegram_web v${PCATELEGRAM_WEB_VERSION}${NC}"
        echo -e "  ${DIM}MTProxy powered by telemt (Rust + Tokio)${NC}"
        echo -e "  ${DIM}Anti-DPI • Fake TLS • TCP Splice • JA3/JA4${NC}"
    fi
    echo -e "${CYAN}${line}${NC}"
    echo ""
}

# ── Credits ──────────────────────────────────────────────────────────────────
show_credits() {
    local line
    line=$(printf '─%.0s' $(seq 1 60))
    echo ""
    echo -e "${MAGENTA}${line}${NC}"
    echo -e "  ${BOLD}$(type t &>/dev/null && t credits_title || echo 'Credits')${NC}"
    echo -e "${MAGENTA}${line}${NC}"
    echo -e "  ${WHITE}telemt${NC} — MTProxy engine (Rust)"
    echo -e "  ${DIM}github.com/telemt/telemt${NC}"
    echo ""
    echo -e "  ${WHITE}HTML5 UP${NC} — responsive HTML/CSS templates"
    echo -e "  ${DIM}html5up.net • CC BY 3.0 • @ajlkn${NC}"
    echo ""
    echo -e "  ${WHITE}learning-zone${NC} — 150+ HTML5 templates"
    echo -e "  ${DIM}github.com/learning-zone/website-templates${NC}"
    echo ""
    echo -e "  ${WHITE}Start Bootstrap${NC} — MIT license"
    echo -e "  ${DIM}startbootstrap.com${NC}"
    echo -e "${MAGENTA}${line}${NC}"
    echo ""
}

# ── Системные утилиты ────────────────────────────────────────────────────────
_valid_ip() {
    # Validate that each octet is 0-255
    local ip="$1"
    local IFS='.'
    read -ra octets <<< "$ip"
    [ ${#octets[@]} -ne 4 ] && return 1
    for octet in "${octets[@]}"; do
        [[ "$octet" =~ ^[0-9]+$ ]] || return 1
        [ "$octet" -gt 255 ] && return 1
    done
    return 0
}

get_server_ip() {
    local ip raw
    for url in "https://api.ipify.org" "https://icanhazip.com" "https://ifconfig.me"; do
        raw=$(curl -s -4 --max-time 5 "$url" 2>/dev/null)
        ip=$(echo "$raw" | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
        if [ -n "$ip" ] && _valid_ip "$ip"; then
            echo "$ip"
            return 0
        fi
    done
    echo "0.0.0.0"
    return 1
}

_t_or() {
    # Helper: translate if i18n available, otherwise return fallback
    local key="$1" fallback="$2"
    if type t &>/dev/null; then
        t "$key"
    else
        echo "$fallback"
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "$(_t_or err_need_root 'Run the script with sudo / as root')"
        exit 1
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        log_error "$(_t_or err_os_unknown 'Failed to detect OS. Linux is required.')"
        return 1
    fi
    # Validate os-release before sourcing (reject command injection: ;, backticks, $())
    if grep -qE '(;|`|\$\(|\$\{)' /etc/os-release 2>/dev/null; then
        log_warning "/etc/os-release contains suspicious strings, skipping"
        return 0
    fi
    . /etc/os-release
    case "$ID" in
        ubuntu|debian|centos|rocky|almalinux|fedora|rhel)
            log_dim "OS: $PRETTY_NAME"
            return 0
            ;;
        *)
            log_warning "OS $ID may be incompatible. Supported: Ubuntu, Debian, CentOS, Rocky."
            return 0
            ;;
    esac
}

get_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64|amd64) echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        armv7*|armhf) echo "armv7" ;;
        *) echo "$arch" ;;
    esac
}

get_pkg_manager() {
    if command -v apt-get &>/dev/null; then echo "apt"
    elif command -v dnf &>/dev/null; then echo "dnf"
    elif command -v yum &>/dev/null; then echo "yum"
    else echo "unknown"
    fi
}

install_pkg() {
    local pkg="$1"
    case "$(get_pkg_manager)" in
        apt) apt_install "$pkg" ;;
        dnf) dnf install -y -q "$pkg" ;;
        yum) yum install -y -q "$pkg" ;;
        *) log_error "$(_t_or err_bad_pkg_mgr 'Unknown package manager')"; return 1 ;;
    esac
}

# ── apt lock wait + install ─────────────────────────────────────────────────
# На свежих Ubuntu/Debian unattended-upgrades часто держит dpkg lock на старте
# → любой apt-get install падает с "Could not get lock /var/lib/dpkg/lock-frontend".
# Эти функции ждут освобождения лока до 300с, потом запускают apt с нативным
# таймаутом DPkg::Lock::Timeout. Использовать везде, где раньше был
# "apt-get install ...".
apt_lock_wait() {
    local max_wait="${1:-300}"
    local waited=0
    local warned=0
    while fuser /var/lib/dpkg/lock-frontend &>/dev/null \
          || fuser /var/lib/dpkg/lock &>/dev/null \
          || fuser /var/lib/apt/lists/lock &>/dev/null \
          || pgrep -f '^/usr/bin/unattended-upgrade' &>/dev/null; do
        if [ "$warned" = "0" ]; then
            log_warning "apt/dpkg locked by unattended-upgrades, waiting up to ${max_wait}s..."
            warned=1
        fi
        sleep 3
        waited=$((waited + 3))
        if [ "$waited" -ge "$max_wait" ]; then
            log_error "apt lock not released after ${max_wait}s"
            log_dim "Manual fix: systemctl stop unattended-upgrades && killall -9 unattended-upgr 2>/dev/null; dpkg --configure -a"
            return 1
        fi
    done
    [ "$warned" = "1" ] && log_success "apt lock released (waited ${waited}s)"
    return 0
}

# apt_install <pkg> [pkg2 ...] — ждёт lock + ставит пакеты + показывает ошибку
apt_install() {
    [ $# -eq 0 ] && return 0
    apt_lock_wait || return 1
    export DEBIAN_FRONTEND=noninteractive
    local opts="-o DPkg::Lock::Timeout=120"
    local err_file; err_file=$(mktemp 2>/dev/null || echo /tmp/apt_err.$$)
    if ! apt-get $opts install -y -qq "$@" 2>"$err_file"; then
        log_error "apt-get install failed: $*"
        [ -s "$err_file" ] && tail -n 5 "$err_file" | sed 's/^/    /' >&2
        rm -f "$err_file"
        return 1
    fi
    rm -f "$err_file"
    return 0
}

# apt_update — тихий update с ожиданием лока
apt_update() {
    apt_lock_wait || return 1
    export DEBIAN_FRONTEND=noninteractive
    apt-get -o DPkg::Lock::Timeout=120 update -qq 2>/dev/null || true
    return 0
}

# ── Зависимости PCAtelegram_web ──────────────────────────────────────────────────
# Полный список внешних команд, которые скрипт использует. Для каждой команды
# указан пакет на apt и dnf/yum (имена различаются: например dig = dnsutils на
# Debian, bind-utils на RHEL).
#
# КРИТИЧЕСКИЕ (без них скрипт просто не работает):
#   jq       — парсинг config.json, templates_catalog.json
#   curl     — скачивание telemt и проверки HTTPS
#   openssl  — генерация секретов, шифрование бекапов, SSL проверка
#   git      — клонирование шаблонов через download_template
#   xxd      — hex-encode домена для fake-TLS секрета (ee-prefix)
#   tar      — распаковка telemt архива и бекапы
#   dig      — DNS-проверка домена в Pro-режиме
#
# ЖЕЛАТЕЛЬНЫЕ (есть fallback, но с ними лучше):
#   qrencode — QR-коды для прокси-ссылок
#   bc       — красивое форматирование чисел в статистике
#
# Pro-режим доустанавливает nginx/certbot через install_nginx/install_certbot
# (они большие и нужны только если пользователь выбрал Pro).

# Маппинг команды -> (apt_pkg, dnf_pkg). apt_pkg_for_cmd <cmd>
apt_pkg_for_cmd() {
    case "$1" in
        dig)       echo "dnsutils" ;;
        xxd)       echo "xxd" ;;           # Ubuntu 22+: отдельный пакет, fallback ниже
        nslookup)  echo "dnsutils" ;;
        host)      echo "dnsutils" ;;
        ss)        echo "iproute2" ;;
        netstat)   echo "net-tools" ;;
        flock)     echo "util-linux" ;;
        iptables)  echo "iptables" ;;
        *)         echo "$1" ;;            # команда == имя пакета
    esac
}

dnf_pkg_for_cmd() {
    case "$1" in
        dig|nslookup|host) echo "bind-utils" ;;
        xxd)               echo "vim-common" ;;
        ss)                echo "iproute" ;;
        netstat)           echo "net-tools" ;;
        flock)             echo "util-linux" ;;
        iptables)          echo "iptables" ;;
        *)                 echo "$1" ;;
    esac
}

ensure_deps() {
    # Критические зависимости — без них скрипт не работает.
    # flock используется bot_action_dispatch для сериализации параллельных
    # вызовов (иначе гонка на config.json при одновременных change-template /
    # change-lite-domain из бота).
    local critical=(curl jq openssl git xxd tar dig flock)
    # Желательные — есть fallback, устанавливать всё равно, но не падать если не смогли
    local optional=(qrencode bc iptables)

    local missing_critical=() missing_optional=() cmd
    for cmd in "${critical[@]}"; do
        command -v "$cmd" &>/dev/null || missing_critical+=("$cmd")
    done
    for cmd in "${optional[@]}"; do
        command -v "$cmd" &>/dev/null || missing_optional+=("$cmd")
    done

    local all_missing=("${missing_critical[@]}" "${missing_optional[@]}")
    [ ${#all_missing[@]} -eq 0 ] && return 0

    # Собираем список пакетов для выбранного менеджера
    local pkg_mgr pkg pkgs=()
    pkg_mgr=$(get_pkg_manager)

    for cmd in "${all_missing[@]}"; do
        case "$pkg_mgr" in
            apt)       pkg=$(apt_pkg_for_cmd "$cmd") ;;
            dnf|yum)   pkg=$(dnf_pkg_for_cmd "$cmd") ;;
            *)         pkg="$cmd" ;;
        esac
        pkgs+=("$pkg")
    done

    # Убираем дубликаты (например dig+nslookup оба = dnsutils)
    local uniq_pkgs=()
    for pkg in "${pkgs[@]}"; do
        local found=0 p
        for p in "${uniq_pkgs[@]}"; do
            [ "$p" = "$pkg" ] && { found=1; break; }
        done
        [ "$found" = "0" ] && uniq_pkgs+=("$pkg")
    done

    if type tf &>/dev/null; then
        log_step "$(tf deps_installing "${all_missing[*]}")"
    else
        log_step "Installing dependencies: ${all_missing[*]} (packages: ${uniq_pkgs[*]})"
    fi

    case "$pkg_mgr" in
        apt)
            apt_update
            apt_install "${uniq_pkgs[@]}" || true
            ;;
        dnf) dnf install -y -q "${uniq_pkgs[@]}" 2>/dev/null ;;
        yum) yum install -y -q "${uniq_pkgs[@]}" 2>/dev/null ;;
        *)
            log_error "Unknown package manager — install manually: ${uniq_pkgs[*]}"
            return 1
            ;;
    esac

    # Фолбэки для xxd: на некоторых системах нужен vim-common вместо xxd
    if ! command -v xxd &>/dev/null && [ "$pkg_mgr" = "apt" ]; then
        apt_install vim-common || true
    fi

    # Повторная проверка критических команд
    local still_missing=()
    for cmd in "${critical[@]}"; do
        command -v "$cmd" &>/dev/null || still_missing+=("$cmd")
    done

    if [ ${#still_missing[@]} -gt 0 ]; then
        log_error "Critical dependencies still missing: ${still_missing[*]}"
        log_error "Install manually and re-run pcatelegram_web"
        return 1
    fi

    # Опциональные — только предупреждение
    local still_missing_opt=()
    for cmd in "${optional[@]}"; do
        command -v "$cmd" &>/dev/null || still_missing_opt+=("$cmd")
    done
    if [ ${#still_missing_opt[@]} -gt 0 ]; then
        log_warning "Optional deps missing (features degraded): ${still_missing_opt[*]}"
    fi

    log_success "Dependencies ready"
    return 0
}

# Быстрая проверка — только смотрит что критические установлены, ничего не ставит.
# Возвращает 0 если всё ок, 1 если что-то отсутствует. Используется на старте
# main() чтобы не дёргать apt-get update при каждом запуске меню.
check_deps_present() {
    local cmd
    for cmd in curl jq openssl git xxd tar dig flock; do
        command -v "$cmd" &>/dev/null || return 1
    done
    return 0
}

check_port() {
    local port="$1"
    local line
    line=$(ss -tlnp 2>/dev/null | grep -E ":${port}\b" | head -1)
    [ -z "$line" ] && line=$(netstat -tlnp 2>/dev/null | grep -E ":${port}\b" | head -1)
    if [ -n "$line" ]; then
        echo "$line"
        return 0  # порт занят
    fi
    return 1  # свободен
}

detect_3xui() {
    if systemctl list-unit-files 2>/dev/null | grep -Eq '^(x-ui|3x-ui)\.service'; then
        return 0
    fi
    [ -d /etc/x-ui ] || [ -d /usr/local/x-ui ] || [ -f /etc/x-ui/x-ui.db ]
}

detect_3xui_443_listener() {
    ss -ltnp 2>/dev/null | grep -E '(:|])443[[:space:]]' | grep -Eiq '(xray|x-ui|3x-ui)'
}

warn_3xui_443_conflict() {
    detect_3xui_443_listener || return 1
    log_warning "Обнаружен 3x-ui/Xray, который уже слушает TCP/443."
    log_warning "PCAtelegram_web не будет молча останавливать или переписывать 3x-ui."
    log_dim "Для настоящего shared-443 нужен один фронтовой TLS/SNI-диспетчер и разные SNI-домены для Xray и PCAtelegram_web."
    mkdir -p "$PCATELEGRAM_WEB_DIR" 2>/dev/null
    cat > "$PCATELEGRAM_WEB_DIR/shared-443-3xui.md" <<'EOF' 2>/dev/null || true
# PCAtelegram_web + 3x-ui on one TCP/443

PCAtelegram_web detected that 3x-ui/Xray already owns TCP/443. Two independent
processes cannot bind the same IP:port at the same time. A safe shared setup
needs one front TLS/SNI dispatcher on 443 and internal backends, for example:

- dispatcher: 0.0.0.0:443 (nginx stream ssl_preread)
- PCAtelegram_web telemt: 127.0.0.1:7443
- 3x-ui/Xray inbound: 127.0.0.1:9443
- PCAtelegram_web nginx mask site: 127.0.0.1:8443

The dispatcher routes Xray SNI domains to Xray. Everything else goes to telemt;
telemt then decides whether the session is MTProxy or regular HTTPS and forwards
the website to nginx through dns_overrides.

PCAtelegram_web can generate the dispatcher with:

    source /opt/pcatelegram_web/lib/shared443.sh
    shared443_enable <pcatelegram_web-domain> <xray-sni-domain> 127.0.0.1:9443

Move the 3x-ui/Xray inbound from 0.0.0.0:443 to 127.0.0.1:9443 in the panel first,
or nginx will not be able to own the public 443 socket. PCAtelegram_web intentionally
does not rewrite the 3x-ui SQLite database or generated Xray config without explicit
operator confirmation, because 3x-ui can overwrite manual JSON edits on the next
panel change.
EOF
    return 0
}

check_disk_space() {
    local min_mb="${1:-500}"
    local avail_mb
    avail_mb=$(df -m / | awk 'NR==2 {print $4}')
    if [ "$avail_mb" -lt "$min_mb" ]; then
        if type tf &>/dev/null; then
            log_error "$(tf err_low_disk "$avail_mb" "$min_mb")"
        else
            log_error "Low disk space: ${avail_mb}MB (need ${min_mb}MB+)"
        fi
        return 1
    fi
    return 0
}

# ── Конфигурация PCAtelegram_web (JSON) ──────────────────────────────────────────
save_pcatelegram_web_config() {
    mkdir -p "$(dirname "$PCATELEGRAM_WEB_CONFIG")"
    local cur_lang
    cur_lang=$(type get_language &>/dev/null && get_language || echo en)
    cat > "$PCATELEGRAM_WEB_CONFIG" << EOJSON
{
    "version": "$PCATELEGRAM_WEB_VERSION",
    "engine": "${1:-telemt}",
    "mode": "${2:-lite}",
    "port": ${3:-443},
    "secret": "${4:-}",
    "mask_host": "${5:-google.com}",
    "domain": "${6:-}",
    "template_id": "${7:-}",
    "language": "${cur_lang}",
    "installed_at": "$(date -Iseconds)",
    "updated_at": "$(date -Iseconds)"
}
EOJSON
    chmod 600 "$PCATELEGRAM_WEB_CONFIG"
}

load_pcatelegram_web_config() {
    if [ -f "$PCATELEGRAM_WEB_CONFIG" ]; then
        cat "$PCATELEGRAM_WEB_CONFIG"
        return 0
    fi
    echo "{}"
    return 1
}

config_get() {
    local key="$1"
    if [ ! -f "$PCATELEGRAM_WEB_CONFIG" ]; then
        return 2  # file missing
    fi
    local val
    val=$(jq -r ".$key // empty" "$PCATELEGRAM_WEB_CONFIG" 2>/dev/null)
    if [ $? -ne 0 ]; then
        return 3  # invalid JSON
    fi
    if [ -z "$val" ]; then
        return 1  # key missing or empty
    fi
    echo "$val"
    return 0
}

# ── V1 совместимость ─────────────────────────────────────────────────────────
detect_v1_installation() {
    # Проверяем наличие mtg Docker контейнера (v1)
    if command -v docker &>/dev/null; then
        if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${V1_CONTAINER_NAME}$"; then
            return 0  # v1 обнаружена
        fi
    fi
    # Проверяем наличие конфига v1
    if [ -f "$V1_CONFIG_FILE" ]; then
        return 0
    fi
    return 1
}

get_v1_config() {
    # Извлекаем данные из работающего v1 контейнера
    if ! command -v docker &>/dev/null; then
        echo "{}"
        return 1
    fi

    local running
    running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep "^${V1_CONTAINER_NAME}$")

    if [ -z "$running" ]; then
        # Пробуем из сохранённого конфига
        if [ -f "$V1_CONFIG_FILE" ]; then
            cat "$V1_CONFIG_FILE"
            return 0
        fi
        echo "{}"
        return 1
    fi

    # Достаём из Docker
    local cmd_str port secret ip
    cmd_str=$(docker inspect "$V1_CONTAINER_NAME" --format='{{range .Config.Cmd}}{{.}} {{end}}' 2>/dev/null)
    secret=$(echo "$cmd_str" | awk '{print $NF}')
    port=$(docker inspect "$V1_CONTAINER_NAME" --format='{{range $p,$c := .HostConfig.PortBindings}}{{(index $c 0).HostPort}}{{end}}' 2>/dev/null)
    ip=$(get_server_ip)

    jq -n \
        --arg secret "$secret" \
        --arg port "${port:-443}" \
        --arg ip "$ip" \
        '{secret: $secret, port: ($port | tonumber), ip: $ip, engine: "mtg"}'
}

migrate_v1_to_v2() {
    log_step "$(_t_or v1_migration_step 'Migrating from v1 (mtg) to v2 (telemt)')"

    local v1_config
    v1_config=$(get_v1_config)

    local old_port old_secret
    old_port=$(echo "$v1_config" | jq -r '.port // 443')
    old_secret=$(echo "$v1_config" | jq -r '.secret // empty')

    if [ -z "$old_secret" ]; then
        log_warning "Failed to extract secret from v1. A new one will be generated."
        return 1
    fi

    echo ""
    echo -e "  ${WHITE}$(_t_or v1_found_title 'Found v1 (mtg) installation:')${NC}"
    if type tf &>/dev/null; then
        echo -e "  $(tf v1_port "$old_port")"
        echo -e "  $(tf v1_secret "${old_secret:0:16}")"
    else
        echo -e "  Port: ${CYAN}${old_port}${NC}"
        echo -e "  Secret: ${CYAN}${old_secret:0:16}...${NC}"
    fi
    echo ""
    echo -e "  ${YELLOW}$(_t_or warning 'Warning'):${NC} $(_t_or v1_incompatible 'mtg secret is NOT directly compatible with telemt.')"
    echo -e "  $(_t_or v1_new_link 'Clients will need a new link.')"
    echo ""
    echo -ne "  $(_t_or v1_stop_migrate 'Stop v1 container and migrate to v2? [Y/n]:') "
    read -r ans
    if [[ "$ans" =~ ^[Nn] ]]; then
        log_info "$(_t_or v1_migration_cancelled 'Migration cancelled. v1 left intact.')"
        return 1
    fi

    # Stop v1
    log_info "$(_t_or v1_stopping 'Stopping v1 container...')"
    docker stop "$V1_CONTAINER_NAME" 2>/dev/null
    docker rm "$V1_CONTAINER_NAME" 2>/dev/null

    # Backup v1 config
    if [ -f "$V1_CONFIG_FILE" ]; then
        mkdir -p "$PCATELEGRAM_WEB_DIR"
        cp "$V1_CONFIG_FILE" "$PCATELEGRAM_WEB_DIR/v1_backup_proxy.json" 2>/dev/null
        if type tf &>/dev/null; then
            log_success "$(tf v1_config_saved "$PCATELEGRAM_WEB_DIR/v1_backup_proxy.json")"
        else
            log_success "v1 config saved to $PCATELEGRAM_WEB_DIR/v1_backup_proxy.json"
        fi
    fi

    if type tf &>/dev/null; then
        log_success "$(tf v1_port_freed "$old_port")"
    else
        log_success "v1 stopped. Port $old_port freed."
    fi
    return 0
}

# ── Confirm prompt ───────────────────────────────────────────────────────────
confirm() {
    local default_msg
    default_msg=$(_t_or install_continue_anyway 'Continue?')
    local msg="${1:-$default_msg}"
    echo -ne "  ${msg} [Y/n]: " >&2
    read -r ans
    [[ ! "$ans" =~ ^[Nn] ]]
}

# ── Выбор из списка ──────────────────────────────────────────────────────────
select_option() {
    local title="$1"
    shift
    local options=("$@")

    echo "" >&2
    echo -e "  ${BOLD}${WHITE}${title}${NC}" >&2
    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}" >&2
    local i=1
    for opt in "${options[@]}"; do
        echo -e "  ${CYAN}${i})${NC} ${opt}" >&2
        ((i++))
    done
    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}" >&2
    echo -ne "  ${WHITE}$(_t_or choose 'Choose'):${NC} " >&2
    read -r choice
    echo "$choice"
}

# ── Генерация случайного hex ─────────────────────────────────────────────────
generate_hex() {
    local len="${1:-32}"
    openssl rand -hex "$((len/2))" 2>/dev/null || head -c "$((len/2))" /dev/urandom | xxd -p | tr -d '\n'
}

# ── Проверка домена ──────────────────────────────────────────────────────────
validate_domain() {
    local domain="$1"
    if echo "$domain" | grep -qE '^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'; then
        return 0
    fi
    return 1
}

# ── Init: создание директорий ────────────────────────────────────────────────
init_dirs() {
    mkdir -p "$PCATELEGRAM_WEB_DIR" "$BACKUP_DIR" /etc/telemt 2>/dev/null
    touch "$LOG_FILE" 2>/dev/null
}

ensure_admin_web_password() {
    local pw=""
    if [ -n "${PCATELEGRAM_WEB_ADMIN_PASSWORD:-}" ]; then
        pw="$PCATELEGRAM_WEB_ADMIN_PASSWORD"
    elif [ -f "$ADMIN_WEB_AUTH_FILE" ] && [ -s "$ADMIN_WEB_AUTH_FILE" ]; then
        pw=$(sed -n 's/^password=//p' "$ADMIN_WEB_AUTH_FILE" | head -1)
    fi

    if [ -z "$pw" ]; then
        if command -v openssl >/dev/null 2>&1; then
            pw=$(openssl rand -base64 24 | tr -d '\n')
        else
            pw=$(head -c 24 /dev/urandom | base64 | tr -d '\n')
        fi
    fi

    umask 077
    cat > "$ADMIN_WEB_AUTH_FILE" <<EOF
user=${PCATELEGRAM_WEB_ADMIN_USER:-admin}
password=${pw}
url=http://$(get_server_ip 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}'):${ADMIN_WEB_PORT}/
EOF
    chmod 600 "$ADMIN_WEB_AUTH_FILE" 2>/dev/null || true
    printf '%s' "$pw"
}
