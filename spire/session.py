"""Launch applications inside the live X session and wait for AT-SPI."""

from __future__ import annotations

import glob
import os
import signal
import subprocess
import time

from spire import tree
from spire.wait import wait_until, WaitError


def _read_proc_file(pid: str, name: str) -> bytes:
    try:
        with open(f"/proc/{pid}/{name}", "rb") as fh:
            return fh.read()
    except OSError:
        return b""


def find_display_env(display: str = ":2") -> dict:
    """Discover DISPLAY + session bus env from the running desktop session."""
    for proc in glob.glob("/proc/[0-9]*"):
        pid = proc.rsplit("/", 1)[1]
        cmdline = _read_proc_file(pid, "cmdline").replace(b"\0", b" ")
        if b"xfce4-session" not in cmdline:
            continue
        raw = _read_proc_file(pid, "environ")
        env = {}
        for item in raw.split(b"\0"):
            if b"=" in item:
                k, _, v = item.partition(b"=")
                env[k.decode(errors="ignore")] = v.decode(errors="ignore")
        if env.get("DISPLAY") == display:
            out = {"DISPLAY": display}
            for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR",
                        "XDG_SESSION_TYPE", "XAUTHORITY"):
                if key in env:
                    out[key] = env[key]
            return out
    raise RuntimeError(
        f"no XFCE session found for display {display}; "
        "is the desktop session running?"
    )


class AppSession:
    """Context manager: launch a GUI app, wait for AT-SPI registration, stop it."""

    def __init__(self, cmd, env=None, app_name=None, display=":2",
                 log_path=None, ready_timeout=20.0):
        self.display = display
        self.app_name = app_name
        session_env = find_display_env(display)
        if env:
            session_env.update(env)
        self.env = session_env
        self.proc = None
        self.log_fh = None
        if log_path:
            self.log_fh = open(log_path, "ab")
        self.proc = subprocess.Popen(
            cmd, env=session_env, start_new_session=True,
            stdout=self.log_fh or subprocess.DEVNULL,
            stderr=self.log_fh or subprocess.DEVNULL,
        )
        self.app = None
        self.ready_timeout = ready_timeout

    def wait_ready(self, timeout=None):
        timeout = timeout or self.ready_timeout
        self.app = wait_until(
            lambda: tree.app_by_name(self.app_name, live=True)
            if self.app_name else None,
            timeout=timeout, interval=0.2,
            message=f"app {self.app_name!r} not visible to AT-SPI",
        )
        return self

    def stop(self, grace: float = 3.0):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.proc.wait(timeout=5)
        if self.log_fh:
            self.log_fh.close()

    def __enter__(self):
        return self.wait_ready()

    def __exit__(self, *exc):
        self.stop()
        return False
