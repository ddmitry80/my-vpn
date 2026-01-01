#!/bin/bash
# Файл: run.sh
# Быстрый запуск с sudo и подтягиванием окружения uv

set -euo pipefail

# 1) Устанавливаем portable-бинарники в user-space (без sudo)
uv run python -m vpn_cli.main install-deps

# 2) Стартуем VPN (нужен root для ip/tun/route)
sudo $(uv run which python) -m vpn_cli.main start
