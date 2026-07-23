"""Запуск GUI без консольного окна: pythonw run.pyw"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smsx1.app import main

if __name__ == "__main__":
    sys.exit(main())
