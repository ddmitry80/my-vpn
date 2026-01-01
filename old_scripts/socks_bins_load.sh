#!/bin/bash

# shadowsocks-rust
# Качаем архив (проверьте версию на GitHub, если ссылка устареет)
wget https://github.com/shadowsocks/shadowsocks-rust/releases/download/v1.24.0/shadowsocks-v1.24.0.x86_64-unknown-linux-gnu.tar.xz

# Распаковываем
tar -xf shadowsocks-v1.24.0.x86_64-unknown-linux-gnu.tar.xz

# Кладем в папку /usr/local/bin, чтобы запускать отовсюду
sudo cp sslocal /usr/local/bin/

# Поднятие socks proxy
#sslocal -b 127.0.0.1:1080 -U "ss://ВАША_ДЛИННАЯ_СТРОКА_ОТ_КОЛЛЕГИ"

# tun2socks
# Скачиваем (Linux amd64)
wget https://github.com/xjasonlyu/tun2socks/releases/download/v2.5.2/tun2socks-linux-amd64.zip
unzip tun2socks-linux-amd64.zip
sudo cp tun2socks-linux-amd64 /usr/local/bin/tun2socks
sudo chmod +x /usr/local/bin/tun2socks
