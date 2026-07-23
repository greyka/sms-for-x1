"""Запуск GUI без консольного окна: pythonw run.pyw

Под pythonw нет консоли, поэтому любые ошибки старта пишем в run-error.log
рядом с приложением — иначе окно просто не появится без следов.
"""
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# Защита stdout/stderr под pythonw (дублирует guard в smsx1/__init__, но на всякий)
import io
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

if __name__ == "__main__":
    try:
        from smsx1.app import main
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        log = os.path.join(BASE, "run-error.log")
        try:
            with open(log, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        raise
