# my-vpn

Утилита для ручного управления VPN через Shadowsocks (`sslocal`) + `tun2socks`.

Важно: команды `start/stop` меняют маршруты и поднимают TUN-интерфейс. Используй осознанно — можно “уронить” сеть.

## Быстрый старт

1) Конфиг:

```bash
cp .env.example .env
$EDITOR .env
```

По умолчанию `.env` ищется вверх от текущей директории. Если запускаешь не из корня репозитория — укажи явно:

```bash
uv run my-vpn --env-file /path/to/.env status
```

2) Зависимости (portable user-space, без sudo):

```bash
uv sync
uv run my-vpn install-deps
```

По умолчанию бинарники кладутся в `~/.local/share/my-vpn/bin` (или `$XDG_DATA_HOME/my-vpn/bin`).
Можно переопределить через `MY_VPN_BIN_DIR`.

3) Запуск (нужен root для сети/маршрутов):

```bash
uv run my-vpn start
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
