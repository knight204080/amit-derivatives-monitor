"""Pure computation helpers: annualization, basis, percentile/z-score."""
import statistics


def annualize_funding(rate, interval_hours):
    """Annualized funding rate as a percentage, given a per-period rate."""
    periods_per_year = 8760 / interval_hours
    return rate * periods_per_year * 100


def basis_bps(perp_mid, spot_index):
    """Perp-vs-spot basis in basis points. Positive = perp trades above spot."""
    return ((perp_mid / spot_index) - 1) * 10000


def percentile_rank(value, history):
    """Where `value` ranks among `history` (0-100). len(history) < 2 -> None."""
    if len(history) < 2:
        return None
    below = sum(1 for h in history if h <= value)
    return (below / len(history)) * 100


def z_score(value, history):
    """Standard z-score of `value` against `history`. len(history) < 2 -> None."""
    if len(history) < 2:
        return None
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    if stdev == 0:
        return 0.0
    return (value - mean) / stdev


if __name__ == "__main__":
    assert abs(annualize_funding(0.0001, 8) - 10.95) < 0.01
    assert abs(annualize_funding(0.0000062236, 1) - 5.45) < 0.05
    assert abs(basis_bps(64410, 64400) - 1.553) < 0.01
    assert percentile_rank(5, [1, 2, 3, 4]) == 100.0
    assert percentile_rank(5, [1]) is None
    hist = [1, 2, 3, 4, 5]
    assert abs(z_score(5, hist) - 1.414) < 0.01
    print("compute.py self-tests passed")
