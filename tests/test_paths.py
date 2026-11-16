import pytest

from coresync.core.paths import (
    PathValidationError, is_within, join_inside, personal_root, validate_base_path, validate_name,
    validate_student_id,
)


@pytest.mark.parametrize("ok", ["AMartinez", "a_b-c", "Alumno01"])
def test_student_id_ok(ok):
    assert validate_student_id(ok) == ok


@pytest.mark.parametrize("bad", ["", "ab", "..", "a/b", "a\\b", "..\\x", "C:x", "con", "A.Martinez",
                                 "José", "a b", "x" * 41])
def test_student_id_rejected(bad):
    with pytest.raises(PathValidationError):
        validate_student_id(bad)


@pytest.mark.parametrize("bad", ["", " ", ".", "..", "a/b", "a\\b", "a:b", "nul.txt", "x.", " x", "a\tb"])
def test_name_rejected(bad):
    with pytest.raises(PathValidationError):
        validate_name(bad)


def test_name_ok_with_spaces_and_accents():
    assert validate_name("Informe final ñandú.txt") == "Informe final ñandú.txt"


def test_personal_root():
    assert personal_root("C:\\Laboratorio\\", "AMartinez") == "C:\\Laboratorio\\AMartinez"


@pytest.mark.parametrize("bad", ["Laboratorio", "\\\\server\\share", "C:\\Lab\\..\\Windows", "/tmp"])
def test_base_path_rejected(bad):
    with pytest.raises(PathValidationError):
        validate_base_path(bad)


def test_is_within_prefix_trick():
    root = "C:\\Laboratorio\\AMartinez"
    assert is_within(root, "C:\\Laboratorio\\amartinez\\Archivos\\x.txt")
    assert not is_within(root, "C:\\Laboratorio\\AMartinez2\\x.txt")
    assert not is_within(root, "C:\\Laboratorio\\AMartinez\\..\\Otro")


@pytest.mark.parametrize("bad", ["..\\Otro", "Archivos\\..\\..\\Otro", "C:\\Windows", "\\\\srv\\c$", "D:x"])
def test_join_inside_rejects_escape(bad):
    with pytest.raises(PathValidationError):
        join_inside("C:\\Laboratorio\\AMartinez", bad)


def test_join_inside_ok():
    assert join_inside("C:\\Laboratorio\\A1b", "Archivos", "sub\\a.txt") == "C:\\Laboratorio\\A1b\\Archivos\\sub\\a.txt"
