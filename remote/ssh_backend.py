"""Implementación SSH + SFTP (OpenSSH Server de Windows) con paramiko."""
from __future__ import annotations

import base64
import hashlib
import socket
import threading
import time
from pathlib import Path

import paramiko

from remote.backend import ConnectParams, ProgressCallback, RemoteBackend, RemoteError, UnknownHostKey
from remote.ps import PSResult, encode_command, wrap


def to_sftp_path(win_path: str) -> str:
    """C:\\Lab\\x.txt -> /C:/Lab/x.txt (formato que acepta el SFTP de OpenSSH para Windows)."""
    return "/" + win_path.replace("\\", "/")


def key_fingerprint(key: paramiko.PKey) -> str:
    return base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")


class _RejectUnknown(paramiko.MissingHostKeyPolicy):
    """No acepta claves nuevas en silencio: la interfaz pide confirmación (TOFU)."""

    def missing_host_key(self, client, hostname, key):
        raise UnknownHostKey(hostname, key.get_name(), key_fingerprint(key), key)


class SSHBackend(RemoteBackend):
    name = "OpenSSH (SSH + SFTP)"

    def __init__(self, known_hosts_path: Path):
        self._known_hosts = Path(known_hosts_path)
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._sftp_lock = threading.Lock()
        self._params: ConnectParams | None = None

    # -- huellas -----------------------------------------------------------
    def trust_host_key(self, address: str, port: int, key: paramiko.PKey) -> None:
        self._known_hosts.parent.mkdir(parents=True, exist_ok=True)
        hk = paramiko.HostKeys()
        if self._known_hosts.exists():
            hk.load(str(self._known_hosts))
        entry = address if port == 22 else f"[{address}]:{port}"
        hk.add(entry, key.get_name(), key)
        hk.save(str(self._known_hosts))

    # -- conexión ------------------------------------------------------------
    def connect(self, params: ConnectParams) -> None:
        self.close()
        client = paramiko.SSHClient()
        if self._known_hosts.exists():
            client.load_host_keys(str(self._known_hosts))
        client.set_missing_host_key_policy(_RejectUnknown())
        try:
            client.connect(
                hostname=params.address,
                port=params.port,
                username=params.username,
                password=params.password,
                timeout=params.timeout_s,
                banner_timeout=params.timeout_s,
                auth_timeout=params.timeout_s,
                allow_agent=False,
                look_for_keys=False,
            )
        except UnknownHostKey:
            client.close()
            raise
        except paramiko.BadHostKeyException as e:
            client.close()
            raise RemoteError(
                "La huella del equipo cambió respecto a la guardada.",
                "Puede ser una reinstalación de BOSGAME o un equipo distinto. Verifícalo con el docente.",
            ) from e
        except paramiko.AuthenticationException as e:
            client.close()
            raise RemoteError("Autenticación rechazada.", "Revisa usuario y contraseña.") from e
        except socket.gaierror as e:
            client.close()
            raise RemoteError(f"No se pudo resolver '{params.address}'.", "Usa la IP o revisa el nombre.") from e
        except ConnectionRefusedError as e:
            client.close()
            raise RemoteError(
                f"Conexión rechazada en el puerto {params.port}.",
                "El equipo respondió, pero sshd no escucha en ese puerto o el firewall lo rechaza.",
            ) from e
        except (socket.timeout, TimeoutError) as e:
            client.close()
            raise RemoteError(
                "Sin respuesta dentro del tiempo de espera.",
                "Verifica IP, red y firewall. No significa necesariamente que el equipo esté apagado.",
            ) from e
        except (paramiko.SSHException, OSError) as e:
            client.close()
            raise RemoteError(f"Error de conexión: {e}") from e
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(15)
        self._client = client
        self._params = params

    def close(self) -> None:
        with self._sftp_lock:
            if self._sftp is not None:
                try:
                    self._sftp.close()
                finally:
                    self._sftp = None
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def is_connected(self) -> bool:
        t = self._client.get_transport() if self._client else None
        return bool(t and t.is_active() and t.is_authenticated())

    def _require(self) -> paramiko.SSHClient:
        if not self.is_connected():
            raise RemoteError("No hay sesión remota activa.", "Conéctate desde 'Conexión y estudiante'.")
        return self._client  # type: ignore[return-value]

    # -- comandos ------------------------------------------------------------
    def run_ps(self, body: str, timeout_s: float = 60.0) -> PSResult:
        client = self._require()
        cmd = encode_command(wrap(body))
        t0 = time.perf_counter()
        try:
            _stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout_s)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
        except (socket.timeout, TimeoutError) as e:
            raise RemoteError(f"El comando superó {timeout_s:.0f} s sin terminar.") from e
        except (paramiko.SSHException, OSError) as e:
            raise RemoteError(f"Se perdió la sesión remota: {e}", "Vuelve a conectar.") from e
        return PSResult.parse(body, code, out, err, time.perf_counter() - t0)

    # -- archivos ------------------------------------------------------------
    def _sftp_client(self) -> paramiko.SFTPClient:
        client = self._require()
        with self._sftp_lock:
            if self._sftp is None:
                self._sftp = client.open_sftp()
            return self._sftp

    def upload(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        self._sftp_client().put(local_path, to_sftp_path(remote_path), callback=progress, confirm=True)

    def download(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        self._sftp_client().get(to_sftp_path(remote_path), local_path, callback=progress)

    def rename(self, remote_src: str, remote_dst: str) -> None:
        self._sftp_client().posix_rename(to_sftp_path(remote_src), to_sftp_path(remote_dst))
