# CoreSync

Aplicación de escritorio para monitorear y administrar de forma remota el mini PC **BOSGAME** (Windows) por red local, con evidencias verificables de cada operación.

- Cliente: Python 3.11 + PySide6, en Windows 10/11.
- Mecanismo remoto: OpenSSH Server de Windows, con PowerShell para los comandos (`-EncodedCommand`) y SFTP para las transferencias.
- Configuración en `%APPDATA%\CoreSync\config.json`. La contraseña se guarda solo en el Administrador de credenciales de Windows.

El plan completo está en [`docs/PLAN.md`](docs/PLAN.md).

## Ejecutar en desarrollo
```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python main.py
```

## Pruebas
```powershell
.venv\Scripts\python -m pytest -q
```
Las pruebas de plantillas PowerShell se ejecutan con el `powershell.exe` local mediante un backend de prueba (`tests/conftest.py`). La aplicación nunca usa ese backend.

## Preparar BOSGAME (una sola vez, como administrador)
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service sshd -StartupType Automatic; Start-Service sshd
Get-NetFirewallRule -Name *OpenSSH* | Select Name, Enabled
```

## Estado
- [x] Fase 1: acciones 1–4 (configuración, identificación, conexión/desconexión, carpeta personal)
- [x] Fase 2: monitoreo (5–9)
- [ ] Fase 3: red, servicios y puerto de práctica (10–15)
- [ ] Fase 4: archivos, respaldos y ruta revelada (16–23, 25)
- [ ] Fase 5: historial sincronizado e informe (24)
- [ ] Fase 6: identidad final, ejecutable y documentación
