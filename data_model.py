import warnings
from collections import defaultdict
from dataclasses import dataclass
from enum import IntFlag, Enum, IntEnum
from pathlib import Path
from pprint import pformat
from typing import Optional, Union

VAR_ORDER = "ABCD"


def get_active_lut_inputs(cfg: str) -> dict[str, bool]:
    if len(cfg) != 16 or set(cfg) - {"0", "1"}:
        return {k: False for k in VAR_ORDER}
    active = {k: False for k in VAR_ORDER}
    for addr in range(16):
        base = cfg[15 - addr]
        for bit, name in enumerate(VAR_ORDER):
            if active[name] or addr & (1 << bit):
                continue
            if cfg[15 - (addr | 1 << bit)] != base:
                active[name] = True
        if all(active.values()):
            break
    return active


class LUT_IN_A(IntEnum):
    """BLE INPUT A[4:0]"""

    CLB_BLE_0 = 0b00000
    CLB_BLE_1 = 0b00001
    CLB_BLE_2 = 0b00010
    CLB_BLE_3 = 0b00011
    CLB_BLE_4 = 0b00100
    CLB_BLE_5 = 0b00101
    CLB_BLE_6 = 0b00110
    CLB_BLE_7 = 0b00111
    IN0 = 0b01000
    IN1 = 0b01001
    IN2 = 0b01010
    IN3 = 0b01011
    CLBSWIN0 = 0b01100
    CLBSWIN1 = 0b01101
    CLBSWIN2 = 0b01110
    CLBSWIN3 = 0b01111
    CLBSWIN4 = 0b10000
    CLBSWIN5 = 0b10001
    CLBSWIN6 = 0b10010
    CLBSWIN7 = 0b10011
    COUNT_IS_A1 = 0b10100
    COUNT_IS_A2 = 0b10101


class LUT_IN_B(IntEnum):
    """BLE INPUT B[4:0]"""

    CLB_BLE_8 = 0b00000
    CLB_BLE_9 = 0b00001
    CLB_BLE_10 = 0b00010
    CLB_BLE_11 = 0b00011
    CLB_BLE_12 = 0b00100
    CLB_BLE_13 = 0b00101
    CLB_BLE_14 = 0b00110
    CLB_BLE_15 = 0b00111
    IN4 = 0b01000
    IN5 = 0b01001
    IN6 = 0b01010
    IN7 = 0b01011
    CLBSWIN8 = 0b01100
    CLBSWIN9 = 0b01101
    CLBSWIN10 = 0b01110
    CLBSWIN11 = 0b01111
    CLBSWIN12 = 0b10000
    CLBSWIN13 = 0b10001
    CLBSWIN14 = 0b10010
    CLBSWIN15 = 0b10011
    COUNT_IS_B1 = 0b10100
    COUNT_IS_B2 = 0b10101


class LUT_IN_C(IntEnum):
    """BLE INPUT C[4:0]"""

    CLB_BLE_16 = 0b00000
    CLB_BLE_17 = 0b00001
    CLB_BLE_18 = 0b00010
    CLB_BLE_19 = 0b00011
    CLB_BLE_20 = 0b00100
    CLB_BLE_21 = 0b00101
    CLB_BLE_22 = 0b00110
    CLB_BLE_23 = 0b00111
    IN8 = 0b01000
    IN9 = 0b01001
    IN10 = 0b01010
    IN11 = 0b01011
    CLBSWIN16 = 0b01100
    CLBSWIN17 = 0b01101
    CLBSWIN18 = 0b01110
    CLBSWIN19 = 0b01111
    CLBSWIN20 = 0b10000
    CLBSWIN21 = 0b10001
    CLBSWIN22 = 0b10010
    CLBSWIN23 = 0b10011
    COUNT_IS_C1 = 0b10100
    COUNT_IS_C2 = 0b10101


class LUT_IN_D(IntEnum):
    """BLE INPUT D[4:0]"""

    CLB_BLE_24 = 0b00000
    CLB_BLE_25 = 0b00001
    CLB_BLE_26 = 0b00010
    CLB_BLE_27 = 0b00011
    CLB_BLE_28 = 0b00100
    CLB_BLE_29 = 0b00101
    CLB_BLE_30 = 0b00110
    CLB_BLE_31 = 0b00111
    IN12 = 0b01000
    IN13 = 0b01001
    IN14 = 0b01010
    IN15 = 0b01011
    CLBSWIN24 = 0b01100
    CLBSWIN25 = 0b01101
    CLBSWIN26 = 0b01110
    CLBSWIN27 = 0b01111
    CLBSWIN28 = 0b10000
    CLBSWIN29 = 0b10001
    CLBSWIN30 = 0b10010
    CLBSWIN31 = 0b10011
    COUNT_IS_D1 = 0b10100
    COUNT_IS_D2 = 0b10101


