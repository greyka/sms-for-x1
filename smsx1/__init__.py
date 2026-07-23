"""SMS for X1 — премиальное приложение управления WWAN-модемом ThinkPad X1 Carbon.

Модем: Quectel EM120R-GL (MBIM). SMS/USSD через Windows WinRT (winsdk),
статус и режимы через `netsh mbn`.

Архитектура: MVVM.
  core/        — модели и сервисы (backend, без Qt)
  viewmodels/  — состояние приложения, сигналы
  ui/          — представление (PySide6 + qfluentwidgets)
"""

__version__ = "1.0.0"
__app_name__ = "SMS for X1"
__author__ = "SMS for X1"
