import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, Optional, Type, Union

from data_model import (
    FASM,
    BLE_CFG,
    MUX_CFG,
    COUNTER,
    PPS_OUT0,
    PPS_OUT1,
    PPS_OUT2,
    PPS_OUT3,
    PPS_OUT4,
    PPS_OUT5,
    PPS_OUT6,
    PPS_OUT7,
    IRQ_OUT0,
    IRQ_OUT1,
    IRQ_OUT2,
    IRQ_OUT3,
    LUT_IN_A,
    LUT_IN_B,
    LUT_IN_C,
    LUT_IN_D,
    COUNTERIN,
    OESELn,
    CLBIN,
    CLBInputSync,
    BLEXY,
    FLOPSEL,
    CNTMUX,
    CLKDIV,
    get_lut_setting_bits,
    get_lut_input_bit_addresses,
    get_flopsel,
    PPS_OUT_BITS,
    COUNT_MUX_CFG_bits,
    CLKDIV_bits,
    COUNT_STOP_bits,
    COUNT_RESET_bits,
    IRQ_bits,
    MUX_CFG_bits,
    IRQ_OUT_NUM,
    CLBPPSOUT3,
    CLBPPSOUT0,
    CLBPPSOUT1,
    CLBPPSOUT2,
    CLBPPSOUT4,
    CLBPPSOUT5,
    CLBPPSOUT6,
    CLBPPSOUT7,
    _CLB_ENUM,
)

BITSTREAM_LENGTH = 102 * 16  # 102 16 bit (actually 14 bit) words


def _bits_to_int(get_bit: Callable[[int], str], bit_map: dict[int, int]) -> int:
    """Return an integer whose binary value is found in *bit_map* (LSB first)."""
    return int("".join(get_bit(bit_map[i]) for i in reversed(sorted(bit_map))), 2)


def _int_to_bits(
    set_bit: Callable[[int, int | str], None],
    value: int,
    bit_map: dict[int, int],
    *,
    num_bits: Optional[int] = None,
) -> None:
    """Write *value* into *bit_map* (LSB first)."""
    num_bits = num_bits or len(bit_map)
    bits = f"{value:0{num_bits}b}"[::-1]
    if len(bits) > len(bit_map):
        raise ValueError(f"{value} does not fit into {len(bit_map)} bits")
    for i, b in enumerate(bits):
        set_bit(bit_map[i], b)