class COUNTERIN(IntEnum):
    CLB_BLE_31 = 0b11111
    CLB_BLE_30 = 0b11110
    CLB_BLE_29 = 0b11101
    CLB_BLE_28 = 0b11100
    CLB_BLE_27 = 0b11011
    CLB_BLE_26 = 0b11010
    CLB_BLE_25 = 0b11001
    CLB_BLE_24 = 0b11000
    CLB_BLE_23 = 0b10111
    CLB_BLE_22 = 0b10110
    CLB_BLE_21 = 0b10101
    CLB_BLE_20 = 0b10100
    CLB_BLE_19 = 0b10011
    CLB_BLE_18 = 0b10010
    CLB_BLE_17 = 0b10001
    CLB_BLE_16 = 0b10000
    CLB_BLE_15 = 0b01111
    CLB_BLE_14 = 0b01110
    CLB_BLE_13 = 0b01101
    CLB_BLE_12 = 0b01100
    CLB_BLE_11 = 0b01011
    CLB_BLE_10 = 0b01010
    CLB_BLE_9 = 0b01001
    CLB_BLE_8 = 0b01000
    CLB_BLE_7 = 0b00111
    CLB_BLE_6 = 0b00110
    CLB_BLE_5 = 0b00101
    CLB_BLE_4 = 0b00100
    CLB_BLE_3 = 0b00011
    CLB_BLE_2 = 0b00010
    CLB_BLE_1 = 0b00001
    CLB_BLE_0 = 0b00000


class OESELn(IntEnum):
    BLE_31 = 0b1111
    BLE_27 = 0b1110
    BLE_23 = 0b1101
    BLE_19 = 0b1100
    BLE_15 = 0b1011
    BLE_11 = 0b1010
    BLE_7 = 0b1001
    BLE_3 = 0b1000

    TRIS0 = 0b0111
    TRIS1 = 0b0110
    TRIS2 = 0b0101
    TRIS3 = 0b0100
    TRIS4 = 0b0011
    TRIS5 = 0b0010
    TRIS6 = 0b0001
    TRIS7 = 0b0000


class CLBPPSOUT0(IntEnum):
    CLB_BLE_0 = 0b00
    CLB_BLE_1 = 0b01
    CLB_BLE_2 = 0b10
    CLB_BLE_3 = 0b11


class CLBPPSOUT1(IntEnum):
    CLB_BLE_4 = 0b00
    CLB_BLE_5 = 0b01
    CLB_BLE_6 = 0b10
    CLB_BLE_7 = 0b11


class CLBPPSOUT2(IntEnum):
    CLB_BLE_8 = 0b00
    CLB_BLE_9 = 0b01
    CLB_BLE_10 = 0b10
    CLB_BLE_11 = 0b11


class CLBPPSOUT3(IntEnum):
    CLB_BLE_12 = 0b00
    CLB_BLE_13 = 0b01
    CLB_BLE_14 = 0b10
    CLB_BLE_15 = 0b11


class CLBPPSOUT4(IntEnum):
    CLB_BLE_16 = 0b00
    CLB_BLE_17 = 0b01
    CLB_BLE_18 = 0b10
    CLB_BLE_19 = 0b11


class CLBPPSOUT5(IntEnum):
    CLB_BLE_20 = 0b00
    CLB_BLE_21 = 0b01
    CLB_BLE_22 = 0b10
    CLB_BLE_23 = 0b11


class CLBPPSOUT6(IntEnum):
    CLB_BLE_24 = 0b00
    CLB_BLE_25 = 0b01
    CLB_BLE_26 = 0b10
    CLB_BLE_27 = 0b11


class CLBPPSOUT7(IntEnum):
    CLB_BLE_28 = 0b00
    CLB_BLE_29 = 0b01
    CLB_BLE_30 = 0b10
    CLB_BLE_31 = 0b11


# Interrupts
class CLB1IF0(IntEnum):
    CLB_BLE_0 = 0b000
    CLB_BLE_1 = 0b001
    CLB_BLE_2 = 0b010
    CLB_BLE_3 = 0b011
    CLB_BLE_4 = 0b100
    CLB_BLE_5 = 0b101
    CLB_BLE_6 = 0b110
    CLB_BLE_7 = 0b111


