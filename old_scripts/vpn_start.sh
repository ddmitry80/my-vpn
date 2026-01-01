#!/bin/bash

set -euo pipefail

# ================= НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ =================
# SS_URL храните в .env (он в .gitignore) или передавайте через окружение.
# Пример: SS_URL='ss://....' sudo -E ./old_scripts/vpn_start.sh
# ==========================================================

SOCKS_PORT=1080
TUN_DEV="tun0"
TUN_ADDR="10.255.0.2/24"

# Подгружаем .env (если SS_URL не задан снаружи)
if [ -z "${SS_URL:-}" ]; then
  SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
  ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"

  if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
fi

if [ -z "${SS_URL:-}" ]; then
  echo "Ошибка: SS_URL не задан. Укажи SS_URL в .env или передай как переменную окружения."
  exit 1
fi

# 1. Проверка на root
if [ "$EUID" -ne 0 ]; then
  echo "Ошибка: Для настройки сети нужны права root."
  exit 1
fi

echo "[1/4] Парсинг конфигурации и DNS-резолв..."

export RAW_SS_URL="$SS_URL"

# Читаем 5 переменных, включая IP сервера
read -r SERVER SERVER_PORT METHOD PASSWORD SERVER_IP <<< $(python3 <<'EOF'
import os
import sys
import base64
import socket

url = os.environ.get('RAW_SS_URL', '')

try:
    if not url: raise ValueError("URL пуст")
    if url.startswith('ss://'): url = url[5:]
    if '#' in url: url = url.split('#')[0]
    if '?' in url: url = url.split('?')[0]
    if url.endswith('/'): url = url[:-1]

    if '@' not in url: raise ValueError("Неверный формат ss:// (нет @)")

    userinfo, host_port = url.rsplit('@', 1)
    host, port = host_port.split(':')

    # Декодируем Base64
    userinfo += '=' * (-len(userinfo) % 4)
    decoded_str = base64.b64decode(userinfo, validate=True).decode('utf-8')
    method, password = decoded_str.split(':', 1)

    # === НОВОЕ: Резолвим IP адрес сервера ===
    # Это нужно для команды ip route, которая не понимает домены
    try:
        server_ip = socket.gethostbyname(host)
    except socket.gaierror:
        # Если не удалось узнать IP, вернем хост (скрипт упадет дальше, но с понятной ошибкой)
        server_ip = host

    # Вывод: ХОСТ ПОРТ МЕТОД ПАРОЛЬ IP
    print(f"{host} {port} {method} {password} {server_ip}")

except Exception as e:
    sys.stderr.write(f"Python Error: {str(e)}\n")
    sys.exit(1)
EOF
)

if [ $? -ne 0 ]; then
    echo "КРИТИЧЕСКАЯ ОШИБКА: Сбой парсинга."
    exit 1
fi

echo "      Сервер (DNS): $SERVER"
echo "      Сервер (IP):  $SERVER_IP"
echo "      Метод:        $METHOD"

echo "[2/4] Запуск Shadowsocks (Rust)..."
# Очистка порта с проверкой (fix from previous step)
if ss -lptn | grep -q ":$SOCKS_PORT "; then
    fuser -k -TERM "$SOCKS_PORT/tcp" > /dev/null 2>&1
    sleep 1
fi

sslocal \
    -s "$SERVER:$SERVER_PORT" \
    -m "$METHOD" \
    -k "$PASSWORD" \
    -b "127.0.0.1:$SOCKS_PORT" \
    -U \
    > /tmp/ss.log 2>&1 &

sleep 1

if ! pgrep -f "sslocal.*$SOCKS_PORT" > /dev/null; then
    echo "ОШИБКА: sslocal не запустился. Лог:"
    cat /tmp/ss.log
    exit 1
fi

echo "[3/4] Настройка интерфейса $TUN_DEV..."
ip link delete $TUN_DEV 2>/dev/null || true
ip tuntap add dev $TUN_DEV mode tun
ip addr add $TUN_ADDR dev $TUN_DEV
ip link set dev $TUN_DEV up

echo "[4/4] Запуск Tun2Socks и маршрутизация..."
pkill -f "tun2socks.*$TUN_DEV" || true

tun2socks -device $TUN_DEV -proxy socks5://127.0.0.1:$SOCKS_PORT > /tmp/tun.log 2>&1 &
sleep 1

# Настройка маршрутов
ORIGINAL_GW=$(ip route show default | awk '/default/ {print $3}')

if [ -z "$ORIGINAL_GW" ]; then
    echo "Внимание: Не найден шлюз по умолчанию."
else
    # === ИСПРАВЛЕНИЕ: Используем IP, а не домен ===
    echo "      Фиксация маршрута до $SERVER_IP через $ORIGINAL_GW"
    ip route add $SERVER_IP via $ORIGINAL_GW || true
fi

ip route add 0.0.0.0/1 dev $TUN_DEV || true
ip route add 128.0.0.0/1 dev $TUN_DEV || true

MY_IP=$(curl -s --max-time 3 ifconfig.me || true)
echo "=========================================="
if [ -z "$MY_IP" ]; then
    echo "ВНИМАНИЕ: IP не определен. Возможно, нет интернета."
else
    echo "УСПЕХ! VPN подключен."
    echo "Ваш новый IP: $MY_IP"
fi
echo "=========================================="
