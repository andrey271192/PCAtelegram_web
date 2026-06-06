# Security

## Secrets

Do not commit real tokens, passwords, WARP+ keys, Telegram bot tokens, proxy secrets, backup passwords, or VPS credentials.

Runtime secrets live on server:

- `/root/pcatelegram_web-admin.password`
- `/opt/pcatelegram_web/config.json`
- `/opt/pcatelegram_web/warp.json`
- `/opt/pcatelegram_web-bot/.env`
- `/etc/telemt/config.toml`

Important permissions:

- auth file: `0600`
- WARP config: `0600`
- bot `.env`: `0600`
- telemt config: `0600`

## Web Admin

Default install uses `admin` / `admin`. Change it in web-admin Settings after first login.

Admin session cookie is `HttpOnly`, `SameSite=Lax`, and gains `Secure` when request comes through HTTPS reverse proxy via `X-Forwarded-Proto: https` or `X-Forwarded-Ssl: on`.

Write APIs require `X-PCAtelegram-Web-Admin: 1` and JSON content type. Responses include security headers: CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy`.

## Public Site On Port 80

Uploaded HTML is served publicly. Do not upload files with secrets, internal URLs, API tokens, private notes, or admin links.

## Backups

Backups can include proxy keys, WARP config, bot state, SSL files, admin panel files, and traffic history. Use encrypted backups for transport or off-server storage.

## Reporting

Report security issues privately to project owner. Do not open public issues with secrets or working exploit details.
