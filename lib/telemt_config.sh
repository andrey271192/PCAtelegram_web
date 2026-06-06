#!/bin/bash
# PCAtelegram_web v2.5.0 — Генерация TOML конфигурации для telemt

# ── Популярные домены (не заблокированные в РФ) ──────────────────────────────
QUICK_DOMAINS=(
    "google.com"
    "microsoft.com"
    "cloudflare.com"
    "apple.com"
    "amazon.com"
    "github.com"
    "stackoverflow.com"
    "medium.com"
    "wikipedia.org"
    "coursera.org"
    "udemy.com"
    "habr.com"
    "stepik.org"
    "duolingo.com"
    "khanacademy.org"
    "bbc.com"
    "reuters.com"
    "nytimes.com"
    "ted.com"
    "zoom.us"
)

# ── Генерация TOML конфига (telemt v3 формат) ───────────────────────────────
generate_telemt_toml() {
    local secret="$1"
    local port="${2:-443}"
    local mask_mode="${3:-lite}"   # lite | pro
    local mask_domain="${4:-google.com}"
    local mask_port="${5:-443}"
    local output="${6:-$TELEMT_CONFIG}"

    mkdir -p "$(dirname "$output")"

    # DNS override для pro: домен резолвится в 127.0.0.1
    # чтобы mask-трафик шёл на локальный nginx, а не в интернет
    local dns_line=""
    if [ "$mask_mode" = "pro" ]; then
        dns_line="dns_overrides = [\"${mask_domain}:${mask_port}:127.0.0.1\"]"
    fi

    cat > "$output" << EOTOML
# PCAtelegram_web v${PCATELEGRAM_WEB_VERSION} — telemt v3 configuration
# Сгенерировано: $(date -Iseconds)
# Режим: ${mask_mode}

[general]
use_middle_proxy = true
log_level = "normal"

[general.modes]
classic = false
secure = false
tls = true

[general.links]
show = "*"
public_port = ${port}

[server]
port = ${port}
listen_addr_ipv4 = "0.0.0.0"
metrics_listen = "127.0.0.1:9090"
metrics_whitelist = ["127.0.0.1/32", "::1/128"]

[server.api]
enabled = true
listen = "127.0.0.1:9091"
whitelist = ["127.0.0.1/32", "::1/128"]
minimal_runtime_enabled = false
minimal_runtime_cache_ttl_ms = 1000

[censorship]
tls_domain = "${mask_domain}"
mask = true
mask_port = ${mask_port}
tls_emulation = $([ "$mask_mode" = "pro" ] && echo "false" || echo "true")
unknown_sni_action = "mask"

[access.users]
main = "${secret}"

[network]
${dns_line}
EOTOML

    chmod 600 "$output"
    log_success "Конфиг telemt записан: $output"
    log_dim "Режим: $mask_mode, домен: $mask_domain, порт mask: $mask_port"
}

# ── Добавление дополнительного секрета ───────────────────────────────────────
add_secret_to_config() {
    local name="$1"
    local secret="$2"
    local config="${3:-$TELEMT_CONFIG}"

    if [ ! -f "$config" ]; then
        log_error "Конфиг не найден: $config"
        return 1
    fi

    # telemt v3: добавляем ключ в секцию [access.users]
    # Формат: name = "secret" под блоком [access.users]
    if grep -q '\[access\.users\]' "$config"; then
        sed -i "/\[access\.users\]/a ${name} = \"${secret}\"" "$config"
    else
        cat >> "$config" << EOSECRET

[access.users]
${name} = "${secret}"
EOSECRET
    fi

    log_success "Добавлен секрет: $name"
}

