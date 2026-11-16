"""Utilidades de prueba.

LocalPSBackend ejecuta las MISMAS plantillas PowerShell en esta máquina con
subprocess. Sirve para validar los scripts sin BOSGAME. Solo existe en las
pruebas: la aplicación siempre opera sobre el equipo remoto.
"""
from __future__ import annotations

import shutil
import subprocess
import time

import pytest

from coresync.remote.backend import RemoteBackend
from coresync.remote.ps import PSResult, encode_command, wrap


class LocalPSBackend(RemoteBackend):
    name = "local (pruebas)"

    def connect(self, params):  # pragma: no cover
        pass

    def close(self):
        pass

    def is_connected(self):
        return True

    def run_ps(self, body: str, timeout_s: float = 60.0) -> PSResult:
        t0 = time.perf_counter()
        p = subprocess.run(encode_command(wrap(body)), capture_output=True, timeout=timeout_s, shell=False)
        return PSResult.parse(body, p.returncode, p.stdout.decode("utf-8", "replace"),
                              p.stderr.decode("utf-8", "replace"), time.perf_counter() - t0)

    def upload(self, local_path, remote_path, progress=None):
        shutil.copyfile(local_path, remote_path)

    def download(self, remote_path, local_path, progress=None):
        shutil.copyfile(remote_path, local_path)

    def rename(self, remote_src, remote_dst):
        shutil.move(remote_src, remote_dst)


@pytest.fixture
def local_ps() -> LocalPSBackend:
    if shutil.which("powershell.exe") is None:
        pytest.skip("powershell.exe no disponible")
    return LocalPSBackend()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CORESYNC_HOME", str(tmp_path / "appdata"))
    return tmp_path
