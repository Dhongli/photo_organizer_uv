#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片/视频自动归档工具 - GUI 版
基于 PyQt6，复用 photo_organizer.py 核心逻辑
"""

import sys
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QCheckBox, QFileDialog, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QTextCursor, QIcon


class LogSignal(QObject):
    """跨线程信号：将日志从工作线程传递到 GUI 线程"""
    message = pyqtSignal(str)
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, int)  # current, total


class OrganizerWorker(threading.Thread):
    """在后台线程运行 photo_organizer.main()"""

    def __init__(self, photo_dir: Path, no_log: bool, signal: LogSignal):
        super().__init__(daemon=True)
        self.photo_dir = photo_dir
        self.no_log = no_log
        self.signal = signal

    def run(self):
        from photo_organizer import main
        try:
            main(self.photo_dir, self.no_log, log_callback=self._on_log)
        except Exception as e:
            self.signal.message.emit(f"[ERROR] {e}")
        finally:
            self.signal.finished.emit({})

    def _on_log(self, line: str):
        self.signal.message.emit(line)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片/视频自动归档工具")
        self.setMinimumSize(700, 520)
        self.resize(800, 600)
        self.worker = None
        self.signal = LogSignal()
        self.signal.message.connect(self._on_log_message)
        self.signal.finished.connect(self._on_finished)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # === 目录选择 ===
        dir_group = QGroupBox("目录设置")
        dir_layout = QHBoxLayout(dir_group)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("选择要整理的照片/视频目录...")
        self.dir_input.setMinimumHeight(32)
        dir_layout.addWidget(self.dir_input)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.setMinimumHeight(32)
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.browse_btn)

        layout.addWidget(dir_group)

        # === 选项 ===
        opt_group = QGroupBox("选项")
        opt_layout = QHBoxLayout(opt_group)
        self.no_log_check = QCheckBox("不生成日志文件")
        opt_layout.addWidget(self.no_log_check)
        opt_layout.addStretch()
        layout.addWidget(opt_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶  开始归档")
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #999; }
        """)
        self.start_btn.clicked.connect(self._start_organize)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  停止")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336; color: white; border: none;
                border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #d32f2f; }
            QPushButton:disabled { background-color: #999; }
        """)
        self.stop_btn.clicked.connect(self._stop_organize)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # === 进度条 ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        self.progress_bar.setMinimumHeight(24)
        layout.addWidget(self.progress_bar)

        # === 日志输出 ===
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #333; border-radius: 4px;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, stretch=1)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择照片/视频目录")
        if d:
            self.dir_input.setText(d)

    def _start_organize(self):
        path_str = self.dir_input.text().strip()
        if not path_str:
            self.log_text.append("⚠️ 请先选择目录")
            return

        photo_dir = Path(path_str)
        if not photo_dir.is_dir():
            self.log_text.append(f"❌ 目录不存在: {path_str}")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("正在扫描...")

        self.worker = OrganizerWorker(
            photo_dir, self.no_log_check.isChecked(), self.signal
        )
        self.worker.start()

    def _stop_organize(self):
        if self.worker and self.worker.is_alive():
            self.log_text.append("\n⚠️ 用户请求停止（等待当前文件处理完成）")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setFormat("已停止")

    def _on_log_message(self, line: str):
        self.log_text.append(line)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

        if "✅ 归档:" in line or "❓ 未识别:" in line:
            self.progress_bar.setMaximum(0)

    def _on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat("完成")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 暗色主题
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(76, 175, 80))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
