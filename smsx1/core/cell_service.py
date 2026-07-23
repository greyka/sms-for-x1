"""Данные обслуживающей базовой станции (соты) через Windows WinRT.

Использует MobileBroadbandModem.try_get_cell_info_async(). Доступность зависит
от модема/прав; при недоступности возвращается CellInfo(available=False).
Band рассчитывается из EARFCN (LTE) по стандартным диапазонам 3GPP.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from .models import CellInfo

try:
    from winsdk.windows.networking.networkoperators import MobileBroadbandModem
    _WINRT_OK = True
    _WINRT_ERR = ""
except Exception as exc:  # pragma: no cover
    _WINRT_OK = False
    _WINRT_ERR = str(exc)


# EARFCN (downlink) → (band, обиходная частота). Диапазоны, актуальные для РФ и Европы.
_LTE_BANDS = [
    (0, 599, "B1", "2100"),
    (600, 1199, "B2", "1900"),
    (1200, 1949, "B3", "1800"),
    (1950, 2399, "B4", "1700/2100"),
    (2400, 2649, "B5", "850"),
    (2750, 3449, "B7", "2600"),
    (3450, 3799, "B8", "900"),
    (6150, 6449, "B20", "800"),
    (9210, 9659, "B28", "700"),
    (36200, 36349, "B33", "1900 TDD"),
    (37750, 38249, "B38", "2600 TDD"),
    (38650, 39649, "B40", "2300 TDD"),
    (39650, 41589, "B41", "2500 TDD"),
]


def earfcn_to_band(earfcn: Optional[int]) -> str:
    if earfcn is None:
        return ""
    for lo, hi, band, freq in _LTE_BANDS:
        if lo <= earfcn <= hi:
            return f"{band} ({freq} МГц)"
    return f"EARFCN {earfcn}"


class CellService:
    def __init__(self) -> None:
        self.available = _WINRT_OK
        self.last_error = _WINRT_ERR

    TIMEOUT = 8.0

    def get(self) -> CellInfo:
        if not self.available:
            return CellInfo(available=False, note="WinRT недоступен")
        try:
            return asyncio.run(asyncio.wait_for(self._get_async(), self.TIMEOUT))
        except asyncio.TimeoutError:
            return CellInfo(available=False, note="Таймаут запроса данных соты")
        except Exception as exc:
            return CellInfo(available=False, note=str(exc))

    async def _get_async(self) -> CellInfo:
        modem = MobileBroadbandModem.get_default()
        if modem is None:
            return CellInfo(available=False, note="Модем не найден")

        try:
            info = await modem.try_get_cell_info_async()
        except Exception as exc:
            return CellInfo(available=False,
                            note="Сбор данных соты недоступен (нужны права/поддержка)")
        if info is None:
            return CellInfo(available=False, note="Нет данных соты")

        # LTE
        lte = self._first(getattr(info, "serving_cells_lte", None))
        if lte is not None:
            earfcn = self._val(getattr(lte, "earfcn", None))
            cell = CellInfo(
                tech="LTE",
                cell_id=self._val(getattr(lte, "cell_id", None)),
                pci=self._val(getattr(lte, "physical_cell_id", None)),
                earfcn=earfcn,
                band=earfcn_to_band(earfcn),
                tac=self._val(getattr(lte, "tracking_area_code", None)),
                rsrp_dbm=self._val(getattr(lte, "rsrp", None)),
                rsrq_db=self._val(getattr(lte, "rsrq", None)),
                available=True,
            )
            return cell

        # 5G NR
        nr = self._first(getattr(info, "serving_cells_nr", None))
        if nr is not None:
            cell = CellInfo(
                tech="5G NR",
                cell_id=self._val(getattr(nr, "cell_id", None)),
                pci=self._val(getattr(nr, "physical_cell_id", None)),
                earfcn=self._val(getattr(nr, "nrarfcn", None)),
                band="5G NR",
                tac=self._val(getattr(nr, "tracking_area_code", None)),
                rsrp_dbm=self._val(getattr(nr, "ss_rsrp", None)),
                rsrq_db=self._val(getattr(nr, "ss_rsrq", None)),
                sinr_db=self._val(getattr(nr, "ss_sinr", None)),
                available=True,
            )
            return cell

        # WCDMA / GSM — минимум
        for attr, tech in (("serving_cells_wcdma", "WCDMA"), ("serving_cells_gsm", "GSM")):
            c = self._first(getattr(info, attr, None))
            if c is not None:
                return CellInfo(
                    tech=tech,
                    cell_id=self._val(getattr(c, "cell_id", None)),
                    available=True,
                )

        return CellInfo(available=False, note="Обслуживающая сота не определена")

    @staticmethod
    def _first(vec):
        try:
            if vec and len(vec) > 0:
                return vec[0]
        except Exception:
            pass
        return None

    @staticmethod
    def _val(ref):
        """Развернуть WinRT IReference или вернуть значение как есть."""
        if ref is None:
            return None
        v = getattr(ref, "value", ref)
        return v
