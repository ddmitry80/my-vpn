# AGENTS.md

Инструкции для Codex при работе с репозиторием `my-vpn/`.

## Проект

- Python CLI утилита для управления VPN через `sslocal` (shadowsocks-rust) + `tun2socks`.
- Конфиг через `.env` (`SS_URL=...`), пример в `.env.example`.
- Portable user-space бинарники по умолчанию в `~/.local/share/my-vpn/bin` (или `$XDG_DATA_HOME/my-vpn/bin`), override: `MY_VPN_BIN_DIR`.

## Команды (локально)

- Установка Python зависимостей: `uv sync`
- Проверка CLI справки: `uv run python -m vpn_cli.main --help`
- Скачать `sslocal`/`tun2socks` (нужен интернет): `uv run python -m vpn_cli.main install-deps`
- Запуск (меняет маршруты/создаёт TUN, нужен root): `sudo $(uv run which python) -m vpn_cli.main start`
- Остановка (нужен root): `sudo $(uv run which python) -m vpn_cli.main stop`

## Безопасность и поведение агента

- Не запускать `start/stop` без явного запроса пользователя: команды меняют сетевые маршруты и могут “уронить” сеть.
- Не скачивать бинарники/зависимости без явного запроса пользователя: `install-deps` требует сетевого доступа и скачивает исполняемые файлы.
- При правках CLI сохранять совместимость с текущими командами: `install-deps`, `start`, `stop`, `status`.

## Стиль изменений

- Делать правки минимально и по делу, не трогать `old_scripts/` без необходимости (это исторические артефакты).
- Новую документацию добавлять в `README.md`, не дублировать большие блоки в коде.

