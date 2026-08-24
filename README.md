# napari-volume-spin

[![License BSD-3](https://img.shields.io/pypi/l/napari-volume-spin.svg?color=green)](https://github.com/Macl-I/napari-volume-spin/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-volume-spin.svg?color=green)](https://pypi.org/project/napari-volume-spin)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-volume-spin.svg?color=green)](https://python.org)
[![tests](https://github.com/Macl-I/napari-volume-spin/workflows/tests/badge.svg)](https://github.com/Macl-I/napari-volume-spin/actions)
[![codecov](https://codecov.io/gh/Macl-I/napari-volume-spin/branch/main/graph/badge.svg)](https://codecov.io/gh/Macl-I/napari-volume-spin)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-volume-spin)](https://napari-hub.org/plugins/napari-volume-spin)
[![npe2](https://img.shields.io/badge/plugin-npe2-blue?link=https://napari.org/stable/plugins/index.html)](https://napari.org/stable/plugins/index.html)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)

Imaris-style continuous 3D spin animation controls for napari, with looping GIF export

----------------------------------

This [napari] plugin was generated with [copier] using the [napari-plugin-template].

## Features

`napari-volume-spin` adds a **Volume Spin Controls** dock widget that mimics
Imaris's continuous 3D rotation animation:

- **Play / Pause** a continuous spin of the 3D camera around the currently
  viewed volume.
- Choose the screen-relative rotation **axis**: X (pitch), Y (roll), or Z (yaw).
- Adjust **spin speed** (0.1–10.0 degrees/frame) via a linked slider and spin box.
- **Export a looping GIF** of the current axis/speed settings: a full 360°
  rotation is captured automatically so the animation loops seamlessly, and
  you are always prompted for the save location.

## Usage

1. Open napari with a 3D volume layer and switch to 3D display (`ndisplay=3`).
2. Open `Plugins > napari-volume-spin: Volume Spin Controls`.
3. Pick a rotation axis and speed, then click **Play Spin** to start the
   continuous animation.
4. Click **Export Looping GIF...** to render one full rotation loop at the
   current axis/speed to a GIF file of your choosing.

## Installation

You can install `napari-volume-spin` via [pip]:

```bash
pip install napari-volume-spin
```

If napari is not already installed, you can install `napari-volume-spin` with napari and Qt via:

```bash
pip install "napari-volume-spin[all]"
```


To install latest development version:

```bash
pip install git+https://github.com/Macl-I/napari-volume-spin.git
```



## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-volume-spin" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[copier]: https://copier.readthedocs.io/en/stable/
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[napari-plugin-template]: https://github.com/napari/napari-plugin-template

[file an issue]: https://github.com/Macl-I/napari-volume-spin/issues

[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