class CLB1IF1(IntEnum):
    CLB_BLE_8 = 0b000
    CLB_BLE_9 = 0b001
    CLB_BLE_10 = 0b010
    CLB_BLE_11 = 0b011
    CLB_BLE_12 = 0b100
    CLB_BLE_13 = 0b101
    CLB_BLE_14 = 0b110
    CLB_BLE_15 = 0b111


class CLB1IF2(IntEnum):
    CLB_BLE_16 = 0b000
    CLB_BLE_17 = 0b001
    CLB_BLE_18 = 0b010
    CLB_BLE_19 = 0b011
    CLB_BLE_20 = 0b100
    CLB_BLE_21 = 0b101
    CLB_BLE_22 = 0b110
    CLB_BLE_23 = 0b111


class CLB1IF3(IntEnum):
    CLB_BLE_24 = 0b000
    CLB_BLE_25 = 0b001
    CLB_BLE_26 = 0b010
    CLB_BLE_27 = 0b011
    CLB_BLE_28 = 0b100
    CLB_BLE_29 = 0b101
    CLB_BLE_30 = 0b110
    CLB_BLE_31 = 0b111


class CLBIN(IntFlag):
    RESERVED_BIT = 0b100000
    ZERO = 0b11111
    C2_OUT = 0b11100
    C1_OUT = 0b11011
    CLBSWIN_WRITE_HOLD = 0b11010
    SCK1 = 0b11001
    SDO1 = 0b11000
    TX1 = 0b10111
    CLC4_OUT = 0b10110
    CLC3_OUT = 0b10101
    CLC2_OUT = 0b10100
    CLC1_OUT = 0b10011
    IOCIF = 0b10010
    PWM2_OUT = 0b10001
    PWM1_OUT = 0b10000
    CCP2_OUT = 0b01111
    CCP1_OUT = 0b01110
    TMR2_POSTSCALED_OUT = 0b01101
    TMR1_OVERFLOW_OUT = 0b01100
    TMR0_OVERFLOW_OUT = 0b01011
    ADCRC = 0b01010
    EXTOSC = 0b01001
    MFINTOSC_32KHZ = 0b01000
    MFINTOSC_500KHZ = 0b00111
    LFINTOSC = 0b00110
    HFINTOSC = 0b00101
    FOSC = 0b00100
    CLBIN3PPS = 0b00011
    CLBIN2PPS = 0b00010
    CLBIN1PPS = 0b00001
    CLBIN0PPS = 0b00000


class CLBInputSync(IntFlag):
    DIRECT_IN = 0b000
    SYNC = 0b100
    EDGE_DETECT = 0b010
    EDGE_INVERT = 0b001


class BLEXY(Enum):
    BLE_0_X1Y2 = 0
    BLE_1_X2Y2 = 1
    BLE_2_X3Y2 = 2
    BLE_3_X4Y2 = 3
    BLE_4_X1Y3 = 4
    BLE_5_X2Y3 = 5
    BLE_6_X3Y3 = 6
    BLE_7_X4Y3 = 7
    BLE_8_X1Y4 = 8
    BLE_9_X2Y4 = 9
    BLE_10_X3Y4 = 10
    BLE_11_X4Y4 = 11
    BLE_12_X1Y5 = 12
    BLE_13_X2Y5 = 13
    BLE_14_X3Y5 = 14
    BLE_15_X4Y5 = 15
    BLE_16_X1Y6 = 16
    BLE_17_X2Y6 = 17
    BLE_18_X3Y6 = 18
    BLE_19_X4Y6 = 19
    BLE_20_X1Y7 = 20
    BLE_21_X2Y7 = 21
    BLE_22_X3Y7 = 22
    BLE_23_X4Y7 = 23
    BLE_24_X1Y8 = 24
    BLE_25_X2Y8 = 25
    BLE_26_X3Y8 = 26
    BLE_27_X4Y8 = 27
    BLE_28_X1Y9 = 28
    BLE_29_X2Y9 = 29
    BLE_30_X3Y9 = 30
    BLE_31_X4Y9 = 31

    @classmethod
    def from_fasm(cls, fasm: str) -> "BLEXY":
        """
        Accept FASM format (i.e. BLE_X3Y4).
        """
        for m in cls:
            prefix, _, coords = m.name.split("_", 2)
            if f"{prefix}_{coords}" == fasm:
                return m
        raise KeyError(f"No BLEXY member matches '{fasm}'")


class FLOPSEL(Enum):
    DISABLE = False
    ENABLE = True


