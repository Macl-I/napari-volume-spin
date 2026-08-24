"""napari widget for continuous 3D camera spin animation with looping GIF/MP4 export."""

from pathlib import Path
from typing import TYPE_CHECKING

import imageio
import numpy as np
from napari.qt.threading import thread_worker
from napari.utils import progress
from PIL import Image
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from vispy.util.quaternion import Quaternion

if TYPE_CHECKING:
    import napari

# Screen-relative unit vectors keyed by the axis_group button id (0=X, 1=Y, 2=Z)
_AXIS_VECTORS = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}

# Save-dialog filter and file extension keyed by the export format combo box text
_FORMAT_FILTERS = {'GIF': 'GIF (*.gif)', 'MP4': 'MP4 (*.mp4)'}
_FORMAT_EXTENSIONS = {'GIF': '.gif', 'MP4': '.mp4'}

# Compression schemes offered for shrinking an existing animation, and their file extensions.
# WebP/MP4 use lossy per-frame (JPEG-like) or DCT-based compression instead of GIF's 256-color
# palette, which is what caused the previous "choppy" banding/dithering artifacts.
_COMPRESSION_EXTENSIONS = {
    'WebP (Image-based)': '.webp',
    'MP4 (H.264)': '.mp4',
    'GIF (Palette)': '.gif',
}
_MAX_COMPRESSED_BYTES = 25 * 1024 * 1024  # napari-hub/e-mail-friendly target
_MIN_COMPRESSED_FPS = 24  # never drop below this to avoid choppy playback
# (scale, quality) tiers tried from highest to lowest quality until the file size target is hit
_COMPRESSION_TIERS = [
    (1.0, 90),
    (1.0, 75),
    (0.75, 75),
    (0.75, 60),
    (0.5, 60),
    (0.5, 45),
    (0.35, 35),
]


def _resized_frame(frame, scale):
    if scale >= 0.999:
        return frame
    image = Image.fromarray(frame).convert('RGB')
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return np.array(image.resize(new_size, Image.LANCZOS))


def _write_compressed(path, frames, fps, scheme, scale, quality):
    resized = [_resized_frame(frame, scale) for frame in frames]
    if scheme == 'MP4 (H.264)':
        imageio.mimsave(path, resized, fps=fps, codec='libx264', quality=quality / 10)
    elif scheme == 'WebP (Image-based)':
        pil_frames = [Image.fromarray(frame).convert('RGB') for frame in resized]
        pil_frames[0].save(
            path,
            format='WEBP',
            save_all=True,
            append_images=pil_frames[1:],
            duration=round(1000 / fps),
            loop=0,
            quality=quality,
            method=6,
        )
    else:  # 'GIF (Palette)'
        palette_size = max(32, round(quality / 100 * 256))
        imageio.mimsave(path, resized, fps=fps, loop=0, palettesize=palette_size)


