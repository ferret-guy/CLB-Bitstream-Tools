from enum import IntEnum
from typing import Callable, Mapping, Set, Tuple


from data_model import (
    BLE_CFG,
    FLOPSEL,
    LUT_IN_A,
    LUT_IN_B,
    LUT_IN_C,
    LUT_IN_D,
)
from build_lut import LUT4, Expr, pick

Four_LUT = Tuple[bool, bool, bool, bool]
FourLUT_Bit_Fn = Callable[[bool, bool, bool, bool], bool]


class _SigExpr(Expr):
    __slots__ = ("signals",)

    def __init__(self, fn: Callable[[Four_LUT], bool], signals: Set["LUT_IN"]) -> None:
        super().__init__(fn)
        self.signals: Set["LUT_IN"] = signals

    def _lift(self, other: "Expr", op) -> "_SigExpr":
        coerced_other = LUT_IN._coerce(other)

        other_signals = coerced_other.signals if isinstance(coerced_other, _SigExpr) else set()

        return _SigExpr(
            lambda v, l=self, r=coerced_other, p=op: p(l(v), r(v)),
            self.signals | other_signals,
        )

    def __and__(self, o):
        return self._lift(o, bool.__and__)

    def __or__(self, o):
        return self._lift(o, bool.__or__)

    def __xor__(self, o):
        return self._lift(o, bool.__xor__)

    def __invert__(self):
        return _SigExpr(lambda v, s=self: not s(v), set(self.signals))

    def __eq__(self, o):
        return self._lift(o, lambda x, y: x == y)  # XNOR

    def __ne__(self, o):
        return self._lift(o, lambda x, y: x != y)  # XOR

    def __bool__(self) -> bool:
        raise TypeError("Expr objects are symbolic; use &, |, ~, ^, ==, !=")


