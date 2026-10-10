"""Shared constants and utilities for AdaptiveCrypt dashboard pages."""

MODE_ACCENT = {
    "CLASSICAL":    "#64748b",
    "HYBRID":       "#78716c",
    "QUANTUM_SAFE": "#6b7280",
}


def label(mode: str) -> str:
    return mode.replace("_", "-")


def fmt_bw(kbps: float) -> str:
    return f"{kbps / 1000:g} Mbps" if kbps >= 1000 else f"{kbps:g} kbps"


def fmt_size(n: int) -> str:
    for unit, f in (("MB", 1e6), ("KB", 1e3)):
        if n >= f:
            return f"{n / f:g} {unit}"
    return f"{n} B"
