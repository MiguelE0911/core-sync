"""Acciones 5 a 9: sistema, CPU, RAM, almacenamiento y procesos.

Todas las consultas usan CIM/WMI, cuyos nombres de clase no dependen del
idioma de Windows. Get-Counter usa nombres traducidos ("\\Procesador(_Total)\\...")
y fallaría en un Windows en español.
"""
from __future__ import annotations

from datetime import datetime

from app.session import Session
from core.result import OpResult
from core.units import KIB
from remote.ps import as_list, ps_int
from ops.common import run_body

TEST_MARKER = "CoreSyncCarga"  # se incluye en la línea de comandos del proceso de prueba


# -- Acción 5 ---------------------------------------------------------------
SYSTEM_FIELDS = [  # (clave, etiqueta, fuente)
    ("equipo", "Nombre del equipo", "$env:COMPUTERNAME"),
    ("fabricante", "Fabricante", "Win32_ComputerSystem.Manufacturer"),
    ("modelo", "Modelo", "Win32_ComputerSystem.Model"),
    ("so", "Sistema operativo", "Win32_OperatingSystem.Caption"),
    ("version", "Versión de Windows", "Win32_OperatingSystem.Version"),
    ("compilacion", "Compilación", "Win32_OperatingSystem.BuildNumber"),
    ("arquitectura", "Arquitectura", "Win32_OperatingSystem.OSArchitecture"),
    ("procesador", "Procesador", "Win32_Processor.Name"),
    ("nucleos", "Núcleos físicos", "Win32_Processor.NumberOfCores"),
    ("hilos", "Procesadores lógicos", "Win32_Processor.NumberOfLogicalProcessors"),
    ("mhz", "Frecuencia máxima (MHz)", "Win32_Processor.MaxClockSpeed"),
    ("memoria_instalada", "Memoria instalada", "Σ Win32_PhysicalMemory.Capacity"),
    ("memoria_visible", "Memoria utilizable por Windows", "Win32_ComputerSystem.TotalPhysicalMemory"),
    ("arranque", "Último arranque", "Win32_OperatingSystem.LastBootUpTime"),
]

_SYSTEM = r"""
function Get-Safe([scriptblock]$sb) { try { & $sb } catch { $null } }
$cs  = Get-Safe { Get-CimInstance Win32_ComputerSystem }
$os  = Get-Safe { Get-CimInstance Win32_OperatingSystem }
$cpu = Get-Safe { Get-CimInstance Win32_Processor | Select-Object -First 1 }
$mem = Get-Safe { (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum }
[pscustomobject]@{
    equipo            = $env:COMPUTERNAME
    fabricante        = $cs.Manufacturer
    modelo            = $cs.Model
    so                = $os.Caption
    version           = $os.Version
    compilacion       = $os.BuildNumber
    arquitectura      = $os.OSArchitecture
    procesador        = if ($cpu) { $cpu.Name.Trim() } else { $null }
    nucleos           = $cpu.NumberOfCores
    hilos             = $cpu.NumberOfLogicalProcessors
    mhz               = $cpu.MaxClockSpeed
    memoria_instalada = $mem
    memoria_visible   = $cs.TotalPhysicalMemory
    arranque          = if ($os) { $os.LastBootUpTime.ToString('o') } else { $null }
}
"""


def system_info(session: Session) -> OpResult:
    op = OpResult(5, "Consultar información del sistema")
    if run_body(session, op, _SYSTEM):
        d = op.data or {}
        op.data = d
        missing = [label for key, label, _ in SYSTEM_FIELDS if d.get(key) in (None, "")]
        op.verified = bool(d.get("equipo"))
        op.message = "Datos obtenidos." + (f" No disponibles: {', '.join(missing)}." if missing else "")
    return session.record(op)


