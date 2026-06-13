"""Savourtaste — Claude-powered restaurant recommendation site.

Uses the Anthropic API as the sole intelligence layer. Claude receives
the user's saved food memory, current location, and time of day, then
has a natural conversation about where to eat. Claude can also save
new restaurants into memory folders via tool use.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import anthropic
from flask import Flask, jsonify, render_template, request

from SavourTaste import LearningModel, Location, Memory, MemoryFolder, Restaurant

app = Flask(__name__)

client = anthropic.Anthropic()

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "save_restaurant",
        "description": (
            "Save a restaurant to the user's food memory under a named folder. "
            "Call this when the user asks to remember a restaurant or add it to a folder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": 'Folder name, e.g. "Late Night Cravings"',
                },
                "name": {"type": "string", "description": "Restaurant name"},
                "cuisine": {"type": "string", "description": "Cuisine type"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Mood/context tags like cozy, spicy, romantic",
                },
                "price_level": {
                    "type": "integer",
                    "description": "1 (cheap) to 4 (expensive)",
                },
                "rating": {"type": "number", "description": "Rating out of 5"},
            },
            "required": ["folder", "name"],
        },
    },
    {
        "name": "create_folder",
        "description": "Create a new empty folder in the user's food memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Folder name, e.g. 'Rainy Day Comfort'",
                },
            },
            "required": ["name"],
        },
    },
]


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
        ("Late Night Cravings", Restaurant("Joe's Pizza", 40.7306, -73.9866, "pizza", 1, ["late-night", "comfort", "cheap"], 4.5)),
        ("Late Night Cravings", Restaurant("Xi'an Famous Foods", 40.7614, -73.9845, "chinese noodles", 1, ["late-night", "spicy", "quick"], 4.4)),
        ("Comfort Food When Sad", Restaurant("Ippudo Ramen", 40.7614, -73.9776, "japanese ramen", 2, ["cozy", "comfort", "warm", "dinner"], 4.3)),
        ("Comfort Food When Sad", Restaurant("Jackson Hole Burgers", 40.7536, -73.9832, "american burgers", 2, ["comfort", "hearty", "lunch", "dinner"], 4.1)),
        ("Fancy Date Night", Restaurant("Le Bernardin", 40.7614, -73.9819, "french seafood", 4, ["fancy", "romantic", "dinner"], 4.8)),
        ("Morning Fuel", Restaurant("Blue Bottle Coffee", 40.7549, -73.9840, "coffee breakfast", 2, ["morning", "quick", "cozy"], 4.2)),
    ]
    for folder, restaurant in seeds:
        model.save_to_memory(folder, restaurant)
    return model


model = _seed_model()
conversations: dict[str, list] = {}


def _build_system_prompt() -> str:
    loc = model.location
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 11:
        time_slot = "morning"
    elif 11 <= hour < 15:
        time_slot = "lunchtime"
    elif 15 <= hour < 18:
        time_slot = "afternoon"
    elif 18 <= hour < 22:
        time_slot = "dinnertime"
    else:
        time_slot = "late night"

    memory_text = ""
    for name, folder in model.memory.folders.items():
        items = []
        for r in folder.restaurants:
            dist = loc.distance_km(r.latitude, r.longitude)
            price = "$" * r.price_level
            items.append(
                f"  - {r.name} ({r.cuisine}) — {price}, "
                f"rated {r.rating}/5, {dist:.1f}km away, "
                f"tags: {', '.join(r.tags)}"
            )
        memory_text += f"\n[{name}]\n" + "\n".join(items) + "\n"

    return f"""You are Savourtaste, a warm and opinionated AI food companion. You know the \
user's saved restaurants, their location, and the time of day. Your job is to \
recommend where to eat based on how they feel right now.

Personality: friendly, a little playful, decisive. You don't hedge — you pick \
a spot and tell the user why it's perfect for their mood. Keep responses concise \
(2-4 sentences for a recommendation). Use the restaurant data below, including \
distance and tags, to make smart picks.

If the user mentions a new restaurant or asks to save one, use the save_restaurant \
tool. If they want to create a new folder, use create_folder.

If the user asks about a restaurant you don't have in memory, you can still talk \
about it knowledgeably and offer to save it.

Current context:
- Location: {loc.city or "Unknown"}, {loc.neighborhood or ""} ({loc.latitude:.4f}, {loc.longitude:.4f})
- Search radius: {loc.search_radius_km}km
- Time: {now.strftime("%I:%M %p")} ({time_slot})
- Day: {now.strftime("%A")}

User's food memory:
{memory_text if memory_text.strip() else "(empty — no saved restaurants yet)"}
"""


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


def _handle_tool_use(tool_name: str, tool_input: dict) -> str:
    if tool_name == "save_restaurant":
        r = Restaurant(
            name=tool_input["name"],
            latitude=model.location.latitude,
            longitude=model.location.longitude,
            cuisine=tool_input.get("cuisine"),
            price_level=tool_input.get("price_level", 2),
            tags=tool_input.get("tags", []),
            rating=tool_input.get("rating", 0.0),
        )
        model.save_to_memory(tool_input["folder"], r)
        return json.dumps({"saved": True, "folder": tool_input["folder"], "name": r.name})

    if tool_name == "create_folder":
        model.memory.create_folder(tool_input["name"])
        return json.dumps({"created": True, "folder": tool_input["name"]})

    return json.dumps({"error": "unknown tool"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def state():
    return jsonify({
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
    })


@app.route("/api/location", methods=["POST"])
def set_location():
    data = request.get_json(force=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "latitude and longitude required"}), 400
    model.location.update(lat, lon, data.get("city"), data.get("neighborhood"))
    if "search_radius_km" in data:
        try:
            model.location.search_radius_km = float(data["search_radius_km"])
        except (TypeError, ValueError):
            pass
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    user_msg = (data.get("message") or "").strip()
    session_id = data.get("session_id", "default")
    if not user_msg:
        return jsonify({"error": "message is required"}), 400

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": user_msg})

    system = _build_system_prompt()
    messages = conversations[session_id]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        tools=TOOLS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        assistant_content = response.content
        conversations[session_id].append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                result = _handle_tool_use(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        conversations[session_id].append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[{"type": "text", "text": _build_system_prompt(), "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=conversations[session_id],
        )

    reply_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            reply_text += block.text

    conversations[session_id].append({"role": "assistant", "content": response.content})

    folders_updated = {
        name: [_restaurant_dict(r) for r in folder.restaurants]
        for name, folder in model.memory.folders.items()
    }

    return jsonify({"reply": reply_text, "folders": folders_updated})


@app.route("/api/save", methods=["POST"])
def save_to_folder():
    data = request.get_json(force=True) or {}
    folder = (data.get("folder") or "").strip()
    r = data.get("restaurant") or {}
    if not folder or not r.get("name"):
        return jsonify({"error": "folder and restaurant.name required"}), 400
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
