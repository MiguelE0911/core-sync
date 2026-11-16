"""Acciones 2, 3 y 4: identidad, conexión y carpeta personal."""
from __future__ import annotations

from ..app.session import RemoteIdentity, Session
from ..core.result import OpResult, now_local
from ..records.activity import COLUMNS
from ..remote.backend import ConnectParams, RemoteError, UnknownHostKey
from ..remote.ps import ps_str, ps_str_array

SUBFOLDERS = ["Archivos", "Respaldos", "Restaurados", "Evidencias", "Informes", "Temporales"]

_WHOAMI = r"""
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$admin = (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
    equipo  = $env:COMPUTERNAME
    usuario = $id.Name
    admin   = $admin
    so      = $os.Caption
    ps      = $PSVersionTable.PSVersion.ToString()
}
"""


# -- Acción 3 ---------------------------------------------------------------
def connect(session: Session, password: str) -> OpResult:
    c = session.config.connection
    op = OpResult(3, "Conectar sesión remota",
                  params={"equipo": c.host_name, "direccion": c.address, "puerto": c.port,
                          "usuario": c.username, "mecanismo": session.backend.name},
                  destination=f"{c.address}:{c.port}", command=_WHOAMI.strip())
    try:
        session.backend.connect(ConnectParams(c.address, c.port, c.username, password, c.timeout_s))
        op.executed = True
        res = session.backend.run_ps(_WHOAMI, timeout_s=30)
        if not res.ok:
            raise RemoteError(f"Conectado, pero PowerShell remoto falló: {res.error}")
        d = res.data or {}
        session.remote = RemoteIdentity(d.get("equipo", ""), d.get("usuario", ""), bool(d.get("admin")),
                                        d.get("so", ""), d.get("ps", ""))
        op.data = d
        # Comprobar el destino: el nombre real debe coincidir con el esperado.
        expected = c.host_name.strip().upper()
        if expected and session.remote.computer_name.upper() != expected:
            op.verified = False
            op.message = (f"Conectado, pero el equipo responde como '{session.remote.computer_name}' "
                          f"y se esperaba '{c.host_name}'. Verifica el destino antes de operar.")
        else:
            op.verified = True
            op.message = (f"Autenticado como {session.remote.user} en {session.remote.computer_name} "
                          f"({'administrador' if session.remote.is_admin else 'sin privilegios de administrador'}).")
    except UnknownHostKey as e:
        # La interfaz debe pedir confirmación de la huella y reintentar.
        op.error = str(e)
        session.backend.close()
        session.record(op)
        raise
    except RemoteError as e:
        op.error = str(e) + (f" {e.hint}" if e.hint else "")
        session.backend.close()
    finally:
        session.connection_changed.emit(session.connected)
    return session.record(op)


def disconnect(session: Session) -> OpResult:
    op = OpResult(3, "Desconectar sesión remota", destination=session.config.connection.address)
    session.backend.close()
    op.executed = True
    op.verified = not session.connected
    op.message = "Sesión cerrada y recursos liberados." if op.verified else "La sesión sigue activa."
    session.remote = RemoteIdentity()
    session.connection_changed.emit(session.connected)
    return session.record(op)


