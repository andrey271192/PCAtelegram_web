#!/bin/bash
# GoTelegram v2.5.0 — Управление telemt binary
# Скачивание, обновление, запуск, остановка через systemd

TELEMT_GITHUB="telemt/telemt"
TELEMT_RELEASE_API="https://api.github.com/repos/${TELEMT_GITHUB}/releases/latest"
TELEMT_USER="telemt"
TELEMT_GROUP="telemt"

# ── Получение последней версии ───────────────────────────────────────────────
get_latest_telemt_version() {
    local resp
    resp=$(curl -s --max-time 10 "$TELEMT_RELEASE_API" 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$resp" ]; then
        log_error "Не удалось получить информацию о релизах telemt"
        return 1
    fi
    echo "$resp" | jq -r '.tag_name // empty'
}

get_telemt_download_url() {
    local arch
    arch=$(get_arch)
    local resp
    resp=$(curl -s --max-time 10 "$TELEMT_RELEASE_API" 2>/dev/null)
    if [ -z "$resp" ]; then return 1; fi

    # URL format: telemt-x86_64-linux-gnu.tar.gz (arch BEFORE linux)
    local arch_pattern
    case "$arch" in
        amd64)  arch_pattern="(amd64|x86_64)" ;;
        arm64)  arch_pattern="(arm64|aarch64)" ;;
        armv7)  arch_pattern="(armv7|arm)" ;;
        *)      arch_pattern="${arch}" ;;
    esac

    echo "$resp" | jq -r ".assets[].browser_download_url" 2>/dev/null \
        | grep -iE "$arch_pattern" \
        | grep -i "linux" \
        | grep -v "sha256" \
        | grep "gnu" \
        | head -1
}

# ── Установленная версия ─────────────────────────────────────────────────────
get_installed_telemt_version() {
    if [ -x "$TELEMT_BIN" ]; then
        "$TELEMT_BIN" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
    else
        echo ""
    fi
}

is_telemt_installed() {
    [ -x "$TELEMT_BIN" ]
}

# ── Скачивание и установка ───────────────────────────────────────────────────
download_telemt() {
    local url
    url=$(get_telemt_download_url)
    if [ -z "$url" ]; then
        log_error "Не найден бинарник telemt для архитектуры $(get_arch)"
        return 1
    fi

    local tmp_file="/tmp/telemt_download_$$"
    local extract_dir="/tmp/telemt_extract_$$"
    log_info "Скачивание: $url"

    if ! curl -L -s --max-time 120 -o "$tmp_file" "$url"; then
        log_error "Ошибка скачивания telemt"
        rm -f "$tmp_file"
        return 1
    fi

    # Проверяем что файл не пустой и не HTML
    local file_size
    file_size=$(stat -c%s "$tmp_file" 2>/dev/null || echo 0)
    if [ "$file_size" -lt 1000 ]; then
        log_error "Скачанный файл слишком маленький ($file_size байт) — возможна ошибка сети"
        rm -f "$tmp_file"
        return 1
    fi

    # Определяем тип файла и распаковываем
    local mime extracted=""
    mime=$(file -b --mime-type "$tmp_file" 2>/dev/null)
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"

    case "$mime" in
        application/gzip|application/x-gzip)
            tar xzf "$tmp_file" -C "$extract_dir" 2>/dev/null
            extracted=$(find "$extract_dir" -name "telemt" -type f 2>/dev/null | head -1)
            if [ -z "$extracted" ]; then
                # Может быть просто gzip без tar
                gunzip -c "$tmp_file" > "$extract_dir/telemt_bin" 2>/dev/null
                extracted="$extract_dir/telemt_bin"
            fi
            ;;
        application/x-tar)
            tar xf "$tmp_file" -C "$extract_dir" 2>/dev/null
            extracted=$(find "$extract_dir" -name "telemt" -type f 2>/dev/null | head -1)
            ;;
        application/zip)
            unzip -o "$tmp_file" -d "$extract_dir" 2>/dev/null
            extracted=$(find "$extract_dir" -name "telemt" -type f 2>/dev/null | head -1)
            ;;
        application/octet-stream|application/x-executable)
            extracted="$tmp_file"
            ;;
        *)
            # Пробуем определить по содержимому
            if file "$tmp_file" 2>/dev/null | grep -q "ELF"; then
                extracted="$tmp_file"
            else
                # Пробуем как tar.gz
                tar xzf "$tmp_file" -C "$extract_dir" 2>/dev/null
                extracted=$(find "$extract_dir" -name "telemt" -type f 2>/dev/null | head -1)
            fi
            ;;
    esac

    if [ -z "$extracted" ] || [ ! -f "$extracted" ]; then
        log_error "Не удалось извлечь бинарник telemt (mime: $mime)"
        rm -f "$tmp_file"
        rm -rf "$extract_dir"
        return 1
    fi

    # Устанавливаем
    cp "$extracted" "$TELEMT_BIN"
    chmod 755 "$TELEMT_BIN"
    rm -f "$tmp_file"
    rm -rf "$extract_dir"

    # Проверяем
    if "$TELEMT_BIN" --version &>/dev/null; then
        log_success "telemt $(get_installed_telemt_version) установлен в $TELEMT_BIN"
        return 0
    else
        log_error "Бинарник telemt не запускается ($(file -b "$TELEMT_BIN" 2>/dev/null))"
        return 1
    fi
}