def get_lut_setting_bits(lut_index):
    """Get LUT 0-15 bit seettings"""

    # Determine LUT type (A, B, or C) based on LUT index mod 3
    r = lut_index % 3
    # Calculate the cycle number (LUT0 is cycle 12, decreasing every 3 LUTs)
    cycle = 12 - (lut_index // 3)
    if r == 0:  # Type A
        offsets = (90, 9, 21, 33)
    elif r == 1:  # Type B
        offsets = (48, 11, 22, 32)
    else:  # Type C
        offsets = (5, 11, 20, 32)

    # Base (bit0) address for this LUT:
    base = cycle * 128 + offsets[0]

    lut = {}
    # Group 4 (bits 0-3): consecutive starting at base.
    for b in range(0, 4):
        lut[b] = base + b
    # Group 3 (bits 4-7): starting at (base - group3_offset)
    for b in range(4, 8):
        lut[b] = (base - offsets[1]) + (b - 4)
    # Group 2 (bits 8-11): starting at (base - group2_offset)
    for b in range(8, 12):
        lut[b] = (base - offsets[2]) + (b - 8)
    # Group 1 (bits 12-15): starting at (base - group1_offset)
    for b in range(12, 16):
        lut[b] = (base - offsets[3]) + (b - 12)
    return lut


def get_lut_input_bit_addresses(lut_index):
    """Get LUT A/B/C/D addre"""
    # Determine type based on index mod 3 and compute the cycle
    r = lut_index % 3
    cycle = 12 - (lut_index // 3)

    if r == 0:  # Type A
        base = cycle * 128 + 90
        # For type A, jump occurs in LUT_I_B (last increment is +6 instead of +4)
        groups_spec = {
            "LUT_I_A": (5, [0, 1, 2, 3, 4]),
            "LUT_I_B": (16, [0, 1, 2, 3, 6]),
            "LUT_I_C": (26, [0, 1, 2, 3, 4]),
            "LUT_I_D": (38, [0, 1, 2, 3, 4]),
        }
    elif r == 1:  # Type B
        base = cycle * 128 + 48
        # For type B, all groups are sequential
        groups_spec = {
            "LUT_I_A": (7, [0, 1, 2, 3, 4]),
            "LUT_I_B": (16, [0, 1, 2, 3, 4]),
            "LUT_I_C": (27, [0, 1, 2, 3, 4]),
            "LUT_I_D": (39, [0, 1, 2, 3, 4]),
        }
    else:  # Type C
        base = cycle * 128 + 5
        # For type C, jump occurs in LUT_I_C (last increment is +6 instead of +4)
        groups_spec = {
            "LUT_I_A": (5, [0, 1, 2, 3, 4]),
            "LUT_I_B": (16, [0, 1, 2, 3, 4]),
            "LUT_I_C": (27, [0, 1, 2, 3, 6]),
            "LUT_I_D": (37, [0, 1, 2, 3, 4]),
        }

    groups = {}
    for group, (delta, incs) in groups_spec.items():
        start = base - delta
        groups[group] = {i: start + inc for i, inc in enumerate(incs)}
    return groups


def get_pps_out_addr(pps):
    if type(pps) is str:
        pps = PPS_OUT_NAME[pps]
    elif type(pps) is int:
        pps = PPS_OUT_NUM[pps]

    return PPS_OUT_BITS[pps]


def get_flopsel(lut):
    # Determine type based on index mod 3 (A, B, or C)
    types = ["A", "B", "C"]
    t = types[lut % 3]

    # Compute the cycle number: cycle = 12 - (lut_index // 3)
    cycle = 12 - (lut // 3)

    # Compute FLOPSEL bit based on type:
    # For type A: FLOPSEL = cycle * 128 + 61
    # For type B: FLOPSEL = cycle * 128 + 20
    # For type C: FLOPSEL = cycle * 128 - 23
    if t == "A":
        flopsel = cycle * 128 + 61
    elif t == "B":
        flopsel = cycle * 128 + 20
    else:  # t == 'C'
        flopsel = cycle * 128 - 23
    return flopsel


class LUTConfigWarning(UserWarning):
    """Possible LUT misconfigurations."""


@dataclass
class BLE_CFG:
    LUT_CONFIG: str = None  # 16 Bit
    FLOPSEL: bool = None
    LUT_I_A: LUT_IN_A = None
    LUT_I_B: LUT_IN_B = None
    LUT_I_C: LUT_IN_C = None
    LUT_I_D: LUT_IN_D = None

    def __post_init__(self) -> None:
        inputs = {k: getattr(self, f"LUT_I_{k}") for k in "ABCD"}
        active = {k for k, v in inputs.items() if v is not None}

        if self.LUT_CONFIG:
            expected = {
                k for k, u in get_active_lut_inputs(self.LUT_CONFIG).items() if u
            }
            for k in expected - active:
                warnings.warn(
                    f"LUT_I_{k} is used in LUT_CONFIG but was None",
                    category=LUTConfigWarning,
                    stacklevel=3,
                )
            for k in active - expected:
                warnings.warn(
                    f"LUT_I_{k} is not used in LUT_CONFIG but was {inputs[k]!r}",
                    category=LUTConfigWarning,
                    stacklevel=3,
                )
        elif active:
            joined = ", ".join(f"LUT_I_{k}={inputs[k]!r}" for k in sorted(active))
            warnings.warn(
                f"BLE has no LUT_CONFIG but has set LUT_I vals ({joined}).",
                category=LUTConfigWarning,
                stacklevel=3,
            )


@dataclass
class MUX_CFG:
    INSYNC: CLBInputSync = None
    CLBIN: CLBIN = None


class CNTMUX(IntEnum):
    CNT0_COUNT_IS_0 = 0b000
    CNT0_COUNT_IS_1 = 0b001
    CNT0_COUNT_IS_2 = 0b010
    CNT0_COUNT_IS_3 = 0b011
    CNT0_COUNT_IS_4 = 0b100
    CNT0_COUNT_IS_5 = 0b101
    CNT0_COUNT_IS_6 = 0b110
    CNT0_COUNT_IS_7 = 0b111


@dataclass
class COUNTER:
    CNT_STOP: COUNTERIN = None
    CNT_RESET: COUNTERIN = None
    COUNT_IS_A1: CNTMUX = None
    COUNT_IS_A2: CNTMUX = None
    COUNT_IS_B1: CNTMUX = None
    COUNT_IS_B2: CNTMUX = None
    COUNT_IS_C1: CNTMUX = None
    COUNT_IS_C2: CNTMUX = None
    COUNT_IS_D1: CNTMUX = None
    COUNT_IS_D2: CNTMUX = None


_CLB_ENUM: dict[int, type[IntEnum]] = {
    0: CLBPPSOUT0,
    1: CLBPPSOUT1,
    2: CLBPPSOUT2,
    3: CLBPPSOUT3,
    4: CLBPPSOUT4,
    5: CLBPPSOUT5,
    6: CLBPPSOUT6,
    7: CLBPPSOUT7,
}


@dataclass
class _PPS_OUT:
    """PPS-OUT val.

    * Accepts **either** a BLEXY **or** the correct CLBPPSOUTx value.
    * Rejects BLEs that belong to a different PPS group.
    * Rejects CLBPPSOUT values from the wrong enum.
    """

    idx: int
    _out: Optional[IntEnum] = None

    @property
    def OUT(self) -> Optional[IntEnum]:
        return self._out

    @OUT.setter
    def OUT(self, v: Union[IntEnum, BLEXY]) -> None:
        enum_cls = _CLB_ENUM[self.idx]
        if isinstance(v, BLEXY):
            group = v.value >> 2
            if group != self.idx:
                raise ValueError(
                    f"{v.name} is routed via PPS_OUT{group}, not PPS_OUT{self.idx}"
                )
            self._out = enum_cls(v.value & 0b11)
        elif isinstance(v, enum_cls):
            self._out = v
        else:
            raise TypeError(
                f"PPS_OUT{self.idx}.OUT expects {enum_cls.__name__} or BLEXY"
            )


class PPS_OUT0(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(0)


class PPS_OUT1(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(1)


class PPS_OUT2(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(2)


class PPS_OUT3(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(3)


class PPS_OUT4(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(4)


class PPS_OUT5(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(5)


class PPS_OUT6(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(6)


class PPS_OUT7(_PPS_OUT):
    def __init__(self) -> None:
        super().__init__(7)


@dataclass
class IRQ_OUT0:
    OUT: CLB1IF0 = None


@dataclass
class IRQ_OUT1:
    OUT: CLB1IF1 = None


@dataclass
class IRQ_OUT2:
    OUT: CLB1IF2 = None


@dataclass
class IRQ_OUT3:
    OUT: CLB1IF3 = None


IRQ_OUT_NUM = {
    0: IRQ_OUT0,
    1: IRQ_OUT1,
    2: IRQ_OUT2,
    3: IRQ_OUT3,
}

PPS_OUT_NAME = {
    "PPS_X5Y2": PPS_OUT0,
    "PPS_X5Y3": PPS_OUT1,
    "PPS_X5Y4": PPS_OUT2,
    "PPS_X5Y5": PPS_OUT3,
    "PPS_X5Y6": PPS_OUT4,
    "PPS_X5Y7": PPS_OUT5,
    "PPS_X5Y8": PPS_OUT6,
    "PPS_X5Y9": PPS_OUT7,
}

PPS_OUT_NUM = {
    0: PPS_OUT0,
    1: PPS_OUT1,
    2: PPS_OUT2,
    3: PPS_OUT3,
    4: PPS_OUT4,
    5: PPS_OUT5,
    6: PPS_OUT6,
    7: PPS_OUT7,
}

PPS_OUT_BITS = {
    PPS_OUT0: {0: 85, 1: 86},
    PPS_OUT1: {0: 87, 1: 88},
    PPS_OUT2: {0: 74, 1: 75},
    PPS_OUT3: {0: 76, 1: 77},
    PPS_OUT4: {0: 64, 1: 65},
    PPS_OUT5: {0: 66, 1: 67},
    PPS_OUT6: {0: 52, 1: 53},
    PPS_OUT7: {0: 54, 1: 55},
}

COUNT_MUX_CFG_bits = {
    "COUNT_IS_A1": {0: 41, 1: 42, 2: 43},
    "COUNT_IS_A2": {0: 44, 1: 45, 2: 48},
    "COUNT_IS_B1": {0: 49, 1: 50, 2: 51},
    "COUNT_IS_B2": {0: 32, 1: 33, 2: 34},
    "COUNT_IS_C1": {0: 35, 1: 36, 2: 37},
    "COUNT_IS_C2": {0: 38, 1: 39, 2: 40},
    "COUNT_IS_D1": {0: 21, 1: 22, 2: 23},
    "COUNT_IS_D2": {0: 24, 1: 25, 2: 26},
}


class CLKDIV(IntEnum):
    DIV_BY_1 = 0b000
    DIV_BY_2 = 0b001
    DIV_BY_4 = 0b010
    DIV_BY_8 = 0b011
    DIV_BY_16 = 0b100
    DIV_BY_32 = 0b101
    DIV_BY_64 = 0b110
    DIV_BY_128 = 0b111


CLKDIV_bits = {0: 0, 1: 1, 2: 2}

COUNT_STOP_bits = {0: 9, 1: 10, 2: 11, 3: 12, 4: 13}
COUNT_RESET_bits = {0: 16, 1: 17, 2: 18, 3: 19, 4: 20}

IRQ_bits = {
    0: {0: 89, 1: 90, 2: 91},
    1: {0: 80, 1: 81, 2: 82},
    2: {0: 68, 1: 69, 2: 70},
    3: {0: 56, 1: 57, 2: 58},
}

MUX_CFG_bits = {
    0: {
        "CLBIN": {0: 256, 1: 257, 2: 258, 3: 259, 4: 260, 5: 261},
        "INSYNC": {0: 262, 1: 263, 2: 264},
    },
    1: {
        "CLBIN": {0: 245, 1: 246, 2: 247, 3: 248, 4: 249, 5: 250},
        "INSYNC": {0: 251, 1: 252, 2: 253},
    },
    2: {
        "CLBIN": {0: 234, 1: 235, 2: 236, 3: 237, 4: 240, 5: 241},
        "INSYNC": {0: 242, 1: 243, 2: 244},
    },
    3: {
        "CLBIN": {0: 224, 1: 225, 2: 226, 3: 227, 4: 228, 5: 229},
        "INSYNC": {0: 230, 1: 231, 2: 232},
    },
    4: {
        "CLBIN": {0: 213, 1: 214, 2: 215, 3: 216, 4: 217, 5: 218},
        "INSYNC": {0: 219, 1: 220, 2: 221},
    },
    5: {
        "CLBIN": {0: 202, 1: 203, 2: 204, 3: 205, 4: 208, 5: 209},
        "INSYNC": {0: 210, 1: 211, 2: 212},
    },
    6: {
        "CLBIN": {0: 192, 1: 193, 2: 194, 3: 195, 4: 196, 5: 197},
        "INSYNC": {0: 198, 1: 199, 2: 200},
    },
    7: {
        "CLBIN": {0: 180, 1: 181, 2: 182, 3: 183, 4: 184, 5: 185},
        "INSYNC": {0: 186, 1: 187, 2: 188},
    },
    8: {
        "CLBIN": {0: 169, 1: 170, 2: 171, 3: 172, 4: 173, 5: 176},
        "INSYNC": {0: 177, 1: 178, 2: 179},
    },
    9: {
        "CLBIN": {0: 160, 1: 161, 2: 162, 3: 163, 4: 164, 5: 165},
        "INSYNC": {0: 166, 1: 167, 2: 168},
    },
    10: {
        "CLBIN": {0: 149, 1: 150, 2: 151, 3: 152, 4: 153, 5: 154},
        "INSYNC": {0: 155, 1: 156, 2: 157},
    },
    11: {
        "CLBIN": {0: 137, 1: 138, 2: 139, 3: 140, 4: 141, 5: 144},
        "INSYNC": {0: 145, 1: 146, 2: 147},
    },
    12: {
        "CLBIN": {0: 128, 1: 129, 2: 130, 3: 131, 4: 132, 5: 133},
        "INSYNC": {0: 134, 1: 135, 2: 136},
    },
    13: {
        "CLBIN": {0: 117, 1: 118, 2: 119, 3: 120, 4: 121, 5: 122},
        "INSYNC": {0: 123, 1: 124, 2: 125},
    },
    14: {
        "CLBIN": {0: 106, 1: 107, 2: 108, 3: 109, 4: 112, 5: 113},
        "INSYNC": {0: 114, 1: 115, 2: 116},
    },
    15: {
        "CLBIN": {0: 96, 1: 97, 2: 98, 3: 99, 4: 100, 5: 101},
        "INSYNC": {0: 102, 1: 103, 2: 104},
    },
}


class FASM:
    def __init__(self, fasm_file: Path):
        self.LUTS = defaultdict(BLE_CFG)
        self.PPS_OUT = dict()
        self.IRQ_OUT = dict()
        self.OE = defaultdict(OESELn)
        self.MUXS = defaultdict(MUX_CFG)
        self.CLKDIV = CLKDIV.DIV_BY_1
        self.COUNTER = COUNTER()
        self.TIMR0_IN = None

        with open(fasm_file, "r") as f:
            for l in f.readlines():
                if l.startswith("#"):
                    continue
                if l.startswith("BLE_X"):
                    self.pharse_ble(l)
                    continue
                if l.startswith("PPS_X"):
                    self.pharse_pps(l)
                    continue
                if l.startswith("MUX"):
                    self.pharse_mux(l)
                    continue
                if l.startswith("CLKDIV"):
                    _, val = l.split("=")
                    _, val = val.split("b")
                    val = int(val.strip(), 2)
                    self.CLKDIV = CLKDIV(val)
                    continue
                if l.startswith("CNT_X0Y3"):
                    self.pharse_cnt(l)
                    continue
                if l.startswith("CLB_IRQ"):
                    self.pharse_irq(l)
                    continue
                if l.startswith("PPS_OE"):
                    self.pharse_oe(l)
                    continue
                if l.startswith("MODULE_CLB_"):
                    self.pharse_module(l)
                    continue
                print(f"Unhandled line: {repr(l)}")

    @staticmethod
    def lo_to_ble(lo_str: str) -> str:
        """Convert 'LO_Y_X' to 'BLE_XY'."""
        _, lo_y, lo_x = lo_str.split("_")
        return f"BLE_X{int(lo_x) + 1}Y{int(lo_y) + 2}"

    @staticmethod
    def ble_to_lo(ble_str: str) -> str:
        """Convert 'BLE_XY' to 'LO_Y_X'."""
        ble_x, ble_y = ble_str[5:].split("Y")
        return f"LO_{int(ble_y) - 2}_{int(ble_x) - 1}"

    def pharse_ble(self, line):
        parts = line.split(".")
        try:
            ble_sel = BLEXY.from_fasm(parts[0])

            if parts[1] == "BLE0":
                if parts[2] == "FLOPSEL":
                    # ex: BLE_X1Y2.BLE0.FLOPSEL.DISABLE
                    self.LUTS[ble_sel].FLOPSEL = FLOPSEL.__members__[parts[3].strip()]
                    return
                if parts[2] == "LUT":
                    # ex: BLE_X1Y2.BLE0.LUT.INIT[15:0] = 16'b1110101111110100
                    self.LUTS[ble_sel].LUT_CONFIG = parts[-1][-17:-1]
                    return

            if parts[1].startswith("BLE0_LI"):
                if parts[2].startswith("LO_"):
                    ble_num = BLEXY.from_fasm(self.lo_to_ble(parts[2])).value
                    ble_id = f"CLB_BLE_{ble_num}"
                else:
                    ble_id = parts[2].strip()

                if parts[1][-1] == "0":
                    self.LUTS[ble_sel].LUT_I_A = LUT_IN_A.__members__[ble_id]
                    return
                if parts[1][-1] == "1":
                    self.LUTS[ble_sel].LUT_I_B = LUT_IN_B.__members__[ble_id]
                    return
                if parts[1][-1] == "2":
                    self.LUTS[ble_sel].LUT_I_C = LUT_IN_C.__members__[ble_id]
                    return
                if parts[1][-1] == "3":
                    self.LUTS[ble_sel].LUT_I_D = LUT_IN_D.__members__[ble_id]
                    return
        except Exception as e:
            raise RuntimeError(f"Error parsing line '{line}'") from e

        print(f"Unhandled ble line: {parts}")
        return

    def pharse_pps(self, line):
        pps_name, opad, lo_val = line.strip().split(".")
        assert opad == "OPAD0_O"

        pps_val = PPS_OUT_NAME[pps_name]()

        pps_val.OUT = _CLB_ENUM[pps_val.idx](int(lo_val[-1]))

        self.PPS_OUT[PPS_OUT_NAME[pps_name]] = pps_val

    def pharse_irq(self, line):
        irq_name, opad, lo_val = line.strip().split(".")
        assert opad == "OPAD0_O"

        irq_val = IRQ_OUT_NUM[int(irq_name[-1])]()

        irq_val.OUT = irq_val.__annotations__["OUT"](int(lo_val[-1]))

        self.IRQ_OUT[int(irq_name[-1])] = irq_val

    def pharse_oe(self, line):
        oe_name, opad, lo_val = line.strip().split(".")
        assert opad == "OPAD0_O"

        self.OE[int(oe_name[-1])] = OESELn.__members__[lo_val[3:]]

    def pharse_mux(self, line):
        try:
            mux_type, value = line.strip().split("=")
            _, value = value.strip().split("b")

            mux_num, reg_name = mux_type.strip().split(".")
            mux_num = int(mux_num[3:])

            if reg_name.startswith("CLBIN"):
                self.MUXS[mux_num].CLBIN = CLBIN(int(value, 2))
            elif reg_name.startswith("INSYNC"):
                self.MUXS[mux_num].INSYNC = CLBInputSync(int(value, 2))
            else:
                raise RuntimeError(f"Error parsing line '{line}'")
        except Exception as e:
            raise RuntimeError(f"Error parsing line '{line}'") from e

    def pharse_cnt(self, line):
        parts = line.strip().split(".")

        if parts[1] == "CNT0_RESET":
            ble_num = BLEXY.from_fasm(self.lo_to_ble(parts[2])).value
            self.COUNTER.CNT_RESET = COUNTERIN(ble_num)
        elif parts[1] == "CNT0_STOP":
            ble_num = BLEXY.from_fasm(self.lo_to_ble(parts[2])).value
            self.COUNTER.CNT_STOP = COUNTERIN(ble_num)
        elif parts[1].startswith("COUNT_IS_"):
            setattr(self.COUNTER, parts[1], CNTMUX.__members__[parts[2]])
        else:
            raise RuntimeError(f"Error parsing line '{line}'")

    def pharse_module(self, line):
        module, opad, lo_val = line.strip().split(".")

        if module == "MODULE_CLB_TMR0_IN":
            self.TIMR0_IN = lo_val
            return
        if module == "MODULE_CLB_TMR1_IN":
            self.TIMR1_IN = lo_val
            return
        if module == "MODULE_CLB_TMR1_GATE":
            self.TIMR1_GATE = lo_val
            return
        if module == "MODULE_CLB_TMR2_IN":
            self.TIMR2_IN = lo_val
            return
        if module == "MODULE_CLB_TMR2_RST":
            self.TIMR2_RST = lo_val
            return
        if module == "MODULE_CLB_CCP1_IN":
            self.CCP1_IN = lo_val
            return
        if module == "MODULE_CLB_CCP2_IN":
            self.CCP2_IN = lo_val
            return
        if module == "MODULE_CLB_ADC_IN":
            self.ADC_IN = lo_val
            return

        raise RuntimeError(f"Error parsing line '{line}'")

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            + ", ".join(f"\n\t{k}={pformat(v)}" for k, v in self.__dict__.items())
            + "\n)"
        )

    def __repr__(self):
        return self.__str__()
