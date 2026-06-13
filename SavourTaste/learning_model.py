"""The SavourTaste Learning Model.

Combines a user's current Location with their Memory bank of saved
restaurants to recommend where to eat based on mood, cravings, and
time of day. The model "learns" implicitly as the user saves more
restaurants into mood/context-labeled folders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .location import Location
from .memory import Memory, Restaurant


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 15:
        return "lunch"
    if 15 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "dinner"
    return "late-night"


@dataclass
class Recommendation:
    restaurant: Restaurant
    distance_km: float
    score: float
    reason: str


@dataclass
class LearningModel:
    """Two-part learning model: where you are + what you remember."""

    location: Location
    memory: Memory = field(default_factory=Memory)

    def save_to_memory(self, folder_name: str, restaurant: Restaurant) -> None:
        """Teach the model that this restaurant fits a given context."""
        self.memory.save(folder_name, restaurant)

    def recommend(
        self,
        mood: Optional[str] = None,
        craving: Optional[str] = None,
        when: Optional[datetime] = None,
        limit: int = 5,
    ) -> List[Recommendation]:
        """Rank saved restaurants by fit to mood/craving/time and proximity."""
        when = when or datetime.now()
        slot = _time_of_day(when.hour)

        candidates = self.memory.recall(mood=mood, craving=craving)
        scored: List[Recommendation] = []

        for r in candidates:
            distance = self.location.distance_km(r.latitude, r.longitude)
            if distance > self.location.search_radius_km:
                continue

            # Lower distance is better; higher rating and tag overlap boost score.
            proximity = 1.0 - (distance / self.location.search_radius_km)
            tag_hits = sum(
                1
                for t in r.tags
                if slot in t.lower()
                or (mood and mood.lower() in t.lower())
                or (craving and craving.lower() in t.lower())
            )
            score = proximity + 0.2 * r.rating + 0.5 * tag_hits

            reason_bits = [f"{distance:.1f}km away"]
            if tag_hits:
                reason_bits.append(f"matches {slot}/{mood or craving}")
            if r.rating:
                reason_bits.append(f"rated {r.rating:.1f}")

            scored.append(
                Recommendation(
                    restaurant=r,
                    distance_km=distance,
                    score=score,
                    reason=", ".join(reason_bits),
                )
            )

        scored.sort(key=lambda rec: rec.score, reverse=True)
        return scored[:limit]
