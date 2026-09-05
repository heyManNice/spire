# Spire

**Semantic Pixel-free Interface Regression Engine** — a thin, AI-friendly toolkit
for black-box testing of Linux desktop applications through the AT-SPI 2
accessibility tree.

Spire does not look at pixels. It reads roles, names, text and states from the
accessibility tree, drives the UI with semantic actions (AT-SPI `Action`) and
real input (XTEST via `xdotool`), and can emit compact numbered snapshots that
an LLM can reason about.

## Components

- `spire.tree` — walk/find nodes by role, name, text, state; text & JSON snapshots
- `spire.wait` — `wait_until` helpers to survive lazy/asynchronous UIs
- `spire.input` — click/double-click/type/key via XTEST (`xdotool`)
- `spire.session` — launch an app in the same X/D-Bus session and wait for it to
  register with the AT-SPI registry
- CLI: `python -m spire apps`, `python -m spire dump <app>`

## Example

```python
from spire.session import AppSession
from spire.tree import find, text_of
from spire.wait import wait_until

with AppSession(["/root/regedit/builddir/linux-regedit"],
                env={"LR_TEST_ETC": "/tmp/fake/etc"},
                app_name="linux-regedit") as app:
    menu = find(app.app, name="文件", role="menu")
    assert menu is not None
```

See `examples/linux-regedit/` for a complete pytest-based regression demo.
