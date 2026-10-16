# PyInstaller mueve los DLL al raíz del bundle. espeakng_loader busca
# espeak-ng.dll y espeak-ng-data junto al paquete, así que el DLL viaja como dato.
import os

from PyInstaller.utils.hooks import collect_data_files, get_package_paths

datas = collect_data_files("espeakng_loader")
_, pkg_dir = get_package_paths("espeakng_loader")
for name in os.listdir(pkg_dir):
    if name.endswith((".dll", ".so", ".dylib")) or ".so." in name:
        datas.append((os.path.join(pkg_dir, name), "espeakng_loader"))
