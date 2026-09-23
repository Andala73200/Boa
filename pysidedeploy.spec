[app]
title = Boa
project_dir = .
input_file = main.py
project_file = pyproject.toml
exec_directory = dist
icon = assets/boa_logo.ico

[python]
python_path = python
packages = nuitka,ordered_set,zstandard

[qt]
qml_files =
excluded_qml_plugins = QtQuick,QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Widgets
plugins = platforms,imageformats

[nuitka]
mode = onefile
extra_args = --quiet --noinclude-qt-translations=True --include-data-dir=boa/i18n=boa/i18n --include-data-dir=boa/resources=boa/resources --include-data-dir=boa/python_importer/indexes=boa/python_importer/indexes --include-data-dir=boa/assets=boa/assets
