"""Minimal example: launch napari with random 3D data and the Volume Spin widget."""

import napari
import numpy as np

from napari_volume_spin._widget import VolumeSpinWidget

viewer = napari.Viewer(ndisplay=3)
viewer.add_image(np.random.rand(64, 64, 64), rendering='mip')

spin_widget = VolumeSpinWidget(viewer)
viewer.window.add_dock_widget(spin_widget, area='right', name='Volume Spin Controls')

napari.run()

viewer.window.add_dock_widget(spin_widget, area='right', name='Imaris Control Center')

napari.run()
