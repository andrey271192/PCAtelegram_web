#!/bin/bash
# GoTelegram v2.5.0 — Управление сайтом (nginx + certbot + шаблоны)

# ── Установка nginx ──────────────────────────────────────────────────────────
install_nginx() {
    if command -v nginx &>/dev/null; then
        log_dim "nginx уже установлен"
        return 0
    fi
    log_info "Установка nginx..."
    case "$(get_pkg_manager)" in
        apt) apt_update && apt_install nginx || return 1 ;;
        dnf) dnf install -y -q nginx || return 1 ;;
        yum) yum install -y -q nginx || return 1 ;;
    esac
    systemctl enable nginx 2>/dev/null
}

# ── Установка certbot ────────────────────────────────────────────────────────
install_certbot() {
    if command -v certbot &>/dev/null; then
        log_dim "certbot уже установлен"
        return 0
    fi
    log_info "Установка certbot..."
    case "$(get_pkg_manager)" in
        apt) apt_install certbot python3-certbot-nginx || return 1 ;;
        dnf) dnf install -y -q certbot python3-certbot-nginx || return 1 ;;
        yum) yum install -y -q certbot python3-certbot-nginx || return 1 ;;
    esac
}

# ── Генерация nginx конфига ──────────────────────────────────────────────────
generate_nginx_config() {
    local domain="$1"
    local proxy_port="${2:-443}"
    local use_ssl="${3:-true}"

    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

    cat > "$NGINX_SITE_CONF" << 'EONGINX'
# GoTelegram v2.5.0 — nginx config
# Pro: nginx на 127.0.0.1:8443 (внутренний), telemt на 0.0.0.0:443 (внешний)
# Обычный браузер → :443 → telemt → 127.0.0.1:8443 → nginx (сайт)

server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 127.0.0.1:SSL_PORT_PLACEHOLDER ssl http2;
    server_name DOMAIN_PLACEHOLDER;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;

    # Современные TLS настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Корень сайта
    root /var/www/gotelegram-site;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
        expires 30d;
    }

    # Кеширование статики
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Скрываем служебные файлы
    location ~ /\. { deny all; }
    location = /robots.txt { allow all; log_not_found off; access_log off; }
    location = /favicon.ico { log_not_found off; access_log off; }
}
EONGINX

    # Подставляем значения (используем | как разделитель, чтобы / в домене не ломал sed)
    local escaped_domain
    escaped_domain=$(printf '%s\n' "$domain" | sed 's/[&/\]/\\&/g')
    sed -i "s|DOMAIN_PLACEHOLDER|${escaped_domain}|g" "$NGINX_SITE_CONF"
    sed -i "s|SSL_PORT_PLACEHOLDER|${proxy_port}|g" "$NGINX_SITE_CONF"

    # Активируем сайт
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null
    ln -sf "$NGINX_SITE_CONF" "$NGINX_SITE_LINK"

    log_success "nginx конфиг создан для $domain"
}

# ── Временный конфиг (до получения SSL) ──────────────────────────────────────
generate_nginx_temp_config() {
    local domain="$1"

    cat > "$NGINX_SITE_CONF" << EONGINX_TEMP
# GoTelegram — временный конфиг (до получения SSL)
server {
    listen 80;
    listen [::]:80;
    server_name ${domain};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }

    root /var/www/gotelegram-site;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EONGINX_TEMP

    rm -f /etc/nginx/sites-enabled/default 2>/dev/null
    ln -sf "$NGINX_SITE_CONF" "$NGINX_SITE_LINK"
    mkdir -p /var/www/certbot
}

# ── Получение SSL сертификата ────────────────────────────────────────────────
obtain_ssl_certificate() {
    local domain="$1"
    local email="${2:-}"

    if [ ! -d "/etc/letsencrypt/live/$domain" ]; then
        log_info "Получение SSL сертификата для $domain..."

        # Временный конфиг для ACME challenge
        generate_nginx_temp_config "$domain"
        systemctl restart nginx 2>/dev/null

        local certbot_args=(
            certonly
            --webroot
            -w /var/www/certbot
            -d "$domain"
            --non-interactive
            --agree-tos
        )

        if [ -n "$email" ]; then
            certbot_args+=(--email "$email")
        else
            certbot_args+=(--register-unsafely-without-email)
        fi

        if certbot "${certbot_args[@]}" 2>/dev/null; then
            log_success "SSL сертификат получен для $domain"
            return 0
        else
            log_error "Не удалось получить SSL сертификат"
            log_dim "Убедитесь что домен $domain направлен на IP этого сервера"
            log_dim "и порт 80 открыт в файрволе."
            return 1
        fi
    else
        log_dim "SSL сертификат уже существует для $domain"
        return 0
    fi
}

# ── Авто-обновление сертификата ──────────────────────────────────────────────
setup_ssl_auto_renewal() {
    # Certbot systemd timer (предпочтительно)
    if [ -f /etc/systemd/system/certbot.timer ] || [ -f /lib/systemd/system/certbot.timer ]; then
        systemctl enable certbot.timer 2>/dev/null
        systemctl start certbot.timer 2>/dev/null
        log_success "Авто-обновление SSL через systemd timer"
        return 0
    fi

    # Fallback: cron
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
        log_success "Авто-обновление SSL через cron (3:00 ежедневно)"
    fi
}

