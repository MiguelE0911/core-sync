"""Acciones 2 y 4 ejecutadas con las plantillas reales contra una carpeta temporal."""
from pathlib import Path

from coresync.app.config import AppConfig, LabConfig, StudentConfig
from coresync.app.session import Session
from coresync.ops import workspace


def make_session(tmp_path, backend) -> Session:
    cfg = AppConfig(lab=LabConfig(base_path=str(tmp_path / "Laboratorio")),
                    student=StudentConfig(full_name="Ana Martínez", group="1A", student_id="AMartinez"),
                    local_dir=str(tmp_path / "local"))
    s = Session(cfg)
    s.backend = backend
    s.remote.computer_name = "BOSGAME"
    return s


def test_prepare_creates_and_preserves(tmp_path, local_ps):
    s = make_session(tmp_path, local_ps)
    root = Path(s.personal_root)
    (root / "Archivos").mkdir(parents=True)
    (root / "Archivos" / "previo.txt").write_text("no borrar")

    op = workspace.prepare_workspace(s)
    assert op.executed and op.verified, op.error
    for sub in workspace.SUBFOLDERS:
        assert (root / sub).is_dir()
    assert (root / "Archivos" / "previo.txt").read_text() == "no borrar"
    assert (root / "actividad.csv").read_text(encoding="utf-8-sig").startswith("op_id,")
    by_path = {Path(i["ruta"]).name: i for i in op.data}
    assert by_path["Archivos"]["existia"] is True and by_path["Respaldos"]["existia"] is False

    # Segunda ejecución: todo se conserva, nada se crea.
    op2 = workspace.prepare_workspace(s)
    assert op2.verified and all(i["existia"] for i in op2.data if not i["ruta"].endswith("identificacion.txt"))
    assert len(s.log.rows()) == 2


def test_identification_appends_session(tmp_path, local_ps):
    s = make_session(tmp_path, local_ps)
    workspace.prepare_workspace(s)
    op = workspace.write_identification(s)
    assert op.verified, op.error
    text = (Path(s.personal_root) / "identificacion.txt").read_text(encoding="utf-8-sig")
    assert "Ana Martínez" in text and s.session_id in text
    workspace.write_identification(s)
    text2 = (Path(s.personal_root) / "identificacion.txt").read_text(encoding="utf-8-sig")
    assert text2.count("Identificación ====") == 2


def test_identification_fails_without_folder(tmp_path, local_ps):
    s = make_session(tmp_path, local_ps)
    op = workspace.write_identification(s)
    assert not op.executed and "carpeta personal no existe" in op.error
    assert s.log.rows()[-1]["resultado"] == "error"