# -- Acción 4 ---------------------------------------------------------------
def prepare_workspace(session: Session) -> OpResult:
    root = session.personal_root
    header = ",".join(COLUMNS)
    body = f"""
$root = {ps_str(root)}
$subs = {ps_str_array(SUBFOLDERS)}
$full = [IO.Path]::GetFullPath($root)
if ($full.TrimEnd('\\') -ne $root.TrimEnd('\\')) {{ throw "Ruta personal no canónica: $full" }}
$out = @()
foreach ($rel in @('') + $subs) {{
    $p = if ($rel) {{ Join-Path $root $rel }} else {{ $root }}
    $p = [IO.Path]::GetFullPath($p)
    if (-not $p.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {{ throw "Ruta fuera de la carpeta personal: $p" }}
    $existia = Test-Path -LiteralPath $p -PathType Container
    if (-not $existia) {{ New-Item -ItemType Directory -Path $p | Out-Null }}
    $out += [pscustomobject]@{{ ruta = $p; tipo = 'Carpeta'; existia = $existia; existe = (Test-Path -LiteralPath $p -PathType Container) }}
}}
$csv = Join-Path $root 'actividad.csv'
$existia = Test-Path -LiteralPath $csv -PathType Leaf
if (-not $existia) {{ [IO.File]::WriteAllText($csv, {ps_str(header)} + "`r`n", (New-Object Text.UTF8Encoding $true)) }}
$out += [pscustomobject]@{{ ruta = $csv; tipo = 'Archivo'; existia = $existia; existe = (Test-Path -LiteralPath $csv -PathType Leaf) }}
$id = Join-Path $root 'identificacion.txt'
$out += [pscustomobject]@{{ ruta = $id; tipo = 'Archivo'; existia = (Test-Path -LiteralPath $id); existe = (Test-Path -LiteralPath $id -PathType Leaf) }}
$out
"""
    op = OpResult(4, "Preparar carpeta personal", params={"carpeta": root}, destination=root, command=body.strip())
    _run(session, op, body)
    if op.executed and op.data is not None:
        items = op.data if isinstance(op.data, list) else [op.data]
        op.data = items
        # identificacion.txt la genera la acción 2; aquí solo se informa si falta.
        required = [i for i in items if not i["ruta"].lower().endswith("identificacion.txt")]
        missing = [i["ruta"] for i in required if not i["existe"]]
        created = [i["ruta"] for i in items if i["existe"] and not i["existia"]]
        op.verified = not missing
        op.message = (f"Estructura verificada en {root}. Creados: {len(created)}, conservados: "
                      f"{len(items) - len(created)}." if not missing else f"Faltan: {', '.join(missing)}")
    return session.record(op)


# -- Acción 2 ---------------------------------------------------------------
def write_identification(session: Session) -> OpResult:
    s = session.config.student
    root = session.personal_root
    ts = now_local()
    block = (
        "==== CoreSync - Identificación ====\r\n"
        f"Nombre completo: {s.full_name}\r\n"
        f"Grupo: {s.group}\r\n"
        f"Identificador: {s.student_id}\r\n"
        f"Sesión: {session.session_id}\r\n"
        f"Equipo: {session.remote.computer_name}\r\n"
        f"Cliente: CoreSync\r\n"
        f"Fecha: {ts.isoformat(timespec='seconds')}\r\n\r\n"
    )
    body = f"""
$p = Join-Path {ps_str(root)} 'identificacion.txt'
if (-not (Test-Path -LiteralPath {ps_str(root)} -PathType Container)) {{ throw 'La carpeta personal no existe. Ejecuta primero "Preparar carpeta".' }}
[IO.File]::AppendAllText($p, {ps_str(block)}, (New-Object Text.UTF8Encoding $true))
$txt = [IO.File]::ReadAllText($p)
[pscustomobject]@{{ ruta = $p; contiene_sesion = $txt.Contains({ps_str("Sesión: " + session.session_id)}); bytes = (Get-Item -LiteralPath $p).Length }}
"""
    op = OpResult(2, "Identificar al estudiante",
                  params={"nombre": s.full_name, "grupo": s.group, "id": s.student_id, "sesion": session.session_id},
                  destination=root + "\\identificacion.txt", command=body.strip())
    _run(session, op, body)
    if op.executed and isinstance(op.data, dict):
        op.verified = bool(op.data.get("contiene_sesion"))
        op.evidence = op.data.get("ruta", "")
        op.message = "identificacion.txt actualizado y verificado." if op.verified else "No se encontró la sesión en el archivo."
    return session.record(op)


def _run(session: Session, op: OpResult, body: str, timeout_s: float = 60) -> None:
    try:
        res = session.backend.run_ps(body, timeout_s=timeout_s)
    except RemoteError as e:
        op.error = str(e) + (f" {e.hint}" if e.hint else "")
        return
    if res.ok:
        op.executed = True
        op.data = res.data
    else:
        op.error = res.error
