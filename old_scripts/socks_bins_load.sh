#!/bin/bash

set -e  # Останавливаем скрипт при любой ошибке

echo "=== Логирование для диагностики ==="
echo "Текущая директория: $(pwd)"
echo "Пользователь: $(whoami)"
echo ""

# shadowsocks-rust
echo "[1] Скачивание shadowsocks-rust..."
wget https://github.com/shadowsocks/shadowsocks-rust/releases/download/v1.24.0/shadowsocks-v1.24.0.x86_64-unknown-linux-gnu.tar.xz
echo "  ✓ Архив скачан"
echo ""

# Распаковываем
echo "[2] Распаковка shadowsocks..."
tar -xf shadowsocks-v1.24.0.x86_64-unknown-linux-gnu.tar.xz
echo "  ✓ Архив распакован"
echo ""

# Проверяем, что файл sslocal существует
echo "[3] Проверка наличия файла sslocal..."
if [ -f "sslocal" ]; then
    echo "  ✓ Файл sslocal найден в текущей директории"
    ls -lh sslocal
else
    echo "  ✗ ОШИБКА: Файл sslocal НЕ найден!"
    echo "  Содержимое текущей директории:"
    ls -la
    echo ""
    echo "  Поиск sslocal в подпапках:"
    find . -name "sslocal" -type f 2>/dev/null || echo "    Не найден"
    exit 1
fi
echo ""

# Кладем в папку /usr/local/bin, чтобы запускать отовсюду
echo "[4] Копирование sslocal в /usr/local/bin..."
sudo cp sslocal /usr/local/bin/
echo "  ✓ sslocal скопирован"
sudo chmod +x /usr/local/bin/sslocal
echo "  ✓ Права выполнения установлены"
echo ""

# Поднятие socks proxy
#sslocal -b 127.0.0.1:1080 -U "ss://ВАША_ДЛИННАЯ_СТРОКА_ОТ_КОЛЛЕГИ"

# tun2socks
echo "[5] Скачивание tun2socks..."
wget https://github.com/xjasonlyu/tun2socks/releases/download/v2.5.2/tun2socks-linux-amd64.zip
echo "  ✓ Архив tun2socks скачан"
echo ""

echo "[6] Распаковка tun2socks..."
unzip tun2socks-linux-amd64.zip
echo "  ✓ Архив распакован"
echo ""

# Проверяем, что файл tun2socks-linux-amd64 существует
echo "[7] Проверка наличия файла tun2socks-linux-amd64..."
if [ -f "tun2socks-linux-amd64" ]; then
    echo "  ✓ Файл tun2socks-linux-amd64 найден"
    ls -lh tun2socks-linux-amd64
else
    echo "  ✗ ОШИБКА: Файл tun2socks-linux-amd64 НЕ найден!"
    echo "  Содержимое текущей директории:"
    ls -la
    echo ""
    echo "  Поиск tun2socks в подпапках:"
    find . -name "tun2socks*" -type f 2>/dev/null || echo "    Не найден"
    exit 1
fi
echo ""

echo "[8] Копирование tun2socks в /usr/local/bin..."
sudo cp tun2socks-linux-amd64 /usr/local/bin/tun2socks
echo "  ✓ tun2socks скопирован"
sudo chmod +x /usr/local/bin/tun2socks
echo "  ✓ Права выполнения установлены"
echo ""

echo "=== Очистка временных файлов ==="
echo "[9] Удаление архивов и временных файлов..."
rm -f shadowsocks-v1.24.0.x86_64-unknown-linux-gnu.tar.xz
rm -f tun2socks-linux-amd64.zip
rm -f sslocal ssserver ssmanager ssservice ssurl
rm -f tun2socks-linux-amd64
echo "  ✓ Временные файлы удалены"
echo ""

echo "=== Успешно завершено ==="