class Bitstream(FASM):
    # noinspection PyMissingConstructor
    def __init__(self, bitstream_json_file: Optional[Path] = None) -> None:
        self.LUTS: Dict[BLEXY, BLE_CFG] = defaultdict(BLE_CFG)
        self.PPS_OUT: Dict[
            Type,
            Union[
                PPS_OUT0,
                PPS_OUT1,
                PPS_OUT2,
                PPS_OUT3,
                PPS_OUT4,
                PPS_OUT5,
                PPS_OUT6,
                PPS_OUT7,
            ],
        ] = {}
        self.IRQ_OUT: Dict[int, Union[IRQ_OUT0, IRQ_OUT1, IRQ_OUT2, IRQ_OUT3]] = {}
        self.MUXS: Dict[int, MUX_CFG] = defaultdict(MUX_CFG)
        self.CLKDIV: CLKDIV = CLKDIV.DIV_BY_1
        self.COUNTER: COUNTER = COUNTER()

        # non‑bitstream inputs are kept verbatim
        self.TIMR0_IN = self.TIMR1_IN = self.TIMR1_GATE = None
        self.TIMR2_IN = self.TIMR2_RST = None
        self.CCP1_IN = self.CCP2_IN = self.ADC_IN = None
        self.OE: Dict[int, OESELn] = {}

        self._bitstream: str = (
            self._load_bitstream_from_json(bitstream_json_file)
            if bitstream_json_file
            else "0" * BITSTREAM_LENGTH
        )

        self._parse_bitstream()

    @staticmethod
    def _load_bitstream_from_json(json_file: Path) -> str:
        if not json_file.exists():
            raise FileNotFoundError(json_file)
        try:
            data = json.loads(json_file.read_text(encoding="utf8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {json_file}: {exc}") from exc

        words = data["bitstream"] if isinstance(data, dict) else data
        if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
            raise TypeError("'bitstream' must be a list[str] of hexadecimal words")

        bs = "".join(f"{int(w, 16):016b}" for w in words)[::-1]
        if len(bs) != BITSTREAM_LENGTH:
            raise ValueError(
                f"bitstream length is {len(bs)}, expected {BITSTREAM_LENGTH}"
            )
        return bs

    def _save_bitstream_to_json(self, json_file: Path) -> None:
        words = [
            f"{int(self._bitstream[::-1][i: i + 16], 2):04x}"
            for i in range(0, BITSTREAM_LENGTH, 16)
        ]
        json_file.write_text(
            json.dumps({"bitstream": words}, indent=2), encoding="utf8"
        )

    def _get_bit(self, idx: int) -> str:
        if idx >= BITSTREAM_LENGTH or idx < 0:
            raise IndexError(idx)
        return self._bitstream[idx]

    def _set_bit(self, idx: int, val: int | str) -> None:
        if idx >= BITSTREAM_LENGTH or idx < 0:
            raise IndexError(idx)
        v = str(int(val))
        if v not in "01":
            raise ValueError("bit must be 0/1")
        self._bitstream = f"{self._bitstream[:idx]}{v}{self._bitstream[idx + 1:]}"

    def _parse_bitstream(self) -> None:
        self._parse_luts()
        self._parse_pps()
        self._parse_irq()
        self._parse_mux()
        self.CLKDIV = CLKDIV(_bits_to_int(self._get_bit, CLKDIV_bits))
        self._parse_counter()

    def _parse_luts(self) -> None:
        for ble_idx in BLEXY:
            cfg = self.LUTS[ble_idx]
            idx = ble_idx.value
            bits_map = get_lut_setting_bits(idx)
            cfg.LUT_CONFIG = "".join(
                self._get_bit(bits_map[i]) for i in reversed(range(16))
            )
            # FLOPSEL
            cfg.FLOPSEL = FLOPSEL(self._get_bit(get_flopsel(idx)) == "1")
            in_maps = get_lut_input_bit_addresses(idx)
            cfg.LUT_I_A = LUT_IN_A(_bits_to_int(self._get_bit, in_maps["LUT_I_A"]))
            cfg.LUT_I_B = LUT_IN_B(_bits_to_int(self._get_bit, in_maps["LUT_I_B"]))
            cfg.LUT_I_C = LUT_IN_C(_bits_to_int(self._get_bit, in_maps["LUT_I_C"]))
            cfg.LUT_I_D = LUT_IN_D(_bits_to_int(self._get_bit, in_maps["LUT_I_D"]))

    def _parse_pps(self) -> None:
        for pps_cls, bit_map in PPS_OUT_BITS.items():
            raw_val: int = _bits_to_int(self._get_bit, bit_map) & 0b11  # 0-3
            inst = pps_cls()
            enum_cls = _CLB_ENUM[inst.idx]
            inst.OUT = enum_cls(raw_val)
            self.PPS_OUT[pps_cls] = inst

    def _parse_irq(self) -> None:
        for idx, bit_map in IRQ_bits.items():
            val = _bits_to_int(self._get_bit, bit_map)
            irq_cls = IRQ_OUT_NUM[idx]
            inst = irq_cls()
            inst.OUT = irq_cls.__annotations__["OUT"](val)
            self.IRQ_OUT[idx] = inst

    def _parse_mux(self) -> None:
        for idx, maps in MUX_CFG_bits.items():
            cfg = self.MUXS[idx]
            cfg.CLBIN = CLBIN(_bits_to_int(self._get_bit, maps["CLBIN"]))
            cfg.INSYNC = CLBInputSync(_bits_to_int(self._get_bit, maps["INSYNC"]))

    def _parse_counter(self) -> None:
        c = self.COUNTER
        c.CNT_STOP = COUNTERIN(_bits_to_int(self._get_bit, COUNT_STOP_bits))
        c.CNT_RESET = COUNTERIN(_bits_to_int(self._get_bit, COUNT_RESET_bits))
        for name, m in COUNT_MUX_CFG_bits.items():
            setattr(c, name, CNTMUX(_bits_to_int(self._get_bit, m)))

    def _update_bitstream(self) -> None:
        self._update_luts()
        self._update_pps()
        self._update_irq()
        self._update_mux()
        _int_to_bits(self._set_bit, self.CLKDIV.value, CLKDIV_bits)
        self._update_counter()

    def _update_luts(self) -> None:
        for ble_idx, cfg in self.LUTS.items():
            idx = ble_idx.value
            # LUT_CONFIG
            _int_to_bits(
                self._set_bit,
                int(cfg.LUT_CONFIG, 2),
                get_lut_setting_bits(idx),
                num_bits=16,
            )
            # FLOPSEL
            self._set_bit(get_flopsel(idx), int(cfg.FLOPSEL == FLOPSEL.ENABLE.value))
            # inputs
            maps = get_lut_input_bit_addresses(idx)
            _int_to_bits(
                self._set_bit,
                (0 if cfg.LUT_I_A is None else cfg.LUT_I_A.value),
                maps["LUT_I_A"],
            )
            _int_to_bits(
                self._set_bit,
                (0 if cfg.LUT_I_B is None else cfg.LUT_I_B.value),
                maps["LUT_I_B"],
            )
            _int_to_bits(
                self._set_bit,
                (0 if cfg.LUT_I_C is None else cfg.LUT_I_C.value),
                maps["LUT_I_C"],
            )
            _int_to_bits(
                self._set_bit,
                (0 if cfg.LUT_I_D is None else cfg.LUT_I_D.value),
                maps["LUT_I_D"],
            )

    def _update_pps(self) -> None:
        for cls_, inst in self.PPS_OUT.items():
            _int_to_bits(self._set_bit, inst.OUT.value, PPS_OUT_BITS[cls_])

    def _update_irq(self) -> None:
        for idx, inst in self.IRQ_OUT.items():
            _int_to_bits(self._set_bit, inst.OUT.value, IRQ_bits[idx])

    def _update_mux(self) -> None:
        for idx, cfg in self.MUXS.items():
            maps = MUX_CFG_bits[idx]
            _int_to_bits(self._set_bit, cfg.CLBIN.value, maps["CLBIN"])  # type: ignore
            _int_to_bits(self._set_bit, cfg.INSYNC.value, maps["INSYNC"])  # type: ignore

    def _update_counter(self) -> None:
        c = self.COUNTER
        _int_to_bits(self._set_bit, c.CNT_STOP.value, COUNT_STOP_bits)
        _int_to_bits(self._set_bit, c.CNT_RESET.value, COUNT_RESET_bits)
        for name, m in COUNT_MUX_CFG_bits.items():
            _int_to_bits(self._set_bit, getattr(c, name).value, m)

    def save_bitstream(self, output_json_file: Path) -> None:
        self._update_bitstream()
        self._save_bitstream_to_json(output_json_file)

    def save_bitstream_s(
        self,
        out_file: Path,
        *,
        device_macros: list[str] | None = None,
        psect: str = "clb_config",
    ) -> None:
        self._update_bitstream()
        words = [
            f"{int(self._bitstream[::-1][i: i + 16], 2):04X}"
            for i in range(0, BITSTREAM_LENGTH, 16)
        ]
        device_macros = device_macros or [
            "_16F13113",
            "_16F13114",
            "_16F13115",
            "_16F13123",
            "_16F13124",
            "_16F13125",
            "_16F13143",
            "_16F13144",
            "_16F13145",
        ]
        guard = " || ".join(f"defined({m})" for m in device_macros)
        tpl = f"""\
#if !({guard})
    #error This module is only suitable for PIC16F13145 family devices
#endif

#ifdef CLB_CONFIG_ADDR
    psect {psect},global,class=STRCODE,abs,ovrld,delta=2,noexec,split=0,merge=0,keep
#else
    psect {psect},global,class=STRCODE,delta=2,noexec,split=0,merge=0,keep
#endif

global _start_{psect}

psect   {psect}
#ifdef CLB_CONFIG_ADDR
    ORG CLB_CONFIG_ADDR
#endif

_start_{psect}:
""" + "\n".join(
            f"    dw  0x{w};" for w in words
        )
        out_file.write_text(tpl, encoding="utf8")

    def __str__(self) -> str:  # pragma: no cover
        from pprint import pformat

        ivars = ", ".join(f"\n\t{k}={pformat(v)}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({ivars}\n)"

    __repr__ = __str__


if __name__ == "__main__":
    bs = Bitstream()

    print(bs)
