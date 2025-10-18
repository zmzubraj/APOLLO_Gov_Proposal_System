"""Calibration utilities for mapping raw approval probabilities to calibrated values.

Scaffolding: If a models/referendum_calibration.json file is present, it may contain
either a linear mapping or a set of (x,y) points for piecewise-linear calibration.

Example JSON (linear):
{
  "type": "linear",
  "m": 1.0,
  "c": 0.0,
  "source_overrides": {
    "forum": {"m": 1.05, "c": -0.02},
    "chat": {"m": 0.98, "c": 0.01}
  }
}

Example JSON (points):
{
  "type": "points",
  "points": [[0.0, 0.02], [0.5, 0.5], [1.0, 0.98]]
}
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple
import json

ROOT = Path(__file__).resolve().parents[2]
CALIB_PATH = ROOT / "models" / "referendum_calibration.json"


def _clamp01(x: float) -> float:
    return float(0.0 if x < 0.0 else 1.0 if x > 1.0 else x)


def _interp_points(points: Sequence[Tuple[float, float]], x: float) -> float:
    if not points:
        return x
    pts = sorted((float(a), float(b)) for a, b in points)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return x


def load_calibration() -> Optional[dict]:
    try:
        with CALIB_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def apply_calibration(p: float, source: Optional[str] = None, calib: Optional[dict] = None) -> float:
    """Apply a simple calibration mapping to probability ``p``.

    Supports:
    - linear mapping with optional per-source overrides
    - piecewise linear mapping via points
    """
    calib = calib or load_calibration()
    if not calib:
        return p

    typ = str(calib.get("type", "linear")).lower()
    if typ == "linear":
        m = float(calib.get("m", 1.0))
        c = float(calib.get("c", 0.0))
        if source and isinstance(calib.get("source_overrides"), dict):
            ov = calib["source_overrides"].get(str(source).lower())
            if isinstance(ov, dict):
                m = float(ov.get("m", m))
                c = float(ov.get("c", c))
        return _clamp01(m * p + c)

    if typ == "points":
        pts = calib.get("points") or []
        try:
            pts = [(float(a), float(b)) for a, b in pts]
        except Exception:
            return p
        return _clamp01(_interp_points(pts, p))

    return p

