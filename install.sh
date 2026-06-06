#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# PCAtelegram_web v2.5.0 — MTProxy powered by telemt (Rust + Tokio)
# Anti-DPI • Fake TLS • TCP Splice • JA3/JA4 Resistance • i18n (EN/RU)
#
# Install:
#   curl -sL URL/bootstrap.sh | sudo bash
# ══════════════════════════════════════════════════════════════════════════════

set -uo pipefail

# Script path and libraries
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

# Load libraries
source "$LIB_DIR/common.sh"
source "$LIB_DIR/i18n.sh"
source "$LIB_DIR/telemt.sh"
source "$LIB_DIR/telemt_config.sh"
source "$LIB_DIR/website.sh"
source "$LIB_DIR/templates_catalog.sh"
source "$LIB_DIR/backup.sh"
[ -f "$LIB_DIR/stats.sh" ] && source "$LIB_DIR/stats.sh"
[ -f "$LIB_DIR/shared443.sh" ] && source "$LIB_DIR/shared443.sh"

# Load language (from config.json or marker file, default en)
load_language "$(detect_language)"

# ── Главное меню (Compact Dashboard + 5 Top-Level Items) ──────────────────────
show_main_menu() {
    local proxy_status bot_status nginx_st mode domain secret port ip link ssl_expiry
    proxy_status=$(telemt_status)
    bot_status=$(bot_service_status)
    nginx_st=$(nginx_status 2>/dev/null || echo "stopped")
    mode=$(config_get mode 2>/dev/null || echo "—")
    domain=$(config_get domain 2>/dev/null || echo "")
    secret=$(get_config_value secret 2>/dev/null || echo "")
    port=$(get_config_value port 2>/dev/null || echo "443")
    ip=$(get_server_ip 2>/dev/null || echo "N/A")

    local W=54
    local line; line=$(printf '━%.0s' $(seq 1 $W))
    local line2; line2=$(printf '─%.0s' $(seq 1 $W))

    # ── Header (no right border — ANSI breaks alignment) ──
    echo ""
    echo -e "  ${BOLD}${CYAN}━${line}━${NC}"
    echo -e "  ${BOLD}${WHITE} PCAtelegram_web v${PCATELEGRAM_WEB_VERSION}${NC}  ${DIM}— $(t dashboard_title)${NC}"
    echo -e "  ${BOLD}${CYAN}━${line}━${NC}"

    # ── Service health ──
    echo ""
    echo -e "  ${DIM}${line2}${NC}"

    # Proxy
    local proxy_icon proxy_color
    case "$proxy_status" in
        running) proxy_icon="●"; proxy_color="${GREEN}" ;;
        stopped) proxy_icon="○"; proxy_color="${YELLOW}" ;;
        *)       proxy_icon="✗"; proxy_color="${RED}" ;;
    esac
    echo -e "  ${proxy_color}${proxy_icon}${NC} $(t svc_proxy)    ${proxy_color}${proxy_status}${NC}    ${DIM}(telemt ${mode})${NC}"

    # nginx
    local nginx_icon nginx_color
    case "$nginx_st" in
        running) nginx_icon="●"; nginx_color="${GREEN}" ;;
        *)       nginx_icon="✗"; nginx_color="${RED}" ;;
    esac
    echo -e "  ${nginx_icon}${nginx_color}${NC} $(t svc_nginx)     ${nginx_color}${nginx_st}${NC}    ${DIM}(127.0.0.1:8443)${NC}"

    # Site (pro)
    if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
        local site_icon site_color
        if curl -sk --max-time 3 "https://${domain}/" -o /dev/null 2>/dev/null; then
            site_icon="●"; site_color="${GREEN}"
        else
            site_icon="✗"; site_color="${RED}"
        fi
        echo -e "  ${site_color}${site_icon}${NC} $(t svc_site)      ${site_color}https://${domain}${NC}"

        ssl_expiry=$(get_ssl_expiry "$domain" 2>/dev/null || echo "N/A")
        echo -e "  ${GREEN}●${NC} $(t svc_ssl)       ${DIM}$(tf ssl_until "$ssl_expiry")${NC}"
    fi

    # Bot
    case "$bot_status" in
        running) echo -e "  ${GREEN}●${NC} $(t svc_bot)       ${GREEN}$(t running)${NC}" ;;
        stopped) echo -e "  ${YELLOW}○${NC} $(t svc_bot)       ${YELLOW}$(t stopped)${NC}" ;;
    esac

    echo -e "  ${DIM}${line2}${NC}"

    # ── Network parameters ──
    echo -e "  ${WHITE}$(t net_ip)${NC}    ${CYAN}${ip}${NC}    ${WHITE}$(t net_port)${NC} ${CYAN}${port}${NC}    ${WHITE}$(t net_mode)${NC} ${CYAN}${mode}${NC}"
    if [ -n "$domain" ]; then
        echo -e "  ${WHITE}$(t net_domain)${NC} ${CYAN}${domain}${NC}"
    fi

    echo -e "  ${DIM}${line2}${NC}"

    # ── Proxy link + QR ──
    local mask_host
    mask_host=$(config_get mask_host 2>/dev/null || echo "")
    if [ -n "$secret" ] && [ "$proxy_status" = "running" ]; then
        if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
            link=$(generate_proxy_link "$domain" "$port" "$secret" "$domain")
        else
            link=$(generate_proxy_link "$ip" "$port" "$secret" "$mask_host")
        fi

        echo -e "  ${BOLD}${WHITE}$(t connection_link)${NC}"
        echo -e "  ${GREEN}${link}${NC}"

        if command -v qrencode &>/dev/null; then
            echo ""
            qrencode -t UTF8 -m 2 "$link" 2>/dev/null | while IFS= read -r qr_line; do
                echo "  ${qr_line}"
            done
            echo ""
        fi
    else
        echo -e "  ${DIM}$(t proxy_not_configured)${NC}"
        echo ""
    fi

    # ── Menu ──
    echo -e "  ${DIM}${line2}${NC}"
    echo -e "  ${CYAN}1${NC}) $(t menu_proxy)"
    echo -e "  ${CYAN}2${NC}) $(t menu_stats)"
    echo -e "  ${CYAN}3${NC}) $(t menu_manage)"
    echo -e "  ${CYAN}4${NC}) $(t menu_telegram_bot)"
    echo -e "  ${CYAN}5${NC}) $(t menu_about)"
    echo -e "  ${CYAN}0${NC}) ${DIM}$(t exit)${NC}"
    echo -e "  ${DIM}${line2}${NC}"
    echo -e "  ${DIM}$(t auto_refresh_30s)${NC}"
    echo -ne "  ${WHITE}▸ ${NC}"
}

# ── Submenu: Proxy ──────────────────────────────────────────────────────────
submenu_proxy() {
    while true; do
        echo ""
        echo -e "  ${BOLD}${WHITE}$(t submenu_proxy_title)${NC}"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -e "  ${CYAN}1${NC}) $(t proxy_install_update)"
        echo -e "  ${CYAN}2${NC}) $(t proxy_status_detail)"
        echo -e "  ${CYAN}3${NC}) $(t proxy_copy_link)"
        echo -e "  ${CYAN}4${NC}) $(t proxy_share)"
        echo -e "  ${CYAN}5${NC}) $(t proxy_restart)"
        echo -e "  ${CYAN}6${NC}) $(t proxy_logs)"
        echo -e "  ${CYAN}7${NC}) $(t proxy_change_mode)"
        echo -e "  ${CYAN}0${NC}) $(t back)"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -ne "  ${WHITE}$(t choose):${NC} "
        read -r ch

        case "$ch" in
            1) menu_install ;;
            2) menu_status ;;
            3) menu_link ;;
            4) menu_share ;;
            5) menu_restart ;;
            6) menu_logs ;;
            7) menu_change_mode ;;
            0) break ;;
            *) log_error "$(t invalid_choice)" ;;
        esac

        echo ""
        echo -ne "  ${DIM}$(t press_enter)${NC}"
        read -r
    done
}

# ── Submenu: Management ─────────────────────────────────────────────────────
submenu_manage() {
    while true; do
        echo ""
        echo -e "  ${BOLD}${WHITE}$(t submenu_manage_title)${NC}"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -e "  ${CYAN}1${NC}) $(t manage_backup)"
        echo -e "  ${CYAN}2${NC}) $(t manage_restore)"
        echo -e "  ${CYAN}3${NC}) $(t manage_update_telemt)"
        echo -e "  ${CYAN}4${NC}) $(t manage_site_ssl)"
        echo -e "  ${CYAN}5${NC}) $(t manage_remove)"
        echo -e "  ${CYAN}6${NC}) $(t manage_language)"
        echo -e "  ${CYAN}0${NC}) $(t back)"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -ne "  ${WHITE}$(t choose):${NC} "
        read -r ch

        case "$ch" in
            1) interactive_backup ;;
            2) interactive_restore ;;
            3) update_telemt ;;
            4) menu_website ;;
            5) menu_remove ;;
            6) menu_language ;;
            0) break ;;
            *) log_error "$(t invalid_choice)" ;;
        esac

        echo ""
        echo -ne "  ${DIM}$(t press_enter)${NC}"
        read -r
    done
}

