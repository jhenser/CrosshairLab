"""CrosshairLab v0.2: non-injected, click-through Windows overlay.

Controls a separately painted top-level transparent window. Does not access
or interfere with any game's memory, rendering process, or network traffic.
"""
import ctypes
import os
from pathlib import Path
import sys

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from model import CrosshairProfile, arm_rectangles, circle_geometry, dot_rectangle

if sys.platform != 'win32':
    raise SystemExit('CrosshairLab supports Windows 10/11 only.')

USER32 = ctypes.windll.user32
VK_RBUTTON, VK_X, VK_CONTROL, VK_MENU = 0x02, 0x58, 0x11, 0x12
WS_EX_TRANSPARENT, WS_EX_LAYERED = 0x20, 0x80000
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80, 0x08000000
GWL_EXSTYLE, HWND_TOPMOST = -20, -1
SWP_NOSIZE, SWP_NOMOVE = 0x0001, 0x0002
SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x0010, 0x0020


def pressed(key):
    return bool(USER32.GetAsyncKeyState(key) & 0x8000)


def settings_path():
    return Path(os.environ.get('APPDATA', str(Path.home()))) / 'CrosshairLab' / 'current.json'


class CrosshairCanvas(QWidget):
    SIZE = 440

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        p = self.profile
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center_x, center_y = self.width() / 2, self.height() / 2
        fg = QColor(p.color)
        fg.setAlpha(p.opacity)
        bg = QColor(p.outline_color)
        bg.setAlpha(p.opacity)

        # Independent horizontal and vertical arms, with optional outline.
        for x, y, w, h in arm_rectangles(p, center_x, center_y):
            if p.outline:
                painter.fillRect(QRectF(x - p.outline, y - p.outline,
                                        w + p.outline * 2, h + p.outline * 2), bg)
            painter.fillRect(QRectF(x, y, w, h), fg)

        # An ellipse is a true circle when both radii are equal.
        ring = circle_geometry(p, center_x, center_y)
        if ring is not None:
            cx, cy, rx, ry, width = ring
            bounds = QRectF(cx - rx, cy - ry, 2 * rx, 2 * ry)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if p.outline:
                pen = QPen(bg)
                pen.setWidthF(width + p.outline * 2)
                painter.setPen(pen)
                painter.drawEllipse(bounds)
            pen = QPen(fg)
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawEllipse(bounds)

        # Draw the central dot last so it remains visible above the ring.
        dot = dot_rectangle(p, center_x, center_y)
        if dot is not None:
            x, y, w, h = dot
            if p.outline:
                painter.fillRect(QRectF(x - p.outline, y - p.outline,
                                        w + p.outline * 2, h + p.outline * 2), bg)
            painter.fillRect(QRectF(x, y, w, h), fg)
        painter.end()


