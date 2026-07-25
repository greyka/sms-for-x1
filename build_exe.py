"""Сборка standalone .exe (PyInstaller) с вшитой иконкой.

Запуск: python build_exe.py
Результат: dist/SMS for X1/SMS for X1.exe
"""
import PyInstaller.__main__
from pathlib import Path

HERE = Path(__file__).resolve().parent

PyInstaller.__main__.run([
    "run.pyw",
    "--name=SMS for X1",
    "--noconfirm",
    "--clean",
    "--windowed",                       # без консольного окна
    "--onedir",                         # каталог (быстрый старт, надёжнее onefile)
    f"--icon={HERE / 'assets' / 'icon.ico'}",
    f"--add-data={HERE / 'assets'}{';'}assets",
    "--collect-all=qfluentwidgets",
    "--collect-all=qframelesswindow",
    "--collect-submodules=winsdk",
    "--collect-submodules=winrt",
    "--exclude-module=tkinter",
    "--exclude-module=pytest",
])
