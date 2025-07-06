from typing import Callable, Tuple

Four_LUT = Tuple[bool, bool, bool, bool]
FourLUT_Bit_Fn = Callable[[bool, bool, bool, bool], bool]


class Expr:
    """Symbolic Boolean expression on inputs (a, b, c, d)."""

    __slots__ = ("f",)

    def __init__(self, f: FourLUT_Bit_Fn) -> None:
        self.f = f

    def __call__(self, bits: Four_LUT) -> bool:
        return self.f(bits)

    def __bool__(self) -> bool:
        raise TypeError("Expr objects are symbolic; use &, |, ~, ^, ==, !=")

    def __invert__(self) -> "Expr":
        """Implement ``~a``."""
        return Expr(lambda v, s=self: not s(v))

    def _combine(self, o: "Expr", op) -> "Expr":
        return Expr(lambda v, l=self, r=o, p=op: p(l(v), r(v)))

    def __and__(self, o: "Expr") -> "Expr":
        """Implement ``a & b``."""
        return self._combine(o, bool.__and__)

    def __or__(self, o: "Expr") -> "Expr":
        """Implement ``a | b``."""
        return self._combine(o, bool.__or__)

    def __xor__(self, o: "Expr") -> "Expr":
        """Implement ``a ^ b``."""
        return self._combine(o, bool.__xor__)

    def __eq__(self, o: object) -> "Expr":
        """Implement ``a == b`` (XNOR)."""
        return (
            self._combine(o, lambda x, y: x == y)
            if isinstance(o, Expr)
            else NotImplemented
        )

    def __ne__(self, o: object) -> "Expr":
        """Implement ``a != b`` (XOR)."""
        return (
            self._combine(o, lambda x, y: x != y)
            if isinstance(o, Expr)
            else NotImplemented
        )

    def __repr__(self) -> str:
        return "Expr(...)"


def pick(i: int) -> Expr:
    return Expr(lambda bits: bits[i])


a, b, c, d = (pick(i) for i in range(4))


class LUT4:
    """Create a 16-bit LUT mask from an Expr or callable."""

    __slots__ = ("fn",)

    def __init__(self, logic: Expr | FourLUT_Bit_Fn) -> None:
        if isinstance(logic, Expr):
            self.fn: Callable[[Four_LUT], bool] = logic
        else:
            self.fn = lambda bits, f=logic: f(*bits)

    def bitstream(self) -> str:
        val = 0
        for w in range(16):
            bits: Four_LUT = tuple(bool(w & 1 << k) for k in range(4))  # type: ignore
            if self.fn(bits):
                val |= 1 << w
        return f"{val:016b}"


if __name__ == "__main__":
    print(LUT4(lambda a, b, c, d: a if b else c).bitstream())
    print(LUT4(a ^ b ^ c ^ d).bitstream())
