import unittest
import json
from pathlib import Path

import re

from bitstream import FASM, Bitstream

TEST_FILES_BASE_DIR = Path(__file__).parent.parent
print(f"{TEST_FILES_BASE_DIR=}")


def sanitize_name(name_str):
    """Sanitizes a string to be a valid Python identifier part."""
    name_str = re.sub(r"\W|^(?=\d)", "_", str(name_str))
    return name_str


def find_test_cases(base_dir: Path):
    """
    Recursively finds directories containing one .json (with 'bitstream' key)
    and one .fasm file.
    """
    test_case_paths = []
    if not base_dir.is_dir():
        return []

    for item in base_dir.rglob("*"):
        if item.is_dir():
            json_files = list(item.glob("*.json"))
            fasm_files = list(item.glob("*.fasm"))

            valid_json_file = None
            if (
                len(json_files) >= 1
            ):
                try:
                    with open(json_files[0], "r") as f:
                        data = json.load(f)
                    if "bitstream" in data:
                        valid_json_file = json_files[0]
                    elif isinstance(data, list):
                        valid_json_file = json_files[0]
                except (json.JSONDecodeError, IOError):
                    pass  # Ignore malformed JSON or unreadable files

            if valid_json_file and len(fasm_files) == 1:
                test_case_paths.append(
                    {
                        "dir_path": item,
                        "json_path": valid_json_file,
                        "fasm_path": fasm_files[0],
                    }
                )
    return test_case_paths


class TestFasmBitstreamConsistency(unittest.TestCase):

    def _compare_luts(self, fasm_luts, bs_luts, case_name):
        for ble_xy_enum, fasm_ble_cfg in fasm_luts.items():
            # FASM might not configure all LUTs. Bitstream will have all (defaulted).
            self.assertIn(
                ble_xy_enum,
                bs_luts,
                f"[{case_name}] BLE {ble_xy_enum.name} in FASM but not in Bitstream LUTS",
            )
            bs_ble_cfg = bs_luts[ble_xy_enum]

            msg_prefix = f"[{case_name}] BLE {ble_xy_enum.name}"

            if fasm_ble_cfg.LUT_CONFIG is not None:
                self.assertEqual(
                    fasm_ble_cfg.LUT_CONFIG,
                    bs_ble_cfg.LUT_CONFIG,
                    f"{msg_prefix} LUT_CONFIG mismatch",
                )
            if fasm_ble_cfg.FLOPSEL is not None:
                self.assertEqual(
                    fasm_ble_cfg.FLOPSEL,
                    bs_ble_cfg.FLOPSEL,
                    f"{msg_prefix} FLOPSEL mismatch",
                )
            if fasm_ble_cfg.LUT_I_A is not None:
                self.assertEqual(
                    fasm_ble_cfg.LUT_I_A,
                    bs_ble_cfg.LUT_I_A,
                    f"{msg_prefix} LUT_I_A mismatch",
                )
            if fasm_ble_cfg.LUT_I_B is not None:
                self.assertEqual(
                    fasm_ble_cfg.LUT_I_B,
                    bs_ble_cfg.LUT_I_B,
                    f"{msg_prefix} LUT_I_B mismatch",
                )
            if fasm_ble_cfg.LUT_I_C is not None:
                self.assertEqual(
                    fasm_ble_cfg.LUT_I_C,
                    bs_ble_cfg.LUT_I_C,
                    f"{msg_prefix} LUT_I_C mismatch",
                )
            if fasm_ble_cfg.LUT_I_D is not None:
                self.assertEqual(
                    fasm_ble_cfg.LUT_I_D,
                    bs_ble_cfg.LUT_I_D,
                    f"{msg_prefix} LUT_I_D mismatch",
                )

    def _compare_pps_out(self, fasm_pps, bs_pps, case_name):
        for pps_type_key, fasm_pps_instance in fasm_pps.items():
            self.assertIn(
                pps_type_key,
                bs_pps,
                f"[{case_name}] PPS_OUT key {pps_type_key.__name__} in FASM but not in Bitstream",
            )
            bs_pps_instance = bs_pps[pps_type_key]
            if fasm_pps_instance.OUT is not None:
                self.assertEqual(
                    fasm_pps_instance.OUT,
                    bs_pps_instance.OUT,
                    f"[{case_name}] PPS_OUT {pps_type_key.__name__} .OUT mismatch",
                )

    def _compare_irq_out(self, fasm_irq, bs_irq, case_name):
        for irq_idx_key, fasm_irq_instance in fasm_irq.items():
            self.assertIn(
                irq_idx_key,
                bs_irq,
                f"[{case_name}] IRQ_OUT key {irq_idx_key} in FASM but not in Bitstream",
            )
            bs_irq_instance = bs_irq[irq_idx_key]
            if fasm_irq_instance.OUT is not None:
                self.assertEqual(
                    fasm_irq_instance.OUT,
                    bs_irq_instance.OUT,
                    f"[{case_name}] IRQ_OUT {irq_idx_key} .OUT mismatch",
                )

    def _compare_muxs(self, fasm_muxs, bs_muxs, case_name):
        for mux_idx, fasm_mux_cfg in fasm_muxs.items():
            self.assertIn(
                mux_idx,
                bs_muxs,
                f"[{case_name}] MUX index {mux_idx} in FASM but not in Bitstream MUXS",
            )
            bs_mux_cfg = bs_muxs[mux_idx]
            msg_prefix = f"[{case_name}] MUX {mux_idx}"
            if fasm_mux_cfg.CLBIN is not None:
                self.assertEqual(
                    fasm_mux_cfg.CLBIN, bs_mux_cfg.CLBIN, f"{msg_prefix} CLBIN mismatch"
                )
            if fasm_mux_cfg.INSYNC is not None:
                self.assertEqual(
                    fasm_mux_cfg.INSYNC,
                    bs_mux_cfg.INSYNC,
                    f"{msg_prefix} INSYNC mismatch",
                )

    def _compare_counter(self, fasm_counter, bs_counter, case_name):
        msg_prefix = f"[{case_name}] COUNTER"
        if fasm_counter.CNT_STOP is not None:
            self.assertEqual(
                fasm_counter.CNT_STOP,
                bs_counter.CNT_STOP,
                f"{msg_prefix} CNT_STOP mismatch",
            )
        if fasm_counter.CNT_RESET is not None:
            self.assertEqual(
                fasm_counter.CNT_RESET,
                bs_counter.CNT_RESET,
                f"{msg_prefix} CNT_RESET mismatch",
            )

        # Compare COUNT_IS_XN fields
        counter_fields = [
            "COUNT_IS_A1",
            "COUNT_IS_A2",
            "COUNT_IS_B1",
            "COUNT_IS_B2",
            "COUNT_IS_C1",
            "COUNT_IS_C2",
            "COUNT_IS_D1",
            "COUNT_IS_D2",
        ]
        for field_name in counter_fields:
            fasm_val = getattr(fasm_counter, field_name)
            bs_val = getattr(bs_counter, field_name)
            if fasm_val is not None:
                self.assertEqual(
                    fasm_val, bs_val, f"{msg_prefix} {field_name} mismatch"
                )


