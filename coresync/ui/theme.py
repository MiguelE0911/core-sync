"""Identidad visual de CoreSync: paleta, tipografía y estados (texto + color)."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel

PALETTE = {
    "navy": "#0B1F33",
    "navy_2": "#12304D",
    "teal": "#14B8A6",
    "teal_dark": "#0F766E",
    "bg": "#F4F7FA",
    "card": "#FFFFFF",
    "text": "#1E293B",
    "muted": "#64748B",
    "border": "#D9E2EC",
    "ok": "#15803D",
    "warn": "#B45309",
    "error": "#B91C1C",
    "info": "#1D4ED8",
}

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; color: {PALETTE['text']}; }}
QMainWindow, QWidget#content {{ background: {PALETTE['bg']}; }}
QListWidget#nav {{
    background: {PALETTE['navy']}; border: none; padding-top: 8px; outline: 0;
}}
QListWidget#nav::item {{ color: #CBD5E1; padding: 10px 14px; border-left: 3px solid transparent; }}
QListWidget#nav::item:selected {{
    background: {PALETTE['navy_2']}; color: white; border-left: 3px solid {PALETTE['teal']};
}}
QWidget#header {{ background: {PALETTE['card']}; border-bottom: 1px solid {PALETTE['border']}; }}
QLabel#title {{ font-size: 15pt; font-weight: 600; }}
QLabel#muted {{ color: {PALETTE['muted']}; }}
QGroupBox {{
    background: {PALETTE['card']}; border: 1px solid {PALETTE['border']}; border-radius: 8px;
    margin-top: 14px; padding: 12px 10px 10px 10px; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {PALETTE['teal_dark']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTableWidget {{
    background: white; border: 1px solid {PALETTE['border']}; border-radius: 5px; padding: 4px;
}}
QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {PALETTE['teal']}; }}
QLineEdit[invalid="true"] {{ border: 1px solid {PALETTE['error']}; }}
QPushButton {{
    background: {PALETTE['teal_dark']}; color: white; border: none; border-radius: 5px; padding: 7px 14px;
}}
QPushButton:hover {{ background: {PALETTE['teal']}; }}
QPushButton:disabled {{ background: #94A3B8; color: #E2E8F0; }}
QPushButton[flat="true"] {{ background: transparent; color: {PALETTE['teal_dark']}; border: 1px solid {PALETTE['teal_dark']}; }}
QPlainTextEdit#console {{ font-family: "Cascadia Mono", "Consolas", monospace; font-size: 9pt; background: #0F172A; color: #E2E8F0; }}
QHeaderView::section {{ background: {PALETTE['bg']}; border: none; border-bottom: 1px solid {PALETTE['border']}; padding: 4px; font-weight: 600; }}
"""

# estado -> (símbolo, color). El texto siempre acompaña al color.
STATUS = {
    "conectado": ("●", PALETTE["ok"]),
    "desconectado": ("○", PALETTE["muted"]),
    "conectando": ("◌", PALETTE["info"]),
    "verificado": ("✔", PALETTE["ok"]),
    "ejecutado": ("◐", PALETTE["warn"]),
    "error": ("✖", PALETTE["error"]),
    "no ejecutado": ("–", PALETTE["muted"]),
    "advertencia": ("▲", PALETTE["warn"]),
}


class StatusBadge(QLabel):
    def set_status(self, key: str, text: str | None = None) -> None:
        sym, color = STATUS.get(key, ("•", PALETTE["muted"]))
        self.setText(f"{sym} {text or key.capitalize()}")
        self.setStyleSheet(f"color: {color}; font-weight: 600;")
