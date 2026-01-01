# my-vpn

Утилита для ручного управления VPN через Shadowsocks (`sslocal`) + `tun2socks`.

## Быстрый старт

1) Конфиг:

```bash
cp .env.example .env
$EDITOR .env
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

## Логи

- `sslocal`: `/tmp/my-vpn-sslocal.log`
- `tun2socks`: `/tmp/my-vpn-tun2socks.log`