# ── Submenu: About ──────────────────────────────────────────────────────────
submenu_about() {
    while true; do
        echo ""
        echo -e "  ${BOLD}${WHITE}$(t submenu_about_title)${NC}"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -e "  ${CYAN}1${NC}) $(t about_version_info)"
        echo -e "  ${CYAN}0${NC}) $(t back)"
        echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
        echo -ne "  ${WHITE}$(t choose):${NC} "
        read -r ch

        case "$ch" in
            1) menu_version ;;
            0) break ;;
            *) log_error "$(t invalid_choice)" ;;
        esac

        echo ""
        echo -ne "  ${DIM}$(t press_enter)${NC}"
        read -r
    done
}

# ── Version info ────────────────────────────────────────────────────────────
menu_version() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t version_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
    echo -e "  ${WHITE}$(t version_label)${NC}   v${PCATELEGRAM_WEB_VERSION}"
    echo -e "  ${WHITE}$(t version_engine)${NC}         telemt (Rust + Tokio)"
    echo -e "  ${WHITE}$(t version_tech)${NC}   Anti-DPI, Fake TLS, TCP Splice"
    echo -e "  ${WHITE}$(t version_license)${NC}     MIT"
    echo -e "  ${DIM}$(printf '─%.0s' {1..54})${NC}"
}

# ── Upgrade migration ────────────────────────────────────────────────────────
snapshot_preupgrade_state() {
    local marker="$PCATELEGRAM_WEB_DIR/.preupgrade_${PCATELEGRAM_WEB_VERSION}_done"
    [ -f "$marker" ] && return 0
    mkdir -p "$BACKUP_DIR"

    local ts tmp archive
    ts=$(date +%Y%m%d_%H%M%S)
    tmp="/tmp/pcatelegram_web_preupgrade_${ts}"
    archive="$BACKUP_DIR/preupgrade_${PCATELEGRAM_WEB_VERSION}_${ts}.tar.gz"
    mkdir -p "$tmp"

    [ -f "$PCATELEGRAM_WEB_CONFIG" ] && mkdir -p "$tmp/opt/pcatelegram_web" && cp "$PCATELEGRAM_WEB_CONFIG" "$tmp/opt/pcatelegram_web/config.json" 2>/dev/null
    [ -f "$TELEMT_CONFIG" ] && mkdir -p "$tmp/etc/telemt" && cp "$TELEMT_CONFIG" "$tmp/etc/telemt/config.toml" 2>/dev/null
    [ -f "$NGINX_SITE_CONF" ] && mkdir -p "$tmp/etc/nginx/sites-available" && cp "$NGINX_SITE_CONF" "$tmp/etc/nginx/sites-available/pcatelegram_web" 2>/dev/null
    [ -d "$WEBSITE_ROOT" ] && mkdir -p "$tmp/var/www/pcatelegram_web-site" && cp -a "$WEBSITE_ROOT/." "$tmp/var/www/pcatelegram_web-site/" 2>/dev/null
    [ -f "$BOT_DIR/.env" ] && mkdir -p "$tmp/opt/pcatelegram_web-bot" && cp "$BOT_DIR/.env" "$tmp/opt/pcatelegram_web-bot/.env" 2>/dev/null

    if tar czf "$archive" -C "$tmp" . 2>/dev/null; then
        log_dim "Pre-upgrade snapshot: $archive"
        touch "$marker" 2>/dev/null || true
    fi
    rm -rf "$tmp"
}

read_config_or_default() {
    local key="$1" fallback="$2"
    config_get "$key" 2>/dev/null || echo "$fallback"
}

detect_deployed_template_id() {
    local tpl=""
    if [ -f "$WEBSITE_ROOT/.pcatelegram_web_template_id" ]; then
        tpl=$(head -1 "$WEBSITE_ROOT/.pcatelegram_web_template_id" 2>/dev/null || echo "")
        [ -n "$tpl" ] && { echo "$tpl"; return 0; }
    fi
    if [ -d "$WEBSITE_ROOT" ] && [ -f "$WEBSITE_ROOT/index.html" ]; then
        echo "deployed_site"
        return 0
    fi
    tpl=$(read_config_or_default template_id "")
    [ -n "$tpl" ] && { echo "$tpl"; return 0; }
    echo ""
}

detect_template_source() {
    local src
    if [ -f "$WEBSITE_ROOT/.pcatelegram_web_template_source" ]; then
        src=$(head -1 "$WEBSITE_ROOT/.pcatelegram_web_template_source" 2>/dev/null || echo "")
        [ -n "$src" ] && { echo "$src"; return 0; }
    fi
    [ -d "$WEBSITE_ROOT" ] && [ -f "$WEBSITE_ROOT/index.html" ] && return 0
    read_config_or_default template_source ""
}

write_normalized_pcatelegram_web_config() {
    local mode="$1" port="$2" secret="$3" mask_host="$4" domain="$5" tpl_id="$6" tpl_source="$7"
    local lang installed_at stats_enabled tmp
    lang=$(read_config_or_default language "$(get_language 2>/dev/null || echo en)")
    installed_at=$(read_config_or_default installed_at "$(date -Iseconds)")
    stats_enabled=$(read_config_or_default stats_enabled "")
    tmp=$(mktemp) || return 1

    jq -n \
        --arg version "$PCATELEGRAM_WEB_VERSION" \
        --arg engine "telemt" \
        --arg mode "$mode" \
        --argjson port "$port" \
        --arg secret "$secret" \
        --arg mask_host "$mask_host" \
        --arg domain "$domain" \
        --arg template_id "$tpl_id" \
        --arg template_source "$tpl_source" \
        --arg language "$lang" \
        --arg installed_at "$installed_at" \
        --arg updated_at "$(date -Iseconds)" \
        --arg stats_enabled "$stats_enabled" \
        '{
            version: $version,
            engine: $engine,
            mode: $mode,
            port: $port,
            secret: $secret,
            mask_host: $mask_host,
            domain: $domain,
            template_id: $template_id,
            language: $language,
            installed_at: $installed_at,
            updated_at: $updated_at
        }
        + (if $template_source != "" then {template_source: $template_source} else {} end)
        + (if $stats_enabled == "true" then {stats_enabled: true} elif $stats_enabled == "false" then {stats_enabled: false} else {} end)' \
        > "$tmp" || { rm -f "$tmp"; return 1; }

    mkdir -p "$(dirname "$PCATELEGRAM_WEB_CONFIG")"
    mv "$tmp" "$PCATELEGRAM_WEB_CONFIG"
    chmod 600 "$PCATELEGRAM_WEB_CONFIG"
}

auto_migrate_legacy_state() {
    local marker="$PCATELEGRAM_WEB_DIR/.migrated_${PCATELEGRAM_WEB_VERSION}"
    local current_version
    current_version=$(read_config_or_default version "")
    if [ -f "$marker" ] && [ "$current_version" = "$PCATELEGRAM_WEB_VERSION" ]; then
        return 0
    fi

    [ -f "$TELEMT_CONFIG" ] || [ -f "$PCATELEGRAM_WEB_CONFIG" ] || [ -d "$WEBSITE_ROOT" ] || return 0

    log_step "Миграция состояния PCAtelegram_web"
    snapshot_preupgrade_state

    local mode port secret mask_host domain mask_port tpl_id tpl_source users_block tls_emulation changed=0 users_block_needs_write=0
    users_block=$(get_telemt_users_block "$TELEMT_CONFIG" 2>/dev/null || true)
    secret=$(get_config_value secret "$TELEMT_CONFIG" 2>/dev/null || echo "")
    [ -z "$secret" ] && secret=$(read_config_or_default secret "")
    [ -z "$secret" ] && secret=$(first_telemt_user_secret "$TELEMT_CONFIG" 2>/dev/null || echo "")
    [ -z "$secret" ] && secret=$(generate_hex 32)

    if [ -n "$users_block" ] && ! telemt_users_block_has_main "$users_block"; then
        users_block=$(printf 'main = "%s"\n%s\n' "$secret" "$users_block")
        users_block_needs_write=1
    fi
    if [ -z "$users_block" ]; then
        users_block="main = \"$secret\""
        users_block_needs_write=1
    fi

    port=$(get_config_value port "$TELEMT_CONFIG" 2>/dev/null || echo "")
    [ -z "$port" ] && port=$(read_config_or_default port "443")
    [[ "$port" =~ ^[0-9]+$ ]] || port=443

    mask_host=$(get_config_value mask_host "$TELEMT_CONFIG" 2>/dev/null || echo "")
    [ -z "$mask_host" ] && mask_host=$(read_config_or_default mask_host "google.com")
    domain=$(read_config_or_default domain "")
    mask_port=$(get_config_value mask_port "$TELEMT_CONFIG" 2>/dev/null || echo "")
    [ -z "$mask_port" ] && mask_port="443"
    tls_emulation=$(toml_bool_value censorship tls_emulation "$TELEMT_CONFIG" 2>/dev/null || echo "")

    mode=$(read_config_or_default mode "")
    if [ -z "$mode" ]; then
        if [ -n "$domain" ] || [ "$tls_emulation" = "false" ] || grep -q 'dns_overrides' "$TELEMT_CONFIG" 2>/dev/null; then
            mode="pro"
        else
            mode="lite"
        fi
    fi
    if [ "$mode" = "pro" ]; then
        [ -z "$domain" ] && domain="$mask_host"
        [ -n "$domain" ] && mask_host="$domain"
        [ "$mask_port" = "443" ] && mask_port="8443"
    else
        domain=""
        mask_port="443"
    fi

    tpl_id=$(detect_deployed_template_id)
    tpl_source=$(detect_template_source || echo "")
    if [ -d "$WEBSITE_ROOT" ] && [ -f "$WEBSITE_ROOT/index.html" ] && [ -n "$tpl_id" ]; then
        echo "$tpl_id" > "$WEBSITE_ROOT/.pcatelegram_web_template_id" 2>/dev/null || true
        [ -n "$tpl_source" ] && echo "$tpl_source" > "$WEBSITE_ROOT/.pcatelegram_web_template_source" 2>/dev/null || true
    fi

    if [ -f "$TELEMT_CONFIG" ]; then
        if ! grep -q '\[server.api\]' "$TELEMT_CONFIG" 2>/dev/null || \
           ! grep -q 'metrics_listen' "$TELEMT_CONFIG" 2>/dev/null || \
           ! grep -q "PCAtelegram_web v${PCATELEGRAM_WEB_VERSION}" "$TELEMT_CONFIG" 2>/dev/null; then
            generate_telemt_toml "$secret" "$port" "$mode" "$mask_host" "$mask_port" "$TELEMT_CONFIG" >&2
            replace_telemt_users_block "$users_block" "$TELEMT_CONFIG"
            changed=1
            users_block_needs_write=0
        elif [ "$users_block_needs_write" = "1" ]; then
            replace_telemt_users_block "$users_block" "$TELEMT_CONFIG"
            changed=1
        fi
    fi

    write_normalized_pcatelegram_web_config "$mode" "$port" "$secret" "$mask_host" "$domain" "$tpl_id" "$tpl_source" || \
        log_warning "Не удалось нормализовать config.json"

    if [ "$changed" = "1" ] && systemctl is-active --quiet "$TELEMT_SERVICE" 2>/dev/null; then
        log_info "Перезапускаю telemt, чтобы применить нормализованный конфиг..."
        restart_telemt || log_warning "telemt не перезапустился после миграции; проверьте journalctl -u telemt"
    fi

    touch "$marker" 2>/dev/null || true
    log_success "Миграция завершена: ключи, режим, домен и сайт сохранены"
}

