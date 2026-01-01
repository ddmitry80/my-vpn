#!/bin/bash
# Файл: run.sh
# Быстрый запуск с sudo и подтягиванием окружения uv

set -euo pipefail

# 1) Устанавливаем portable-бинарники в user-space (без sudo)
uv run my-vpn install-deps

# 2) Стартуем VPN (нужен root для ip/tun/route, утилита перезапустится через sudo сама)
uv run my-vpn start
