import os
import sys
import shutil
import platform
import tarfile
import zipfile
import stat
import tempfile
import pwd
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Имя проекта для XDG путей
APP_DIRNAME = "my-vpn"
ENV_BIN_DIR = "MY_VPN_BIN_DIR"
ENV_ENV_FILE = "MY_VPN_ENV_FILE"

# === КОНФИГУРАЦИЯ ВЕРСИЙ ===
# Можно обновлять версии здесь
SS_VERSION = "1.24.0"
T2S_VERSION = "v2.5.2"

def _effective_user_home() -> Path:
    """
    Если команда запущена через sudo, Path.home() указывает на /root,
    но бинарники в portable-режиме должны жить в HOME исходного пользователя.
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        try:
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except KeyError:
            pass
    return Path.home()

def get_bin_dir() -> Path:
    """
    Директория для portable-бинарников.
    По умолчанию: $XDG_DATA_HOME/my-vpn/bin или ~/.local/share/my-vpn/bin
    Можно переопределить через $MY_VPN_BIN_DIR.
    """
    override = os.environ.get(ENV_BIN_DIR)
    if override:
        override = override.strip()
        if override.startswith("~/"):
            return _effective_user_home() / override[2:]
        return Path(override).expanduser()

    home = _effective_user_home()
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))).expanduser()
    return data_home / APP_DIRNAME / "bin"

def get_env_file() -> Path | None:
    """
    Путь к .env (конфигу).
    Приоритет:
      1) $MY_VPN_ENV_FILE
      2) $XDG_CONFIG_HOME/my-vpn/.env или ~/.config/my-vpn/.env (учитывая sudo/SUDO_USER)
      3) None (тогда вызывающий код может искать относительно cwd)
    """
    override = os.environ.get(ENV_ENV_FILE)
    if override:
        override = override.strip()
        if override.startswith("~/"):
            return _effective_user_home() / override[2:]
        return Path(override).expanduser()

    home = _effective_user_home()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))).expanduser()
    candidate = config_home / APP_DIRNAME / ".env"
    return candidate if candidate.exists() else None

def ensure_bin_dir_in_path(bin_dir: Path) -> None:
    """Добавить `bin_dir` в начало `PATH`, если он ещё не присутствует."""
    bin_dir_str = str(bin_dir)
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if parts and parts[0] == bin_dir_str:
        return
    if bin_dir_str not in parts:
        os.environ["PATH"] = bin_dir_str + os.pathsep + current

def find_binary(name: str, bin_dir: Path) -> str | None:
    """Найти исполняемый файл: сначала в `bin_dir`, затем через `PATH`."""
    local = bin_dir / name
    if local.exists() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which(name)

def get_architecture():
    """Определить архитектуру для релизов `sslocal` и `tun2socks`."""
    arch = platform.machine().lower()
    if arch in ["x86_64", "amd64"]:
        return "x86_64", "amd64"  # (для SS, для Tun2Socks)
    elif arch in ["aarch64", "arm64"]:
        return "aarch64", "arm64"
    else:
        console.print(f"[red]Архитектура {arch} официально не поддерживается скриптом авто-установки.[/red]")
        sys.exit(1)

def download_file(url: str, dest_path: Path):
    """Скачать файл по `url` в `dest_path`, показывая прогресс-бар."""
    with requests.get(url, stream=True, timeout=(10, 60), headers={"User-Agent": "my-vpn/0.1"}) as r:
        r.raise_for_status()
        total_len = int(r.headers.get('content-length', 0))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task(f"Скачивание {dest_path.name}...", total=total_len)
            
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))

def _extract_tar_member(tar: tarfile.TarFile, member_name: str) -> bytes:
    """Прочитать конкретный файл из tar-архива и вернуть его содержимое."""
    member = None
    for cand in tar.getmembers():
        if cand.name == member_name or cand.name.endswith("/" + member_name):
            member = cand
            break
    if member is None:
        raise FileNotFoundError(f"{member_name} not found in archive")
    fileobj = tar.extractfile(member)
    if fileobj is None:
        raise RuntimeError(f"Cannot extract {member.name}")
    return fileobj.read()

def _extract_zip_member(zip_ref: zipfile.ZipFile, member_name: str) -> bytes:
    """Прочитать конкретный файл из zip-архива и вернуть его содержимое."""
    chosen = None
    for cand in zip_ref.infolist():
        if cand.filename == member_name or cand.filename.endswith("/" + member_name):
            chosen = cand
            break
    if chosen is None:
        raise FileNotFoundError(f"{member_name} not found in archive")
    return zip_ref.read(chosen)

def install_shadowsocks(bin_dir: Path) -> Path:
    """Portable-установка Shadowsocks (`sslocal`) в `bin_dir` (если ещё не установлен)."""
    ss_arch, _ = get_architecture()
    filename = f"shadowsocks-v{SS_VERSION}.{ss_arch}-unknown-linux-gnu.tar.xz"
    url = f"https://github.com/shadowsocks/shadowsocks-rust/releases/download/v{SS_VERSION}/{filename}"
    
    install_path = bin_dir / "sslocal"
    existing = find_binary("sslocal", bin_dir)
    if existing:
        return Path(existing)

    console.print(f"[yellow]sslocal не найден. Устанавливаем v{SS_VERSION}...[/yellow]")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / filename
        
        try:
            download_file(url, archive_path)
            
            console.print("Распаковка...")
            with tarfile.open(archive_path, "r:xz") as tar:
                payload = _extract_tar_member(tar, "sslocal")

            bin_dir.mkdir(parents=True, exist_ok=True)
            install_path.write_bytes(payload)
            os.chmod(install_path, 0o755)
            
            console.print(f"[green]Shadowsocks установлен в {install_path}[/green]")
            return install_path
            
        except Exception as e:
            console.print(f"[bold red]Ошибка установки Shadowsocks:[/bold red] {e}")
            sys.exit(1)

def install_tun2socks(bin_dir: Path) -> Path:
    """Portable-установка `tun2socks` в `bin_dir` (если ещё не установлен)."""
    _, t2s_arch = get_architecture()
    filename = f"tun2socks-linux-{t2s_arch}.zip"
    url = f"https://github.com/xjasonlyu/tun2socks/releases/download/{T2S_VERSION}/{filename}"
    
    install_path = bin_dir / "tun2socks"
    existing = find_binary("tun2socks", bin_dir)
    if existing:
        return Path(existing)

    console.print(f"[yellow]tun2socks не найден. Устанавливаем {T2S_VERSION}...[/yellow]")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / filename
        
        try:
            download_file(url, archive_path)
            
            console.print("Распаковка...")
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # В архиве лежит файл tun2socks-linux-amd64, нам надо его переименовать
                extracted_name = f"tun2socks-linux-{t2s_arch}"
                payload = _extract_zip_member(zip_ref, extracted_name)

            bin_dir.mkdir(parents=True, exist_ok=True)
            install_path.write_bytes(payload)
            os.chmod(install_path, 0o755)
            
            console.print(f"[green]Tun2Socks установлен в {install_path}[/green]")
            return install_path
            
        except Exception as e:
            console.print(f"[bold red]Ошибка установки Tun2Socks:[/bold red] {e}")
            sys.exit(1)

def check_and_install_deps() -> dict[str, Path]:
    """Проверить наличие `sslocal`/`tun2socks` и установить их при необходимости."""
    bin_dir = get_bin_dir()
    ss_path = install_shadowsocks(bin_dir)
    t2s_path = install_tun2socks(bin_dir)
    ensure_bin_dir_in_path(bin_dir)
    return {"bin_dir": bin_dir, "sslocal": ss_path, "tun2socks": t2s_path}
