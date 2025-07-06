from dataclasses import dataclass, field
from itertools import cycle
from pathlib import Path
from typing import Mapping, MutableMapping, Union, Iterator

from bitstream import Bitstream
from data_model import (
    FASM,
    LUT_IN_A,
    LUT_IN_B,
    LUT_IN_C,
    LUT_IN_D,
    BLEXY,
    FLOPSEL,
    PPS_OUT_NUM,
)

VAR_ORDER = "ABCD"

COUNTER_OUTPUT_PORT_MAP = {
    "COUNT_IS_A1": "out0",
    "COUNT_IS_A2": "out1",
    "COUNT_IS_B1": "out2",
    "COUNT_IS_B2": "out3",
    "COUNT_IS_C1": "out4",
    "COUNT_IS_C2": "out5",
    "COUNT_IS_D1": "out6",
    "COUNT_IS_D2": "out7",
}
COUNTER_OUTPUT_LABELS_ORDERED = [
    ("A1", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_A1"]),
    ("A2", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_A2"]),
    ("B1", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_B1"]),
    ("B2", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_B2"]),
    ("C1", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_C1"]),
    ("C2", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_C2"]),
    ("D1", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_D1"]),
    ("D2", COUNTER_OUTPUT_PORT_MAP["COUNT_IS_D2"]),
]


def _parse_ble_index_from_name(name_str: str) -> int | None:
    if name_str is None or not isinstance(name_str, str):
        return None
    parts = name_str.split("_")
    try:
        for i, part in enumerate(parts):
            if part.upper() == "BLE" and i + 1 < len(parts) and parts[i + 1].isdigit():
                return int(parts[i + 1])
        if parts[-1].isdigit():
            return int(parts[-1])
    except (ValueError, IndexError):
        return None
    return None


def get_lut_equation_str(cfg: str, active: Mapping[str, bool]) -> str:
    if len(cfg) != 16 or set(cfg) - {"0", "1"}:
        return "Invalid"
    if cfg == "0" * 16:
        return "O = 0"
    if cfg == "1" * 16:
        return "O = 1"

    used = [
        i
        for i, v in enumerate(VAR_ORDER)
        if active.get(v, False) or active.get(v.lower(), False)
    ]
    if not used:
        return "O = 1" if cfg[15] == "1" else "O = 0"

    sop, pos = set(), set()
    for addr in range(16):
        bit = cfg[15 - addr]
        mt, pt = [], []
        for b in used:
            var = VAR_ORDER[b]
            if (addr >> b) & 1:
                mt.append(var)
                pt.append(f"~{var}")
            else:
                mt.append(f"~{var}")
                pt.append(var)
        mt_str = "&".join(mt) if mt else "1"
        pt_str = "|".join(pt) if pt else "0"
        (sop if bit == "1" else pos).add(mt_str if bit == "1" else pt_str)

    sop_expr = "|".join(sorted(sop)) or "0"
    pos_expr = "&".join(f"({t})" if "|" in t else t for t in sorted(pos)) or "1"

    expr = sop_expr if len(sop_expr) <= len(pos_expr) else pos_expr
    return f"O={expr}" if len(expr) <= len(cfg) else f"0x{int(cfg, 2):04X}"


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


@dataclass
class DotBuilder:
    name: str = "main"
    nodes: MutableMapping[str, str] = field(default_factory=dict)
    edges: list[str] = field(default_factory=list)
    source_rank: set[str] = field(default_factory=set)
    sink_rank: set[str] = field(default_factory=set)
    _colours: Iterator[int] = field(
        default_factory=lambda: cycle(range(1, 9)), init=False
    )

    def add_pin(
        self, pin_id: str, label: str, *, cls: str, rank: str | None = None
    ) -> None:
        if pin_id in self.nodes:
            return
        self.nodes[pin_id] = (
            f'  {pin_id} [shape=octagon, class="pin {cls}", label="{label}"];'
        )
        if rank == "source":
            self.source_rank.add(pin_id)
        elif rank == "sink":
            self.sink_rank.add(pin_id)

    def add_clb(
        self, clb_id: str, tooltip: str, label: str, route_only=False, is_block=False
    ) -> None:
        shape = "record" if is_block else "Mrecord"
        cls_base = "bel" if not is_block else "block"
        cls_type = "lut4" if not is_block else clb_id.replace("clb_", "")

        full_cls = f"{cls_base} {cls_type}" + (
            " route_only" if route_only and not is_block else ""
        )

        self.nodes[clb_id] = (
            f'  {clb_id} [shape={shape}, tooltip="{tooltip}", '
            f'color=grey, fontcolor=grey, class="{full_cls}", label="{label}"];'
        )

    def add_edge(self, src: str, dst: str, tooltip: str, *, dashed=False) -> None:
        style = "style=dashed, color=grey" if dashed else f"color={next(self._colours)}"
        self.edges.append(
            f'  {src} -> {dst} [tooltip="{tooltip}", {style}, class="net"];'
        )

    def build(self) -> str:
        lines = [
            f'digraph "{self.name}" {{',
            "  rankdir=LR;",
            "  remincross=true;",
            "  newrank  = true;",
            "  ranksep  = 1.2;",
            "  bgcolor=transparent;",
            '  edge [colorscheme=dark28, label="", fontname="Arial", fontsize=9];',
            '  node [fontname="Arial", fontsize=10];',
            *self.nodes.values(),
        ]
        if self.source_rank:
            lines.append(f"  {{ rank=source; {'; '.join(sorted(self.source_rank))}; }}")
        if self.sink_rank:
            lines.append(f"  {{ rank=sink; {'; '.join(sorted(self.sink_rank))}; }}")
        lines.extend(self.edges)
        lines.append("}")
        return "\n".join(lines)


def generate_dot_from_config(
    cfg: Union[Bitstream, FASM], graph_name: str = "main"
) -> str:
    dot = DotBuilder(graph_name)
    all_luts = getattr(cfg, "LUTS", {})

    in_mux: dict[int, str | None] = {
        idx: (
            m.CLBIN.name
            if m.CLBIN is not None and hasattr(m.CLBIN, "name") and bool(m.CLBIN.name)
            else None
        )
        for idx, m in getattr(cfg, "MUXS", {}).items()
    }
    for idx in range(16):
        pin_id = f"pin_IN{idx}"
        dot.add_pin(pin_id, f"IN{idx}", cls="pin_input in_channel")
        src_mux_sel_name = in_mux.get(idx)
        if src_mux_sel_name is not None:
            src_id = f"pin_{src_mux_sel_name}"
            dot.add_pin(
                src_id, src_mux_sel_name, cls="pin_input clbin_pin", rank="source"
            )
            dot.add_edge(
                f"{src_id}:e",
                f"{pin_id}:w",
                f"{src_mux_sel_name} -> IN{idx}",
                dashed=True,
            )
        else:
            unconf_src_id = f"pin_IN{idx}_Unconfigured"
            dot.add_pin(
                unconf_src_id,
                f"IN{idx}_Unconfigured",
                cls="pin_input clbin_pin",
                rank="source",
            )
            dot.add_edge(
                f"{unconf_src_id}:e",
                f"{pin_id}:w",
                f"IN{idx}_Unconfigured -> IN{idx}",
                dashed=True,
            )

    active_bles: dict[BLEXY, dict] = {}
    for ble_xy, ble_cfg_obj in all_luts.items():
        idx = ble_xy.value
        active_ins = get_active_lut_inputs(ble_cfg_obj.LUT_CONFIG)
        used_elsewhere = _ble_output_used(cfg, idx, ble_xy)
        if any(active_ins.values()) or used_elsewhere:
            active_bles[ble_xy] = {
                "cfg": ble_cfg_obj,
                "inputs": active_ins,
                "used_elsewhere": used_elsewhere,
            }

    for ble_xy, meta in active_bles.items():
        idx = ble_xy.value
        ble_cfg_obj = meta["cfg"]
        active_ins = meta["inputs"]
        eq = get_lut_equation_str(ble_cfg_obj.LUT_CONFIG, active_ins)
        tooltip = f"BLE{idx}: {eq}"
        if ble_cfg_obj.FLOPSEL == FLOPSEL.ENABLE:
            tooltip += " (DFF Enabled)"

        port_lbl_parts = [
            f"<{p.lower()}> {p}" for p in VAR_ORDER if active_ins.get(p, False)
        ]
        port_lbl = " | ".join(port_lbl_parts)
        node_label = (
            f"{{{{{port_lbl}}}|LUT4 : BLE{idx}\\n{eq}|{{<outO> O}}}}"
            if port_lbl
            else f"{{LUT4 : BLE{idx}\\n{eq}|{{<outO> O}}}}"
        )

        is_simple_passthrough = (
            sum(active_ins.values()) == 1
            and eq.startswith("O=")
            and len(eq.split("=")[1].strip()) in [1, 2]
        )
        is_const_output_used_elsewhere = (
            not any(active_ins.values()) and meta["used_elsewhere"]
        )
        route_only_flag = (
            is_simple_passthrough or is_const_output_used_elsewhere
        ) and ble_cfg_obj.FLOPSEL != FLOPSEL.ENABLE
        dot.add_clb(f"clb{idx}", tooltip, node_label, route_only=route_only_flag)

    input_attr_map = {"A": "LUT_I_A", "B": "LUT_I_B", "C": "LUT_I_C", "D": "LUT_I_D"}
    lut_input_enums = (LUT_IN_A, LUT_IN_B, LUT_IN_C, LUT_IN_D)

    counter_cfg_obj = getattr(cfg, "COUNTER", None)
    counter_node_id = "clb_counter"
    if counter_cfg_obj is not None:
        counter_input_ports_def = []

        stop_src_enum = getattr(counter_cfg_obj, "CNT_STOP", None)
        if (
            stop_src_enum is not None
            and hasattr(stop_src_enum, "name")
            and bool(stop_src_enum.name)
        ):
            counter_input_ports_def.append("<stop> Stop")

        reset_src_enum = getattr(counter_cfg_obj, "CNT_RESET", None)
        if (
            reset_src_enum is not None
            and hasattr(reset_src_enum, "name")
            and bool(reset_src_enum.name)
        ):
            counter_input_ports_def.append("<reset> Reset")

        counter_output_ports_disp = [
            f"<{port_tag}> {label_suffix}"
            for label_suffix, port_tag in COUNTER_OUTPUT_LABELS_ORDERED
        ]

        lbl_parts = []
        if counter_input_ports_def:
            lbl_parts.append("{" + " | ".join(counter_input_ports_def) + "}")
        lbl_parts.append("Counter")
        lbl_parts.append("{" + " | ".join(counter_output_ports_disp) + "}")

        counter_node_label = "{" + " | ".join(lbl_parts) + "}"
        dot.add_clb(
            counter_node_id, "CLB Counter Block", counter_node_label, is_block=True
        )

        counter_inputs_to_connect = {}
        if (
            stop_src_enum is not None
            and hasattr(stop_src_enum, "name")
            and bool(stop_src_enum.name)
        ):
            counter_inputs_to_connect["CNT_STOP"] = (stop_src_enum, "stop")
        if (
            reset_src_enum is not None
            and hasattr(reset_src_enum, "name")
            and bool(reset_src_enum.name)
        ):
            counter_inputs_to_connect["CNT_RESET"] = (reset_src_enum, "reset")

        for _, (source_enum_val, dest_port_name) in counter_inputs_to_connect.items():
            source_name_str = source_enum_val.name
            src_id, src_port = "", ""
            ble_idx_val = _parse_ble_index_from_name(source_name_str)

            if ble_idx_val is not None:
                src_id = f"clb{ble_idx_val}"
                src_port = ":outO:e"
                if BLEXY(ble_idx_val) not in active_bles:
                    _ensure_ble_node_exists(
                        dot,
                        ble_idx_val,
                        all_luts,
                        f"Counter Input Source from {source_name_str}",
                    )
            else:
                src_id = f"pin_{source_name_str}"
                src_port = ":e"
                dot.add_pin(src_id, source_name_str, cls="pin_input", rank="source")

            if src_id is not None:
                dot.add_edge(
                    f"{src_id}{src_port}",
                    f"{counter_node_id}:{dest_port_name}:w",
                    f"{source_name_str} to Counter {dest_port_name.capitalize()}",
                )

    for dest_xy, meta in active_bles.items():
        dest_id = f"clb{dest_xy.value}"
        for port_char in VAR_ORDER:
            if not meta["inputs"].get(port_char, False):
                continue
            attr_name = input_attr_map[port_char]
            src_enum = getattr(meta["cfg"], attr_name)
            if src_enum is None:
                continue

            tooltip = src_enum.name if hasattr(src_enum, "name") else str(src_enum)
            src_id, src_port = _resolve_source(
                dot,
                cfg,
                all_luts,
                active_bles,
                src_enum,
                lut_input_enums,
                counter_node_id if counter_cfg_obj is not None else None,
            )
            if src_id is not None:
                dot.add_edge(
                    f"{src_id}{src_port}", f"{dest_id}:{port_char.lower()}:w", tooltip
                )

    for pps_idx, pps_enum_type in PPS_OUT_NUM.items():
        pps_cfg_obj = getattr(cfg, "PPS_OUT", {}).get(pps_enum_type)
        if pps_cfg_obj is None or not (
            getattr(pps_cfg_obj, "OUT", None) is not None
            and hasattr(getattr(pps_cfg_obj, "OUT", None), "name")
            and bool(getattr(pps_cfg_obj, "OUT", None).name)
        ):
            continue

        src_ble_name = pps_cfg_obj.OUT.name
        src_idx_val = _parse_ble_index_from_name(src_ble_name)

        if src_idx_val is not None:
            src_id = f"clb{src_idx_val}"
            if BLEXY(src_idx_val) not in active_bles:
                _ensure_ble_node_exists(
                    dot, src_idx_val, all_luts, f"PPS Source from {src_ble_name}"
                )

            sink_id = f"pin_PPS_OUT{pps_idx}"
            dot.add_pin(sink_id, f"PPS_OUT{pps_idx}", cls="pin_output", rank="sink")
            dot.add_edge(
                f"{src_id}:outO:e",
                f"{sink_id}:w",
                f"{src_ble_name} to PPS_OUT{pps_idx}",
            )
        else:
            print(
                f"Warning: Could not parse BLE index from PPS source '{src_ble_name}' for PPS_OUT{pps_idx}"
            )

    for oe_idx, oe_sel_enum in getattr(cfg, "OE", {}).items():
        if not (
            oe_sel_enum is not None
            and hasattr(oe_sel_enum, "name")
            and bool(oe_sel_enum.name)
        ):
            continue

        pin_id = f"pin_OE{oe_idx}"
        dot.add_pin(pin_id, f"OE{oe_idx}", cls="pin_output", rank="sink")
        src_ble_name = oe_sel_enum.name
        src_idx_val = _parse_ble_index_from_name(src_ble_name)

        if src_idx_val is not None:
            src_id = f"clb{src_idx_val}"
            if BLEXY(src_idx_val) not in active_bles:
                _ensure_ble_node_exists(
                    dot, src_idx_val, all_luts, f"OE Source from {src_ble_name}"
                )

            dot.add_edge(
                f"{src_id}:outO:e", f"{pin_id}:w", f"{src_ble_name} to OE{oe_idx}"
            )
        else:
            print(
                f"Warning: Could not parse BLE index from OE source '{src_ble_name}' for OE{oe_idx}"
            )

    for irq_idx, irq_cfg_val in getattr(cfg, "IRQ_OUT", {}).items():
        if irq_cfg_val is None or not (
            getattr(irq_cfg_val, "OUT", None) is not None
            and hasattr(getattr(irq_cfg_val, "OUT", None), "name")
            and bool(getattr(irq_cfg_val, "OUT", None).name)
        ):
            continue

        irq_pin_id = f"pin_IRQ_OUT{irq_idx}"
        dot.add_pin(irq_pin_id, f"IRQ_OUT{irq_idx}", cls="pin_output", rank="sink")
        src_ble_name = irq_cfg_val.OUT.name
        src_idx_val = _parse_ble_index_from_name(src_ble_name)

        if src_idx_val is not None:
            src_id = f"clb{src_idx_val}"
            if BLEXY(src_idx_val) not in active_bles:
                _ensure_ble_node_exists(
                    dot, src_idx_val, all_luts, f"IRQ Source from {src_ble_name}"
                )
            dot.add_edge(
                f"{src_id}:outO:e",
                f"{irq_pin_id}:w",
                f"{src_ble_name} to IRQ_OUT{irq_idx}",
            )
        else:
            print(
                f"Warning: Could not parse BLE index from IRQ source '{src_ble_name}' for IRQ_OUT{irq_idx}"
            )

    peripheral_inputs_map = {
        "TIMR0_IN": "Timer0 Input",
        "TIMR1_IN": "Timer1 Input",
        "TIMR1_GATE": "Timer1 Gate",
        "TIMR2_IN": "Timer2 Input",
        "TIMR2_RST": "Timer2 Reset",
        "CCP1_IN": "CCP1 Input",
        "CCP2_IN": "CCP2 Input",
        "ADC_IN": "ADC Input",
    }
    for attr_key, pin_label_base in peripheral_inputs_map.items():
        source_name_str = getattr(cfg, attr_key, None)
        if source_name_str is None or not isinstance(source_name_str, str):
            continue

        peripheral_pin_id = f"pin_{attr_key}"
        dot.add_pin(
            peripheral_pin_id, pin_label_base, cls="pin_peripheral_input", rank="sink"
        )

        src_id, src_port = "", ""
        ble_idx_val = _parse_ble_index_from_name(source_name_str)

        if ble_idx_val is not None:
            src_id = f"clb{ble_idx_val}"
            src_port = ":outO:e"
            if BLEXY(ble_idx_val) not in active_bles:
                _ensure_ble_node_exists(
                    dot,
                    ble_idx_val,
                    all_luts,
                    f"Peripheral Input Source from {source_name_str}",
                )
        else:
            src_id = f"pin_{source_name_str}"
            src_port = ":e"
            dot.add_pin(src_id, source_name_str, cls="pin_input", rank="source")

        if src_id is not None:
            dot.add_edge(
                f"{src_id}{src_port}",
                f"{peripheral_pin_id}:w",
                f"{source_name_str} to {pin_label_base}",
            )
    return dot.build()


def _ensure_ble_node_exists(
    dot: DotBuilder, ble_idx: int, all_luts: Mapping[BLEXY, any], reason: str
):
    node_id = f"clb{ble_idx}"
    if node_id in dot.nodes:
        return

    ble_cfg_data = all_luts.get(BLEXY(ble_idx))
    eq_str = "Route-through"
    tooltip_reason = f"BLE{ble_idx} ({reason})"
    is_dff = False
    if ble_cfg_data is not None:
        lut_config_str = getattr(ble_cfg_data, "LUT_CONFIG", "0" * 16)
        temp_active_ins = get_active_lut_inputs(lut_config_str)
        eq_str = get_lut_equation_str(lut_config_str, temp_active_ins)
        tooltip_reason = f"BLE{ble_idx}: {eq_str} ({reason})"
        if getattr(ble_cfg_data, "FLOPSEL", FLOPSEL.DISABLE) == FLOPSEL.ENABLE:
            tooltip_reason += " (DFF Enabled)"
            is_dff = True

    label = f"{{LUT4 : BLE{ble_idx}\\n({eq_str})|{{<outO> O}}}}"
    dot.add_clb(
        node_id,
        tooltip_reason,
        label,
        route_only=(
            not is_dff and (eq_str.startswith("O=") or eq_str == "Route-through")
        ),
    )


def _ble_output_used(
    cfg: FASM | Bitstream, idx_of_interest: int, ble_xy_of_interest
) -> bool:
    for pps_val in getattr(cfg, "PPS_OUT", {}).values():
        if (
            getattr(pps_val, "OUT", None) is not None
            and hasattr(getattr(pps_val, "OUT", None), "name")
            and bool(getattr(pps_val, "OUT", None).name)
        ):
            if _parse_ble_index_from_name(pps_val.OUT.name) == idx_of_interest:
                return True
    for other_ble_xy, other_ble_cfg in getattr(cfg, "LUTS", {}).items():
        if other_ble_xy == ble_xy_of_interest:
            continue
        for attr_name in ("LUT_I_A", "LUT_I_B", "LUT_I_C", "LUT_I_D"):
            input_source = getattr(other_ble_cfg, attr_name)
            if (
                input_source is not None
                and hasattr(input_source, "name")
                and bool(input_source.name)
            ):
                if input_source.name.startswith("CLB_BLE_"):
                    if _parse_ble_index_from_name(input_source.name) == idx_of_interest:
                        return True
    for oe_sel in getattr(cfg, "OE", {}).values():
        if oe_sel is not None and hasattr(oe_sel, "name") and bool(oe_sel.name):
            if _parse_ble_index_from_name(oe_sel.name) == idx_of_interest:
                return True
    for irq_val in getattr(cfg, "IRQ_OUT", {}).values():
        if (
            getattr(irq_val, "OUT", None) is not None
            and hasattr(getattr(irq_val, "OUT", None), "name")
            and bool(getattr(irq_val, "OUT", None).name)
        ):
            if _parse_ble_index_from_name(irq_val.OUT.name) == idx_of_interest:
                return True

    peripheral_input_attrs = [
        "TIMR0_IN",
        "TIMR1_IN",
        "TIMR1_GATE",
        "TIMR2_IN",
        "TIMR2_RST",
        "CCP1_IN",
        "CCP2_IN",
        "ADC_IN",
    ]
    for attr_key in peripheral_input_attrs:
        source_name_val = getattr(cfg, attr_key, None)
        if source_name_val is not None and isinstance(source_name_val, str):
            if _parse_ble_index_from_name(source_name_val) == idx_of_interest:
                return True

    counter_obj = getattr(cfg, "COUNTER", None)
    if counter_obj is not None:
        counter_input_source_enums = [
            getattr(counter_obj, "CNT_STOP", None),
            getattr(counter_obj, "CNT_RESET", None),
        ]
        for src_enum in counter_input_source_enums:
            if (
                src_enum is not None
                and hasattr(src_enum, "name")
                and bool(src_enum.name)
            ):
                if _parse_ble_index_from_name(src_enum.name) == idx_of_interest:
                    return True
    return False


def _resolve_source(
    dot: DotBuilder,
    cfg_obj: Union[Bitstream, FASM],
    all_luts: Mapping[BLEXY, any],
    active_bles: Mapping[BLEXY, dict],
    src_enum,
    lut_input_enums: tuple[type, ...],
    counter_node_id: str | None,
) -> tuple[str | None, str]:
    name = src_enum.name if hasattr(src_enum, "name") else str(src_enum)

    if name.startswith("COUNT_IS_") and counter_node_id is not None:
        port_tag = COUNTER_OUTPUT_PORT_MAP.get(name)
        if port_tag is not None:
            return counter_node_id, f":{port_tag}:e"
        else:
            print(
                f"Warning: Unknown COUNT_IS_ signal '{name}' or no mapping to port tag."
            )
            pin_name = f"pin_{name}"
            if pin_name not in dot.nodes:
                dot.add_pin(
                    pin_name, name, cls="pin_input unknown_count_is", rank="source"
                )
            return pin_name, ":e"

    if name.startswith("CLB_BLE_"):
        ble_idx = _parse_ble_index_from_name(name)
        if ble_idx is not None:
            src_node_id = f"clb{ble_idx}"
            if BLEXY(ble_idx) not in active_bles:
                _ensure_ble_node_exists(
                    dot, ble_idx, all_luts, f"LUT Input Source from {name}"
                )
            return src_node_id, ":outO:e"
        else:
            print(f"Warning: Malformed CLB_BLE_ name: {name}")
            return None, ""

    if name.startswith(("IN", "CLBSWIN")):
        pin_name = f"pin_{name}"
        if pin_name not in dot.nodes:
            dot.add_pin(pin_name, name, cls="pin_input", rank="source")
        return pin_name, ":e"

    if hasattr(type(src_enum), "__bases__") and any(
        base in lut_input_enums for base in type(src_enum).__bases__
    ):
        print(
            f"Warning: Unresolved LUT input source (unmapped enum value): {name} (type: {type(src_enum)})"
        )
        if name is not None:
            pin_name = f"pin_{name}"
            if pin_name not in dot.nodes:
                dot.add_pin(
                    pin_name, name, cls="pin_input unmapped_enum_source", rank="source"
                )
            return pin_name, ":e"
        return None, ""

    if name is not None:
        print(f"Warning: Treating unknown source '{name}' as an external pin.")
        pin_name = f"pin_{name}"
        if pin_name not in dot.nodes:
            dot.add_pin(pin_name, name, cls="pin_input unknown_source", rank="source")
        return pin_name, ":e"

    return None, ""


if __name__ == "__main__":
    cfg_path_str = r"C:\Users\momo\Dropbox\MENGR Share Folder\CLB RE\CLB_RE_PY\test_gen_counter_out_design\Request 2025-03-12_08-50-16\response_files\build\1741794616786.result.json"
    cfg_path = Path(cfg_path_str)
    cfg = Bitstream(cfg_path)
    print(cfg)
    print(generate_dot_from_config(cfg))
