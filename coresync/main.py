"""Punto de entrada de CoreSync."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME
from .app.config import AppConfig, ConfigError
from .app.session import Session
from .ui.main_window import MainWindow, app_icon
from .ui.theme import QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(QSS)
    try:
        config = AppConfig.load()
    except ConfigError as e:
        QMessageBox.warning(None, APP_NAME, f"{e}\n\nSe usará una configuración nueva.")
        config = AppConfig()
    session = Session(config)
    win = MainWindow(session)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
