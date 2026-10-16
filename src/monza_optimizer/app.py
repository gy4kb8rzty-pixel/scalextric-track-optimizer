"""Application entry point for Monza Optimizer."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Launch the Monza Optimizer desktop application."""
    argv = argv if argv is not None else sys.argv

    from PySide6.QtWidgets import QApplication

    from monza_optimizer.gui.main_window import MainWindow

    app = QApplication(argv)
    app.setApplicationName("Monza Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MonzaOptimizer")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
