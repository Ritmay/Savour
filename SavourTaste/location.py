"""Location component for the SavourTaste learning model.

Tracks where the user currently is so recommendations stay local. A
Location stores a coordinate pair plus optional city/neighborhood context
and can compute simple distances to nearby restaurants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt
from typing import Optional


EARTH_RADIUS_KM = 6371.0088


@dataclass
class Location:
    latitude: float
    longitude: float
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    search_radius_km: float = 5.0

    def update(
        self,
        latitude: float,
        longitude: float,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> None:
        """Move the user to a new coordinate, optionally refreshing context."""
        self.latitude = latitude
        self.longitude = longitude
        if city is not None:
            self.city = city
        if neighborhood is not None:
            self.neighborhood = neighborhood

    def distance_km(self, latitude: float, longitude: float) -> float:
        """Great-circle distance (Haversine) to the given point, in km."""
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(latitude), radians(longitude)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 2 * EARTH_RADIUS_KM * asin(sqrt(a))

    def is_within_radius(self, latitude: float, longitude: float) -> bool:
        """Check whether a point is within the user's search radius."""
        return self.distance_km(latitude, longitude) <= self.search_radius_km