# ── Install: mode selection ─────────────────────────────────────────────────
menu_install() {
    # Check for v1
    if detect_v1_installation; then
        echo ""
        echo -e "  ${YELLOW}$(t v1_detected)${NC}"
        echo -e "  ${DIM}$(tf v1_container "$V1_CONTAINER_NAME")${NC}"
        echo ""
        if ! migrate_v1_to_v2; then
            return
        fi
    fi

    echo ""
    echo -e "  ${BOLD}${WHITE}$(t install_select_mode)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -e "  ${CYAN}1)${NC} ${GREEN}$(t install_lite_title)${NC}"
    echo -e "     ${DIM}$(t install_lite_desc1)${NC}"
    echo -e "     ${DIM}$(t install_lite_desc2)${NC}"
    echo ""
    echo -e "  ${CYAN}2)${NC} ${MAGENTA}$(t install_pro_title)${NC}"
    echo -e "     ${DIM}$(t install_pro_desc1)${NC}"
    echo -e "     ${DIM}$(t install_pro_desc2)${NC}"
    echo -e "     ${DIM}$(t install_pro_desc3)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -ne "  ${WHITE}$(t install_mode_choice)${NC} "
    read -r mode_choice
    mode_choice="${mode_choice:-}"

    case "$mode_choice" in
        1) install_lite_mode ;;
        2) install_pro_mode ;;
        *) log_error "$(tf install_bad_choice "${mode_choice:-<empty>}")" ;;
    esac
}

# ── Lite mode ───────────────────────────────────────────────────────────────
install_lite_mode() {
    log_step "$(t install_lite_step)"

    # Domain selection
    local domain
    domain=$(select_quick_domain)
    [ $? -ne 0 ] && return

    # Port selection
    local port
    port=$(select_port)
    [ $? -ne 0 ] && return
    if [ "$port" = "443" ]; then
        warn_3xui_443_conflict || true
    fi

    # Generate secret
    local secret
    secret=$(generate_hex 32)

    # Confirm
    local ip
    ip=$(get_server_ip)
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t install_config_title)${NC}"
    echo -e "  $(t install_cfg_ip)         ${CYAN}${ip}${NC}"
    echo -e "  $(t install_cfg_port)       ${CYAN}${port}${NC}"
    echo -e "  $(t install_cfg_mask) ${CYAN}${domain}${NC}"
    echo -e "  $(t install_cfg_mode)      ${GREEN}Lite${NC}"
    echo ""

    if ! confirm "$(t install_confirm_proxy)"; then
        return
    fi

    # Install
    ensure_deps
    install_telemt_full || return

    # Generate telemt config
    generate_telemt_toml "$secret" "$port" "lite" "$domain" "443"

    # Validate
    validate_telemt_config || return

    # Start
    start_telemt || return

    # Save PCAtelegram_web config
    save_pcatelegram_web_config "telemt" "lite" "$port" "$secret" "$domain" "" ""

    # Credits
    show_credits

    # Result
    show_proxy_info
    log_success "$(tf install_done "$PCATELEGRAM_WEB_VERSION" "Lite")"
}

# ── Pro mode ────────────────────────────────────────────────────────────────
install_pro_mode() {
    log_step "$(t install_pro_step)"

    warn_3xui_443_conflict || true

    # Enter domain
    echo ""
    echo -ne "  ${WHITE}$(t install_enter_domain)${NC} "
    read -r user_domain

    if [ -z "$user_domain" ] || ! validate_domain "$user_domain"; then
        log_error "$(tf install_bad_domain "${user_domain:-<empty>}")"
        return
    fi

    # Check DNS
    local resolved_ip server_ip
    resolved_ip=$(dig +short "$user_domain" A 2>/dev/null | head -1)
    server_ip=$(get_server_ip)

    if [ -n "$resolved_ip" ] && [ "$resolved_ip" != "$server_ip" ]; then
        log_warning "$(tf install_dns_mismatch "$user_domain" "$resolved_ip" "$server_ip")"
        if ! confirm "$(t install_continue_anyway)"; then
            return
        fi
    fi

    # Email for Let's Encrypt
    echo -ne "  ${WHITE}$(t install_enter_email)${NC} "
    read -r ssl_email

    # Template selection
    local template_dir
    template_dir=$(interactive_template_selection)
    [ $? -ne 0 ] && return

    # Pro architecture:
    # telemt listens on 0.0.0.0:443 (accepts ALL connections)
    # nginx listens on 127.0.0.1:8443 with SSL (serves website)
    # MTProxy client → :443 → telemt (proxies)
    # Regular browser → :443 → telemt → 127.0.0.1:8443 → nginx (website)
    # ISP only sees HTTPS on 443 to domain
    local nginx_internal_port=8443
    echo ""
    echo -e "  ${DIM}$(t install_arch_desc1)${NC}"
    echo -e "  ${DIM}$(tf install_arch_desc2 "$nginx_internal_port")${NC}"
    echo -e "  ${DIM}$(tf install_arch_desc3 "$user_domain")${NC}"

    # Generate fake-TLS secret (ee + secret + hex domain)
    # ee prefix tells Telegram client to masquerade traffic as TLS to domain
    local raw_secret
    raw_secret=$(generate_hex 32)
    local domain_hex
    domain_hex=$(printf '%s' "$user_domain" | xxd -p | tr -d '\n')
    local faketls_secret="ee${raw_secret}${domain_hex}"

    # Confirmation
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t install_config_title)${NC}"
    echo -e "  $(t install_cfg_domain)      ${CYAN}${user_domain}${NC}"
    echo -e "  $(t install_cfg_port)       ${CYAN}443 (telemt + nginx)${NC}"
    echo -e "  $(t install_cfg_mode)      ${MAGENTA}Pro (fake-TLS)${NC}"
    echo ""

    if ! confirm "$(t install_confirm_proxy_site)"; then
        return
    fi

    # Install
    ensure_deps
    install_telemt_full || return

    # telemt config: listen 443, masquerade to local nginx via dns_override
    generate_telemt_toml "$raw_secret" "443" "pro" "$user_domain" "$nginx_internal_port"

    # Website setup (nginx on internal port + certbot + template)
    setup_pro_mode "$user_domain" "$template_dir" "$nginx_internal_port" "$ssl_email" || return

    # Stop nginx on 443 before starting telemt (telemt will take 443)
    # nginx already reconfigured to internal port
    systemctl restart nginx 2>/dev/null

    # Start telemt
    start_telemt || return

    # Save config
    local tpl_id
    tpl_id=$(basename "$template_dir")
    save_pcatelegram_web_config "telemt" "pro" "443" "$raw_secret" "$user_domain" "$user_domain" "$tpl_id"

    # Result — use domain and fake-TLS link
    show_proxy_info_pro "$user_domain" "$faketls_secret"
    echo -e "  ${WHITE}$(t svc_site):${NC} ${GREEN}https://${user_domain}${NC}"
    log_success "$(tf install_done "$PCATELEGRAM_WEB_VERSION" "Pro")"
}

