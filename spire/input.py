"""Real input synthesis on X11 via xdotool/XTEST."""

from __future__ import annotations

import os
import subprocess
import time

from spire import tree


def xdotool(args, display=":2", check=True):
    env = dict(os.environ)
    env["DISPLAY"] = display
    return subprocess.run(["xdotool", *map(str, args)], env=env,
                          check=check, capture_output=True, text=True)


def activate_window(title: str, display=":2") -> str | None:
    res = xdotool(["search", "--name", title], display=display, check=False)
    ids = res.stdout.split()
    if not ids:
        return None
    wid = ids[0]
    xdotool(["windowactivate", "--sync", wid], display=display, check=False)
    return wid


def move_window(title: str, x: int, y: int, display=":2"):
    wid = activate_window(title, display)
    if wid:
        xdotool(["windowmove", wid, x, y], display=display, check=False)
    return wid


def _point(node, x_offset=None):
    ex = tree.extents(node)
    if not ex:
        raise RuntimeError("node has no screen extents")
    x, y, w, h = ex
    cx = x + (x_offset if x_offset is not None else max(12, w // 2))
    cy = y + h // 2
    return cx, cy


def click(node, display=":2", x_offset=None, count: int = 1,
          interval: float = 0.15):
    cx, cy = _point(node, x_offset)
    xdotool(["mousemove", cx, cy], display=display)
    for i in range(count):
        xdotool(["click", "1"], display=display)
        if i < count - 1:
            time.sleep(interval)
    return cx, cy


def double_click(node, display=":2", x_offset=None):
    return click(node, display=display, x_offset=x_offset,
                 count=2, interval=0.15)


def type_text(node, text: str, display=":2", clear: bool = True):
    click(node, display=display, x_offset=40)
    if clear:
        xdotool(["key", "ctrl+a"], display=display)
    xdotool(["type", "--delay", "6", text], display=display)


def press(keys, display=":2", title=None):
    if title:
        activate_window(title, display)
    xdotool(["key", keys], display=display)
