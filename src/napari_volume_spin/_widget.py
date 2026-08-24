"""napari widget for continuous 3D camera spin animation with looping GIF export."""

from typing import TYPE_CHECKING

import imageio
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from vispy.util.quaternion import Quaternion

if TYPE_CHECKING:
    import napari

# Screen-relative unit vectors keyed by the axis_group button id (0=X, 1=Y, 2=Z)
_AXIS_VECTORS = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}


class VolumeSpinWidget(QWidget):
    """Imaris-style continuous spin controls for napari's 3D camera, with looping GIF export."""

    def __init__(self, viewer: 'napari.viewer.Viewer'):
        super().__init__()
        self.viewer = viewer

        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate_camera_relative)
        self.step_size = 1.0  # Degrees per frame

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        self.play_button = QPushButton('Play Spin')
        self.play_button.setCheckable(True)
        self.play_button.clicked.connect(self._toggle_spin)
        layout.addWidget(self.play_button)

        layout.addWidget(QLabel('Rotation Axis (Screen-Relative):'))
        axis_layout = QHBoxLayout()
        self.axis_group = QButtonGroup(self)
        self.radio_x = QRadioButton('X (Pitch)')
        self.radio_y = QRadioButton('Y (Roll)')
        self.radio_z = QRadioButton('Z (Yaw)')
        self.radio_z.setChecked(True)
        for i, radio_button in enumerate([self.radio_x, self.radio_y, self.radio_z]):
            axis_layout.addWidget(radio_button)
            self.axis_group.addButton(radio_button, i)
        layout.addLayout(axis_layout)

        layout.addWidget(QLabel('Spin Speed (Degrees/Frame):'))
        speed_layout = QHBoxLayout()
        self.speed_box = QDoubleSpinBox()
        self.speed_box.setRange(0.05, 1.0)
        self.speed_box.setSingleStep(0.05)
        self.speed_box.setValue(1.0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 20)  # 1-20 maps to 0.05-1.0 deg/frame
        self.speed_slider.setValue(20)
        self.speed_slider.valueChanged.connect(self._on_slider_moved)
        self.speed_box.valueChanged.connect(self._on_box_changed)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_box)
        layout.addLayout(speed_layout)

        layout.addWidget(QLabel('Export Animation:'))
        export_layout = QHBoxLayout()
        export_layout.addWidget(QLabel('FPS:'))
        self.fps_box = QSpinBox()
        self.fps_box.setRange(1, 60)
        self.fps_box.setValue(30)
        export_layout.addWidget(self.fps_box)
        self.export_button = QPushButton('Export Looping GIF...')
        self.export_button.clicked.connect(self._export_gif)
        export_layout.addWidget(self.export_button)
        layout.addLayout(export_layout)

        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _on_slider_moved(self, val):
        self.speed_box.blockSignals(True)
        speed = val * 0.05
        self.speed_box.setValue(speed)
        self.step_size = speed
        self.speed_box.blockSignals(False)

    def _on_box_changed(self, val):
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(round(val / 0.05))
        self.step_size = val
        self.speed_slider.blockSignals(False)

    def _toggle_spin(self, checked):
        if checked:
            self.play_button.setText('Pause Spin')
            self.timer.start(16)  # Target steady ~60 FPS update loop
        else:
            self.play_button.setText('Play Spin')
            self.timer.stop()

    def _get_camera(self):
        # vispy camera access relies on a private napari attribute that may shift between versions
        try:
            return self.viewer.window._qt_viewer.canvas.view.camera
        except AttributeError:
            return None

    def _current_axis_vector(self):
        return _AXIS_VECTORS[self.axis_group.checkedId()]

    def _rotate_camera_relative(self):
        camera = self._get_camera()
        if camera is None:
            return
        delta_rotation = Quaternion.create_from_axis_angle(
            self.step_size, *self._current_axis_vector(), degrees=True
        )
        camera._quaternion = camera._quaternion * delta_rotation
        camera.view_changed()

    def _export_gif(self):
        camera = self._get_camera()
        if camera is None:
            self.status_label.setText('Could not access the 3D camera for export.')
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Looping GIF', '', 'GIF (*.gif)'
        )
        if not path:
            return
        if not path.lower().endswith('.gif'):
            path += '.gif'

        was_playing = self.timer.isActive()
        self.timer.stop()

        axis_vector = self._current_axis_vector()
        n_frames = max(1, round(360.0 / self.step_size))  # one full loop back to start
        fps = self.fps_box.value()
        original_quaternion = camera._quaternion
        delta_rotation = Quaternion.create_from_axis_angle(
            self.step_size, *axis_vector, degrees=True
        )

        self.export_button.setEnabled(False)
        self.status_label.setText(f'Exporting {n_frames} frames...')
        try:
            frames = []
            for _ in range(n_frames):
                camera._quaternion = camera._quaternion * delta_rotation
                camera.view_changed()
                frames.append(self.viewer.screenshot(canvas_only=True))
            imageio.mimsave(path, frames, fps=fps, loop=0)
            self.status_label.setText(f'Saved looping GIF to {path}')
        finally:
            camera._quaternion = original_quaternion
            camera.view_changed()
            self.export_button.setEnabled(True)
            if was_playing:
                self.timer.start(16)