# ── Статус ───────────────────────────────────────────────────────────────────
menu_status() {
    show_proxy_info

    # Extras for pro
    local mode
    mode=$(config_get mode 2>/dev/null)
    if [ "$mode" = "pro" ]; then
        local domain
        domain=$(config_get domain 2>/dev/null)
        if [ -n "$domain" ]; then
            local ssl_expiry
            ssl_expiry=$(get_ssl_expiry "$domain")
            local nginx_st
            nginx_st=$(nginx_status)
            echo -e "  ${WHITE}$(t svc_nginx):${NC}      ${nginx_st}"
            echo -e "  ${WHITE}$(t website_ssl_until)${NC}     ${ssl_expiry}"
            echo -e "  ${WHITE}$(t svc_site):${NC}       https://${domain}"
            echo ""
        fi
    fi
}

# ── Ссылка ───────────────────────────────────────────────────────────────────
menu_link() {
    local secret port ip link mode domain mask_host
    secret=$(get_config_value secret)
    port=$(get_config_value port)
    ip=$(get_server_ip)
    mode=$(config_get mode 2>/dev/null || echo "lite")
    domain=$(config_get domain 2>/dev/null || echo "")
    mask_host=$(config_get mask_host 2>/dev/null || echo "")

    if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
        link=$(generate_proxy_link "$domain" "$port" "$secret" "$domain")
    else
        link=$(generate_proxy_link "$ip" "$port" "$secret" "$mask_host")
    fi

    echo ""
    echo -e "  ${BOLD}${WHITE}$(t link_title)${NC}"
    echo ""
    echo -e "  ${GREEN}${link}${NC}"
    echo ""

    if command -v qrencode &>/dev/null; then
        qrencode -t UTF8 -m 2 "$link" 2>/dev/null
    fi
}

# ── Поделиться ───────────────────────────────────────────────────────────────
menu_share() {
    local secret port ip link mode domain mask_host server_display
    secret=$(get_config_value secret)
    port=$(get_config_value port)
    ip=$(get_server_ip)
    mode=$(config_get mode 2>/dev/null || echo "lite")
    domain=$(config_get domain 2>/dev/null || echo "")
    mask_host=$(config_get mask_host 2>/dev/null || echo "")

    if [ "$mode" = "pro" ] && [ -n "$domain" ]; then
        link=$(generate_proxy_link "$domain" "$port" "$secret" "$domain")
        server_display="$domain"
    else
        link=$(generate_proxy_link "$ip" "$port" "$secret" "$mask_host")
        server_display="$ip"
    fi

    echo ""
    echo -e "  ${BOLD}$(t share_title)${NC}"
    echo ""
    printf "$(t share_line1)\n" "$PCATELEGRAM_WEB_VERSION"
    echo ""
    printf "$(t share_server)\n" "$server_display"
    printf "$(t share_port)\n" "$port"
    echo ""
    echo "$(t share_connect_cta)"
    echo "$link"
    echo ""
    echo "$(t share_footer)"
    echo ""
}

# ── Перезапуск ───────────────────────────────────────────────────────────────
menu_restart() {
    restart_telemt
    local mode
    mode=$(config_get mode 2>/dev/null)
    if [ "$mode" = "pro" ]; then
        restart_nginx
    fi
}

# ── Logs ────────────────────────────────────────────────────────────────────
menu_logs() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(tf logs_telemt_title 40)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    telemt_logs 40
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
}

# ── Change mode / template ──────────────────────────────────────────────────
update_current_template_id() {
    local template_dir="$1"
    local tpl_id
    tpl_id=$(basename "$template_dir")
    [ -z "$tpl_id" ] && return 0

    if [ -f "$template_dir/.custom_git_source" ]; then
        local source_url
        source_url=$(head -1 "$template_dir/.custom_git_source" 2>/dev/null || echo "")
        bot_update_config_field "template_source" "$source_url" || true
    fi
    bot_update_config_field "template_id" "$tpl_id" || \
        log_warning "Не удалось обновить template_id в config.json"
}

menu_change_mode() {
    local current_mode
    current_mode=$(config_get mode 2>/dev/null)
    echo ""
    echo -e "  ${WHITE}$(t change_current_mode)${NC} ${CYAN}${current_mode}${NC}"
    echo ""
    echo -e "  ${CYAN}1${NC}) $(t change_template)"
    echo -e "  ${CYAN}2${NC}) $(t change_mode_switch)"
    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r ch

    case "$ch" in
        1)
            if [ "$current_mode" != "pro" ]; then
                log_error "$(t change_only_pro)"
                return
            fi
            local template_dir
            template_dir=$(interactive_template_selection)
            [ $? -ne 0 ] && return
            switch_template "$template_dir"
            update_current_template_id "$template_dir"
            ;;
        2)
            log_warning "$(t change_requires_reinstall)"
            if confirm "$(t change_reinstall_confirm)"; then
                menu_install
            fi
            ;;
    esac
}

# ── Website management ─────────────────────────────────────────────────────
menu_website() {
    local mode
    mode=$(config_get mode 2>/dev/null)

    if [ "$mode" != "pro" ]; then
        log_info "$(t website_only_pro)"
        return
    fi

    local domain
    domain=$(config_get domain 2>/dev/null)

    echo ""
    echo -e "  ${BOLD}${WHITE}$(t website_title)${NC}"
    echo -e "  $(t website_domain) ${CYAN}${domain}${NC}"
    echo -e "  $(t website_ssl_until) $(get_ssl_expiry "$domain")"
    echo ""
    echo -e "  ${CYAN}1${NC}) $(t website_renew_ssl)"
    echo -e "  ${CYAN}2${NC}) $(t website_restart_nginx)"
    echo -e "  ${CYAN}3${NC}) $(t website_change_template)"
    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r ch

    case "$ch" in
        1) renew_ssl_certificate ;;
        2) restart_nginx ;;
        3)
            local template_dir
            template_dir=$(interactive_template_selection)
            [ $? -ne 0 ] && return
            switch_template "$template_dir"
            update_current_template_id "$template_dir"
            ;;
    esac
}

# ── Remove ─────────────────────────────────────────────────────────────────
menu_remove() {
    echo ""
    echo -e "  ${BOLD}${RED}$(t remove_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -e "  ${CYAN}1${NC}) $(t remove_proxy_only)"
    echo -e "  ${CYAN}2${NC}) $(t remove_bot_only)"
    echo -e "  ${CYAN}3${NC}) $(t remove_all)"
    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r rm_choice

    case "$rm_choice" in
        1)
            log_warning "$(t remove_warn_proxy)"
            if ! confirm "$(t remove_confirm_proxy)"; then return; fi
            if confirm "$(t remove_backup_before)"; then
                interactive_backup
            fi
            remove_telemt
            local mode
            mode=$(config_get mode 2>/dev/null)
            if [ "$mode" = "pro" ]; then
                remove_pro_mode
            fi
            rm -f "$PCATELEGRAM_WEB_CONFIG"
            log_success "$(t remove_proxy_done)"
            ;;
        2)
            bot_remove
            ;;
        3)
            log_warning "$(t remove_warn_all)"
            if ! confirm "$(t remove_confirm_all)"; then return; fi
            if confirm "$(t remove_backup_before)"; then
                interactive_backup
            fi
            # Proxy
            remove_telemt
            local mode
            mode=$(config_get mode 2>/dev/null)
            if [ "$mode" = "pro" ]; then
                remove_pro_mode
            fi
            rm -f "$PCATELEGRAM_WEB_CONFIG"
            # Bot
            if [ "$(bot_service_status)" != "not_installed" ]; then
                systemctl stop "$BOT_SERVICE" 2>/dev/null
                systemctl disable "$BOT_SERVICE" 2>/dev/null
                rm -f "/etc/systemd/system/${BOT_SERVICE}.service"
                systemctl daemon-reload
                rm -rf "$BOT_DIR"
            fi
            remove_admin_web
            log_success "$(t remove_all_done)"
            ;;
    esac
}

# ── Telegram-бот ────────────────────────────────────────────────────────────
BOT_DIR="/opt/pcatelegram_web-bot"
BOT_SERVICE="pcatelegram_web-bot"

admin_web_service_status() {
    if ! systemctl list-unit-files "$ADMIN_WEB_SERVICE.service" &>/dev/null 2>&1; then
        echo "not_installed"
    elif systemctl is-active "$ADMIN_WEB_SERVICE" &>/dev/null 2>&1; then
        echo "running"
    else
        echo "stopped"
    fi
}