# -- Acción 6 ---------------------------------------------------------------
def _cpu_body(interval_ms: int) -> str:
    return f"""
$q = "SELECT PercentProcessorTime, Timestamp_Sys100NS FROM Win32_PerfRawData_PerfOS_Processor WHERE Name='_Total'"
$t0 = Get-Date
$a = Get-CimInstance -Query $q
Start-Sleep -Milliseconds {ps_int(interval_ms)}
$b = Get-CimInstance -Query $q
$t1 = Get-Date
# PercentProcessorTime (bruto) acumula tiempo INACTIVO en unidades de 100 ns.
$dt = [double]$b.Timestamp_Sys100NS - [double]$a.Timestamp_Sys100NS
$di = [double]$b.PercentProcessorTime - [double]$a.PercentProcessorTime
$uso = if ($dt -gt 0) {{ [math]::Round([math]::Max(0, [math]::Min(100, (1 - $di / $dt) * 100)), 1) }} else {{ $null }}
[pscustomobject]@{{
    porcentaje   = $uso
    inicio       = $t0.ToString('o')
    fin          = $t1.ToString('o')
    intervalo_ms = {ps_int(interval_ms)}
    medido_ms    = [math]::Round($dt / 10000, 0)
    logicos      = [Environment]::ProcessorCount
}}
"""


def cpu_usage(session: Session, record: bool = True) -> OpResult:
    interval_ms = int(session.config.lab.cpu_interval_s * 1000)
    op = OpResult(6, "Consultar uso de CPU", params={"intervalo_ms": interval_ms,
                                                    "fuente": "Win32_PerfRawData_PerfOS_Processor (_Total)"})
    if run_body(session, op, _cpu_body(interval_ms), timeout_s=30 + interval_ms / 1000):
        d = op.data or {}
        value = d.get("porcentaje")
        op.verified = value is not None and 0 <= value <= 100
        op.message = f"CPU {value} % medido entre {_hms(d.get('inicio'))} y {_hms(d.get('fin'))}."
    if record:
        session.record(op)
    else:
        op.finish()
    return op


def _cpu_load_body(seconds: int, max_procs: int) -> str:
    # Un bucle activo por procesador lógico (con tope). El marcador en la línea de
    # comandos permite identificar estos procesos en la acción 9.
    return f"""
$n = [Math]::Min([Environment]::ProcessorCount, {ps_int(max_procs)})
$loop = '$end=(Get-Date).AddSeconds({ps_int(seconds)});while((Get-Date) -lt $end){{}};#{TEST_MARKER}'
$procs = @(1..$n | ForEach-Object {{
    Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-Command', $loop -WindowStyle Hidden -PassThru
}})
$ids = @($procs | ForEach-Object {{ $_.Id }})
$procs | Wait-Process -Timeout {ps_int(seconds + 15)} -ErrorAction SilentlyContinue
$restantes = @($procs | Where-Object {{ -not $_.HasExited }})
$restantes | Stop-Process -Force -ErrorAction SilentlyContinue
[pscustomobject]@{{ procesos = $n; pids = $ids; segundos = {ps_int(seconds)}; forzados = $restantes.Count }}
"""


def generate_cpu_load(session: Session, seconds: int = 20, max_procs: int = 16) -> OpResult:
    """Genera carga de prueba en BOSGAME. Bloquea el hilo de trabajo durante `seconds`."""
    seconds = max(3, min(int(seconds), 120))
    op = OpResult(6, "Generar carga de CPU de prueba",
                  params={"segundos": seconds, "max_procesos": max_procs, "marcador": TEST_MARKER})
    if run_body(session, op, _cpu_load_body(seconds, max_procs), timeout_s=seconds + 60):
        d = op.data or {}
        op.verified = len(as_list(d.get("pids"))) == d.get("procesos")
        op.message = (f"{d.get('procesos')} procesos de carga (PID {', '.join(map(str, as_list(d.get('pids'))))}) "
                      f"durante {seconds} s; todos finalizados.")
    return session.record(op)


# -- Acción 7 ---------------------------------------------------------------
_RAM = r"""
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
    total_kib = $os.TotalVisibleMemorySize
    libre_kib = $os.FreePhysicalMemory
    instante  = (Get-Date).ToString('o')
}
"""
RAM_SOURCE = "Win32_OperatingSystem: TotalVisibleMemorySize y FreePhysicalMemory (KiB)"


def ram_usage(session: Session) -> OpResult:
    op = OpResult(7, "Consultar uso de RAM", params={"fuente": RAM_SOURCE})
    if run_body(session, op, _RAM):
        d = op.data or {}
        total = int(d.get("total_kib") or 0) * KIB
        free = int(d.get("libre_kib") or 0) * KIB
        op.data = {"total": total, "disponible": free, "usada": total - free, "instante": d.get("instante")}
        op.verified = total > 0 and 0 <= free <= total
        op.message = f"RAM usada {(total - free) * 100 / total:.1f} %." if total else "Datos inválidos."
    return session.record(op)


