# Plan de desarrollo — CoreSync (Proyecto Semestral App Multipropósito)

## Contexto
El enunciado (`Semestral - App multiuso.md`) pide una app de escritorio para Windows que monitoree y administre **de forma remota** el mini PC BOSGAME por red local, con 25 acciones obligatorias, evidencias verificables guardadas en BOSGAME, un ciclo de diagnóstico, cierre y restauración del puerto de práctica, y transferencias con métricas reales e integridad. El repo está vacío (solo el enunciado). Nombre: **CoreSync**.

**Decisiones tomadas**
- **Stack:** Python 3.12 + PySide6 (Qt), empaquetado con PyInstaller.
- **Mecanismo remoto:** OpenSSH Server de Windows. Comandos con `powershell -NoProfile -EncodedCommand` y transferencias por SFTP. Uso de `paramiko`. La conexión va detrás de una interfaz abstracta (`RemoteBackend`) para poder añadir WinRM (`pypsrp`) si el docente lo exige.
- **Configuración:** archivo JSON en `%APPDATA%\CoreSync\config.json`. Credenciales en el Administrador de credenciales de Windows (`keyring`).
- **Organización:** por fases funcionales; cada fase deja algo demostrable.

## Arquitectura (separa interfaz, conexión, operaciones y registro, como exige el enunciado)
```
coresync/
  main.py                    # punto de entrada
  app/config.py              # carga/validación de config (pydantic) + keyring
  app/session.py             # identidad del estudiante, session_id (UUID), estado de conexión
  remote/backend.py          # interfaz RemoteBackend: run_ps(), upload(), download(), close()
  remote/ssh_backend.py      # implementación paramiko (SSH + SFTP)
  remote/ps.py               # plantillas PowerShell + codificación -EncodedCommand + parseo JSON
  core/paths.py              # validación de identificador y de rutas dentro de C:\Laboratorio\<id>
  core/integrity.py          # SHA-256 local y remoto (Get-FileHash)
  core/transfer.py           # motor de transferencias: progreso, velocidad, ETA, .part, cancelación
  ops/                       # una función por grupo de acciones; devuelven OpResult
    system.py  network.py  services.py  port_lab.py  files.py  backup.py  cleanup.py  recover.py
  logging/activity.py        # registro de operaciones (CSV/SQLite local) + cola de pendientes + sincronización
  logging/report.py          # informe HTML/Markdown
  ui/                        # ventanas Qt: dashboard, conexión, monitoreo, red, archivos, historial, acerca de
  ui/workers.py              # QRunnable + señales (nada bloquea el hilo de la UI)
  resources/                 # logo, icono, QSS de paleta, fuentes (con licencias)
tests/                       # pytest: validadores, plantillas, cálculos de transferencia
docs/                        # manual, matriz de 25 acciones, ficha de producto, uso de IA
```

**Principios clave**
- **Cada comando remoto** se arma con una plantilla PowerShell fija. Los parámetros van validados y se insertan como literales escapados, y todo se envía con `-EncodedCommand` (UTF-16LE base64) para evitar inyección y problemas de comillas. La salida se pide como `ConvertTo-Json` y se parsea en Python.
- **`OpResult`** contiene `op_id`, la acción, los parámetros no sensibles, el comando mostrado, stdout/stderr, `executed` y `verified` por separado, y la referencia de evidencia. Así se cumple "diferenciar operación ejecutada de verificada".
- **Validación de rutas en dos capas.** En el cliente se rechazan identificadores con `\ / .. :` y caracteres inválidos. En el remoto se aplica `[IO.Path]::GetFullPath()` y se comprueba que la ruta empiece por la carpeta personal (la acción 25 es la única excepción, en solo lectura).
- **Ningún valor de laboratorio en el código.** Host, IP, puerto SSH, usuario, carpeta base, rango TCP, servicio de práctica, puerto de práctica y lista de servicios a consultar viven en la config.