def _create_test_method(json_path, fasm_path, dir_path):
    def test_method(self):
        case_name = dir_path.absolute()
        print(
            f"\nRunning test for: {case_name} (FASM: {fasm_path.name}, JSON: {json_path.name})"
        )

        try:
            fasm_obj = FASM(fasm_path)
        except Exception as e:
            self.fail(f"[{case_name}] Failed to load FASM file {fasm_path}: {e}")

        try:
            bs_obj = Bitstream(json_path)  # Initialize empty
        except Exception as e:
            self.fail(f"[{case_name}]Failed to load Bitstream from JSON {json_path}")

        try:
            self._compare_luts(fasm_obj.LUTS, bs_obj.LUTS, case_name)
            self._compare_pps_out(fasm_obj.PPS_OUT, bs_obj.PPS_OUT, case_name)
            self._compare_irq_out(fasm_obj.IRQ_OUT, bs_obj.IRQ_OUT, case_name)
            self._compare_muxs(fasm_obj.MUXS, bs_obj.MUXS, case_name)
            # FASM parser initializes CLKDIV, so it's always set.
            self.assertEqual(
                fasm_obj.CLKDIV, bs_obj.CLKDIV, f"[{case_name}] CLKDIV mismatch"
            )
            self._compare_counter(fasm_obj.COUNTER, bs_obj.COUNTER, case_name)

        except AssertionError as e:
            print(f"\n--- FAILURE DETAILS FOR CASE: {case_name} ---")
            print(f"FASM Path: {fasm_path}")
            print(f"JSON Path: {json_path}")
            print("\nFASM Object State:")
            if fasm_obj:
                print(fasm_obj)  # Relies on FASM.__str__
            else:
                print("FASM object could not be loaded.")

            print("\nBitstream Object State:")
            if bs_obj:
                print(bs_obj)
            else:
                print("Bitstream object could not be loaded or initialized from JSON.")

            print(f"\nOriginal Assertion Error: {e}")
            print("--- END FAILURE DETAILS ---")
            raise

    return test_method



discovered_cases = find_test_cases(TEST_FILES_BASE_DIR)
if not discovered_cases:
    print(
        f"No test cases found in {TEST_FILES_BASE_DIR}. Ensure subdirectories have one .fasm and one .json (with 'bitstream' key)."
    )
else:
    print(f"Found {len(discovered_cases)} potential test cases.")

for case_info in discovered_cases:
    dir_path = case_info["dir_path"]
    json_p = case_info["json_path"]
    fasm_p = case_info["fasm_path"]

    try:
        relative_dir_path = dir_path.relative_to(TEST_FILES_BASE_DIR)
    except (
        ValueError
    ):
        relative_dir_path = dir_path.name

    test_method_name = f"test_{sanitize_name(relative_dir_path)}"

    test_method_func = _create_test_method(json_p, fasm_p, dir_path)

    setattr(TestFasmBitstreamConsistency, test_method_name, test_method_func)

if __name__ == "__main__":
    if not discovered_cases:
        print("Skipping unittest.main() as no test cases were generated.")
    else:
        unittest.main(verbosity=2)