install_admin_web() {
    local src_dir="$SCRIPT_DIR/admin-web"
    [ -d "$src_dir" ] || { log_warning "admin-web files not found: $src_dir"; return 1; }
    command -v python3 &>/dev/null || { log_warning "python3 not found; web admin skipped"; return 1; }

    mkdir -p "$ADMIN_WEB_DIR/static"
    cp "$src_dir/server.py" "$ADMIN_WEB_DIR/server.py"
    cp -a "$src_dir/static/." "$ADMIN_WEB_DIR/static/"
    chmod 700 "$ADMIN_WEB_DIR"
    chmod 755 "$ADMIN_WEB_DIR/server.py" "$ADMIN_WEB_DIR/static"
    rm -f "$ADMIN_WEB_DIR/token" 2>/dev/null || true

    local python_bin
    python_bin=$(command -v python3)
    ensure_admin_web_password >/dev/null
    cat > "/etc/systemd/system/${ADMIN_WEB_SERVICE}.service" << SVCEOF
[Unit]
Description=PCAtelegram_web v${PCATELEGRAM_WEB_VERSION} Local Web Admin
After=network.target

[Service]
Type=simple
WorkingDirectory=$ADMIN_WEB_DIR
ExecStart=$python_bin $ADMIN_WEB_DIR/server.py
Restart=always
RestartSec=5
Environment=PCATELEGRAM_WEB_ADMIN_HOST=$ADMIN_WEB_HOST
Environment=PCATELEGRAM_WEB_ADMIN_PORT=$ADMIN_WEB_PORT
Environment=PCATELEGRAM_WEB_ADMIN_USER=${PCATELEGRAM_WEB_ADMIN_USER:-admin}

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable "$ADMIN_WEB_SERVICE" &>/dev/null
    systemctl restart "$ADMIN_WEB_SERVICE" 2>/dev/null || systemctl start "$ADMIN_WEB_SERVICE"
    if type install_stats_collector &>/dev/null; then
        install_stats_collector >/dev/null 2>&1 || log_warning "stats collector was not started; open Web Admin traffic page and use Repair"
    fi
    log_success "Web admin installed: http://$(get_server_ip):${ADMIN_WEB_PORT}/"
    log_info "Web admin login saved: $ADMIN_WEB_AUTH_FILE"
}

auto_install_admin_web_if_possible() {
    [ -d "$SCRIPT_DIR/admin-web" ] || return 0
    command -v python3 &>/dev/null || return 0
    if [ "$(admin_web_service_status)" != "not_installed" ] && \
       [ -f "$ADMIN_WEB_DIR/server.py" ] && \
       cmp -s "$SCRIPT_DIR/admin-web/server.py" "$ADMIN_WEB_DIR/server.py" && \
       cmp -s "$SCRIPT_DIR/admin-web/static/index.html" "$ADMIN_WEB_DIR/static/index.html" && \
       cmp -s "$SCRIPT_DIR/admin-web/static/app.js" "$ADMIN_WEB_DIR/static/app.js" && \
       cmp -s "$SCRIPT_DIR/admin-web/static/styles.css" "$ADMIN_WEB_DIR/static/styles.css"; then
        return 0
    fi
    install_admin_web >/dev/null 2>&1 || true
}

remove_admin_web() {
    systemctl stop "$ADMIN_WEB_SERVICE" 2>/dev/null
    systemctl disable "$ADMIN_WEB_SERVICE" 2>/dev/null
    rm -f "/etc/systemd/system/${ADMIN_WEB_SERVICE}.service"
    systemctl daemon-reload 2>/dev/null
    rm -rf "$ADMIN_WEB_DIR"
}

bot_service_status() {
    if ! systemctl list-unit-files "$BOT_SERVICE.service" &>/dev/null 2>&1; then
        echo "not_installed"
    elif systemctl is-active "$BOT_SERVICE" &>/dev/null 2>&1; then
        echo "running"
    else
        echo "stopped"
    fi
}

