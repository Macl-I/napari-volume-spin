import numpy as np

from napari_volume_spin._widget import VolumeSpinWidget


def test_widget_builds_ui(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    assert widget.radio_z.isChecked()
    assert widget.axis_group.checkedId() == 2
    assert widget.step_size == 1.0


def test_toggle_spin_starts_and_stops_timer(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    widget._toggle_spin(True)
    assert widget.timer.isActive()

    widget._toggle_spin(False)
    assert not widget.timer.isActive()


def test_slider_and_spinbox_stay_in_sync(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    widget._on_slider_moved(10)
    assert widget.speed_box.value() == 0.5
    assert widget.step_size == 0.5

    widget._on_box_changed(0.25)
    assert widget.speed_slider.value() == 5
    assert widget.step_size == 0.25


def test_axis_vector_matches_selected_radio_button(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    widget.radio_x.setChecked(True)
    assert widget._current_axis_vector() == (1, 0, 0)

    widget.radio_y.setChecked(True)
    assert widget._current_axis_vector() == (0, 1, 0)

    widget.radio_z.setChecked(True)
    assert widget._current_axis_vector() == (0, 0, 1)


def test_export_tab_has_format_and_compress_controls(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    assert [widget.format_combo.itemText(i) for i in range(widget.format_combo.count())] == [
        'GIF',
        'MP4',
    ]
    assert not widget.cancel_export_button.isEnabled()
    assert widget.compress_button.isEnabled()
    assert [
        widget.compression_scheme_combo.itemText(i)
        for i in range(widget.compression_scheme_combo.count())
    ] == ['WebP (Image-based)', 'MP4 (H.264)', 'GIF (Palette)']


def test_axis_loop_combo_only_offers_full_spin_for_3d_only_image(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    assert widget.axis_loop_combo.count() == 1
    assert widget.axis_loop_combo.currentData() is None


def test_axis_loop_combo_offers_extra_dims_for_4d_image(make_napari_viewer):
    viewer = make_napari_viewer(ndisplay=3)
    viewer.add_image(np.random.random((5, 16, 16, 16)))
    widget = VolumeSpinWidget(viewer)

    assert widget.axis_loop_combo.count() == 2
    assert widget.axis_loop_combo.itemData(1) == 0
    assert widget._axis_step_count(0) == 5
