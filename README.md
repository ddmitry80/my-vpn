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
uv run python -m vpn_cli.main install-deps
```

По умолчанию бинарники кладутся в `~/.local/share/my-vpn/bin` (или `$XDG_DATA_HOME/my-vpn/bin`).
Можно переопределить через `MY_VPN_BIN_DIR`.

3) Запуск (нужен root для сети/маршрутов):

```bash
sudo $(uv run which python) -m vpn_cli.main start
```

## Команды

- `python -m vpn_cli.main install-deps` — скачать `sslocal` и `tun2socks` в user-space
- `sudo python -m vpn_cli.main start` — запустить VPN
- `sudo python -m vpn_cli.main stop` — остановить VPN
- `python -m vpn_cli.main status` — состояние интерфейса/процессов/путей

## Логи

- `sslocal`: `/tmp/my-vpn-sslocal.log`
- `tun2socks`: `/tmp/my-vpn-tun2socks.log`