auto_update_bot_if_possible() {
    [ -d "$SCRIPT_DIR/pcatelegram_web-bot" ] || return 0
    [ "$(bot_service_status)" = "not_installed" ] && return 0
    [ -f "$BOT_DIR/.env" ] || return 0

    local needs_update=0
    [ -f "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" ] && \
        ! cmp -s "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" "$BOT_DIR/bot.py" && needs_update=1
    [ -f "$SCRIPT_DIR/pcatelegram_web-bot/i18n.py" ] && \
        ! cmp -s "$SCRIPT_DIR/pcatelegram_web-bot/i18n.py" "$BOT_DIR/i18n.py" && needs_update=1
    [ -f "$SCRIPT_DIR/pcatelegram_web-bot/requirements.txt" ] && \
        ! cmp -s "$SCRIPT_DIR/pcatelegram_web-bot/requirements.txt" "$BOT_DIR/requirements.txt" && needs_update=1

    local lang_file lang_name
    for lang_file in "$SCRIPT_DIR"/pcatelegram_web-bot/lang/*.json; do
        [ -e "$lang_file" ] || continue
        lang_name=$(basename "$lang_file")
        ! cmp -s "$lang_file" "$BOT_DIR/lang/$lang_name" && needs_update=1
    done

    [ "$needs_update" = "1" ] || return 0
    bot_install >/dev/null 2>&1 || \
        log_warning "Telegram bot auto-update failed; run menu 12 → Telegram-bot → Install/update"
}

menu_bot() {
    local st
    st=$(bot_service_status)

    echo ""
    echo -e "  ${BOLD}${WHITE}$(t bot_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"

    case "$st" in
        running)
            echo -e "  $(t bot_status_colon) ${GREEN}$(t bot_status_running)${NC}"
            echo ""
            echo -e "  ${CYAN}1${NC}) $(t bot_menu_status)"
            echo -e "  ${CYAN}2${NC}) $(t bot_menu_logs)"
            echo -e "  ${CYAN}3${NC}) $(t bot_menu_restart)"
            echo -e "  ${CYAN}4${NC}) $(t bot_menu_stop)"
            echo -e "  ${CYAN}5${NC}) $(t bot_menu_settings)"
            echo -e "  ${CYAN}6${NC}) $(t bot_menu_remove)"
            ;;
        stopped)
            echo -e "  $(t bot_status_colon) ${YELLOW}$(t bot_status_stopped)${NC}"
            echo ""
            echo -e "  ${CYAN}1${NC}) $(t bot_menu_status)"
            echo -e "  ${CYAN}2${NC}) $(t bot_menu_logs)"
            echo -e "  ${CYAN}3${NC}) $(t bot_menu_start)"
            echo -e "  ${CYAN}5${NC}) $(t bot_menu_settings)"
            echo -e "  ${CYAN}6${NC}) $(t bot_menu_remove)"
            ;;
        *)
            echo -e "  $(t bot_status_colon) ${RED}$(t bot_status_not_installed)${NC}"
            echo ""
            echo -e "  ${DIM}$(t bot_intro1)${NC}"
            echo -e "  ${DIM}$(t bot_intro2)${NC}"
            echo ""
            echo -e "  ${CYAN}1${NC}) $(t bot_menu_install)"
            ;;
    esac

    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r ch

    case "$st" in
        running)
            case "$ch" in
                1) bot_show_status ;;
                2) bot_show_logs ;;
                3) systemctl restart "$BOT_SERVICE" && log_success "$(t bot_restarted)" ;;
                4) systemctl stop "$BOT_SERVICE" && log_info "$(t bot_stopped)" ;;
                5) bot_edit_config ;;
                6) bot_remove ;;
            esac
            ;;
        stopped)
            case "$ch" in
                1) bot_show_status ;;
                2) bot_show_logs ;;
                3) systemctl start "$BOT_SERVICE" && log_success "$(t bot_started)" ;;
                5) bot_edit_config ;;
                6) bot_remove ;;
            esac
            ;;
        *)
            case "$ch" in
                1) bot_install ;;
            esac
            ;;
    esac
}

bot_install() {
    log_step "$(t bot_install_step)"

    # Python + venv + pip (always ensure — python3 can be present without venv/pip)
    local need_py=0
    command -v python3 &>/dev/null || need_py=1
    # python3-venv not having its own command; probe by trying 'python3 -m venv --help'
    if ! python3 -m venv --help &>/dev/null; then need_py=1; fi
    # pip check
    if ! python3 -m pip --version &>/dev/null; then need_py=1; fi

    if [ "$need_py" = "1" ]; then
        log_info "$(t bot_install_python)"
        if command -v apt-get &>/dev/null; then
            # Detect Python version for versioned venv package (Debian 12 / Ubuntu 24.04 need python3.12-venv)
            local py_ver=""
            if command -v python3 &>/dev/null; then
                py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
            fi

            apt_update

            # Build package list with versioned venv fallback
            local pkg_list=(python3 python3-venv python3-pip)
            [ -n "$py_ver" ] && pkg_list+=("python${py_ver}-venv")
            # python3-full optional
            if ! apt_install "${pkg_list[@]}" python3-full; then
                log_warning "python3-full unavailable, installing core packages only..."
                apt_install "${pkg_list[@]}" || {
                    log_error "Failed to install Python packages. Run manually: apt install ${pkg_list[*]}"
                    return 1
                }
            fi
        elif command -v dnf &>/dev/null; then
            dnf install -y -q python3 python3-pip
        elif command -v yum &>/dev/null; then
            yum install -y -q python3 python3-pip
        fi
    fi

    # Copy bot files
    mkdir -p "$BOT_DIR"
    if [ -f "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" ]; then
        cp "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" "$BOT_DIR/"
        cp "$SCRIPT_DIR/pcatelegram_web-bot/requirements.txt" "$BOT_DIR/"
        [ -f "$SCRIPT_DIR/pcatelegram_web-bot/config.example.env" ] && \
            cp "$SCRIPT_DIR/pcatelegram_web-bot/config.example.env" "$BOT_DIR/"
        # Copy i18n language files for bot
        if [ -d "$SCRIPT_DIR/pcatelegram_web-bot/lang" ]; then
            mkdir -p "$BOT_DIR/lang"
            cp -f "$SCRIPT_DIR/pcatelegram_web-bot/lang/"*.json "$BOT_DIR/lang/" 2>/dev/null
        fi
        [ -f "$SCRIPT_DIR/pcatelegram_web-bot/i18n.py" ] && \
            cp "$SCRIPT_DIR/pcatelegram_web-bot/i18n.py" "$BOT_DIR/"
    else
        log_error "$(tf bot_files_not_found "$SCRIPT_DIR/pcatelegram_web-bot/")"
        return 1
    fi

    # Templates catalog — skip if source and dest are the same file (symlink install case)
    if [ -f "$SCRIPT_DIR/templates_catalog.json" ]; then
        local src_tc="$SCRIPT_DIR/templates_catalog.json"
        local dst_tc="$PCATELEGRAM_WEB_DIR/templates_catalog.json"
        if [ "$(readlink -f "$src_tc" 2>/dev/null)" != "$(readlink -f "$dst_tc" 2>/dev/null)" ]; then
            cp "$src_tc" "$dst_tc"
        fi
    fi

    # Venv — create, and verify pip exists (python3-venv can silently create broken venv)
    if [ ! -d "$BOT_DIR/venv" ] || [ ! -x "$BOT_DIR/venv/bin/pip" ]; then
        log_info "$(t bot_create_venv)"
        rm -rf "$BOT_DIR/venv"
        if ! python3 -m venv "$BOT_DIR/venv" 2>/tmp/venv_err; then
            log_error "venv creation failed:"
            cat /tmp/venv_err >&2 2>/dev/null
            # Try to fix by installing versioned python3.X-venv package
            if command -v apt-get &>/dev/null; then
                local py_ver
                py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
                log_info "reinstalling python${py_ver}-venv..."
                apt_install python3-venv python3-pip "python${py_ver}-venv" python3-full || \
                    apt_install python3-venv python3-pip "python${py_ver}-venv" || true
                rm -rf "$BOT_DIR/venv"
                python3 -m venv "$BOT_DIR/venv" || { log_error "venv still broken, aborting. Manual fix: apt install python${py_ver}-venv python3-pip"; return 1; }
            else
                return 1
            fi
        fi
    fi

    if [ ! -x "$BOT_DIR/venv/bin/pip" ]; then
        log_info "bootstrapping pip via ensurepip..."
        "$BOT_DIR/venv/bin/python" -m ensurepip --upgrade 2>/dev/null || true
    fi

    if [ ! -x "$BOT_DIR/venv/bin/pip" ]; then
        log_error "pip missing in venv — install python3-venv manually: apt install python3-venv python3-pip"
        return 1
    fi

    log_info "$(t bot_install_deps)"
    if ! "$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" -q 2>/tmp/pip_err; then
        log_error "pip install failed:"
        tail -n 5 /tmp/pip_err >&2
        return 1
    fi

    # Sanity check: verify critical imports succeed
    if ! "$BOT_DIR/venv/bin/python" -c "import telegram, toml, dotenv" 2>/tmp/imp_err; then
        log_error "dependency import check failed:"
        cat /tmp/imp_err >&2
        return 1
    fi

    # Configuration
    if [ ! -f "$BOT_DIR/.env" ]; then
        echo ""
        echo -e "  ${YELLOW}$(t bot_enter_token)${NC}"
        local token=""
        while [ -z "$token" ]; do
            echo -ne "  ${WHITE}$(t bot_token)${NC} "
            read -r token
            token=$(echo "$token" | tr -d '[:space:]')
            [ -z "$token" ] && log_error "$(t bot_token_empty)"
        done

        echo ""
        echo -e "  ${WHITE}$(t bot_add_admin_how)${NC}"
        echo -e "  ${CYAN}1${NC}) $(t bot_admin_auto)"
        echo -e "  ${CYAN}2${NC}) $(t bot_admin_manual)"
        echo -ne "  ${WHITE}$(t choose) [1]:${NC} "
        read -r admin_mode
        admin_mode="${admin_mode:-1}"

        local admin_ids=""
        if [ "$admin_mode" = "2" ]; then
            echo -ne "  ${WHITE}$(t bot_admin_ids_prompt)${NC} "
            read -r admin_ids
            admin_ids=$(echo "$admin_ids" | tr ' ' ',' | sed 's/,,*/,/g; s/^,//; s/,$//')
        fi

        # Propagate selected language to bot so UI matches
        local bot_lang
        bot_lang=$(get_language 2>/dev/null || echo en)
        {
            echo "BOT_TOKEN=$token"
            [ -n "$admin_ids" ] && echo "ALLOWED_IDS=$admin_ids"
            echo "BOT_LANG=$bot_lang"
        } > "$BOT_DIR/.env"
        chmod 600 "$BOT_DIR/.env"
        log_success "$(t bot_env_created)"
    else
        log_info "$(t bot_env_exists)"
    fi

    # Systemd
    cat > "/etc/systemd/system/${BOT_SERVICE}.service" << SVCEOF
[Unit]
Description=PCAtelegram_web v${PCATELEGRAM_WEB_VERSION} Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/bot.py
Restart=always
RestartSec=5
Environment=PATH=$BOT_DIR/venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable "$BOT_SERVICE" &>/dev/null
    systemctl restart "$BOT_SERVICE" 2>/dev/null || systemctl start "$BOT_SERVICE"

    install_admin_web || log_warning "Web admin could not be installed"

    # If auto mode — wait until bot captures first admin
    local has_ids
    has_ids=$(grep "^ALLOWED_IDS=" "$BOT_DIR/.env" 2>/dev/null | cut -d= -f2)
    if [ -z "$has_ids" ]; then
        echo ""
        # Simple bullet-style block (no box — printf %-Ns breaks on UTF-8 multibyte chars)
        echo -e "  ${YELLOW}▸${NC} ${BOLD}$(t bot_wait_admin_title)${NC}"
        echo ""
        echo -e "    $(t bot_wait_admin_msg1) ${CYAN}/start${NC}"
        echo -e "    $(t bot_wait_admin_msg2)"
        echo ""
        echo -e "    ${DIM}$(t bot_wait_admin_skip)${NC}"
        echo ""

        local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
        local i=0
        local waited=0
        local max_wait=300  # 5 min max

        # Catch Ctrl+C to skip waiting without killing the script
        local interrupted=0
        trap 'interrupted=1' INT

        while [ $waited -lt $max_wait ] && [ $interrupted -eq 0 ]; do
            printf "\r  ${CYAN}${frames[$i]}${NC} $(tf bot_wait_spinner "$waited")  " >&2
            i=$(( (i+1) % ${#frames[@]} ))
            sleep 1
            waited=$((waited + 1))

            # Check if ALLOWED_IDS has appeared
            has_ids=$(grep "^ALLOWED_IDS=" "$BOT_DIR/.env" 2>/dev/null | cut -d= -f2)
            if [ -n "$has_ids" ]; then
                break
            fi
        done

        trap - INT
        printf "\r\033[K" >&2  # clear spinner line

        if [ -n "$has_ids" ]; then
            echo ""
            log_success "$(t bot_admin_assigned)"
            echo -e "  ${WHITE}ID:${NC} ${GREEN}${has_ids}${NC}"
        elif [ $interrupted -eq 1 ]; then
            echo ""
            log_warning "$(t bot_wait_skipped)"
        else
            echo ""
            log_warning "$(t bot_wait_timeout)"
        fi
    fi

    echo ""
    log_success "$(t bot_installed)"
    echo -e "  ${DIM}systemctl status $BOT_SERVICE${NC}"
    echo -e "  ${DIM}journalctl -u $BOT_SERVICE -f${NC}"
}

bot_show_status() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t bot_status_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    systemctl status "$BOT_SERVICE" --no-pager -l 2>/dev/null | head -15 | while IFS= read -r line; do
        echo "  $line"
    done
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"

    if [ -f "$BOT_DIR/.env" ]; then
        local has_token has_ids
        has_token=$(grep -c "BOT_TOKEN=" "$BOT_DIR/.env" 2>/dev/null || echo 0)
        has_ids=$(grep "ALLOWED_IDS=" "$BOT_DIR/.env" 2>/dev/null | cut -d= -f2)
        if [ "${has_token:-0}" -gt 0 ]; then
            echo -e "  $(t bot_token)   ${GREEN}✓ $(t bot_token_configured)${NC}"
        fi
        if [ -n "$has_ids" ]; then
            echo -e "  $(t bot_access_colon)  $(tf bot_access_ids_fmt "$has_ids")"
        else
            echo -e "  $(t bot_access_colon)  ${YELLOW}$(t bot_access_open)${NC}"
        fi
    fi
}

bot_show_logs() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t bot_logs_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    journalctl -u "$BOT_SERVICE" --no-pager -n 30 2>/dev/null | while IFS= read -r line; do
        echo "  $line"
    done
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
}

bot_edit_config() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t bot_settings_title)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"

    if [ -f "$BOT_DIR/.env" ]; then
        echo -e "  ${DIM}$(t bot_current_env)${NC}"
        while IFS= read -r line; do
            # Mask token for security
            if [[ "$line" == BOT_TOKEN=* ]]; then
                local tok="${line#BOT_TOKEN=}"
                echo -e "  BOT_TOKEN=${tok:0:10}...${tok: -5}"
            else
                echo "  $line"
            fi
        done < "$BOT_DIR/.env"
    fi

    echo ""
    echo -e "  ${CYAN}1${NC}) $(t bot_change_token)"
    echo -e "  ${CYAN}2${NC}) $(t bot_change_allowed)"
    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r ch

    case "$ch" in
        1)
            echo -ne "  ${WHITE}$(t bot_new_token)${NC} "
            read -r new_token
            new_token=$(echo "$new_token" | tr -d '[:space:]')
            if [ -n "$new_token" ]; then
                sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$new_token|" "$BOT_DIR/.env"
                systemctl restart "$BOT_SERVICE"
                log_success "$(t bot_token_updated)"
            else
                log_error "$(t bot_token_empty_err)"
            fi
            ;;
        2)
            echo -ne "  ${WHITE}$(t bot_allowed_prompt)${NC} "
            read -r new_ids
            # Normalize: spaces and commas → commas, strip extras
            new_ids=$(echo "$new_ids" | tr ' ' ',' | sed 's/,,*/,/g; s/^,//; s/,$//')
            if grep -q "^ALLOWED_IDS=" "$BOT_DIR/.env" 2>/dev/null; then
                if [ -n "$new_ids" ]; then
                    sed -i "s|^ALLOWED_IDS=.*|ALLOWED_IDS=$new_ids|" "$BOT_DIR/.env"
                else
                    sed -i '/^ALLOWED_IDS=/d' "$BOT_DIR/.env"
                fi
            else
                [ -n "$new_ids" ] && echo "ALLOWED_IDS=$new_ids" >> "$BOT_DIR/.env"
            fi
            systemctl restart "$BOT_SERVICE"
            log_success "$(t bot_access_updated)"
            ;;
    esac
}

