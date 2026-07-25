"""Экраны приложения."""
from .dashboard_page import DashboardPage
from .messages_page import MessagesPage
from .ussd_page import UssdPage
from .modem_page import ModemPage
from .cell_page import CellPage
from .settings_page import SettingsPage

__all__ = ["DashboardPage", "MessagesPage", "UssdPage", "ModemPage",
           "CellPage", "SettingsPage"]
