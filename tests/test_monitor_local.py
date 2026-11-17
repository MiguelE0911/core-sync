"""Acciones 5-9 con las plantillas reales ejecutadas en esta máquina."""
import os
import threading
import time

from app.config import AppConfig, LabConfig
from app.session import Session
from ops import monitor


def make_session(tmp_path, backend) -> Session:
    s = Session(AppConfig(lab=LabConfig(cpu_interval_s=0.5), local_dir=str(tmp_path / "local")))
    s.backend = backend
    return s


def test_system_info(tmp_path, local_ps):
    op = monitor.system_info(make_session(tmp_path, local_ps))
    assert op.verified, op.error
    assert op.data["equipo"] == os.environ["COMPUTERNAME"]
    assert op.data["procesador"] and op.data["arquitectura"]


def test_cpu_in_range(tmp_path, local_ps):
    op = monitor.cpu_usage(make_session(tmp_path, local_ps))
    assert op.verified, op.error
    assert 0 <= op.data["porcentaje"] <= 100
    assert op.data["medido_ms"] >= 400


def test_ram(tmp_path, local_ps):
    op = monitor.ram_usage(make_session(tmp_path, local_ps))
    assert op.verified, op.error
    assert op.data["total"] == op.data["usada"] + op.data["disponible"]


def test_storage_has_system_drive(tmp_path, local_ps):
    op = monitor.storage(make_session(tmp_path, local_ps))
    assert op.executed, op.error
    units = {d["unidad"] for d in op.data}
    assert os.environ.get("SystemDrive", "C:") in units


def test_processes_and_cpu_load_marker(tmp_path, local_ps):
    s = make_session(tmp_path, local_ps)
    load = {}
    t = threading.Thread(target=lambda: load.setdefault("op", monitor.generate_cpu_load(s, seconds=4, max_procs=2)))
    t.start()
    time.sleep(1.5)
    op = monitor.processes(s)
    t.join(timeout=60)
    assert op.verified, op.error
    assert any(p["pid"] == os.getpid() for p in op.data)
    tests = [p for p in op.data if p["prueba"]]
    assert len(tests) == 2
    assert all((p["cpu_pct"] or 0) > 0 for p in tests)
    assert load["op"].verified, load["op"].error