bot_remove() {
    echo ""
    log_warning "$(t bot_remove_warn)"
    if ! confirm "$(t bot_remove_confirm)"; then
        return
    fi

    systemctl stop "$BOT_SERVICE" 2>/dev/null
    systemctl disable "$BOT_SERVICE" 2>/dev/null
    rm -f "/etc/systemd/system/${BOT_SERVICE}.service"
    systemctl daemon-reload
    rm -rf "$BOT_DIR"
    log_success "$(t bot_removed)"
}

# ── First-run: pick language ─────────────────────────────────────────────────
first_run_language_picker() {
    # Show picker only if language not yet saved
    local marker="${PCATELEGRAM_WEB_DIR:-/opt/pcatelegram_web}/.language"
    local cfg_lang=""
    if [ -f "$PCATELEGRAM_WEB_CONFIG" ] && command -v jq >/dev/null 2>&1; then
        cfg_lang=$(jq -r '.language // empty' "$PCATELEGRAM_WEB_CONFIG" 2>/dev/null)
    fi
    if [ -f "$marker" ] || [ -n "$cfg_lang" ]; then
        return 0
    fi

    local chosen
    chosen=$(pick_language_interactive)
    save_language "$chosen"
    load_language "$chosen"
}

# ── Change language on demand ────────────────────────────────────────────────
menu_language() {
    echo ""
    echo -e "  ${BOLD}${WHITE}$(t lang_change_prompt)${NC}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..55})${NC}"
    echo -e "  ${CYAN}1${NC}) English"
    echo -e "  ${CYAN}2${NC}) Русский"
    echo -e "  ${CYAN}0${NC}) $(t back)"
    echo -ne "  ${WHITE}$(t choose):${NC} "
    read -r ch
    case "$ch" in
        1) save_language "en"; load_language "en"; log_success "$(tf lang_saved English)" ;;
        2) save_language "ru"; load_language "ru"; log_success "$(tf lang_saved Русский)" ;;
    esac
}

# ══════════════════════════════════════════════════════════════════════════════
# Non-interactive action dispatcher (bot / CI / scripting interface)
# ══════════════════════════════════════════════════════════════════════════════
# Usage examples:
#   pcatelegram_web --action=change-template --template=th_ariclaw --json
#   pcatelegram_web --action=change-lite-domain --domain=google.com --json
#
# Rules for action handlers:
#  - Only JSON may be written to stdout (the caller parses it).
#  - All human-oriented logging must go to stderr (log_* already do that).
#  - Exit code 0 on success, non-zero on failure (caller still parses JSON).
# ══════════════════════════════════════════════════════════════════════════════

bot_emit_json() {
    # bot_emit_json <status> <message> [key=value ...]
    local status="$1"; shift
    local message="$1"; shift
    local extra="" kv k v
    for kv in "$@"; do
        k="${kv%%=*}"
        v="${kv#*=}"
        # escape backslashes and double quotes in value
        v="${v//\\/\\\\}"
        v="${v//\"/\\\"}"
        extra="${extra},\"${k}\":\"${v}\""
    done
    # escape message
    local msg_esc="${message//\\/\\\\}"
    msg_esc="${msg_esc//\"/\\\"}"
    printf '{"status":"%s","message":"%s"%s}\n' "$status" "$msg_esc" "$extra"
}

# Update a single key in config.json without rewriting the whole file.
# Uses `date -Iseconds` rather than jq's `now | todate` — the latter requires
# jq 1.6+ which is not available on Debian 10 or older CentOS.
bot_update_config_field() {
    local key="$1"
    local value="$2"
    if [ ! -f "$PCATELEGRAM_WEB_CONFIG" ]; then
        return 1
    fi
    local tmp now
    tmp=$(mktemp) || return 1
    now=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)
    if jq --arg k "$key" --arg v "$value" --arg t "$now" \
        '.[$k] = $v | .updated_at = $t' \
        "$PCATELEGRAM_WEB_CONFIG" > "$tmp" 2>/dev/null; then
        mv "$tmp" "$PCATELEGRAM_WEB_CONFIG"
        chmod 600 "$PCATELEGRAM_WEB_CONFIG"
        return 0
    fi
    rm -f "$tmp"
    return 1
}

