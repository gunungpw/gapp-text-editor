import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QStatusBar,
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QLabel,
    QMenu,
    QMenuBar,
    QMessageBox,
)
from PySide6.QtGui import QShortcut, QKeySequence, QPainter, QAction
from PySide6.QtCore import Qt, QRect


class LineNumberArea(QWidget):
    """Widget to display line numbers for the text editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.text_editor = editor
        self.setFixedWidth(self._calculate_width())

    def _calculate_width(self):
        """Calculate the width needed for line numbers based on maximum lines."""
        digits = len(str(max(1, self.text_editor.document().blockCount())))
        return 10 + digits * self.text_editor.fontMetrics().horizontalAdvance("9")

    def paintEvent(self, event):
        """Paint the line numbers."""
        if not self.text_editor.show_line_numbers:
            return

        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.text_editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.text_editor.blockBoundingGeometry(block).translated(self.text_editor.contentOffset()).top()
        bottom = top + self.text_editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    0,
                    int(top),
                    self.width(),
                    self.text_editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignLeft,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + self.text_editor.blockBoundingRect(block).height()
            block_number += 1

    def update_width(self):
        """Update the width of the line number area."""
        self.setFixedWidth(self._calculate_width())


class TextEditor(QTextEdit):
    """Custom text editor widget with line number support."""

    def __init__(self):
        super().__init__()
        self.current_file_path = ""
        self.show_line_numbers = True
        self.setUndoRedoEnabled(True)
        self.line_number_area = LineNumberArea(self)
        self.document().blockCountChanged.connect(self.line_number_area.update_width)
        self.textChanged.connect(self.line_number_area.update)
        self.verticalScrollBar().valueChanged.connect(self.line_number_area.update)
        self.update_margins()

    def update_margins(self):
        """Update the left margin based on line number visibility."""
        if self.show_line_numbers:
            self.setViewportMargins(self.line_number_area.width(), 0, 0, 0)
        else:
            self.setViewportMargins(0, 0, 0, 0)
        self.line_number_area.setVisible(self.show_line_numbers)

    def toggle_line_numbers(self):
        """Toggle the visibility of line numbers."""
        self.show_line_numbers = not self.show_line_numbers
        self.update_margins()
        self.line_number_area.update()

    def resizeEvent(self, event):
        """Adjust the line number area geometry when the editor is resized."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area.width(), cr.height()))


class StatusBar(QStatusBar):
    """Custom status bar displaying file information."""

    def __init__(self, text_editor):
        super().__init__()
        self.file_label = QLabel(text_editor.current_file_path or "No file open")
        self.addWidget(self.file_label)

        text_editor.textChanged.connect(self._update_file_label)
        self._text_editor = text_editor

    def _update_file_label(self):
        """Update the file label when the current file changes."""
        self.file_label.setText(self._text_editor.current_file_path or "No file open")


class FileMenu(QMenu):
    """File menu containing file operations."""

    def __init__(self, parent, text_editor):
        super().__init__("File", parent)
        self.text_editor = text_editor
        self._setup_actions()

    def _setup_actions(self):
        """Set up file menu actions."""
        actions = [
            ("Open", "Ctrl+O", self._open_file),
            ("Save", "Ctrl+S", self._save_file),
            ("Save As", None, self._save_as_file),
        ]

        for name, shortcut, handler in actions:
            action = QAction(name, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(handler)
            self.addAction(action)

    def _open_file(self):
        """Open a file and load its content."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(self.parent(), "Open File", "", "Text Files (*.txt)")
            if file_path:
                with open(file_path, "r", encoding="utf-8") as file:
                    self.text_editor.setPlainText(file.read())
                self.text_editor.current_file_path = file_path
                self.parent().parent().statusBar().showMessage(f"Opened: {file_path}", 5000)
        except Exception as e:
            self.parent().parent().statusBar().showMessage(f"Error opening file: {str(e)}", 5000)

    def _save_file(self):
        """Save the current file."""
        self.parent().parent().save_file()

    def _save_as_file(self):
        """Save file with a new name."""
        self.parent().parent()._save_as_file()


class ViewMenu(QMenu):
    """View menu for toggling editor features."""

    def __init__(self, parent, text_editor):
        super().__init__("View", parent)
        self.text_editor = text_editor
        self._setup_actions()

    def _setup_actions(self):
        """Set up view menu actions."""
        toggle_line_numbers = QAction("Show Line Numbers", self, checkable=True)
        toggle_line_numbers.setChecked(self.text_editor.show_line_numbers)
        toggle_line_numbers.triggered.connect(self.text_editor.toggle_line_numbers)
        self.addAction(toggle_line_numbers)


class MenuBar(QMenuBar):
    """Custom menu bar for the application."""

    def __init__(self, parent, text_editor):
        super().__init__(parent)
        self.text_editor = text_editor
        self._setup_menus()

    def _setup_menus(self):
        """Set up all menu items."""
        self.addMenu(FileMenu(self, self.text_editor))
        self.addMenu(ViewMenu(self, self.text_editor))
        self.addMenu(self._create_about_menu())

    def _create_about_menu(self):
        """Create the About menu."""
        about_menu = QMenu("About", self)
        about_action = about_menu.addAction("About Gapp Text Editor")
        about_action.triggered.connect(self._show_about_dialog)
        return about_menu

    def _show_about_dialog(self):
        """Display the About dialog."""
        QMessageBox.about(
            self.parent(),
            "About Gapp Text Editor",
            "Gapp Text Editor\nVersion 1.0.0\nA simple text editor built with PySide6.\n© 2025",
        )


class MainWindow(QMainWindow):
    """Main window for the text editor application."""

    def __init__(self):
        super().__init__()
        self.text_editor = TextEditor()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Gapp Text Editor")
        self.resize(QApplication.primaryScreen().size().width() - 20, QApplication.primaryScreen().size().height() - 75)

        # Set up layout
        self.text_editor_layout = QVBoxLayout()
        self.text_editor_layout.addWidget(self.text_editor)

        # Create container widget
        container = QWidget()
        container.setLayout(self.text_editor_layout)
        self.setCentralWidget(container)

        # Set up menu and status bars
        self.setMenuBar(MenuBar(self, self.text_editor))
        self.setStatusBar(StatusBar(self.text_editor))

        # Set up shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Configure keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.new_file)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)

    def save_file(self):
        """Save the current file content."""
        try:
            text = self.text_editor.toPlainText()
            file_path = self.text_editor.current_file_path
            if file_path:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(text)
            else:
                self._save_as_file()
        except Exception as e:
            self.statusBar().showMessage(f"Error saving file: {str(e)}", 5000)

    def new_file(self):
        """Create a new file."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Create a new file", "NewFile.txt", "Text Files (*.txt)")
            if file_path:
                self.text_editor.clear()
                self.text_editor.current_file_path = file_path
        except Exception as e:
            self.statusBar().showMessage(f"Error creating new file: {str(e)}", 5000)

    def _save_as_file(self):
        """Save file with a new name."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "NewFile.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(self.text_editor.toPlainText())
                self.text_editor.current_file_path = file_path
            except Exception as e:
                self.statusBar().showMessage(f"Error saving file: {str(e)}", 5000)


def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
