import pytest
from pydantic import ValidationError

from app.config import AppConfig, ConnectionConfig, LabConfig, StudentConfig
from core.result import OpResult
from records.activity import ActivityLog, to_row


@pytest.mark.parametrize("addr", ["192.168.1.50", "bosgame", "BOSGAME.local", "fe80::1"])
def test_address_ok(addr):
    assert ConnectionConfig(address=addr).address == addr


@pytest.mark.parametrize("addr", ["192.168.1.300 ", "bos game", "-bad", "a;b"])
def test_address_rejected(addr):
    with pytest.raises(ValidationError):
        ConnectionConfig(address=addr)


def test_range_validation():
    with pytest.raises(ValidationError):
        LabConfig(tcp_range_start=9000, tcp_range_end=8000)
    with pytest.raises(ValidationError):
        LabConfig(tcp_range_start=1, tcp_range_end=5000)


def test_student_id_validated():
    with pytest.raises(ValidationError):
        StudentConfig(full_name="A", group="1", student_id="..\\x")


def test_save_load_roundtrip_has_no_password():
    cfg = AppConfig(connection=ConnectionConfig(address="10.0.0.5", username="lab"),
                    lab=LabConfig(services_to_query=[" sshd ", "", "W3SVC"]))
    path = cfg.save()
    text = path.read_text(encoding="utf-8")
    assert "password" not in text.lower()
    loaded = AppConfig.load()
    assert loaded.connection.address == "10.0.0.5"
    assert loaded.lab.services_to_query == ["sshd", "W3SVC"]


def test_activity_log_pending_and_sync(tmp_path):
    log = ActivityLog(tmp_path / "hist")
    op = OpResult(5, "Info", params={"x": 1}, executed=True, verified=True).finish()
    log.append(to_row(op, "S1", "AMartinez", "Ana Martínez", "BOSGAME"))
    log.append(to_row(OpResult(6, "CPU", error="falló").finish(), "S1", "AMartinez", "Ana Martínez", "BOSGAME"))
    rows = log.rows()
    assert [r["resultado"] for r in rows] == ["verificado", "error"]
    assert rows[0]["estudiante"] == "Ana Martínez"
    assert len(log.pending_ids()) == 2
    log.mark_synced([op.op_id])
    assert log.pending_ids() == [rows[1]["op_id"]]
