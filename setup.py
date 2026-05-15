"""
Build script for the C++ solver extension module.

Usage:
    pip install -e .
    # or
    python setup.py build_ext --inplace
"""

import os
import sys
import subprocess
from pathlib import Path

from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    """A CMake-based extension module."""
    def __init__(self, name, sourcedir=""):
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())


class CMakeBuild(build_ext):
    """Custom build command that invokes CMake."""

    def build_extension(self, ext):
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)
        extdir = ext_fullpath.parent.resolve()

        cfg = "Release"
        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",
            "-DBUILD_TESTS=OFF",
            "-DBUILD_PYTHON_BINDINGS=ON",
        ]
        build_args = ["--config", cfg, "-j"]

        build_temp = Path(self.build_temp) / ext.name
        build_temp.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["cmake", ext.sourcedir, *cmake_args],
            cwd=build_temp,
            check=True,
        )
        subprocess.run(
            ["cmake", "--build", ".", *build_args],
            cwd=build_temp,
            check=True,
        )


setup(
    name="network3tier",
    version="0.2.0",
    description="Network 3-Tier Optimizer with C++ LNS Solver",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=[CMakeExtension("network3tier._solver_core", sourcedir="cpp")],
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.9",
    install_requires=[
        "pandas>=1.5",
        "openpyxl>=3.0",
        "xlrd>=2.0",
    ],
)
