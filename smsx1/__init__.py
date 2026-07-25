"""SMS for X1 — премиальное приложение управления WWAN-модемом ThinkPad X1 Carbon.

Модем: Quectel EM120R-GL (MBIM). SMS/USSD через Windows WinRT (winsdk),
статус и режимы через `netsh mbn`.

Архитектура: MVVM.
  core/        — модели и сервисы (backend, без Qt)
  viewmodels/  — состояние приложения, сигналы
  ui/          — представление (PySide6 + qfluentwidgets)
"""

# ── Защита от pythonw.exe ────────────────────────────────────────────────────
# Под pythonw sys.stdout/stderr == None. Любой print() (в т.ч. баннер
# qfluentwidgets при импорте) уронил бы запуск. Подменяем на безопасный поток
# ДО импорта любых зависимостей, которые могут писать в консоль.
import io as _io
import sys as _sys

if _sys.stdout is None:
    _sys.stdout = _io.StringIO()
if _sys.stderr is None:
    _sys.stderr = _io.StringIO()

__version__ = "1.1.0"
__app_name__ = "SMS for X1"
__author__ = "SMS for X1"