# ── Системный пользователь ───────────────────────────────────────────────────
create_telemt_user() {
    if ! id "$TELEMT_USER" &>/dev/null; then
        useradd -r -s /usr/sbin/nologin -d /etc/telemt "$TELEMT_USER" 2>/dev/null
        log_dim "Создан системный пользователь: $TELEMT_USER"
    fi
}

# ── Systemd сервис ───────────────────────────────────────────────────────────
install_telemt_service() {
    local config_path="${1:-$TELEMT_CONFIG}"

    cat > "/etc/systemd/system/${TELEMT_SERVICE}.service" << EOF
[Unit]
Description=goTelegram Pro MTProxy (telemt engine)
Documentation=https://github.com/telemt/telemt
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=$TELEMT_BIN run $config_path
Restart=always
RestartSec=5
LimitNOFILE=65535

# Безопасность
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_success "Systemd сервис $TELEMT_SERVICE создан"
}

# ── Управление сервисом ──────────────────────────────────────────────────────
# start_telemt ensures telemt is running with the CURRENT on-disk config.
# If the service is already active we must restart (not plain start) — otherwise
# the running process keeps its old in-memory config and the freshly generated
# /etc/telemt/config.toml is silently ignored. This was the root cause of the
# "lite-mode key doesn't work after reinstall" bug: telemt had loaded the
# previous Pro config (tls_domain=legacy-upstream-domain) and was rejecting SNI=google.com
# clients with unknown_sni_action=Drop even though the on-disk config said
# tls_domain=google.com.
wait_telemt_ready() {
    local timeout="${1:-90}"
    local port elapsed=0
    port=$(awk '
        /^\[server\]/ { in_server=1; next }
        /^\[/ && in_server { exit }
        in_server && $1 == "port" {
            sub(/^[^=]*=[[:space:]]*/, "")
            gsub(/[[:space:]]/, "")
            print
            exit
        }
    ' "$TELEMT_CONFIG" 2>/dev/null)
    [[ "$port" =~ ^[0-9]+$ ]] || port=443

    while [ "$elapsed" -lt "$timeout" ]; do
        if ! systemctl is-active --quiet "$TELEMT_SERVICE" 2>/dev/null; then
            return 1
        fi
        if ss -ltnp 2>/dev/null | grep -E ":${port}\b" | grep -q "telemt"; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

start_telemt() {
    if systemctl is-active --quiet "$TELEMT_SERVICE" 2>/dev/null; then
        systemctl restart "$TELEMT_SERVICE" 2>/dev/null
    else
        systemctl start "$TELEMT_SERVICE" 2>/dev/null
    fi
    if wait_telemt_ready 90; then
        log_success "telemt запущен"
        return 0
    else
        log_error "telemt не запустился или не открыл порт"
        journalctl -u "$TELEMT_SERVICE" --no-pager -n 10 2>/dev/null
        return 1
    fi
}

stop_telemt() {
    if systemctl is-active --quiet "$TELEMT_SERVICE" 2>/dev/null; then
        systemctl stop "$TELEMT_SERVICE"
        log_success "telemt остановлен"
    else
        log_dim "telemt уже остановлен"
    fi
}

restart_telemt() {
    systemctl restart "$TELEMT_SERVICE" 2>/dev/null
    if wait_telemt_ready 90; then
        log_success "telemt перезапущен"
        return 0
    else
        log_error "telemt не перезапустился или не открыл порт"
        journalctl -u "$TELEMT_SERVICE" --no-pager -n 10 2>/dev/null
        return 1
    fi
}

enable_telemt() {
    systemctl enable "$TELEMT_SERVICE" 2>/dev/null
}

telemt_status() {
    if ! is_telemt_installed; then
        echo "not_installed"
        return
    fi
    if systemctl is-active --quiet "$TELEMT_SERVICE" 2>/dev/null; then
        echo "running"
    elif systemctl is-enabled --quiet "$TELEMT_SERVICE" 2>/dev/null; then
        echo "stopped"
    else
        echo "disabled"
    fi
}

telemt_logs() {
    local lines="${1:-40}"
    journalctl -u "$TELEMT_SERVICE" --no-pager -n "$lines" 2>/dev/null
}

telemt_uptime() {
    local started
    started=$(systemctl show "$TELEMT_SERVICE" --property=ActiveEnterTimestamp --value 2>/dev/null)
    if [ -n "$started" ] && [ "$started" != "" ]; then
        echo "$started"
    else
        echo "N/A"
    fi
}

# ── Обновление ───────────────────────────────────────────────────────────────
check_telemt_update() {
    local current latest
    current=$(get_installed_telemt_version)
    latest=$(get_latest_telemt_version)

    if [ -z "$current" ] || [ -z "$latest" ]; then
        return 1
    fi

    if [ "$current" != "$latest" ]; then
        echo "$latest"
        return 0  # есть обновление
    fi
    return 1  # актуально
}

update_telemt() {
    local latest
    latest=$(check_telemt_update)
    if [ $? -ne 0 ]; then
        log_info "telemt уже последней версии ($(get_installed_telemt_version))"
        return 0
    fi

    log_info "Доступно обновление: $(get_installed_telemt_version) → $latest"
    if ! confirm "Обновить telemt?"; then
        return 0
    fi

    stop_telemt
    if download_telemt; then
        start_telemt
        log_success "telemt обновлён до $latest"
    else
        start_telemt  # запускаем старую версию обратно
        log_error "Обновление не удалось"
        return 1
    fi
}

# ── Полная установка telemt ──────────────────────────────────────────────────
install_telemt_full() {
    log_step "Установка telemt"

    # Создаём директории
    mkdir -p /etc/telemt

    # Скачиваем бинарник
    run_with_spinner "Скачивание telemt" download_telemt || return 1

    # Устанавливаем systemd сервис
    install_telemt_service

    # Включаем автозапуск
    enable_telemt

    log_success "telemt готов к работе"
    return 0
}

# ── Удаление telemt ──────────────────────────────────────────────────────────
remove_telemt() {
    stop_telemt
    systemctl disable "$TELEMT_SERVICE" 2>/dev/null
    rm -f "/etc/systemd/system/${TELEMT_SERVICE}.service"
    systemctl daemon-reload
    rm -f "$TELEMT_BIN"
    rm -rf /etc/telemt
    log_success "telemt полностью удалён"
}
