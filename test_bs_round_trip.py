import tempfile
import unittest
from pathlib import Path

from hypothesis import strategies as st, given, settings
from bitstream import Bitstream
from data_model import (
    PPS_OUT_NUM,
    BLEXY,
    CLKDIV,
    FLOPSEL,
    LUT_IN_A,
    LUT_IN_B,
    LUT_IN_C,
    LUT_IN_D,
    CLBIN,
    CLBInputSync,
    IRQ_OUT_NUM,
    COUNTERIN,
    CNTMUX,
    COUNT_MUX_CFG_bits,
    _CLB_ENUM,
)

enum = lambda e: st.sampled_from(list(e))
bitstring16 = st.integers(0, 0xFFFF).map(lambda n: f"{n:016b}")


@st.composite
def bitstreams(draw):
    bs = Bitstream()

    bs.CLKDIV = draw(enum(CLKDIV))
    for ble in BLEXY:
        cfg = bs.LUTS[ble]
        cfg.LUT_CONFIG = draw(bitstring16)
        cfg.FLOPSEL = draw(enum(FLOPSEL))
        cfg.LUT_I_A = draw(enum(LUT_IN_A))
        cfg.LUT_I_B = draw(enum(LUT_IN_B))
        cfg.LUT_I_C = draw(enum(LUT_IN_C))
        cfg.LUT_I_D = draw(enum(LUT_IN_D))

    for i in range(16):
        bs.MUXS[i].CLBIN = draw(enum(CLBIN))
        bs.MUXS[i].INSYNC = CLBInputSync(draw(st.integers(0, 7)))

    for typ in PPS_OUT_NUM.values():
        bs.PPS_OUT.setdefault(typ, typ()).OUT = draw(enum(_CLB_ENUM[typ().idx]))

    for idx, typ in IRQ_OUT_NUM.items():
        bs.IRQ_OUT.setdefault(idx, typ()).OUT = draw(enum(typ.__annotations__["OUT"]))

    bs.COUNTER.CNT_STOP = draw(enum(COUNTERIN))
    bs.COUNTER.CNT_RESET = draw(enum(COUNTERIN))
    for attr in COUNT_MUX_CFG_bits:
        setattr(bs.COUNTER, attr, draw(enum(CNTMUX)))

    return bs


class BitstreamRoundTrip(unittest.TestCase):
    """TestCase wrapper"""

    @settings(max_examples=5_000)
    @given(bs=bitstreams())
    def test_roundtrip_survives_disk(self, bs) -> None:
        with tempfile.TemporaryDirectory() as d:
            fn = Path(d) / "bs.json"
            bs.save_bitstream(fn)
            reloaded = Bitstream(fn)
            self.assertEqual(bs._bitstream, reloaded._bitstream)
            self.assertEqual(
                {k: v for k, v in vars(bs).items() if k != "_bitstream"},
                {k: v for k, v in vars(reloaded).items() if k != "_bitstream"},
            )