class Overlay(CrosshairCanvas):
    def __init__(self, profile):
        super().__init__(profile)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.update_position()

    def force_clickthrough(self):
        hwnd = int(self.winId())
        current = USER32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        USER32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                             current | WS_EX_TRANSPARENT | WS_EX_LAYERED |
                             WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        USER32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOSIZE | SWP_NOMOVE |
                            SWP_NOACTIVATE | SWP_FRAMECHANGED)

    def update_position(self):
        screens = QGuiApplication.screens()
        if not screens:
            return
        screen = screens[min(self.profile.monitor, len(screens) - 1)]
        rect = screen.geometry()
        x = rect.x() + rect.width() / 2 + self.profile.offset_x
        y = rect.y() + rect.height() / 2 + self.profile.offset_y
        self.move(round(x - self.width() / 2), round(y - self.height() / 2))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.profile = CrosshairProfile.load(settings_path())
        except (OSError, ValueError, TypeError):
            self.profile = CrosshairProfile()
        self.overlay = Overlay(self.profile)
        self.setWindowTitle('CrosshairLab v0.2 — 照準エディター')
        self.resize(1110, 810)
        self._previous_hotkey = False
        self._syncing = False
        self.controls = {}
        self.number_spins = {}

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)

        left = QVBoxLayout()
        outer.addLayout(left, 3)
        tip = QLabel('Ctrl + Alt + X：照準の表示／非表示　｜　設定は終了時に自動保存')
        tip.setWordWrap(True)
        left.addWidget(tip)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        form_stack = QVBoxLayout(content)
        scroll.setWidget(content)
        left.addWidget(scroll, 1)

        grp, form = self.group(form_stack, '横軸（水平線）')
        self.flag(form, '横線を表示', 'horizontal')
        self.numeric(form, '横線の長さ', 'horizontal_length', 0, 130)
        self.numeric(form, '横線と中心の隙間', 'horizontal_gap', 0, 55)
        self.numeric(form, '横線の太さ', 'horizontal_thickness', 1, 24)

        grp, form = self.group(form_stack, '縦軸（垂直線）')
        self.flag(form, '縦線を表示', 'vertical')
        self.numeric(form, '縦線の長さ', 'vertical_length', 0, 130)
        self.numeric(form, '縦線と中心の隙間', 'vertical_gap', 0, 55)
        self.numeric(form, '縦線の太さ', 'vertical_thickness', 1, 24)

        grp, form = self.group(form_stack, '円／楕円')
        self.flag(form, '円形照準を表示', 'circle')
        self.numeric(form, '横半径', 'circle_radius_x', 1, 125)
        self.numeric(form, '縦半径', 'circle_radius_y', 1, 125)
        self.numeric(form, '円の線幅', 'circle_thickness', 1, 24)
        self.numeric(form, '円の横ずれ', 'circle_offset_x', -50, 50)
        self.numeric(form, '円の縦ずれ', 'circle_offset_y', -50, 50)

        grp, form = self.group(form_stack, '中心・色・輪郭')
        self.flag(form, '中心点を表示', 'dot')
        self.numeric(form, '中心点の大きさ', 'dot_size', 1, 30)
        self.numeric(form, '輪郭の太さ', 'outline', 0, 10)
        self.numeric(form, '不透明度', 'opacity', 0, 255)
        for label, key in (('照準色', 'color'), ('輪郭色', 'outline_color')):
            btn = QPushButton(label + 'を変更')
            btn.clicked.connect(lambda checked=False, k=key: self.choose_color(k))
            form.addRow(btn)

        grp, form = self.group(form_stack, '位置・表示')
        self.numeric(form, '画面中心から横へ', 'offset_x', -500, 500)
        self.numeric(form, '画面中心から縦へ', 'offset_y', -500, 500)
        self.flag(form, '右クリック中は非表示（ADS）', 'hide_when_aiming')
        self.screen_combo = QComboBox()
        form.addRow('表示モニター', self.screen_combo)
        self.refresh_screens()
        self.screen_combo.currentIndexChanged.connect(self.monitor_changed)
        app = QGuiApplication.instance()
        app.screenAdded.connect(lambda screen: self.refresh_screens())
        app.screenRemoved.connect(lambda screen: self.refresh_screens())
        form_stack.addStretch()

        actions = QHBoxLayout()
        self.show_btn = QPushButton('照準を非表示')
        self.show_btn.clicked.connect(self.toggle_visibility)
        actions.addWidget(self.show_btn)
        reset = QPushButton('初期値に戻す')
        reset.clicked.connect(self.reset)
        actions.addWidget(reset)
        left.addLayout(actions)

        presets = QHBoxLayout()
        save = QPushButton('プリセット保存')
        save.clicked.connect(self.save_as)
        load = QPushButton('プリセット読込')
        load.clicked.connect(self.load_from)
        presets.addWidget(save)
        presets.addWidget(load)
        left.addLayout(presets)

        right = QVBoxLayout()
        outer.addLayout(right, 2)
        right.addWidget(QLabel('ライブプレビュー'))
        preview_back = QWidget()
        preview_back.setStyleSheet('background-color: #30363D; border-radius: 8px;')
        preview_box = QVBoxLayout(preview_back)
        self.preview = CrosshairCanvas(self.profile)
        preview_box.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        right.addWidget(preview_back, alignment=Qt.AlignmentFlag.AlignTop)
        notice = QLabel('横線・縦線は完全に独立した設定です。\n'
                        '円の横半径と縦半径を同じにすると真円になります。\n\n'
                        'ウィンドウ／ボーダーレス表示を想定。\n'
                        'ゲーム内部の操作や解析は行いません。')
        notice.setWordWrap(True)
        right.addWidget(notice)
        right.addStretch()

        self.tick = QTimer(self)
        self.tick.setInterval(50)
        self.tick.timeout.connect(self.poll)
        self.tick.start()
        self.reposition = QTimer(self)
        self.reposition.setInterval(1500)
        self.reposition.timeout.connect(self.overlay.update_position)
        self.reposition.start()
        self.apply()

    @staticmethod
    def group(stack, title):
        group = QGroupBox(title)
        form = QFormLayout(group)
        stack.addWidget(group)
        return group, form

    def flag(self, form, label, key):
        check = QCheckBox(label)
        check.setChecked(getattr(self.profile, key))
        check.toggled.connect(lambda on, k=key: self.set_value(k, on))
        form.addRow(check)
        self.controls[key] = check

    def numeric(self, form, label, key, low, high):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(getattr(self.profile, key))
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setValue(getattr(self.profile, key))
        spin.setFixedWidth(66)
        row = QHBoxLayout()
        row.addWidget(slider, 1)
        row.addWidget(spin)
        form.addRow(label, row)
        slider.valueChanged.connect(lambda val, k=key: self.set_number(k, val))
        spin.valueChanged.connect(lambda val, k=key: self.set_number(k, val))
        self.controls[key] = slider
        self.number_spins[key] = spin

    def set_number(self, key, val):
        if self._syncing:
            return
        slider = self.controls[key]
        spin = self.number_spins[key]
        for control in (slider, spin):
            if control.value() != val:
                control.blockSignals(True)
                control.setValue(val)
                control.blockSignals(False)
        self.set_value(key, val)

    def set_value(self, key, value):
        if self._syncing:
            return
        setattr(self.profile, key, value)
        self.apply()

    def choose_color(self, key):
        result = QColorDialog.getColor(QColor(getattr(self.profile, key)), self, '色を変更')
        if result.isValid():
            self.set_value(key, result.name().upper())

    def refresh_screens(self):
        self.screen_combo.blockSignals(True)
        self.screen_combo.clear()
        for index, screen in enumerate(QGuiApplication.screens()):
            rect = screen.geometry()
            self.screen_combo.addItem(f'{index + 1}: {screen.name()}  ({rect.width()}×{rect.height()})')
        if self.screen_combo.count():
            self.profile.monitor = min(self.profile.monitor, self.screen_combo.count() - 1)
            self.screen_combo.setCurrentIndex(self.profile.monitor)
        self.screen_combo.blockSignals(False)
        self.overlay.update_position()

    def monitor_changed(self, index):
        if index >= 0:
            self.set_value('monitor', index)

    def apply(self):
        self.preview.update()
        self.overlay.update_position()
        self.overlay.update()
        self.sync_visibility()

    def sync_visibility(self):
        show = self.profile.visible and not (
            self.profile.hide_when_aiming and pressed(VK_RBUTTON))
        if show and not self.overlay.isVisible():
            self.overlay.show()
            self.overlay.force_clickthrough()
        elif not show and self.overlay.isVisible():
            self.overlay.hide()
        self.show_btn.setText('照準を非表示' if self.profile.visible else '照準を表示')

    def poll(self):
        combo = pressed(VK_CONTROL) and pressed(VK_MENU) and pressed(VK_X)
        if combo and not self._previous_hotkey:
            self.toggle_visibility()
        self._previous_hotkey = combo
        if self.profile.hide_when_aiming:
            self.sync_visibility()

    def toggle_visibility(self):
        self.profile.visible = not self.profile.visible
        self.apply()

    def refresh_controls(self):
        self._syncing = True
        try:
            for key, widget in self.controls.items():
                if isinstance(widget, QSlider):
                    widget.setValue(getattr(self.profile, key))
                    self.number_spins[key].setValue(getattr(self.profile, key))
                else:
                    widget.setChecked(getattr(self.profile, key))
            self.refresh_screens()
        finally:
            self._syncing = False
        self.apply()

    def replace_profile(self, profile):
        self.profile = profile
        self.overlay.profile = profile
        self.preview.profile = profile
        self.refresh_controls()

    def reset(self):
        self.replace_profile(CrosshairProfile())

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, 'プリセットを保存',
                                             'crosshair.json', 'JSON (*.json)')
        if path:
            try:
                self.profile.save(path)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, '保存できません', str(exc))

    def load_from(self):
        path, _ = QFileDialog.getOpenFileName(self, 'プリセットを開く',
                                             '', 'JSON (*.json)')
        if path:
            try:
                self.replace_profile(CrosshairProfile.load(path))
            except (OSError, ValueError, TypeError) as exc:
                QMessageBox.warning(self, '読み込めません', str(exc))

    def closeEvent(self, event):
        try:
            self.profile.save(settings_path())
        except (OSError, ValueError):
            pass
        self.overlay.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle('Fusion')
    main_window = MainWindow()
    main_window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
