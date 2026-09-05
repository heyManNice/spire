"""Polling helpers for asynchronous GTK UIs."""

from __future__ import annotations

import time


class WaitError(TimeoutError):
    pass


def wait_until(fn, timeout: float = 10.0, interval: float = 0.1,
               message: str = "condition not met"):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = fn()
        except Exception as exc:  # tolerate transient AT-SPI failures
            last = exc
        if last:
            return last
        time.sleep(interval)
    raise WaitError(f"{message} (last result: {last!r})")


def wait_app(app_name: str, timeout: float = 15.0, interval: float = 0.2):
    from spire import tree
    return wait_until(lambda: tree.app_by_name(app_name),
                      timeout=timeout, interval=interval,
                      message=f"application {app_name!r} did not register")


def wait_node(root, name=None, role=None, text=None, timeout: float = 10.0,
              **kwargs):
    from spire import tree
    return wait_until(
        lambda: tree.find(root, name=name, role=role, text=text, **kwargs),
        timeout=timeout,
        message=f"node name={name!r} role={role!r} text={text!r} did not appear",
    )
