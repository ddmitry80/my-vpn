#!/bin/bash

echo "[1/2] Останавливаем процессы..."
sudo pkill sslocal
sudo pkill tun2socks

echo "[2/2] Удаляем интерфейс tun0..."
# Удаление интерфейса автоматически удалит и маршруты, связанные с ним
sudo ip link delete tun0 2>/dev/null

echo "Готово! VPN выключен, работаем напрямую."
echo "IP: $(curl -s --max-time 2 ifconfig.me)"