class VolumeSpinWidget(QWidget):
    """Imaris-style continuous spin controls for napari's 3D camera, with looping GIF/MP4 export."""

    def __init__(self, viewer: 'napari.viewer.Viewer'):
        super().__init__()
        self.viewer = viewer

        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate_camera_relative)
        self.step_size = 1.0  # Degrees per frame

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self._build_spin_tab(), 'Spin Controls')
        tabs.addTab(self._build_export_tab(), 'Export')
        tabs.addTab(self._build_compress_tab(), 'Compress')
        layout.addWidget(tabs)

        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _build_spin_tab(self):
        tab = QWidget()
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

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Export Animation:'))
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel('Format:'))
        self.format_combo = QComboBox()
        self.format_combo.addItems(['GIF', 'MP4'])
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(QLabel('FPS:'))
        self.fps_box = QSpinBox()
        self.fps_box.setRange(1, 60)
        self.fps_box.setValue(30)
        format_layout.addWidget(self.fps_box)
        layout.addLayout(format_layout)

        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel('Loop Axis:'))
        self.axis_loop_combo = QComboBox()
        axis_layout.addWidget(self.axis_loop_combo)
        layout.addLayout(axis_layout)
        self._refresh_axis_loop_combo()
        self.viewer.dims.events.ndim.connect(self._on_dims_ndim_changed)

        export_buttons_layout = QHBoxLayout()
        self.export_button = QPushButton('Export Looping Animation...')
        self.export_button.clicked.connect(self._export_animation)
        export_buttons_layout.addWidget(self.export_button)
        self.cancel_export_button = QPushButton('Cancel')
        self.cancel_export_button.setEnabled(False)
        self.cancel_export_button.clicked.connect(self._cancel_export)
        export_buttons_layout.addWidget(self.cancel_export_button)
        layout.addLayout(export_buttons_layout)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_compress_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Reduce File Size (e.g. for e-mail attachments, target <25 MB):'))
        compress_layout = QHBoxLayout()
        compress_layout.addWidget(QLabel('Scheme:'))
        self.compression_scheme_combo = QComboBox()
        self.compression_scheme_combo.addItems(list(_COMPRESSION_EXTENSIONS))
        compress_layout.addWidget(self.compression_scheme_combo)
        layout.addLayout(compress_layout)
        self.compress_button = QPushButton('Compress Animation...')
        self.compress_button.clicked.connect(self._compress_animation)
        layout.addWidget(self.compress_button)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _on_dims_ndim_changed(self, event=None):
        self._refresh_axis_loop_combo()

    def _refresh_axis_loop_combo(self):
        # Lets the user loop through an extra (e.g. time) axis of a multi-dimensional image during export
        self.axis_loop_combo.blockSignals(True)
        self.axis_loop_combo.clear()
        self.axis_loop_combo.addItem('Full 360\u00b0 Spin (no extra axis)', None)
        dims = self.viewer.dims
        for axis in dims.not_displayed:
            label = dims.axis_labels[axis]
            text = f'Axis {axis}' if label == str(axis) else f'Axis {axis} ({label})'
            self.axis_loop_combo.addItem(text, axis)
        self.axis_loop_combo.blockSignals(False)

    def _axis_step_count(self, axis):
        start, stop, step = self.viewer.dims.range[axis]
        return max(1, int(round((stop - start) / step)) + 1)

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

    def _export_animation(self):
        camera = self._get_camera()
        if camera is None:
            self.status_label.setText('Could not access the 3D camera for export.')
            return

        fmt = self.format_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Looping Animation', '', _FORMAT_FILTERS[fmt]
        )
        if not path:
            return
        if not path.lower().endswith(_FORMAT_EXTENSIONS[fmt]):
            path += _FORMAT_EXTENSIONS[fmt]

        loop_axis = self.axis_loop_combo.currentData()

        self._export_format = fmt
        self._export_camera = camera
        self._export_was_playing = self.timer.isActive()
        self.timer.stop()

        self._export_original_quaternion = camera._quaternion
        self._export_delta_rotation = Quaternion.create_from_axis_angle(
            self.step_size, *self._current_axis_vector(), degrees=True
        )
        self._export_axis = loop_axis
        if loop_axis is None:
            self._export_n_frames = max(1, round(360.0 / self.step_size))  # one full loop back to start
            self._export_axis_original_step = None
            desc = f'Capturing {fmt} frames'
        else:
            self._export_n_frames = self._axis_step_count(loop_axis)
            self._export_axis_original_step = self.viewer.dims.current_step[loop_axis]
            desc = f'Capturing {fmt} frames (looping axis {loop_axis})'

        self._export_fps = self.fps_box.value()
        self._export_path = path
        self._export_frames = []
        self._export_frame_index = 0
        self._export_cancelled = False
        self._export_progress = progress(total=self._export_n_frames, desc=desc)

        self.export_button.setEnabled(False)
        self.cancel_export_button.setEnabled(True)
        self.status_label.setText(f'Capturing {self._export_n_frames} frames...')
        self._capture_next_frame()

    def _capture_next_frame(self):
        if self._export_cancelled or self._export_frame_index >= self._export_n_frames:
            self._export_progress.close()
            self._finish_capture()
            return

        camera = self._export_camera
        camera._quaternion = camera._quaternion * self._export_delta_rotation
        camera.view_changed()
        if self._export_axis is not None:
            self.viewer.dims.set_current_step(self._export_axis, self._export_frame_index)
        self._export_frames.append(self.viewer.screenshot(canvas_only=True))
        self._export_frame_index += 1
        self._export_progress.update(1)

        # Schedule via the Qt event loop (rather than a blocking loop) so the progress bar repaints and Cancel stays clickable
        QTimer.singleShot(0, self._capture_next_frame)

    def _cancel_export(self):
        self._export_cancelled = True

    def _finish_capture(self):
        camera = self._export_camera
        camera._quaternion = self._export_original_quaternion
        camera.view_changed()
        if self._export_axis is not None and self._export_axis_original_step is not None:
            self.viewer.dims.set_current_step(self._export_axis, self._export_axis_original_step)
        if self._export_was_playing:
            self.timer.start(16)

        if self._export_cancelled or not self._export_frames:
            self.status_label.setText('Export cancelled.')
            self.export_button.setEnabled(True)
            self.cancel_export_button.setEnabled(False)
            return

        self.status_label.setText(f'Encoding {self._export_format} in the background...')
        self.cancel_export_button.setEnabled(False)
        worker = self._encode_animation(
            self._export_path, self._export_frames, self._export_fps, self._export_format
        )
        worker.returned.connect(self._on_export_finished)
        worker.errored.connect(self._on_export_errored)
        self._export_worker = worker  # keep a reference so the thread isn't garbage-collected
        worker.start()

    @thread_worker
    def _encode_animation(self, path, frames, fps, fmt):
        if fmt == 'GIF':
            imageio.mimsave(path, frames, fps=fps, loop=0)
        else:
            imageio.mimsave(path, frames, fps=fps, codec='libx264', quality=8)
        return path

    def _on_export_finished(self, path):
        self.status_label.setText(f'Saved looping animation to {path}')
        self.export_button.setEnabled(True)

    def _on_export_errored(self, exc):
        self.status_label.setText(f'Export failed: {exc}')
        self.export_button.setEnabled(True)

    def _compress_animation(self):
        input_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Animation to Compress', '',
            'Animations (*.gif *.mp4 *.mov *.avi *.webp)'
        )
        if not input_path:
            return

        scheme = self.compression_scheme_combo.currentText()
        extension = _COMPRESSION_EXTENSIONS[scheme]
        output_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Compressed Animation', '', f'{scheme} (*{extension})'
        )
        if not output_path:
            return
        if not output_path.lower().endswith(extension):
            output_path += extension

        self.compress_button.setEnabled(False)
        self.status_label.setText(f'Compressing to {scheme}...')
        worker = self._compress_animation_worker(input_path, output_path, scheme)
        worker.returned.connect(self._on_compress_finished)
        worker.errored.connect(self._on_compress_errored)
        self._compress_worker = worker  # keep a reference so the thread isn't garbage-collected
        worker.start()

    @thread_worker
    def _compress_animation_worker(self, input_path, output_path, scheme):
        original_size = Path(input_path).stat().st_size

        reader = imageio.get_reader(input_path)
        source_fps = reader.get_meta_data().get('fps', _MIN_COMPRESSED_FPS)
        frames = [frame for frame in reader]
        reader.close()
        fps = max(round(source_fps), _MIN_COMPRESSED_FPS)  # never go choppier than this

        compressed_size = original_size
        for scale, quality in _COMPRESSION_TIERS:
            _write_compressed(output_path, frames, fps, scheme, scale, quality)
            compressed_size = Path(output_path).stat().st_size
            if compressed_size <= _MAX_COMPRESSED_BYTES:
                break

        return output_path, original_size, compressed_size, fps

    def _on_compress_finished(self, result):
        output_path, original_size, compressed_size, fps = result
        savings = (1 - compressed_size / original_size) * 100 if original_size else 0
        size_note = (
            'under the 25 MB target' if compressed_size <= _MAX_COMPRESSED_BYTES
            else 'still above the 25 MB target even at lowest quality'
        )
        self.status_label.setText(
            f'Compressed animation saved to {output_path} at {fps} fps '
            f'({original_size // 1024} KB \u2192 {compressed_size // 1024} KB, '
            f'{savings:.0f}% smaller, {size_note})'
        )
        self.compress_button.setEnabled(True)

    def _on_compress_errored(self, exc):
        self.status_label.setText(f'Compression failed: {exc}')
        self.compress_button.setEnabled(True)
