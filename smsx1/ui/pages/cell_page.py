"""Экран «БС» — параметры обслуживающей базовой станции (соты)."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout

from qfluentwidgets import CaptionLabel, ProgressBar, StrongBodyLabel, TransparentToolButton
from qfluentwidgets import FluentIcon as FIF

from ...config import THEME
from ...core.models import ModemStatus
from ..components import GlassCard, MetricRow, StatusBadge
from ..components.section import SectionHeader
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class CellPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__("cellPage", "Базовая станция",
                         "Параметры обслуживающей соты (BS)",
                         crumbs=["SMS for X1", "БС"], parent=parent)
        self.state = state

        top = QHBoxLayout()
        top.addWidget(SectionHeader("Обслуживающая сота",
                                    "Диапазон, идентификаторы, качество сигнала"))
        top.addStretch(1)
        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setToolTip("Обновить")
        self.refresh_btn.clicked.connect(self.state.refresh_status)
        top.addWidget(self.refresh_btn)
        self.body().addLayout(top)

        self.body().addWidget(self._cell_card())
        self.state.statusChanged.connect(self._update)

    def _cell_card(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)

        head = QHBoxLayout()
        self.tech = StrongBodyLabel("—", card)
        self.tech.setStyleSheet("font-size: 26px; font-weight: 700;")
        head.addWidget(self.tech)
        head.addStretch(1)
        self.badge = StatusBadge("Нет данных", "muted")
        head.addWidget(self.badge)
        card.body().addLayout(head)

        self.quality = ProgressBar(card)
        self.quality.setValue(0)
        self.quality.setFixedHeight(6)
        card.body().addWidget(self.quality)
        card.body().addSpacing(S.md)

        grid = QGridLayout()
        grid.setHorizontalSpacing(S.xxl)
        grid.setVerticalSpacing(2)
        self.m_band = MetricRow("Диапазон (Band)", "—")
        self.m_cid = MetricRow("Cell ID", "—", mono=True)
        self.m_pci = MetricRow("PCI", "—", mono=True)
        self.m_earfcn = MetricRow("EARFCN", "—", mono=True)
        self.m_tac = MetricRow("TAC", "—", mono=True)
        self.m_rsrp = MetricRow("RSRP", "—", mono=True)
        self.m_rsrq = MetricRow("RSRQ", "—", mono=True)
        self.m_rssi = MetricRow("RSSI", "—", mono=True)
        for i, m in enumerate((self.m_band, self.m_cid, self.m_pci, self.m_earfcn)):
            grid.addWidget(m, i, 0)
        for i, m in enumerate((self.m_tac, self.m_rsrp, self.m_rsrq, self.m_rssi)):
            grid.addWidget(m, i, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        card.body().addLayout(grid)

        self.note = CaptionLabel("", card)
        self.note.setStyleSheet(f"color: {P.text_tertiary};")
        self.note.setWordWrap(True)
        card.body().addWidget(self.note)
        return card

    def _update(self, st: ModemStatus) -> None:
        c = st.cell
        if c and c.available:
            self.tech.setText(c.tech or "—")
            self.m_band.set_value(c.band or "—", P.cyan if c.band else P.text)
            self.m_cid.set_value(str(c.cell_id) if c.cell_id is not None else "—")
            self.m_pci.set_value(str(c.pci) if c.pci is not None else "—")
            self.m_earfcn.set_value(str(c.earfcn) if c.earfcn is not None else "—")
            self.m_tac.set_value(str(c.tac) if c.tac is not None else "—")
            self.m_rsrp.set_value(f"{c.rsrp_dbm:.0f} dBm" if c.rsrp_dbm is not None else "—")
            self.m_rsrq.set_value(f"{c.rsrq_db:.0f} dB" if c.rsrq_db is not None else "—")
            self.m_rssi.set_value(f"{st.rssi_dbm} dBm" if st.rssi_dbm is not None else "—")
            q = c.quality_label
            lvl = ("success" if q in ("Отличное", "Хорошее") else
                   "warning" if q == "Среднее" else "error")
            self.badge.set_status(q, lvl)
            self.quality.setValue(int(c.quality_ratio * 100))
            self.note.setText("")
        else:
            self.tech.setText(st.data_class.split(",")[-1].strip() or "—")
            for m in (self.m_band, self.m_cid, self.m_pci, self.m_earfcn,
                      self.m_tac, self.m_rsrp, self.m_rsrq):
                m.set_value("—")
            self.m_rssi.set_value(f"{st.rssi_dbm} dBm" if st.rssi_dbm is not None else "—")
            self.badge.set_status("Нет данных", "muted")
            self.quality.setValue(0)
            note = (st.cell.note if st.cell else "") or \
                "Подробные данные соты недоступны в MBIM-режиме или требуют прав. " \
                "RSSI показан по данным Windows."
            self.note.setText(note)