## Mapeo de las 25 acciones → implementación
| # | Acción | Implementación remota/cliente |
|---|---|---|
| 1 | Configurar acceso | Formulario y validación de IP/host/puerto; `keyring` para la contraseña |
| 2 | Identificar estudiante | Nombre, grupo e id → `identificacion.txt` remoto; `session_id` en cada registro |
| 3 | Conectar/desconectar | `paramiko.SSHClient` con verificación de host key (TOFU con confirmación), timeouts, mensajes según el fallo (auth, timeout, rechazo); `close()` libera SFTP y transporte |
| 4 | Preparar carpeta | `New-Item -ItemType Directory -Force` por subcarpeta (Archivos, Respaldos, Restaurados, Evidencias, Informes, Temporales); luego `Test-Path` de cada una |
| 5 | Info del sistema | `Get-CimInstance Win32_ComputerSystem / Win32_OperatingSystem / Win32_Processor`; los campos nulos se muestran como "No disponible" |
| 6 | CPU | Dos muestras de `Win32_PerfRawData_PerfOS_Processor` (_Total) con un intervalo configurable (por defecto 1 s). Evita `Get-Counter`, cuyos nombres se traducen en Windows en español. Botón para generar carga de prueba en BOSGAME y demostrar la variación |
| 7 | RAM | `Win32_OperatingSystem` (TotalVisibleMemorySize/FreePhysicalMemory en KiB) → GiB; la fuente se muestra en la UI |
| 8 | Almacenamiento | `Win32_LogicalDisk -Filter DriveType=3` → capacidad, usado y libre por unidad |
| 9 | Procesos | `Get-Process` → Name, Id, CPU(s), WorkingSet64; filtro para localizar el proceso de prueba |
| 10 | Red | `Get-NetIPConfiguration -Detailed` + `Get-NetAdapter` (MAC); varias interfaces y campos vacíos |
| 11 | Conectividad | Desde el cliente: ping ICMP (`ping -n`) y conexión TCP al puerto SSH con tiempo medido. Se indica el método; "sin respuesta" no se interpreta como "apagado" |
| 12 | Puertos TCP | Escaneo `socket.connect_ex` solo en el rango de la config, en paralelo y con timeout: aceptado / rechazado (RST) / indeterminado (timeout) |
| 13 | Servicios | `Get-Service -Name <lista de config>` con estado real; no se deduce el servicio por el puerto |
| 14 | Administrar servicio | `Start/Stop/Restart-Service` solo sobre el servicio autorizado, seguido de `Get-Service` para verificar |
| 15 | Puerto de práctica | Menú de 5 opciones (ver abajo) |
| 16 | Explorar carpeta | `Get-ChildItem` → nombre, tipo, tamaño, con validación de la ruta efectiva |
| 17 | Crear subcarpeta | Validar el nombre y comprobar con `Test-Path`; si ya existe, se informa sin tocarla |
| 18 | Enviar archivo | SFTP `put` a `<nombre>.part` con callback de progreso → `rename`; SHA-256 local frente a `Get-FileHash` remoto; pregunta antes de sobrescribir |
| 19 | Descargar archivo | SFTP `get` a `.part` local → hash → se renombra solo si coincide |
| 20 | Copiar en BOSGAME | `Copy-Item`; si el nombre existe, se ofrece sobrescribir o crear `archivo (n).ext`; se verifica con el hash |
| 21 | Respaldo | `Compress-Archive` de la carpeta elegida → `Respaldos\<id>_<fecha>.zip` + `manifest.json` (ruta, tamaño, SHA-256, fecha). Se excluyen Respaldos y Restaurados |
| 22 | Restaurar | `Expand-Archive` → `Restaurados\<id_respaldo>\`; se recalculan los hashes y se comparan con el manifiesto archivo por archivo |
| 23 | Limpiar temporales | Listar solo `Temporales` → selección en la UI → confirmación → `Remove-Item` por archivo. Se registra el espacio liberado real (antes/después) y los fallos |
| 24 | Historial e informe | `actividad.csv` local con `op_id` único; se sube a BOSGAME. Si falla, queda como pendiente y se sincroniza por `op_id` sin duplicar. Informe HTML a `Informes` |
| 25 | Ruta revelada | Ruta ingresada en la UI (con espacios, inexistente o sin permiso, con su mensaje) → listar → descargar a `Recuperados` local en solo lectura → comparar hashes |

**Acción 15: plantillas del menú.** Cada instrucción se muestra antes de ejecutarla y su salida después.
1. `Get-NetTCPConnection -State Listen | Select LocalAddress,LocalPort,OwningProcess`
2. `Get-Process -Id <pid>` + `Get-CimInstance Win32_Service -Filter "ProcessId=<pid>"`
3. `Stop-Service -Name <servicio autorizado>`
4. `Stop-Process -Id <pid validado>`: solo si el PID pertenece al proceso o servicio de práctica
5. `Start-Service -Name <servicio>` → comprobar estado, puerto accesible y SSH operativo

Después del cierre se repite `Get-NetTCPConnection` y la prueba TCP (un timeout por sí solo no cuenta como cierre). Si el proceso reaparece, se detecta y se avisa. La evidencia (instrucción, salida y comprobaciones) se guarda en `Evidencias` **antes** de restaurar. "Laboratorio listo" solo se muestra cuando todas las comprobaciones pasan.

**Transferencias (18, 19 y 25).** Se muestran nombre, equipo, origen/destino, tamaño, bytes, %, velocidad actual (ventana móvil de unos 2 s) y promedio en MB/s, tiempo transcurrido, ETA ("calculando…" mientras no hay estimación válida) y estado (conectando, transfiriendo, verificando, completado, cancelado o error). Los tiempos de conexión, transferencia y verificación se miden por separado. Un archivo vacío no provoca divisiones entre cero. La cancelación usa una bandera que el callback revisa y lanza una excepción.

## Fases
0. **Plan en el repo.** Copiar este plan a `docs/PLAN.md` dentro de `core-sync-oac`.
1. **Base (acciones 1–4).** Esqueleto del proyecto, config + keyring, `RemoteBackend` SSH, workers Qt, `OpResult` y registro de actividad, pantalla de conexión, identidad del estudiante, carpeta personal. *Demostrable:* conectar, crear la estructura y ver `identificacion.txt` en BOSGAME.
2. **Monitoreo (5–9).** Dashboard con resumen y pestaña de Monitoreo con refresco manual y automático.
3. **Red y servicios (10–15).** Incluye el módulo completo del puerto de práctica con su secuencia de demostración.
4. **Archivos y mantenimiento (16–23, 25).** Motor de transferencias, respaldos con manifiesto, restauración verificada, limpieza y ruta revelada.
5. **Historial e informe (24).** Cola de pendientes, sincronización idempotente, informe HTML.
6. **Identidad y entrega.** Logo/icono, paleta QSS, tipografía (p. ej. Inter, OFL), pantalla Acerca de con licencias, PyInstaller `.exe`, manual, ficha del producto, matriz de 25 acciones, registro del uso de IA.

**Preparación de BOSGAME (documentar en el manual):** habilitar la capacidad OpenSSH Server, servicio `sshd` en automático, regla de firewall en el 22 y una cuenta con permisos de administrador. Para la defensa: una sesión SSH con una cuenta administradora obtiene un token elevado, sin el filtrado de UAC.

## Dependencias
`PySide6`, `paramiko`, `keyring`, `pydantic`, `pyinstaller` (dev), `pytest` (dev). Requirements fijados en `requirements.txt`.

## Verificación
- **pytest:** validación de identificador y rutas (`..`, `\`, absolutas, UNC), generación de comandos codificados, cálculos de velocidad/ETA (incluido archivo vacío), deduplicación de la cola de pendientes.
- **Pruebas manuales contra BOSGAME** (o una VM Windows con OpenSSH mientras no haya acceso) siguiendo la matriz de aceptación: credenciales incorrectas, usuario sin permisos, host apagado o inalcanzable, ruta inexistente, transferencia interrumpida (desconectar red), archivo vacío, falta de espacio, nombre existente y fallo de restauración.
- **Contrastar cada resultado con el estado real** en BOSGAME (Explorador, `services.msc`, `netstat -ano`, `Get-FileHash`) y guardar las capturas en `Evidencias`.
- **Probar el `.exe` empaquetado** en un Windows limpio y documentar la versión de Windows del cliente.
