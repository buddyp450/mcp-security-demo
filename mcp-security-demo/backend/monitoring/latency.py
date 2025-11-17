from __future__ import annotations

from statistics import mean, pstdev
from typing import Dict, List, Tuple


class LatencyAnalyzer:
    def __init__(self, baseline_samples: List[float] | None = None, sigma: float = 2.0) -> None:
        self.baseline_samples = baseline_samples or [100.0, 110.0, 95.0, 105.0]
        self.sigma = sigma
        self._mean = mean(self.baseline_samples)
        self._stdev = pstdev(self.baseline_samples)

    def inspect(self, latency_ms: float) -> Tuple[bool, Dict[str, float]]:
        threshold = self._mean + self.sigma * self._stdev
        breached = latency_ms > threshold
        details = {
            "latency_ms": latency_ms,
            "baseline_mean": self._mean,
            "baseline_sigma": self._stdev,
            "threshold": threshold,
        }
        return breached, details