# ── Чтение текущего конфига (telemt v3 формат) ──────────────────────────────
get_config_value() {
    local key="$1"
    local config="${2:-$TELEMT_CONFIG}"

    if [ ! -f "$config" ]; then return 1; fi

    case "$key" in
        secret)
            # [access.users] main = "..."
            awk '
                /^\[access\.users\]/ { in_users=1; next }
                /^\[/ && in_users { exit }
                in_users && /^[[:space:]]*[^#[:space:]][^=]*=/ {
                    user_key=$1
                    gsub(/"/, "", user_key)
                    if (user_key != "main") next

                    value=$0
                    sub(/^[^=]*=[[:space:]]*/, "", value)
                    sub(/^"/, "", value)
                    sub(/".*$/, "", value)
                    gsub(/[[:space:]]/, "", value)
                    if (value != "") {
                        print value
                        found=1
                    }
                    exit
                }
                END { exit found ? 0 : 1 }
            ' "$config"
            ;;
        port)
            # [server] port = 443
            awk '
                /^\[server\]/ { in_server=1; next }
                /^\[/ && in_server { exit }
                in_server && $1 == "port" {
                    sub(/^[^=]*=[[:space:]]*/, "")
                    gsub(/[[:space:]]/, "")
                    print
                    exit
                }
            ' "$config"
            ;;
        mask_host|tls_domain)
            # [censorship] tls_domain = "..."
            awk '
                /^\[censorship\]/ { in_cens=1; next }
                /^\[/ && in_cens { exit }
                in_cens && $1 == "tls_domain" {
                    sub(/^[^=]*=[[:space:]]*"/, "")
                    sub(/".*$/, "")
                    print
                    exit
                }
            ' "$config"
            ;;
        mask_port)
            awk '
                /^\[censorship\]/ { in_cens=1; next }
                /^\[/ && in_cens { exit }
                in_cens && $1 == "mask_port" {
                    sub(/^[^=]*=[[:space:]]*/, "")
                    gsub(/[[:space:]]/, "")
                    print
                    exit
                }
            ' "$config"
            ;;
        *)
            grep "$key" "$config" | head -1 | sed 's/^[^=]*=[[:space:]]*//; s/^"//; s/"$//' | tr -d ' '
            ;;
    esac
}

get_telemt_users_block() {
    local config="${1:-$TELEMT_CONFIG}"
    [ -f "$config" ] || return 1
    awk '
        /^\[access\.users\]/ { in_users=1; next }
        /^\[/ && in_users { exit }
        in_users && /^[[:space:]]*[^#[:space:]][^=]*=/ { print }
    ' "$config"
}

first_telemt_user_secret() {
    local config="${1:-$TELEMT_CONFIG}"
    get_telemt_users_block "$config" | head -1 | sed 's/^[^=]*=[[:space:]]*//; s/^"//; s/".*$//' | tr -d ' '
}

telemt_users_block_has_main() {
    local users_block="$1"
    printf '%s\n' "$users_block" | awk -F= '
        /^[[:space:]]*#/ || ! /=/ { next }
        {
            key=$1
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
            if (key ~ /^".*"$/ || key ~ /^\047.*\047$/) {
                key=substr(key, 2, length(key) - 2)
            }
            if (key == "main") {
                found=1
                exit
            }
        }
        END { exit found ? 0 : 1 }
    '
}

replace_telemt_users_block() {
    local users_block="$1"
    local config="${2:-$TELEMT_CONFIG}"
    [ -f "$config" ] || return 1
    [ -n "$users_block" ] || return 0

    local tmp
    tmp=$(mktemp) || return 1
    awk -v users="$users_block" '
        BEGIN { split(users, lines, "\n") }
        /^\[access\.users\]/ {
            found=1
            print
            for (i = 1; i in lines; i++) {
                if (lines[i] != "") print lines[i]
            }
            in_users=1
            next
        }
        /^\[/ && in_users { in_users=0 }
        in_users { next }
        { print }
        END {
            if (!found) {
                print ""
                print "[access.users]"
                for (i = 1; i in lines; i++) {
                    if (lines[i] != "") print lines[i]
                }
            }
        }
    ' "$config" > "$tmp" && mv "$tmp" "$config"
    chmod 600 "$config"
}

toml_bool_value() {
    local table="$1"
    local key="$2"
    local config="${3:-$TELEMT_CONFIG}"
    awk -v table="$table" -v key="$key" '
        $0 == "[" table "]" { in_table=1; next }
        /^\[/ && in_table { exit }
        in_table && $1 == key {
            sub(/^[^=]*=[[:space:]]*/, "")
            gsub(/[[:space:]]/, "")
            print
            exit
        }
    ' "$config"
}

# ── Валидация конфига ────────────────────────────────────────────────────────
validate_telemt_config() {
    local config="${1:-$TELEMT_CONFIG}"

    if [ ! -f "$config" ]; then
        log_error "Конфиг не найден: $config"
        return 1
    fi

    # Проверяем обязательные поля
    local secret port host
    secret=$(get_config_value secret "$config")
    port=$(get_config_value port "$config")
    host=$(get_config_value mask_host "$config")

    local errors=0

    if [ -z "$secret" ]; then
        log_error "Не задан secret"
        ((errors++))
    elif [ ${#secret} -lt 32 ]; then
        log_warning "Secret слишком короткий (${#secret} символов, рекомендуется 32+)"
    fi

    if [ -z "$port" ]; then
        log_error "Не задан порт (bind_to)"
        ((errors++))
    elif [ "$port" -lt 1 ] || [ "$port" -gt 65535 ] 2>/dev/null; then
        log_error "Порт вне диапазона: $port"
        ((errors++))
    fi

    if [ -z "$host" ]; then
        log_error "Не задан маскировочный хост (censorship.tls_domain)"
        ((errors++))
    fi

    if [ $errors -gt 0 ]; then
        log_error "Найдено ошибок: $errors"
        return 1
    fi

    log_success "Конфиг валиден"
    return 0
}

# ── Выбор домена (интерактивный) ─────────────────────────────────────────────
select_quick_domain() {
    echo "" >&2
    echo -e "  ${BOLD}${WHITE}🌐 Выберите домен для маскировки (Fake TLS):${NC}" >&2
    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}" >&2

    local i=1
    local row=""
    for d in "${QUICK_DOMAINS[@]}"; do
        printf "  ${CYAN}%2d)${NC} %-25s" "$i" "$d" >&2
        if (( i % 2 == 0 )); then
            echo "" >&2
        fi
        ((i++))
    done
    if (( (i-1) % 2 != 0 )); then echo "" >&2; fi

    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}" >&2
    echo -ne "  ${WHITE}Выбор (1-${#QUICK_DOMAINS[@]}):${NC} " >&2
    read -r choice

    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#QUICK_DOMAINS[@]} ]; then
        echo "${QUICK_DOMAINS[$((choice-1))]}"
        return 0
    fi

    log_error "Неверный выбор"
    return 1
}

# ── Выбор порта (интерактивный) ──────────────────────────────────────────────
select_port() {
    echo "" >&2
    echo -e "  ${BOLD}${WHITE}🔌 Выберите порт:${NC}" >&2

    # Проверяем стандартные порты
    local busy_443 busy_8443
    busy_443=$(check_port 443)
    busy_8443=$(check_port 8443)

    local label_443="443 (рекомендуется)"
    local label_8443="8443"
    [ -n "$busy_443" ] && label_443="443 ⚠️  занят"
    [ -n "$busy_8443" ] && label_8443="8443 ⚠️  занят"

    echo -e "  ${CYAN}1)${NC} $label_443" >&2
    echo -e "  ${CYAN}2)${NC} $label_8443" >&2
    echo -e "  ${CYAN}3)${NC} Свой порт" >&2

    if [ -n "$busy_443" ]; then
        echo -e "  ${DIM}  ⚠ Порт 443 занят: $(echo "$busy_443" | head -c 60)${NC}" >&2
    fi

    echo -ne "  ${WHITE}Выбор:${NC} " >&2
    read -r choice

    case "$choice" in
        1) echo "443" ;;
        2) echo "8443" ;;
        3)
            echo -ne "  Введите порт (1-65535): " >&2
            read -r custom_port
            if [[ "$custom_port" =~ ^[0-9]+$ ]] && [ "$custom_port" -ge 1 ] && [ "$custom_port" -le 65535 ]; then
                echo "$custom_port"
            else
                log_error "Неверный порт"
                return 1
            fi
            ;;
        *) echo "443" ;;
    esac
}

# ── Генерация ссылки tg://proxy ──────────────────────────────────────────────
generate_proxy_link() {
    local server="${1:-$(get_server_ip)}"
    local port="${2:-443}"
    local secret="$3"
    local mask_host="${4:-}"

    # Если указан mask_host (fake-TLS), формируем ee-секрет
    if [ -n "$mask_host" ]; then
        local domain_hex
        domain_hex=$(printf '%s' "$mask_host" | xxd -p | tr -d '\n')
        secret="ee${secret}${domain_hex}"
    fi

    echo "tg://proxy?server=${server}&port=${port}&secret=${secret}"
}

# ── Вывод информации о прокси ────────────────────────────────────────────────
show_proxy_info() {
    local config="${1:-$TELEMT_CONFIG}"
    local secret port mask_host ip link status

    secret=$(get_config_value secret "$config")
    port=$(get_config_value port "$config")
    mask_host=$(get_config_value mask_host "$config")
    ip=$(get_server_ip)
    status=$(telemt_status)

    local mode domain
    mode=$(config_get mode 2>/dev/null || echo "lite")
    domain=$(config_get domain 2>/dev/null || echo "")

    # Генерация ссылки: оба режима используют ee-секрет с mask_host
    if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
        link=$(generate_proxy_link "$domain" "$port" "$secret" "$domain")
    else
        link=$(generate_proxy_link "$ip" "$port" "$secret" "$mask_host")
    fi

    local status_icon status_text
    case "$status" in
        running) status_icon="✅"; status_text="Работает" ;;
        stopped) status_icon="⏸️";  status_text="Остановлен" ;;
        *)       status_icon="❌"; status_text="Не установлен" ;;
    esac

    echo ""
    echo -e "  ${BOLD}${WHITE}${status_icon} Статус прокси: ${status_text}${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}"
    echo -e "  ${WHITE}Ядро:${NC}       telemt (Rust)"
    if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
        echo -e "  ${WHITE}Домен:${NC}      ${CYAN}${domain}${NC}"
    else
        echo -e "  ${WHITE}IP:${NC}         ${CYAN}${ip}${NC}"
    fi
    echo -e "  ${WHITE}Порт:${NC}       ${CYAN}${port}${NC}"
    echo -e "  ${WHITE}Режим:${NC}      ${CYAN}${mode}${NC}"
    echo -e "  ${WHITE}Маскировка:${NC} ${CYAN}${mask_host}${NC}"
    echo -e "  ${WHITE}Secret:${NC}     ${CYAN}${secret:0:16}...${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..50})${NC}"
    echo -e "  ${WHITE}Ссылка:${NC}"
    echo -e "  ${GREEN}${link}${NC}"
    echo ""

    # QR если доступен
    if command -v qrencode &>/dev/null; then
        qrencode -t UTF8 -m 2 "$link" 2>/dev/null
    fi
}

# ── Вывод информации о прокси (Pro-режим) ──────────────────────────────────
# В pro-режиме ссылка содержит домен (не IP) и fake-TLS секрет (ee...)
show_proxy_info_pro() {
    local domain="$1"
    local faketls_secret="$2"

    local link="tg://proxy?server=${domain}&port=443&secret=${faketls_secret}"

    echo ""
    echo -e "  ${BOLD}${WHITE}✅ Pro-прокси настроен${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -e "  ${WHITE}Ядро:${NC}       telemt (Rust)"
    echo -e "  ${WHITE}Домен:${NC}      ${CYAN}${domain}${NC}"
    echo -e "  ${WHITE}Порт:${NC}       ${CYAN}443${NC} (внешний, telemt)"
    echo -e "  ${WHITE}Режим:${NC}      ${MAGENTA}Pro (fake-TLS)${NC}"
    echo -e "  ${WHITE}nginx:${NC}      ${CYAN}127.0.0.1:8443${NC} (внутренний)"
    echo -e "  ${WHITE}Secret:${NC}     ${CYAN}${faketls_secret:0:20}...${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -e "  ${WHITE}Ссылка для Telegram:${NC}"
    echo -e "  ${GREEN}${link}${NC}"
    echo ""
    echo -e "  ${DIM}Провайдер видит: HTTPS-трафик к ${domain}:443${NC}"
    echo -e "  ${DIM}Telegram-клиент маскирует соединение под TLS${NC}"
    echo ""

    # QR если доступен
    if command -v qrencode &>/dev/null; then
        qrencode -t UTF8 -m 2 "$link" 2>/dev/null
    fi
}
