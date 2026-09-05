"""pytest fixtures: fake roots + managed linux-regedit session."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGEDIT = Path(__file__).resolve().parents[2].parent / "regedit"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spire import input as inp
from spire import tree
from spire.session import AppSession, find_display_env
from spire.tree import find
from spire.wait import wait_node, wait_until

REGEDIT_BIN = REGEDIT / "builddir" / "linux-regedit"
SAMPLES = REGEDIT / "testdata"
MO_FILE = Path("/usr/local/share/locale/zh_CN/LC_MESSAGES/linux-regedit.mo")

if not MO_FILE.exists():
    pytest.skip("zh_CN translations not installed; run "
                "'meson install -C regedit/builddir' first")


def kill_regedit():
    """Ensure no lingering single-instance primary survives between tests."""
    subprocess.run(["pkill", "-x", "linux-regedit"], check=False)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "ui: desktop UI regression test (requires X session)")


@pytest.fixture(scope="session")
def display() -> str:
    return os.environ.get("SPIRE_DISPLAY", ":2")


@pytest.fixture(scope="session")
def session_env(display) -> dict:
    return find_display_env(display)


@pytest.fixture(scope="session")
def fake_roots(tmp_path_factory, session_env) -> dict:
    """Build a deterministic fake /etc, ~/.config and /boot."""
    base = tmp_path_factory.mktemp("lr-fake")
    etc = base / "etc"
    config = base / "config"
    boot = base / "boot"
    xdg = base / "xdg"
    for d in (etc, config, boot, xdg):
        d.mkdir(parents=True)
    shutil.copy(SAMPLES / "sample.ini", etc / "sample.ini")
    shutil.copy(SAMPLES / "sample.json", config / "sample.json")
    shutil.copy(SAMPLES / "sample.service", etc / "sample.service")
    return {
        "env": {
            "LR_TEST_ETC": str(etc),
            "LR_TEST_CONFIG": str(config),
            "LR_TEST_BOOT": str(boot),
            "XDG_CONFIG_HOME": str(xdg),
            "HOME": "/root",
        },
        "etc": etc,
        "config": config,
        "boot": boot,
        "sample_ini": etc / "sample.ini",
    }


@pytest.fixture
def regedit(fake_roots, display):
    assert REGEDIT_BIN.exists(), f"build first: {REGEDIT_BIN}"
    kill_regedit()
    # 等 AT-SPI 注册表彻底清空旧实例，避免抓到“将死”的旧句柄
    wait_until(lambda: tree.app_by_name("linux-regedit") is None,
               timeout=10, interval=0.2,
               message="previous instance still in AT-SPI registry")
    with AppSession([str(REGEDIT_BIN)], env=fake_roots["env"],
                    app_name="linux-regedit", display=display,
                    log_path="/tmp/spire-lr.log") as app:
        try:
            wait_node(app.app, role="frame", timeout=10)
            wait_until(lambda: inp.activate_window(
                           wm_class="linux-regedit", name="注册表编辑器",
                           display=display),
                       timeout=5, message="window not mappable")
            # 窗口已属于新实例后重新绑定句柄，避免旧 AT-SPI 对象残留
            app.app = tree.app_by_name("linux-regedit", live=True)
            inp.move_window(0, 100, wm_class="linux-regedit",
                            name="注册表编辑器", display=display)
            yield app
        finally:
            kill_regedit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if call.when == "call" and outcome.get_result().failed:
        shot = f"/tmp/spire-fail-{item.name}.png"
        env = dict(os.environ, DISPLAY=os.environ.get("SPIRE_DISPLAY", ":2"))
        subprocess.run(["import", "-window", "root", shot], env=env,
                       check=False)
        print(f"\n[failure screenshot] {shot}")