class LUT_IN(IntEnum):
    """
    Flattened view of LUT_IN_A … LUT_IN_D

    Each member stores:
    • value:             (port_index << 5) | native_value
    • _enum_member:      the original LUT_IN_A/B/C/D member
    • _port:             "A", "B", "C", or "D"
    """

    # Port A
    CLB_BLE_0 = (0, LUT_IN_A.CLB_BLE_0, "A")
    CLB_BLE_1 = (1, LUT_IN_A.CLB_BLE_1, "A")
    CLB_BLE_2 = (2, LUT_IN_A.CLB_BLE_2, "A")
    CLB_BLE_3 = (3, LUT_IN_A.CLB_BLE_3, "A")
    CLB_BLE_4 = (4, LUT_IN_A.CLB_BLE_4, "A")
    CLB_BLE_5 = (5, LUT_IN_A.CLB_BLE_5, "A")
    CLB_BLE_6 = (6, LUT_IN_A.CLB_BLE_6, "A")
    CLB_BLE_7 = (7, LUT_IN_A.CLB_BLE_7, "A")
    IN0 = (8, LUT_IN_A.IN0, "A")
    IN1 = (9, LUT_IN_A.IN1, "A")
    IN2 = (10, LUT_IN_A.IN2, "A")
    IN3 = (11, LUT_IN_A.IN3, "A")
    CLBSWIN0 = (12, LUT_IN_A.CLBSWIN0, "A")
    CLBSWIN1 = (13, LUT_IN_A.CLBSWIN1, "A")
    CLBSWIN2 = (14, LUT_IN_A.CLBSWIN2, "A")
    CLBSWIN3 = (15, LUT_IN_A.CLBSWIN3, "A")
    CLBSWIN4 = (16, LUT_IN_A.CLBSWIN4, "A")
    CLBSWIN5 = (17, LUT_IN_A.CLBSWIN5, "A")
    CLBSWIN6 = (18, LUT_IN_A.CLBSWIN6, "A")
    CLBSWIN7 = (19, LUT_IN_A.CLBSWIN7, "A")
    COUNT_IS_A1 = (20, LUT_IN_A.COUNT_IS_A1, "A")
    COUNT_IS_A2 = (21, LUT_IN_A.COUNT_IS_A2, "A")

    # Port B
    CLB_BLE_8 = (32, LUT_IN_B.CLB_BLE_8, "B")
    CLB_BLE_9 = (33, LUT_IN_B.CLB_BLE_9, "B")
    CLB_BLE_10 = (34, LUT_IN_B.CLB_BLE_10, "B")
    CLB_BLE_11 = (35, LUT_IN_B.CLB_BLE_11, "B")
    CLB_BLE_12 = (36, LUT_IN_B.CLB_BLE_12, "B")
    CLB_BLE_13 = (37, LUT_IN_B.CLB_BLE_13, "B")
    CLB_BLE_14 = (38, LUT_IN_B.CLB_BLE_14, "B")
    CLB_BLE_15 = (39, LUT_IN_B.CLB_BLE_15, "B")
    IN4 = (40, LUT_IN_B.IN4, "B")
    IN5 = (41, LUT_IN_B.IN5, "B")
    IN6 = (42, LUT_IN_B.IN6, "B")
    IN7 = (43, LUT_IN_B.IN7, "B")
    CLBSWIN8 = (44, LUT_IN_B.CLBSWIN8, "B")
    CLBSWIN9 = (45, LUT_IN_B.CLBSWIN9, "B")
    CLBSWIN10 = (46, LUT_IN_B.CLBSWIN10, "B")
    CLBSWIN11 = (47, LUT_IN_B.CLBSWIN11, "B")
    CLBSWIN12 = (48, LUT_IN_B.CLBSWIN12, "B")
    CLBSWIN13 = (49, LUT_IN_B.CLBSWIN13, "B")
    CLBSWIN14 = (50, LUT_IN_B.CLBSWIN14, "B")
    CLBSWIN15 = (51, LUT_IN_B.CLBSWIN15, "B")
    COUNT_IS_B1 = (52, LUT_IN_B.COUNT_IS_B1, "B")
    COUNT_IS_B2 = (53, LUT_IN_B.COUNT_IS_B2, "B")

    # Port C
    CLB_BLE_16 = (64, LUT_IN_C.CLB_BLE_16, "C")
    CLB_BLE_17 = (65, LUT_IN_C.CLB_BLE_17, "C")
    CLB_BLE_18 = (66, LUT_IN_C.CLB_BLE_18, "C")
    CLB_BLE_19 = (67, LUT_IN_C.CLB_BLE_19, "C")
    CLB_BLE_20 = (68, LUT_IN_C.CLB_BLE_20, "C")
    CLB_BLE_21 = (69, LUT_IN_C.CLB_BLE_21, "C")
    CLB_BLE_22 = (70, LUT_IN_C.CLB_BLE_22, "C")
    CLB_BLE_23 = (71, LUT_IN_C.CLB_BLE_23, "C")
    IN8 = (72, LUT_IN_C.IN8, "C")
    IN9 = (73, LUT_IN_C.IN9, "C")
    IN10 = (74, LUT_IN_C.IN10, "C")
    IN11 = (75, LUT_IN_C.IN11, "C")
    CLBSWIN16 = (76, LUT_IN_C.CLBSWIN16, "C")
    CLBSWIN17 = (77, LUT_IN_C.CLBSWIN17, "C")
    CLBSWIN18 = (78, LUT_IN_C.CLBSWIN18, "C")
    CLBSWIN19 = (79, LUT_IN_C.CLBSWIN19, "C")
    CLBSWIN20 = (80, LUT_IN_C.CLBSWIN20, "C")
    CLBSWIN21 = (81, LUT_IN_C.CLBSWIN21, "C")
    CLBSWIN22 = (82, LUT_IN_C.CLBSWIN22, "C")
    CLBSWIN23 = (83, LUT_IN_C.CLBSWIN23, "C")
    COUNT_IS_C1 = (84, LUT_IN_C.COUNT_IS_C1, "C")
    COUNT_IS_C2 = (85, LUT_IN_C.COUNT_IS_C2, "C")

    # Port D
    CLB_BLE_24 = (96, LUT_IN_D.CLB_BLE_24, "D")
    CLB_BLE_25 = (97, LUT_IN_D.CLB_BLE_25, "D")
    CLB_BLE_26 = (98, LUT_IN_D.CLB_BLE_26, "D")
    CLB_BLE_27 = (99, LUT_IN_D.CLB_BLE_27, "D")
    CLB_BLE_28 = (100, LUT_IN_D.CLB_BLE_28, "D")
    CLB_BLE_29 = (101, LUT_IN_D.CLB_BLE_29, "D")
    CLB_BLE_30 = (102, LUT_IN_D.CLB_BLE_30, "D")
    CLB_BLE_31 = (103, LUT_IN_D.CLB_BLE_31, "D")
    IN12 = (104, LUT_IN_D.IN12, "D")
    IN13 = (105, LUT_IN_D.IN13, "D")
    IN14 = (106, LUT_IN_D.IN14, "D")
    IN15 = (107, LUT_IN_D.IN15, "D")
    CLBSWIN24 = (108, LUT_IN_D.CLBSWIN24, "D")
    CLBSWIN25 = (109, LUT_IN_D.CLBSWIN25, "D")
    CLBSWIN26 = (110, LUT_IN_D.CLBSWIN26, "D")
    CLBSWIN27 = (111, LUT_IN_D.CLBSWIN27, "D")
    CLBSWIN28 = (112, LUT_IN_D.CLBSWIN28, "D")
    CLBSWIN29 = (113, LUT_IN_D.CLBSWIN29, "D")
    CLBSWIN30 = (114, LUT_IN_D.CLBSWIN30, "D")
    CLBSWIN31 = (115, LUT_IN_D.CLBSWIN31, "D")
    COUNT_IS_D1 = (116, LUT_IN_D.COUNT_IS_D1, "D")
    COUNT_IS_D2 = (117, LUT_IN_D.COUNT_IS_D2, "D")

    def __new__(cls, value: int, src_member, port_letter: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._enum_member = src_member
        obj._port = port_letter
        return obj

    def _expr(self):
        idx = "ABCD".index(self._port)
        return _SigExpr(pick(idx), {self})

    @staticmethod
    def _coerce(x):
        """Turn bare LUT_IN members into expressions so that mixed
        expressions (e.g. `~LUT_IN.CLBSWIN4 & expr`) work transparently."""
        return x._expr() if isinstance(x, LUT_IN) else x

    # boolean-algebra overloads
    def __and__(self, other):
        return self._expr() & self._coerce(other)

    def __or__(self, other):
        return self._expr() | self._coerce(other)

    def __xor__(self, other):
        return self._expr() ^ self._coerce(other)

    def __invert__(self):
        return ~self._expr()

    def __eq__(self, other):
        """Implement ``a == b`` (XNOR)."""
        return self._expr() == self._coerce(other)

    def __ne__(self, other):
        """Implement ``a != b`` (XOR)."""
        return self._expr() != self._coerce(other)

    def __hash__(self):
        return int.__hash__(int(self))

    def __bool__(self) -> bool:
        raise TypeError("Expr objects are symbolic; use &, |, ~, ^, ==, !=")


def AutoBLE(expr: LUT_IN | _SigExpr, flopsel: bool | FLOPSEL | None = None) -> BLE_CFG:

    # normalise FLOPSEL
    match flopsel:
        case None:
            flopsel_val = FLOPSEL.DISABLE.value
        case bool():
            flopsel_val = FLOPSEL.ENABLE.value if flopsel else FLOPSEL.DISABLE.value
        case _ if isinstance(flopsel, FLOPSEL):
            flopsel_val = flopsel.value
        case _:
            raise TypeError("flopsel must be bool, FLOPSEL enum, or None.")

    # normalise the logic expression
    if isinstance(expr, LUT_IN):
        expr = expr._expr()  # noinspection PyProtectedMember
    if not isinstance(expr, _SigExpr):
        raise TypeError("AutoBLE() expects a LUT_IN or a boolean expression thereof.")

    used = expr.signals
    if len(used) > 4:
        raise ValueError("A 4‑input LUT can drive only four distinct signals.")

    # ensure each port is used at most once
    port_map: Mapping[str, LUT_IN] = {}
    for sig in used:
        if sig._port in port_map:  # noinspection PyProtectedMember
            raise ValueError(
                f"Port {sig._port} used twice ({port_map[sig._port].name} & {sig.name})."  # noinspection PyProtectedMember
            )
        port_map[sig._port] = sig  # noinspection PyProtectedMember

    # build keyword arguments for BLE_CFG
    cfg_kwargs = {
        "LUT_CONFIG": LUT4(expr).bitstream(),
        "FLOPSEL": flopsel_val,
    }
    for port_letter, sig in port_map.items():
        cfg_kwargs[f"LUT_I_{port_letter}"] = sig._enum_member  # noinspection PyProtectedMember

    return BLE_CFG(**cfg_kwargs)


if __name__ == "__main__":
    IN_SYNC = LUT_IN.IN8
    print(AutoBLE(LUT_IN.CLB_BLE_5 ^ IN_SYNC | LUT_IN.CLB_BLE_8))
