"""Разбор SMS-PDU (формат SMS-DELIVER, 3GPP TS 23.040).

Модем в MBIM-режиме отдаёт SMS как бинарные сообщения (SmsBinaryMessage) —
сырой PDU. Здесь он парсится в отправителя, время и текст (GSM7/8bit/UCS2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

# Базовый алфавит GSM 03.38
_GSM7 = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
         "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")


@dataclass
class Pdu:
    sender: str = ""
    body: str = ""
    timestamp: Optional[datetime] = None
    dcs: int = 0
    # склейка длинных SMS (concatenated / multipart)
    ref: Optional[int] = None   # общий номер набора частей
    total: int = 1              # всего частей
    seq: int = 1                # номер этой части


def gsm7_unpack(data: bytes, septet_count: Optional[int] = None) -> str:
    """Распаковать упакованные 7-битные септеты в текст."""
    septets, bits, cur = [], 0, 0
    for byte in data:
        cur |= byte << bits
        bits += 7 if False else 8
        while bits >= 7:
            septets.append(cur & 0x7F)
            cur >>= 7
            bits -= 7
    if septet_count is not None:
        septets = septets[:septet_count]
    out, i = [], 0
    while i < len(septets):
        s = septets[i]
        if s == 0x1B and i + 1 < len(septets):
            i += 1
            out.append(" ")
        elif s < len(_GSM7):
            out.append(_GSM7[s])
        i += 1
    return "".join(out)


def _decode_address(type_octet: int, addr_bytes: bytes, num_semi_octets: int) -> str:
    ton = (type_octet >> 4) & 0x07
    if ton == 0x05:  # алфавитно-цифровой (напр. "Beeline")
        # длина в семи-октетах = num_semi_octets*4/7 символов
        n_sept = (num_semi_octets * 4) // 7
        return gsm7_unpack(addr_bytes, n_sept).strip()
    # числовой: развёрнутые нибблы
    digits = []
    for b in addr_bytes:
        digits.append(b & 0x0F)
        digits.append((b >> 4) & 0x0F)
    digits = digits[:num_semi_octets]
    num = "".join("0123456789*#abc"[d] if d < 15 else "" for d in digits)
    if type_octet & 0x70 == 0x10:  # международный
        num = "+" + num
    return num


def _decode_scts(b: bytes) -> Optional[datetime]:
    if len(b) < 7:
        return None

    def sw(x):  # развернуть нибблы одного октета в число
        return (x & 0x0F) * 10 + ((x >> 4) & 0x0F)

    try:
        yy = sw(b[0]); mm = sw(b[1]); dd = sw(b[2])
        hh = sw(b[3]); mi = sw(b[4]); ss = sw(b[5])
        tz_raw = b[6]
        quarters = sw(tz_raw & 0x7F)
        sign = -1 if (tz_raw & 0x08) else 1
        tz = timezone(sign * timedelta(minutes=15 * quarters))
        year = 2000 + yy
        return datetime(year, mm, dd, hh, mi, ss, tzinfo=tz)
    except Exception:
        return None


def _parse_udh(ud: bytes) -> tuple[Optional[int], int, int]:
    """Разобрать UDH → (ref, total, seq) для склейки многочастных SMS."""
    if not ud:
        return None, 1, 1
    udh_len = ud[0]
    udh = ud[1:1 + udh_len]
    i = 0
    while i + 1 < len(udh):
        iei, ielen = udh[i], udh[i + 1]
        ie = udh[i + 2:i + 2 + ielen]
        if iei == 0x00 and len(ie) >= 3:            # 8-битный ref
            return ie[0], ie[1], ie[2]
        if iei == 0x08 and len(ie) >= 4:            # 16-битный ref
            return (ie[0] << 8) | ie[1], ie[2], ie[3]
        i += 2 + ielen
    return None, 1, 1


def _decode_ud(dcs: int, udl: int, ud: bytes, udhi: bool) -> str:
    # пропустить UDH при наличии
    if udhi and ud:
        udh_len = ud[0]
        ud = ud[1 + udh_len:]
    # UCS2
    if dcs == 0x08 or (dcs & 0x0C) == 0x08:
        try:
            # некоторые отправители ставят BOM в начале — убираем
            return ud.decode("utf-16-be", errors="replace").lstrip("﻿")
        except Exception:
            return ""
    # 8-bit
    if (dcs & 0x0C) == 0x04:
        return ud.decode("latin-1", errors="replace")
    # GSM 7-bit
    return gsm7_unpack(ud, udl)


def parse_deliver(pdu_hex: str) -> Pdu:
    """Разобрать SMS-DELIVER PDU (hex-строка) в Pdu."""
    b = bytes.fromhex(pdu_hex.strip())
    i = 0
    # SMSC
    smsc_len = b[i]; i += 1 + smsc_len
    first = b[i]; i += 1
    udhi = bool(first & 0x40)
    # TP-OA
    oa_len = b[i]; i += 1               # длина адреса в семи-октетах (цифрах)
    oa_type = b[i]; i += 1
    oa_octets = (oa_len + 1) // 2 if ((oa_type >> 4) & 0x07) != 0x05 else (oa_len * 4 + 7) // 8
    oa = b[i:i + oa_octets]; i += oa_octets
    sender = _decode_address(oa_type, oa, oa_len)
    # TP-PID, TP-DCS
    i += 1                               # PID
    dcs = b[i]; i += 1
    # TP-SCTS
    scts = b[i:i + 7]; i += 7
    ts = _decode_scts(scts)
    # TP-UDL + UD
    udl = b[i]; i += 1
    ud = b[i:]
    ref, total, seq = (_parse_udh(ud) if udhi else (None, 1, 1))
    body = _decode_ud(dcs, udl, ud, udhi)
    return Pdu(sender=sender, body=body.strip(), timestamp=ts, dcs=dcs,
               ref=ref, total=total, seq=seq)