# ── Обновление сертификата вручную ───────────────────────────────────────────
renew_ssl_certificate() {
    log_info "Обновление SSL сертификата..."
    if certbot renew --quiet --post-hook "systemctl reload nginx" 2>/dev/null; then
        log_success "Сертификат обновлён"
        return 0
    else
        log_error "Ошибка обновления сертификата"
        return 1
    fi
}

# ── Дата истечения SSL ───────────────────────────────────────────────────────
get_ssl_expiry() {
    local domain="$1"
    local cert="/etc/letsencrypt/live/$domain/fullchain.pem"
    if [ -f "$cert" ]; then
        openssl x509 -enddate -noout -in "$cert" 2>/dev/null | sed 's/notAfter=//'
    else
        echo "N/A"
    fi
}

# ── Деплой шаблона сайта ─────────────────────────────────────────────────────
deploy_template_to_nginx() {
    local template_dir="$1"
    local template_id="${2:-}"
    local source_url=""

    if [ ! -d "$template_dir" ] || [ ! -f "$template_dir/index.html" ]; then
        log_error "Шаблон не содержит index.html: $template_dir"
        return 1
    fi
    [ -z "$template_id" ] && template_id=$(basename "$template_dir")
    [ -f "$template_dir/.custom_git_source" ] && source_url=$(head -1 "$template_dir/.custom_git_source" 2>/dev/null || echo "")

    # Бекапим старый сайт
    if [ -d "$WEBSITE_ROOT" ] && [ "$(ls -A "$WEBSITE_ROOT" 2>/dev/null)" ]; then
        local backup_name="site_backup_$(date +%Y%m%d_%H%M%S)"
        mv "$WEBSITE_ROOT" "/tmp/$backup_name" 2>/dev/null
        log_dim "Старый сайт сохранён в /tmp/$backup_name"
    fi

    mkdir -p "$WEBSITE_ROOT"
    cp -a "$template_dir/." "$WEBSITE_ROOT/"
    rm -f "$WEBSITE_ROOT/.custom_git_source" 2>/dev/null || true
    echo "$template_id" > "$WEBSITE_ROOT/.gotelegram_template_id" 2>/dev/null || true
    [ -n "$source_url" ] && echo "$source_url" > "$WEBSITE_ROOT/.gotelegram_template_source" 2>/dev/null || true
    chown -R www-data:www-data "$WEBSITE_ROOT" 2>/dev/null || chown -R nginx:nginx "$WEBSITE_ROOT" 2>/dev/null
    chmod -R 755 "$WEBSITE_ROOT"

    log_success "Шаблон развёрнут в $WEBSITE_ROOT"
}

# ── Полная установка pro-режима ──────────────────────────────────────────────
setup_pro_mode() {
    local domain="$1"
    local template_dir="$2"
    local proxy_port="${3:-443}"
    local email="${4:-}"

    log_step "Настройка pro-режима"

    # 1. Устанавливаем nginx
    run_with_spinner "Установка nginx" install_nginx || return 1

    # 2. Устанавливаем certbot
    run_with_spinner "Установка certbot" install_certbot || return 1

    # 3. Деплоим шаблон сайта
    deploy_template_to_nginx "$template_dir" || return 1

    # 4. Получаем SSL
    obtain_ssl_certificate "$domain" "$email" || return 1

    # 5. Генерируем полный nginx конфиг с SSL
    generate_nginx_config "$domain" "$proxy_port"

    # 6. Тестируем и перезапускаем nginx
    if nginx -t 2>/dev/null; then
        systemctl restart nginx
        log_success "nginx запущен с SSL"
    else
        log_error "Ошибка в конфигурации nginx"
        nginx -t
        return 1
    fi

    # 7. Настраиваем авто-обновление SSL
    setup_ssl_auto_renewal

    # 8. Показываем благодарности авторам шаблонов
    show_credits

    log_success "Pro-режим настроен: https://${domain}"
    return 0
}

# ── Управление nginx ────────────────────────────────────────────────────────
nginx_status() {
    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo "running"
    else
        echo "stopped"
    fi
}

restart_nginx() {
    if nginx -t 2>/dev/null; then
        systemctl restart nginx 2>/dev/null
        log_success "nginx перезапущен"
    else
        log_error "Ошибка конфигурации nginx"
        nginx -t
        return 1
    fi
}

# ── Удаление pro-режима ──────────────────────────────────────────────────────
remove_pro_mode() {
    log_info "Удаление pro-режима..."
    rm -f "$NGINX_SITE_CONF" "$NGINX_SITE_LINK"
    rm -rf "$WEBSITE_ROOT"
    systemctl restart nginx 2>/dev/null
    log_success "Pro-режим удалён (nginx оставлен)"
}

# ── Смена шаблона ────────────────────────────────────────────────────────────
switch_template() {
    local new_template_dir="$1"
    deploy_template_to_nginx "$new_template_dir" "$(basename "$new_template_dir")"
    # nginx не требует перезапуска — статика обновилась на месте
    log_success "Шаблон сайта обновлён"
}
