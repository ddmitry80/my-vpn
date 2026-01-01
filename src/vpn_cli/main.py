import os
import sys
import time
import subprocess
import socket
import base64

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from vpn_cli.utils import (
    check_and_install_deps,
    ensure_bin_dir_in_path,
    find_binary,
    get_bin_dir,
)

# Загружаем переменные из .env
load_dotenv()

app = typer.Typer(help="Personal VPN manager wrapping Shadowsocks & Tun2Socks")
console = Console()

# Константы (можно тоже вынести в .env)
TUN_DEV = os.getenv("TUN_DEV", "tun0")
TUN_ADDR = os.getenv("TUN_ADDR", "10.255.0.2/24")
try:
    SOCKS_PORT = int(os.getenv("SOCKS_PORT", "1080"))
except ValueError:
    SOCKS_PORT = 1080

def check_root():
    if os.geteuid() != 0:
        console.print("[bold red]Ошибка:[/bold red] Запускайте через sudo!")
        sys.exit(1)

def parse_ss_url(url: str):
    """Та самая логика парсинга, которую мы чинили"""
    if not url:
        raise ValueError("URL is empty")
    url = url.replace("ss://", "").split("#")[0].split("?")[0]
    if url.endswith("/"):
        url = url[:-1]

    if "@" not in url:
        raise ValueError("Неверный формат ss:// (нет @)")

    userinfo, host_port = url.rsplit("@", 1)
    host, port = host_port.rsplit(":", 1)

    # Base64 decode
    userinfo += "=" * (-len(userinfo) % 4)
    normalized = userinfo.replace("-", "+").replace("_", "/")
    decoded = base64.b64decode(normalized).decode("utf-8")
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

@app.command("install-deps")
def install_deps():
    """Скачать sslocal и tun2socks в user-space (portable)"""
    if os.geteuid() == 0:
        console.print("[yellow]Подсказка:[/yellow] обычно лучше запускать install-deps без sudo.")
    deps = check_and_install_deps()
    console.print(
        Panel(
            f"bin_dir: {deps['bin_dir']}\nsslocal: {deps['sslocal']}\ntun2socks: {deps['tun2socks']}",
            title="Dependencies installed",
        )
    )

@app.command("status")
def status():
    """Показать состояние (интерфейс/процессы/пути)"""
    bin_dir = get_bin_dir()
    ensure_bin_dir_in_path(bin_dir)

    ss_bin = find_binary("sslocal", bin_dir)
    tun_bin = find_binary("tun2socks", bin_dir)

    tun_ok = subprocess.run(
        f"ip link show {TUN_DEV}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    ss_ok = subprocess.run(
        f"pgrep -f \"sslocal.*:{SOCKS_PORT}\"",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    t2s_ok = subprocess.run(
        f"pgrep -f \"tun2socks.*{TUN_DEV}\"",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

    console.print(
        Panel(
            f"TUN_DEV: {TUN_DEV} ({'up' if tun_ok else 'down'})\n"
            f"sslocal: {ss_bin or 'not found'} ({'running' if ss_ok else 'stopped'})\n"
            f"tun2socks: {tun_bin or 'not found'} ({'running' if t2s_ok else 'stopped'})\n"
            f"bin_dir: {bin_dir}",
            title="Status",
        )
    )

@app.command("stop")
def stop():
    """Остановить VPN (аналог old_scripts/vpn_stop.sh)"""
    check_root()
    console.print("[1/2] Останавливаем процессы...")
    subprocess.run("pkill sslocal", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run("pkill tun2socks", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    console.print(f"[2/2] Удаляем интерфейс {TUN_DEV}...")
    subprocess.run(f"ip link delete {TUN_DEV}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ss_url = os.getenv("SS_URL")
        if ss_url:
            _, _, _, _, server_ip = parse_ss_url(ss_url)
            subprocess.run(f"ip route del {server_ip}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    console.print("Готово! VPN выключен, работаем напрямую.")

@app.command("start")
def start(install_deps: bool = typer.Option(False, "--install-deps", help="Скачать deps (лучше запускать без sudo)")):
    """Запуск VPN"""
    check_root()

    bin_dir = get_bin_dir()
    ensure_bin_dir_in_path(bin_dir)

    if install_deps:
        check_and_install_deps()

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

    ss_bin = find_binary("sslocal", bin_dir)
    tun_bin = find_binary("tun2socks", bin_dir)
    if not ss_bin or not tun_bin:
        console.print("[red]Не найдены sslocal или tun2socks.[/red]")
        console.print(f"Поставь зависимости командой: [bold]my-vpn install-deps[/bold] (без sudo)")
        console.print(f"Portable-директория по умолчанию: {bin_dir}")
        console.print("Можно переопределить через env `MY_VPN_BIN_DIR=/path/to/bin`.")
        raise typer.Exit(code=1)

    ss_log_path = "/tmp/my-vpn-sslocal.log"
    tun_log_path = "/tmp/my-vpn-tun2socks.log"

    # 1. Запуск SS Local
    kill_process_on_port(SOCKS_PORT)

    console.print("[green]Запуск shadowsocks...[/green]")
    ss_log = open(ss_log_path, "ab", buffering=0)
    ss_proc = subprocess.Popen(
        [ss_bin, "-s", f"{host}:{port}", "-m", method, "-k", password, "-b", f"127.0.0.1:{SOCKS_PORT}", "-U"],
        stdout=ss_log,
        stderr=subprocess.STDOUT,
    )

    # Даем время на старт
    time.sleep(1)
    if ss_proc.poll() is not None:
        console.print(f"[red]SSLocal упал при старте![/red] Лог: {ss_log_path}")
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
        subprocess.run(
            f"pkill -f \"tun2socks.*{TUN_DEV}\"",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tun_log = open(tun_log_path, "ab", buffering=0)
        tun_proc = subprocess.Popen(
            [tun_bin, "-device", TUN_DEV, "-proxy", f"socks5://127.0.0.1:{SOCKS_PORT}"],
            stdout=tun_log,
            stderr=subprocess.STDOUT,
        )

        # 4. Маршрутизация
        gw = subprocess.check_output("ip route show default | awk '/default/ {print $3}'", shell=True).decode().strip()
        if gw:
            subprocess.run(f"ip route replace {server_ip} via {gw}", shell=True, stderr=subprocess.DEVNULL)

        subprocess.run(f"ip route replace 0.0.0.0/1 dev {TUN_DEV}", shell=True)
        subprocess.run(f"ip route replace 128.0.0.0/1 dev {TUN_DEV}", shell=True)

        console.print("[bold green]VPN ПОДКЛЮЧЕН![/bold green] Нажми Ctrl+C для выхода.")

        while True:
            time.sleep(1)
            if ss_proc.poll() is not None or tun_proc.poll() is not None:
                raise Exception(f"Один из процессов упал! Логи: {ss_log_path}, {tun_log_path}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Остановка...[/yellow]")
    except Exception as e:
        console.print(f"[red]Ошибка в рантайме: {e}[/red]")
    finally:
        console.print("Очистка ресурсов...")
        if "ss_proc" in locals():
            ss_proc.terminate()
        if "tun_proc" in locals():
            tun_proc.terminate()
        if "ss_log" in locals():
            ss_log.close()
        if "tun_log" in locals():
            tun_log.close()
        subprocess.run(f"ip link delete {TUN_DEV}", shell=True, stderr=subprocess.DEVNULL)
        if "server_ip" in locals() and "gw" in locals():
            subprocess.run(f"ip route del {server_ip}", shell=True, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    app()
