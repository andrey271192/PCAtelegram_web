# Changelog

## Unreleased

- Added CI sanity checks for Python, JavaScript, shell scripts, and JSON files.
- Added admin security headers and JSON content-type enforcement.
- Stopped putting web-admin password into systemd environment; admin now reads root-only auth file.
- Added public site manager for port 80 with install, remove, and custom HTML upload.
- Added README docs for custom domain and public site flow.

## 2.5.0

- Web-admin for PCAtelegram_web with keys, traffic, backups, WARP settings, routing, and service controls.
- Default web-admin login is `admin` / `admin`, changeable from Settings.
- Auto-refresh avoids overwriting active form input.