# ── Action: change-template (pro mode only) ──────────────────────────────────
bot_action_change_template() {
    local tpl_id="$1"
    local json_out="${2:-0}"

    if [ -z "$tpl_id" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "template id is required" "code=missing_arg"
        log_error "change-template: --template is required"
        return 2
    fi

    # Must be in pro mode
    local mode
    mode=$(config_get mode 2>/dev/null || echo "")
    if [ "$mode" != "pro" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "change-template requires pro mode (current: ${mode:-none})" "code=wrong_mode"
        log_error "change-template: current mode is '${mode:-none}', requires 'pro'"
        return 3
    fi

    # Validate template id exists in catalog
    if ! get_template_info "$tpl_id" >/dev/null 2>&1; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "unknown template: $tpl_id" "code=unknown_template"
        log_error "change-template: template not found in catalog: $tpl_id"
        return 4
    fi

    # Make sure git (and other deps) are present. download_template uses git
    # clone under the hood — on a minimal host (bootstrap-only install) git may
    # not be installed yet, and the clone would fail silently.
    ensure_deps >&2

    log_info "change-template: downloading $tpl_id..."
    local template_dir
    template_dir=$(download_template "$tpl_id")
    if [ $? -ne 0 ] || [ -z "$template_dir" ] || [ ! -d "$template_dir" ] || [ ! -f "$template_dir/index.html" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "download failed for $tpl_id" "code=download_failed"
        log_error "change-template: download_template failed for $tpl_id"
        return 5
    fi

    log_info "change-template: deploying to nginx..."
    if ! deploy_template_to_nginx "$template_dir" >&2; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "deploy failed" "code=deploy_failed"
        return 6
    fi

    # Reload nginx (no full restart needed for static files — but be safe)
    systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null

    # Update config.json template_id field
    bot_update_config_field "template_id" "$tpl_id" || \
        log_warning "change-template: could not update config.json template_id"

    local domain
    domain=$(config_get domain 2>/dev/null || echo "")
    log_success "change-template: $tpl_id deployed"

    if [ "$json_out" = "1" ]; then
        bot_emit_json "success" "template changed to $tpl_id" \
            "template=$tpl_id" "domain=$domain" "mode=pro"
    fi
    return 0
}

# ── Action: change-lite-domain ───────────────────────────────────────────────
# Regenerates telemt TOML with a new fake-TLS mask domain. Lite mode only.
bot_action_change_lite_domain() {
    local new_domain="$1"
    local json_out="${2:-0}"

    if [ -z "$new_domain" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "domain is required" "code=missing_arg"
        log_error "change-lite-domain: --domain is required"
        return 2
    fi

    if ! validate_domain "$new_domain" 2>/dev/null; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "invalid domain: $new_domain" "code=invalid_domain"
        log_error "change-lite-domain: invalid domain: $new_domain"
        return 3
    fi

    local mode
    mode=$(config_get mode 2>/dev/null || echo "")
    if [ "$mode" != "lite" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "change-lite-domain requires lite mode (current: ${mode:-none})" "code=wrong_mode"
        log_error "change-lite-domain: current mode is '${mode:-none}', requires 'lite'"
        return 4
    fi

    local secret port
    secret=$(get_config_value secret 2>/dev/null || echo "")
    port=$(get_config_value port 2>/dev/null || echo "443")

    if [ -z "$secret" ]; then
        [ "$json_out" = "1" ] && bot_emit_json "error" "no secret in config" "code=no_secret"
        log_error "change-lite-domain: no secret in config.json"
        return 5
    fi

    log_info "change-lite-domain: regenerating telemt TOML..."
    generate_telemt_toml "$secret" "$port" "lite" "$new_domain" "443" >&2 || {
        [ "$json_out" = "1" ] && bot_emit_json "error" "config generation failed" "code=gen_failed"
        return 6
    }

    validate_telemt_config >&2 || {
        [ "$json_out" = "1" ] && bot_emit_json "error" "config validation failed" "code=validate_failed"
        return 7
    }

    restart_telemt >&2 || {
        [ "$json_out" = "1" ] && bot_emit_json "error" "telemt restart failed" "code=restart_failed"
        return 8
    }

    # Update both domain and mask_host fields in config.json
    bot_update_config_field "mask_host" "$new_domain" || \
        log_warning "change-lite-domain: could not update mask_host"
    bot_update_config_field "domain" "$new_domain" || \
        log_warning "change-lite-domain: could not update domain"

    log_success "change-lite-domain: switched to $new_domain"

    if [ "$json_out" = "1" ]; then
        bot_emit_json "success" "lite mask domain changed to $new_domain" \
            "domain=$new_domain" "mode=lite" "port=$port"
    fi
    return 0
}

# Main dispatcher — called from main() when --action=X is present.
# Uses a file lock (flock) so concurrent CLI invocations (from multiple bot
# users, or from bot + manual CLI) serialize cleanly. Without this, two
# parallel `change-lite-domain` calls raced on the jq-rewrite of config.json
# and one process would see a truncated file ("no secret in config").
bot_action_dispatch() {
    local lock_file="/var/lock/pcatelegram_web-bot-action.lock"
    # Make sure /var/lock exists (it does on Debian/Ubuntu; be defensive for minimal images)
    [ -d /var/lock ] || mkdir -p /var/lock 2>/dev/null || true

    if command -v flock >/dev/null 2>&1; then
        # Wait up to 30 seconds for the lock — bot actions are fast (<5s
        # typical), so 30s is plenty for legitimate serialization but short
        # enough to surface a stuck process.
        (
            flock -w 30 9 || {
                # If we time out, emit JSON error for the bot parent.
                local json_out=0 a
                for a in "$@"; do
                    [ "$a" = "--json" ] && json_out=1
                done
                if [ "$json_out" = "1" ]; then
                    bot_emit_json "error" "another action in progress (lock timeout)" "code=lock_timeout"
                fi
                exit 75  # EX_TEMPFAIL
            }
            _bot_action_dispatch_locked "$@"
        ) 9>"$lock_file"
        return $?
    else
        # No flock installed — run unlocked with a warning. ensure_deps/check_deps
        # normally ensures util-linux is present, so this branch is defensive.
        log_warning "flock not available — bot actions not serialized"
        _bot_action_dispatch_locked "$@"
        return $?
    fi
}

_bot_action_dispatch_locked() {
    local action="" tpl_id="" domain="" json_out=0 arg
    for arg in "$@"; do
        case "$arg" in
            --action=*)   action="${arg#--action=}" ;;
            --template=*) tpl_id="${arg#--template=}" ;;
            --domain=*)   domain="${arg#--domain=}" ;;
            --json)       json_out=1 ;;
        esac
    done

    case "$action" in
        change-template)
            bot_action_change_template "$tpl_id" "$json_out"
            return $?
            ;;
        change-lite-domain)
            bot_action_change_lite_domain "$domain" "$json_out"
            return $?
            ;;
        "")
            log_error "no --action specified"
            return 64
            ;;
        *)
            [ "$json_out" = "1" ] && bot_emit_json "error" "unknown action: $action" "code=unknown_action"
            log_error "unknown action: $action"
            return 64
            ;;
    esac
}

# ── Точка входа / Entry point ───────────────────────────────────────────────
main() {
    # Non-interactive action mode: if --action=X is in args, dispatch and exit.
    # Must run BEFORE interactive banner/menus so the bot gets clean JSON.
    local a has_action=0
    for a in "$@"; do
        case "$a" in --action=*) has_action=1; break ;; esac
    done
    if [ "$has_action" = "1" ]; then
        check_root
        init_dirs
        # Для bot-экшенов тоже нужны зависимости (git для change-template), но
        # без шумного apt-get update если всё уже на месте.
        if ! check_deps_present; then
            ensure_deps >&2 || exit 1
        fi
        auto_migrate_legacy_state >&2 || true
        bot_action_dispatch "$@"
        exit $?
    fi

    check_root
    init_dirs

    # Первый запуск: если критические зависимости отсутствуют — ставим их ДО
    # того как пользователь дойдёт до меню. На последующих запусках это просто
    # дёшево проверяет command -v по всем командам и ничего не делает.
    if ! check_deps_present; then
        log_step "Первый запуск: проверяю зависимости..."
        ensure_deps || {
            log_error "Не удалось установить зависимости. См. сообщения выше."
            exit 1
        }
    fi

    auto_migrate_legacy_state || true
    auto_update_bot_if_possible || true
    auto_install_admin_web_if_possible || true

    # First-run language picker (before banner so banner appears in chosen lang)
    first_run_language_picker

    show_banner

    # Pre-flight
    check_os
    check_disk_space 500

    while true; do
        clear
        show_main_menu
        # Auto-refresh: 30 sec timeout
        if read -t 30 -r choice; then
            case "$choice" in
                1) submenu_proxy ;;
                2) submenu_stats ;;
                3) submenu_manage ;;
                4) menu_bot ;;
                5) submenu_about ;;
                0|q|exit) echo ""; log_info "$(t bye)"; exit 0 ;;
                *)  log_error "$(t invalid_choice)" ;;
            esac

            # Pause after submenu (except stats — it has its own loop)
            if [ "$choice" != "2" ]; then
                echo ""
                echo -ne "  ${DIM}$(t press_enter_to_return)${NC}"
                read -r
            fi
        fi
        # If read timed out, loop refreshes the dashboard
    done
}

# ── Статистика (авто-обновление 1 сек, без мерцания) ───────────────────────
submenu_stats() {
    # Инициализируем статистику при первом входе
    if type stats_init &>/dev/null; then
        stats_init 2>/dev/null
    fi

    local line2; line2=$(printf '─%.0s' {1..54})
    local first_draw=1

    # Скрываем курсор для плавного обновления
    tput civis 2>/dev/null

    # Восстанавливаем курсор при выходе из функции
    trap 'tput cnorm 2>/dev/null; trap - RETURN' RETURN

    while true; do
        if [ "$first_draw" -eq 1 ]; then
            clear
            first_draw=0
        else
            # Перемещаем курсор в начало экрана вместо clear — нет мерцания
            tput cup 0 0 2>/dev/null || printf '\033[H'
        fi

        # Draw the whole screen over the previous content
        echo -e "\033[J"  # erase from cursor to end (removes trails)
        echo -e "  ${BOLD}${WHITE}$(t stats_title)${NC}"
        echo -e "  ${DIM}${line2}${NC}"

        if type show_traffic_stats &>/dev/null; then
            show_traffic_stats
        else
            echo -e "  ${DIM}$(t stats_module_missing)${NC}"
            echo -e "  ${DIM}$(t stats_file_missing)${NC}"
            echo ""
        fi

        echo -e "  ${DIM}${line2}${NC}"
        local stats_on
        stats_on=$(t stats_on)
        if type toggle_stats &>/dev/null; then
            local cfg_val
            cfg_val=$(config_get stats_enabled 2>/dev/null || echo "true")
            [ "$cfg_val" = "false" ] && stats_on=$(t stats_off)
        fi
        echo -e "  ${CYAN}1${NC}) $(tf stats_toggle "$stats_on")"
        echo -e "  ${CYAN}2${NC}) $(t stats_install_collector)"
        echo -e "  ${CYAN}0${NC}) ${DIM}$(t back)${NC}"
        echo -e "  ${DIM}${line2}${NC}"
        echo -e "  ${DIM}$(t stats_auto_refresh)${NC}"

        # Show cursor for input, then hide again
        tput cnorm 2>/dev/null
        echo -ne "  ${WHITE}▸ ${NC}"

        if read -t 3 -r ch; then
            tput civis 2>/dev/null
            case "$ch" in
                1)
                    if type toggle_stats &>/dev/null; then
                        toggle_stats
                        echo -ne "  ${DIM}$(t press_enter)${NC}"; read -r
                        first_draw=1  # full redraw after action
                    fi
                    ;;
                2)
                    if type install_stats_collector &>/dev/null; then
                        install_stats_collector
                        echo -ne "  ${DIM}$(t press_enter)${NC}"; read -r
                        first_draw=1
                    fi
                    ;;
                0|"") return ;;
            esac
        fi
        tput civis 2>/dev/null
    done
}

main "$@"
