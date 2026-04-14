"""Memory component for the SavourTaste learning model.

The Memory bank stores restaurants the user has saved into personal
folders such as "Late Night Cravings" or "Comfort Food When Sad". Over
time this becomes a food memory bank that the learning model draws on
to bias recommendations toward places the user already loves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional


@dataclass
class Restaurant:
    name: str
    latitude: float
    longitude: float
    cuisine: Optional[str] = None
    price_level: int = 2  # 1 (cheap) .. 4 (pricey)
    tags: List[str] = field(default_factory=list)  # e.g. ["late-night", "cozy"]
    rating: float = 0.0

    def matches(self, mood: Optional[str], craving: Optional[str]) -> bool:
        """Return True if this restaurant's tags/cuisine hint at a match."""
        needles = [s.lower() for s in (mood, craving) if s]
        if not needles:
            return True
        hay = " ".join([self.cuisine or "", *self.tags]).lower()
        return any(n in hay for n in needles)


@dataclass
class MemoryFolder:
    name: str
    restaurants: List[Restaurant] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add(self, restaurant: Restaurant) -> None:
        if not any(r.name == restaurant.name for r in self.restaurants):
            self.restaurants.append(restaurant)

    def remove(self, restaurant_name: str) -> bool:
        for i, r in enumerate(self.restaurants):
            if r.name == restaurant_name:
                del self.restaurants[i]
                return True
        return False


@dataclass
class Memory:
    folders: Dict[str, MemoryFolder] = field(default_factory=dict)

    def create_folder(self, name: str) -> MemoryFolder:
        if name not in self.folders:
            self.folders[name] = MemoryFolder(name=name)
        return self.folders[name]

    def save(self, folder_name: str, restaurant: Restaurant) -> None:
        """Save a restaurant into a named folder, creating the folder if needed."""
        folder = self.create_folder(folder_name)
        folder.add(restaurant)

    def forget(self, folder_name: str, restaurant_name: str) -> bool:
        folder = self.folders.get(folder_name)
        if folder is None:
            return False
        return folder.remove(restaurant_name)

    def all_restaurants(self) -> Iterable[Restaurant]:
        for folder in self.folders.values():
            yield from folder.restaurants

    def recall(
        self,
        mood: Optional[str] = None,
        craving: Optional[str] = None,
    ) -> List[Restaurant]:
        """Recall saved restaurants that fit the given mood/craving."""
        seen: Dict[str, Restaurant] = {}
        for r in self.all_restaurants():
            if r.matches(mood, craving) and r.name not in seen:
                seen[r.name] = r
        return list(seen.values())
