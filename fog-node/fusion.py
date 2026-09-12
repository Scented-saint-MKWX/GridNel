from dataclasses import dataclass


@dataclass
class FusionResult:
    plate: str | None
    conf: float
    outcome: str
    rejected: list[str]


def _diff_chars(a: str, b: str) -> int:
    n = max(len(a), len(b))
    a = a.ljust(n)
    b = b.ljust(n)
    return sum(1 for i in range(n) if a[i] != b[i])


def resolve(vendor_guess: str | None, vendor_conf: float, engine_read: str | None, engine_conf: float) -> FusionResult:
    vendor = vendor_guess.strip().upper() if vendor_guess else None
    engine = engine_read.strip().upper() if engine_read else None

    if vendor and engine:
        if vendor == engine and max(vendor_conf, engine_conf) >= 0.85:
            return FusionResult(vendor, max(vendor_conf, engine_conf), "agreement", [])

        diff = _diff_chars(vendor, engine)
        if diff == 1 and engine_conf > vendor_conf:
            return FusionResult(engine, engine_conf, "engine_preferred", [vendor])
        if diff == 1 and vendor_conf > engine_conf:
            return FusionResult(vendor, vendor_conf, "vendor_preferred", [engine])
        if diff >= 2:
            best = max((vendor, vendor_conf), (engine, engine_conf), key=lambda x: x[1])
            if best[1] >= 0.90:
                return FusionResult(best[0], best[1], "low_confidence", [vendor, engine])
            return FusionResult(None, 0.0, "low_confidence", [vendor, engine])

    chosen = vendor if vendor else engine
    conf = vendor_conf if vendor else engine_conf
    if chosen and conf >= 0.85:
        return FusionResult(chosen, conf, "single_channel", [])
    return FusionResult(None, 0.0, "single_channel", [x for x in [vendor, engine] if x])