# -- Acción 8 ---------------------------------------------------------------
_STORAGE = r"""
$vols = @{}
try { Get-Volume | Where-Object DriveLetter | ForEach-Object { $vols[[string]$_.DriveLetter] = $_ } } catch { }
@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
    $v = $vols[$_.DeviceID.TrimEnd(':')]
    [pscustomobject]@{
        unidad          = $_.DeviceID
        etiqueta        = $_.VolumeName
        sistema         = $_.FileSystem
        total           = $_.Size
        libre           = $_.FreeSpace
        contraste_total = if ($v) { $v.Size } else { $null }
        contraste_libre = if ($v) { $v.SizeRemaining } else { $null }
    }
})
"""


def storage(session: Session) -> OpResult:
    op = OpResult(8, "Consultar almacenamiento",
                  params={"fuente": "Win32_LogicalDisk (DriveType=3)", "contraste": "Get-Volume"})
    if run_body(session, op, _STORAGE):
        drives = as_list(op.data)
        for d in drives:
            total, free = d.get("total"), d.get("libre")
            d["usado"] = total - free if total is not None and free is not None else None
            ct, cf = d.get("contraste_total"), d.get("contraste_libre")
            # Coinciden si la diferencia de espacio libre es < 0,1 % (el disco cambia entre lecturas).
            d["coincide"] = (None if ct is None or total is None
                             else ct == total and abs((cf or 0) - (free or 0)) <= max(total * 0.001, 1))
        op.data = drives
        op.verified = bool(drives) and all(d["coincide"] is not False for d in drives)
        op.message = f"{len(drives)} unidad(es) fija(s)." + (
            "" if op.verified else " El contraste con Get-Volume no coincide en alguna unidad.")
    return session.record(op)


# -- Acción 9 ---------------------------------------------------------------
def _processes_body(interval_ms: int) -> str:
    return f"""
$cmd = @{{}}
Get-CimInstance Win32_Process -Property ProcessId, CommandLine | ForEach-Object {{ $cmd[[int]$_.ProcessId] = $_.CommandLine }}
$a = @{{}}
Get-Process | ForEach-Object {{ $a[$_.Id] = $_.CPU }}
$t0 = Get-Date
Start-Sleep -Milliseconds {ps_int(interval_ms)}
$seg = ((Get-Date) - $t0).TotalSeconds
$n = [Environment]::ProcessorCount
@(Get-Process | ForEach-Object {{
    $cpu = $_.CPU
    $prev = $a[$_.Id]
    $line = $cmd[[int]$_.Id]
    [pscustomobject]@{{
        pid     = $_.Id
        nombre  = $_.ProcessName
        cpu_pct = if ($cpu -ne $null -and $prev -ne $null) {{ [math]::Round(($cpu - $prev) / $seg / $n * 100, 1) }} else {{ $null }}
        cpu_s   = if ($cpu -ne $null) {{ [math]::Round($cpu, 2) }} else {{ $null }}
        memoria = $_.WorkingSet64
        sesion  = $_.SessionId
        prueba  = [bool]($line -and $line.Contains('{TEST_MARKER}'))
    }}
}})
"""


def processes(session: Session) -> OpResult:
    interval_ms = int(session.config.lab.cpu_interval_s * 1000)
    op = OpResult(9, "Consultar procesos",
                  params={"intervalo_ms": interval_ms, "fuente": "Get-Process + Win32_Process.CommandLine"})
    if run_body(session, op, _processes_body(interval_ms), timeout_s=60):
        procs = as_list(op.data)
        op.data = procs
        tests = [p for p in procs if p.get("prueba")]
        op.verified = bool(procs)
        op.message = f"{len(procs)} procesos." + (
            f" Proceso(s) de prueba: {', '.join(str(p['pid']) for p in tests)}." if tests else " Sin procesos de prueba.")
    return session.record(op)


def resource_summary(session: Session) -> list[OpResult]:
    """Resumen del panel principal: CPU, RAM y almacenamiento (cada uno queda registrado)."""
    return [cpu_usage(session), ram_usage(session), storage(session)]


def _hms(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M:%S.%f")[:-3]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "?"
