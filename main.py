# main.py
import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """
    Main entry point for the Seismic Monitoring System application.
    Initializes the Qt Application loop and displays the main window.
    """
    app = QApplication(sys.argv)

    # Instantiate and display the main window
    window = MainWindow()
    window.show()

    # Execute the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()