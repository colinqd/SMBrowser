import subprocess
import threading
import os
import sys
import re
import json
import configparser
from typing import Optional, Callable, List, Dict


class RcloneProgress:
    __slots__ = [
        'bytes_transferred', 'bytes_total', 'percentage',
        'speed', 'speed_human', 'eta',
        'files_transferred', 'files_total', 'files_percentage',
        'elapsed', 'current_file'
    ]

    def __init__(self):
        self.bytes_transferred = 0
        self.bytes_total = 0
        self.percentage = 0.0
        self.speed = 0.0
        self.speed_human = ""
        self.eta = ""
        self.files_transferred = 0
        self.files_total = 0
        self.files_percentage = 0.0
        self.elapsed = ""
        self.current_file = ""


class RcloneProgressParser:
    SIZE_UNITS = {
        "TiB": 1024 ** 4, "GiB": 1024 ** 3, "MiB": 1024 ** 2, "KiB": 1024,
        "TB": 1000 ** 3, "GB": 1000 ** 3, "MB": 1000 ** 2, "KB": 1000,
        "B": 1,
    }

    TRANSFER_RE = re.compile(
        r"Transferred:\s+"
        r"([\d.]+\s*\w+)\s*/\s*([\d.]+\s*\w+),\s*"
        r"(\d+)%,\s*"
        r"([\d.]+\s*\w+/s),?\s*"
        r"(?:ETA\s*(.+))?"
    )

    FILES_RE = re.compile(r"Transferred:\s+(\d+)\s*/\s*(\d+),\s*(\d+)%")

    CURRENT_FILE_RE = re.compile(r"Transferring:\s*(.+)")

    @classmethod
    def parse_line(cls, line: str) -> Optional[RcloneProgress]:
        line = line.strip()
        if not line:
            return None

        if line.startswith("{"):
            return cls._parse_json_line(line)

        progress = RcloneProgress()

        match = cls.TRANSFER_RE.search(line)
        if match:
            progress.bytes_transferred = cls._parse_size(match.group(1))
            progress.bytes_total = cls._parse_size(match.group(2))
            progress.percentage = float(match.group(3))
            progress.speed_human = match.group(4)
            progress.speed = cls._parse_size(match.group(4).replace("/s", ""))
            if match.group(5):
                progress.eta = match.group(5).strip()
            return progress

        match = cls.FILES_RE.search(line)
        if match:
            progress.files_transferred = int(match.group(1))
            progress.files_total = int(match.group(2))
            progress.files_percentage = float(match.group(3))
            return progress

        match = cls.CURRENT_FILE_RE.search(line)
        if match:
            progress.current_file = match.group(1).strip()
            return progress

        return None

    @classmethod
    def _parse_json_line(cls, line: str) -> Optional[RcloneProgress]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        msg = data.get("msg", "")
        progress = RcloneProgress()

        match = cls.TRANSFER_RE.search(msg)
        if match:
            progress.bytes_transferred = cls._parse_size(match.group(1))
            progress.bytes_total = cls._parse_size(match.group(2))
            progress.percentage = float(match.group(3))
            progress.speed_human = match.group(4)
            progress.speed = cls._parse_size(match.group(4).replace("/s", ""))
            if match.group(5):
                progress.eta = match.group(5).strip()
            return progress

        match = cls.FILES_RE.search(msg)
        if match:
            progress.files_transferred = int(match.group(1))
            progress.files_total = int(match.group(2))
            progress.files_percentage = float(match.group(3))
            return progress

        return None

    @classmethod
    def _parse_size(cls, size_str: str) -> int:
        size_str = size_str.strip()
        for unit, multiplier in sorted(cls.SIZE_UNITS.items(), key=lambda x: -len(x[0])):
            if unit in size_str:
                number = float(size_str.replace(unit, "").strip())
                return int(number * multiplier)
        try:
            return int(float(size_str))
        except ValueError:
            return 0


class RcloneWrapper:
    def __init__(self, rclone_path: str = "rclone"):
        self.rclone_path = rclone_path
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def _build_base_args(self) -> list:
        return [
            self.rclone_path,
            "--config", self._get_config_path(),
            "--contimeout", "30s",
            "--timeout", "300s",
            "--retries", "3",
            "--retries-sleep", "2s",
            "--log-level", "INFO",
        ]

    def _get_config_path(self) -> str:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(base, "config")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "rclone.conf")

    def execute(
        self,
        args: list,
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> int:
        cmd = self._build_base_args() + args
        self._cancelled = False

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        def read_stream(stream, callback):
            for line in iter(stream.readline, b""):
                text = line.decode("utf-8", errors="replace").rstrip()
                if callback:
                    callback(text)
            stream.close()

        t_out = threading.Thread(target=read_stream, args=(self._process.stdout, on_output), daemon=True)
        t_err = threading.Thread(target=read_stream, args=(self._process.stderr, on_error), daemon=True)
        t_out.start()
        t_err.start()

        self._process.wait()
        t_out.join(timeout=5)
        t_err.join(timeout=5)

        return self._process.returncode

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.poll() is None:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    capture_output=True,
                )
            except Exception:
                self._process.kill()
            self._process = None

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.rclone_path, "version"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False


class RcloneConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    def create_smb_remote(
        self,
        name: str,
        host: str,
        username: str,
        password: str,
        port: int = 445,
        domain: str = "",
    ) -> bool:
        encrypted_pass = self._obscure_password(password)
        if not encrypted_pass:
            encrypted_pass = password

        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding="utf-8")

        if not config.has_section(name):
            config.add_section(name)

        config.set(name, "type", "samba")
        config.set(name, "host", host)
        config.set(name, "user", username)
        config.set(name, "pass", encrypted_pass)
        config.set(name, "port", str(port))
        config.set(name, "domain", domain)

        with open(self.config_path, "w", encoding="utf-8") as f:
            config.write(f)
        return True

    def _obscure_password(self, password: str) -> str:
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            rclone_path = os.path.join(exe_dir, "rclone.exe")
            if not os.path.exists(rclone_path):
                rclone_path = "rclone"

            result = subprocess.run(
                [rclone_path, "obscure", password],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def remove_remote(self, name: str):
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        if config.has_section(name):
            config.remove_section(name)
            with open(self.config_path, "w", encoding="utf-8") as f:
                config.write(f)

    def list_remotes(self) -> list:
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        return config.sections()


def get_rclone_path() -> str:
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    rclone = os.path.join(exe_dir, "rclone.exe")
    if os.path.exists(rclone):
        return rclone

    rclone = os.path.join(exe_dir, "vendor", "rclone.exe")
    if os.path.exists(rclone):
        return rclone

    return "rclone"
