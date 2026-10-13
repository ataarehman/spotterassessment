"""Distance-based checkpoints and arrival times along a route polyline."""

import math
from datetime import datetime, timedelta


EARTH_RADIUS_MILES = 3958.7613


def _haversine_miles(a, b):
    lng1, lat1 = a
    lng2, lat2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def _point_at(a, b, fraction):
    return [a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction]


def checkpoints(coords, spacing_miles, departure, duration_seconds):
    if spacing_miles not in (10, 25, 50):
        raise ValueError("spacing_miles must be 10, 25, or 50")
    if len(coords) < 2:
        raise ValueError("route geometry needs at least two coordinates")
    if duration_seconds < 0:
        raise ValueError("duration_seconds must be non-negative")

    legs = []
    total = 0.0
    for start, end in zip(coords, coords[1:]):
        length = _haversine_miles(start, end)
        legs.append((start, end, length))
        total += length
    if total == 0:
        raise ValueError("route length is zero")

    targets = [0.0]
    step = float(spacing_miles)
    cursor = step
    while cursor < total - 1e-6:
        targets.append(cursor)
        cursor += step
    targets.append(total)

    points = []
    for distance in targets:
        remaining = distance
        chosen = coords[-1]
        for start, end, length in legs:
            if remaining <= length or length == 0:
                fraction = 0 if length == 0 else remaining / length
                chosen = _point_at(start, end, min(max(fraction, 0.0), 1.0))
                break
            remaining -= length
        fraction = distance / total
        eta = departure + timedelta(seconds=duration_seconds * fraction)
        points.append(
            {
                "distance_miles": distance,
                "eta": eta,
                "lng": chosen[0],
                "lat": chosen[1],
            }
        )
    return points
