"""AT-SPI tree access helpers built on pyatspi."""

from __future__ import annotations

import pyatspi


def desktop() -> object:
    """Return the root of the AT-SPI desktop (all applications)."""
    return pyatspi.Registry.getDesktop(0)


def applications() -> list:
    d = desktop()
    return [d[i] for i in range(d.childCount)]


def children(node) -> list:
    try:
        return [node[i] for i in range(node.childCount)]
    except Exception:
        return []


def walk(node, max_depth: int = 100):
    """Depth-first traversal of an accessible subtree."""
    def _walk(acc, depth):
        if depth > max_depth:
            return
        yield acc
        for child in children(acc):
            yield from _walk(child, depth + 1)
    yield from _walk(node, 0)


def role_name(node) -> str:
    try:
        return node.getRoleName() or ""
    except Exception:
        return ""


def node_name(node) -> str:
    try:
        return (node.name or "").strip()
    except Exception:
        return ""


def text_of(node) -> str:
    """Text content exposed through the AT-SPI Text interface."""
    try:
        if node.queryText():
            return (node.queryText().getText(0, -1) or "").strip()
    except Exception:
        pass
    return ""


def state_flags(node) -> list:
    flags = []
    try:
        s = node.getState()
    except Exception:
        return flags
    for label, state in (
        ("CHECKED", pyatspi.STATE_CHECKED),
        ("SELECTED", pyatspi.STATE_SELECTED),
        ("FOCUSED", pyatspi.STATE_FOCUSED),
        ("EXPANDED", pyatspi.STATE_EXPANDED),
        ("EDITABLE", pyatspi.STATE_EDITABLE),
        ("SHOWING", pyatspi.STATE_SHOWING),
        ("SENSITIVE", pyatspi.STATE_SENSITIVE),
    ):
        try:
            if s.contains(state):
                flags.append(label)
        except Exception:
            pass
    if "SENSITIVE" not in flags:
        flags.append("DISABLED")
    return flags


def has_state(node, state) -> bool:
    return state in state_flags(node)


def extents(node):
    """Screen extents (x, y, width, height) or None."""
    try:
        comp = node.queryComponent()
        if comp:
            return tuple(comp.getExtents(pyatspi.XY_SCREEN))
    except Exception:
        pass
    return None


def find(root, name=None, role=None, text=None, state=None,
         contains_name: bool = True, max_depth: int = 100):
    """Return first node matching all provided criteria (substring names)."""
    for node in walk(root, max_depth):
        if name is not None:
            nm = node_name(node)
            if not (nm and (name in nm if contains_name else nm == name)):
                continue
        if role is not None and role_name(node) != role:
            continue
        if text is not None and text not in text_of(node):
            continue
        if state is not None and not has_state(node, state):
            continue
        return node
    return None


def find_all(root, name=None, role=None, text=None, state=None,
             contains_name: bool = True, max_depth: int = 100) -> list:
    out = []
    for node in walk(root, max_depth):
        if name is not None:
            nm = node_name(node)
            if not (nm and (name in nm if contains_name else nm == name)):
                continue
        if role is not None and role_name(node) != role:
            continue
        if text is not None and text not in text_of(node):
            continue
        if state is not None and not has_state(node, state):
            continue
        out.append(node)
    return out


def _describe(node) -> dict:
    return {
        "role": role_name(node),
        "name": node_name(node),
        "text": text_of(node),
        "state": state_flags(node),
        "extents": extents(node),
    }


def snapshot(root, max_depth: int = 25, max_nodes: int = 1000) -> list:
    """Numbered compact snapshot: list of {idx, depth, role, name, text, state}."""
    out = []
    idx = 0
    for depth, node in enumerate(walk(root, max_depth)):
        if idx >= max_nodes:
            break
        info = _describe(node)
        info.update({"idx": idx, "depth": depth})
        out.append(info)
        idx += 1
    return out


def dump_text(root, max_depth: int = 25, max_nodes: int = 1000) -> str:
    """Human/LLM friendly indented dump with [#idx] prefixes."""
    lines = []
    for item in snapshot(root, max_depth, max_nodes):
        state = ",".join(item["state"]) if item["state"] else "-"
        label = item["name"] or item["text"]
        extra = f" text={item['text']!r}" if item["text"] and not item["name"] else ""
        lines.append(
            f"#{item['idx']:<4d} {'  ' * item['depth']}"
            f"[{item['role']}] {label!r} <{state}>{extra}"
        )
    return "\n".join(lines)


def app_by_name(app_name: str, live: bool = False):
    """Find a running application by name (substring, case-insensitive).

    With ``live=True`` only applications that currently expose a SHOWING
    frame are considered, which avoids grabbing a dying instance that is
    still listed in the AT-SPI registry.
    """
    wanted = app_name.lower()
    for app in applications():
        if wanted not in (app.name or "").lower():
            continue
        if not live:
            return app
        for node in walk(app, max_depth=4):
            if role_name(node) == "frame" and has_state(node, "SHOWING"):
                return app
    return None
