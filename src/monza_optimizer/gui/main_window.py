"""Main application window shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from monza_optimizer import __version__


class MainWindow(QMainWindow):
    """Primary window for Monza Optimizer 1.0."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Monza Optimizer {__version__}")
        self.resize(1100, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Monza Optimizer 1.0")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 12px;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Scalextric track optimizer — match real circuit outlines "
            "from verified inventory geometry."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        body = QLabel(
            "Milestone 1 shell is running.\n"
            "Geometry, reference matching, optimizer, and export arrive in later milestones."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setStyleSheet("color: #888; margin-top: 24px;")
        layout.addWidget(body)
        layout.addStretch(1)

        status = QStatusBar()
        status.showMessage(f"Ready — v{__version__}")
        self.setStatusBar(status)
