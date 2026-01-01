# my-vpn

Утилита для ручного управления VPN через Shadowsocks (`sslocal`) + `tun2socks`.

Важно: команды `start/stop` меняют маршруты и поднимают TUN-интерфейс. Используй осознанно — можно “уронить” сеть.

## Быстрый старт

1) Конфиг:

```bash
mkdir -p ~/.config/my-vpn
cp .env.example ~/.config/my-vpn/.env
$EDITOR ~/.config/my-vpn/.env
```

По умолчанию `my-vpn` читает конфиг из `$XDG_CONFIG_HOME/my-vpn/.env` (или `~/.config/my-vpn/.env`), а если файла нет — ищет `.env` вверх от текущей директории.
Можно переопределить через `--env-file /path/to/.env` или env `MY_VPN_ENV_FILE=/path/to/.env`.

```bash
my-vpn --env-file /path/to/.env status
```

2) Установка CLI (чтобы `my-vpn` работал из любого места):

```bash
uv tool install -e .
```

Для разработки в репозитории можно использовать: `uv sync` и `uv run my-vpn ...`.

3) Зависимости (portable user-space, без sudo):

```bash
my-vpn install-deps
```

По умолчанию бинарники кладутся в `~/.local/share/my-vpn/bin` (или `$XDG_DATA_HOME/my-vpn/bin`).
Можно переопределить через `MY_VPN_BIN_DIR`.

4) Запуск (нужен root для сети/маршрутов):

```bash
my-vpn start
```

## Команды

- `my-vpn install-deps` — скачать `sslocal` и `tun2socks` в user-space
- `my-vpn start` — запустить VPN (если нужен root, утилита сама перезапустится через `sudo`)
- `my-vpn stop` — остановить VPN (если нужен root, утилита сама перезапустится через `sudo`)
- `my-vpn status` — состояние интерфейса/процессов/путей

Если используешь `uv`, просто добавь префикс: `uv run my-vpn ...`.

## Историческое

- `old_scripts/` — старые bash-скрипты (`vpn_start.sh`, `vpn_stop.sh`, …). Сейчас они считаются reference/архивом: могут быть неактуальны и не поддерживаются наравне с CLI.
- `old_thouts.md` — черновые заметки/история появления текущей реализации.

## Логи

- `sslocal`: `/tmp/my-vpn-sslocal.log`
- `tun2socks`: `/tmp/my-vpn-tun2socks.log`
