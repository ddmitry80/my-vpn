import os
import sys
import time
import subprocess
import signal
import socket
import base64
import shutil
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Загружаем переменные из .env
load_dotenv()

app = typer.Typer()
console = Console()

# Константы (можно тоже вынести в .env)
TUN_DEV = "tun0"
TUN_ADDR = "10.255.0.2/24"
SOCKS_PORT = 1080

def check_root():
    if os.geteuid() != 0:
        console.print("[bold red]Ошибка:[/bold red] Запускайте через sudo!")
        sys.exit(1)

def parse_ss_url(url: str):
    """Та самая логика парсинга, которую мы чинили"""
    if not url: raise ValueError("URL is empty")
    url = url.replace("ss://", "").split("#")[0].split("?")[0]
    if url.endswith("/"): url = url[:-1]
    
    userinfo, host_port = url.rsplit("@", 1)
    host, port = host_port.split(":")
    
    # Base64 decode
    userinfo += "=" * (-len(userinfo) % 4)
    decoded = base64.b64decode(userinfo).decode("utf-8")
    method, password = decoded.split(":", 1)
    
    # Resolve IP
    try:
        server_ip = socket.gethostbyname(host)
    except socket.gaierror:
        server_ip = host
        
    return host, port, method, password, server_ip

def kill_process_on_port(port: int):
    """Аналог fuser -k"""
    try:
        # Ищем PID, слушающий порт
        result = subprocess.check_output(f"ss -lptn 'sport = :{port}'", shell=True).decode()
        if f":{port}" in result:
            console.print(f"[yellow]Порт {port} занят. Очищаем...[/yellow]")
            subprocess.run(f"fuser -k {port}/tcp", shell=True, stderr=subprocess.DEVNULL)
            time.sleep(1)
    except Exception:
        pass

@app.command()
def start():
    """Запуск VPN"""
    check_root()
    
    ss_url = os.getenv("SS_URL")
    if not ss_url:
        console.print("[red]SS_URL не найден в .env[/red]")
        raise typer.Exit(code=1)

    try:
        host, port, method, password, server_ip = parse_ss_url(ss_url)
    except Exception as e:
        console.print(f"[red]Ошибка парсинга URL:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(Panel(f"Server: {host} ({server_ip})\nMethod: {method}", title="Config Parsed"))

    # 1. Запуск SS Local
    kill_process_on_port(SOCKS_PORT)
    
    # Ищем бинарники (можно добавить логику скачивания, если их нет)
    ss_bin = shutil.which("sslocal")
    tun_bin = shutil.which("tun2socks")
    
    if not ss_bin or not tun_bin:
        console.print("[red]Не найдены sslocal или tun2socks в PATH[/red]")
        # Тут можно вызвать функцию auto_download_dependencies()
        raise typer.Exit(code=1)

    console.print("[green]Запуск shadowsocks...[/green]")
    ss_proc = subprocess.Popen(
        [ss_bin, "-s", f"{host}:{port}", "-m", method, "-k", password, "-b", f"127.0.0.1:{SOCKS_PORT}", "-U"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Даем время на старт
    time.sleep(1)
    if ss_proc.poll() is not None:
        console.print("[red]SSLocal упал при старте![/red]")
        print(ss_proc.stdout.read().decode())
        raise typer.Exit(1)

    try:
        # 2. Настройка интерфейса
        console.print(f"[green]Настройка {TUN_DEV}...[/green]")
        subprocess.run(f"ip link delete {TUN_DEV}", shell=True, stderr=subprocess.DEVNULL)
        subprocess.check_call(f"ip tuntap add dev {TUN_DEV} mode tun", shell=True)
        subprocess.check_call(f"ip addr add {TUN_ADDR} dev {TUN_DEV}", shell=True)
        subprocess.check_call(f"ip link set dev {TUN_DEV} up", shell=True)

        # 3. Запуск Tun2Socks
        console.print("[green]Запуск tun2socks...[/green]")
        tun_proc = subprocess.Popen(
            [tun_bin, "-device", TUN_DEV, "-proxy", f"socks5://127.0.0.1:{SOCKS_PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # 4. Маршрутизация
        gw = subprocess.check_output("ip route show default | awk '/default/ {print $3}'", shell=True).decode().strip()
        if gw:
            subprocess.run(f"ip route add {server_ip} via {gw}", shell=True, stderr=subprocess.DEVNULL)
        
        subprocess.run(f"ip route add 0.0.0.0/1 dev {TUN_DEV}", shell=True)
        subprocess.run(f"ip route add 128.0.0.0/1 dev {TUN_DEV}", shell=True)

        console.print("[bold green]VPN ПОДКЛЮЧЕН![/bold green] Нажми Ctrl+C для выхода.")
        
        # Бесконечный цикл ожидания (чтобы скрипт не вышел)
        while True:
            time.sleep(1)
            if ss_proc.poll() is not None or tun_proc.poll() is not None:
                raise Exception("Один из процессов упал!")

    except KeyboardInterrupt:
        console.print("\n[yellow]Остановка...[/yellow]")
    except Exception as e:
        console.print(f"[red]Ошибка в рантайме: {e}[/red]")
    finally:
        # CLEANUP
        console.print("Очистка ресурсов...")
        if 'ss_proc' in locals(): ss_proc.terminate()
        if 'tun_proc' in locals(): tun_proc.terminate()
        subprocess.run(f"ip link delete {TUN_DEV}", shell=True, stderr=subprocess.DEVNULL)
        # Если маршрут до сервера был специфичным, он удалится сам при удалении tun,
        # но маршрут via GW лучше почистить явно, если он остался.
        if 'server_ip' in locals() and 'gw' in locals():
             subprocess.run(f"ip route del {server_ip}", shell=True, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    app()
