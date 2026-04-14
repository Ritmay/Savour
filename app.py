"""Savourtaste web app.

Thin Flask frontend over the SavourTaste learning model. Keeps a single
in-process LearningModel seeded with a handful of restaurants so the
demo has something to recommend out of the box. Users can set their
location, save restaurants into mood folders, and ask for picks.
"""

from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from SavourTaste import LearningModel, Location, Restaurant


def _seed_model() -> LearningModel:
    model = LearningModel(
        location=Location(
            latitude=40.7580,
            longitude=-73.9855,
            city="New York",
            neighborhood="Midtown",
            search_radius_km=5.0,
        )
    )

    seeds = [
        (
            "Late Night Cravings",
            Restaurant(
                name="Joe's Pizza",
                latitude=40.7306,
                longitude=-73.9866,
                cuisine="pizza",
                tags=["late-night", "comfort", "cheap"],
                rating=4.5,
                price_level=1,
            ),
        ),
        (
            "Late Night Cravings",
            Restaurant(
                name="Xi'an Famous Foods",
                latitude=40.7614,
                longitude=-73.9845,
                cuisine="chinese noodles",
                tags=["late-night", "spicy", "quick"],
                rating=4.4,
                price_level=1,
            ),
        ),
        (
            "Comfort Food When Sad",
            Restaurant(
                name="Ippudo Ramen",
                latitude=40.7614,
                longitude=-73.9776,
                cuisine="japanese ramen",
                tags=["cozy", "comfort", "warm", "dinner"],
                rating=4.3,
                price_level=2,
            ),
        ),
        (
            "Comfort Food When Sad",
            Restaurant(
                name="Jackson Hole Burgers",
                latitude=40.7536,
                longitude=-73.9832,
                cuisine="american burgers",
                tags=["comfort", "hearty", "lunch", "dinner"],
                rating=4.1,
                price_level=2,
            ),
        ),
        (
            "Fancy Date Night",
            Restaurant(
                name="Le Bernardin",
                latitude=40.7614,
                longitude=-73.9819,
                cuisine="french seafood",
                tags=["fancy", "romantic", "dinner"],
                rating=4.8,
                price_level=4,
            ),
        ),
        (
            "Morning Fuel",
            Restaurant(
                name="Blue Bottle Coffee",
                latitude=40.7549,
                longitude=-73.9840,
                cuisine="coffee breakfast",
                tags=["morning", "quick", "cozy"],
                rating=4.2,
                price_level=2,
            ),
        ),
    ]

    for folder, restaurant in seeds:
        model.save_to_memory(folder, restaurant)

    return model


app = Flask(__name__)
model = _seed_model()


def _restaurant_dict(r: Restaurant) -> dict:
    return {
        "name": r.name,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "cuisine": r.cuisine,
        "price_level": r.price_level,
        "tags": r.tags,
        "rating": r.rating,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def state():
    return jsonify(
        {
            "location": {
                "latitude": model.location.latitude,
                "longitude": model.location.longitude,
                "city": model.location.city,
                "neighborhood": model.location.neighborhood,
                "search_radius_km": model.location.search_radius_km,
            },
            "folders": {
                name: [_restaurant_dict(r) for r in folder.restaurants]
                for name, folder in model.memory.folders.items()
            },
        }
    )


@app.route("/api/location", methods=["POST"])
def set_location():
    data = request.get_json(force=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "latitude and longitude are required"}), 400

    model.location.update(
        latitude=lat,
        longitude=lon,
        city=data.get("city"),
        neighborhood=data.get("neighborhood"),
    )
    if "search_radius_km" in data:
        try:
            model.location.search_radius_km = float(data["search_radius_km"])
        except (TypeError, ValueError):
            pass
    return jsonify({"ok": True})


@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True) or {}
    mood = (data.get("mood") or "").strip() or None
    craving = (data.get("craving") or "").strip() or None

    recs = model.recommend(mood=mood, craving=craving, limit=5)
    return jsonify(
        {
            "recommendations": [
                {
                    "restaurant": _restaurant_dict(rec.restaurant),
                    "distance_km": round(rec.distance_km, 2),
                    "score": round(rec.score, 2),
                    "reason": rec.reason,
                }
                for rec in recs
            ]
        }
    )


@app.route("/api/save", methods=["POST"])
def save_to_folder():
    data = request.get_json(force=True) or {}
    folder = (data.get("folder") or "").strip()
    r = data.get("restaurant") or {}
    if not folder or not r.get("name"):
        return jsonify({"error": "folder and restaurant.name are required"}), 400

    try:
        restaurant = Restaurant(
            name=r["name"],
            latitude=float(r.get("latitude", model.location.latitude)),
            longitude=float(r.get("longitude", model.location.longitude)),
            cuisine=r.get("cuisine"),
            price_level=int(r.get("price_level", 2)),
            tags=list(r.get("tags") or []),
            rating=float(r.get("rating", 0.0)),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"invalid restaurant: {exc}"}), 400

    model.save_to_memory(folder, restaurant)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
