import base64

import pytest

from remote.ps import PSResult, as_list, encode_command, ps_int, ps_str, wrap

TRICKY = ["simple", "con 'comilla'", "tipográfica ’ ‘", "$(Remove-Item C:\\)", "; Stop-Computer", "`n backtick",
          "ñandú ÁÉÍÓÚ", "C:\\Ruta con espacios\\a b.txt", 'doble "comilla"']


def test_ps_str_escapes_quotes():
    assert ps_str("a'b") == "'a''b'"
    assert ps_str("x\u2019y") == "'x\u2019\u2019y'"


def test_ps_str_rejects_nul():
    with pytest.raises(ValueError):
        ps_str("a\x00b")


def test_ps_int_rejects_non_int():
    with pytest.raises(TypeError):
        ps_int("1; Stop-Computer")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ps_int(True)


def test_encode_command_is_utf16_base64():
    cmd = encode_command("Get-Date")
    b64 = cmd.rsplit(" ", 1)[1]
    assert base64.b64decode(b64).decode("utf-16-le") == "Get-Date"


def test_parse_success_and_error():
    ok = PSResult.parse("x", 0, '{"ok":true,"data":[1,2]}\r\n', "", 0.1)
    assert ok.ok and ok.data == [1, 2]
    err = PSResult.parse("x", 1, '{"ok":false,"error":"No existe"}', "", 0.1)
    assert not err.ok and err.error == "No existe"
    junk = PSResult.parse("x", 1, "", "#< CLIXML\nAcceso denegado", 0.1)
    assert not junk.ok and "Acceso denegado" in junk.error


def test_as_list():
    assert as_list(None) == [] and as_list({"a": 1}) == [{"a": 1}] and as_list([1]) == [1]


# --- Ejecución real con PowerShell local -------------------------------------
@pytest.mark.parametrize("value", TRICKY)
def test_literal_roundtrip_in_real_powershell(local_ps, value):
    """El valor llega intacto: nada se interpreta como código."""
    res = local_ps.run_ps(f"{ps_str(value)}")
    assert res.ok, res.error
    assert res.data == value


def test_errors_are_reported_as_json(local_ps):
    res = local_ps.run_ps("Get-Item -LiteralPath 'C:\\no\\existe\\zzz'")
    assert not res.ok
    assert res.exit_code == 1
    assert res.error
