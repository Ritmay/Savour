const $ = (sel) => document.querySelector(sel);

async function getState() {
    const res = await fetch("/api/state");
    return res.json();
}

async function recommend(mood, craving) {
    const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mood, craving }),
    });
    return res.json();
}

async function setLocation(lat, lon) {
    await fetch("/api/location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lon }),
    });
}

function renderLocation(loc) {
    const chip = $("#location-chip");
    const where = loc.neighborhood || loc.city || `${loc.latitude.toFixed(3)}, ${loc.longitude.toFixed(3)}`;
    chip.textContent = `📍 ${where} · ${loc.search_radius_km}km radius`;
}

function renderFolders(folders) {
    const el = $("#folders");
    const names = Object.keys(folders);
    if (names.length === 0) {
        el.innerHTML = `<p class="muted">no saved restaurants yet.</p>`;
        return;
    }
    el.innerHTML = names
        .map((name) => {
            const items = folders[name]
                .map(
                    (r) => `
                    <li>
                        <span>${r.name}</span>
                        <span class="cuisine">${r.cuisine || ""}</span>
                    </li>`
                )
                .join("");
            return `
                <div class="folder">
                    <h3>${name}</h3>
                    <ul>${items}</ul>
                </div>`;
        })
        .join("");
}

function renderRecs(recs) {
    const el = $("#recs");
    if (!recs.length) {
        el.innerHTML = `<p class="muted">nothing in range matched. try a different mood or craving.</p>`;
        return;
    }
    el.innerHTML = recs
        .map((rec) => {
            const r = rec.restaurant;
            const tags = (r.tags || [])
                .map((t) => `<span class="tag">${t}</span>`)
                .join("");
            return `
                <div class="rec-card">
                    <div>
                        <div class="name">${r.name}</div>
                        <div class="meta">${r.cuisine || ""} · ${rec.reason}</div>
                        <div class="tags">${tags}</div>
                    </div>
                    <div class="score">${rec.score}</div>
                </div>`;
        })
        .join("");
}

async function refresh() {
    const state = await getState();
    renderLocation(state.location);
    renderFolders(state.folders);
}

async function onAsk() {
    const mood = $("#mood").value;
    const craving = $("#craving").value;
    const { recommendations } = await recommend(mood, craving);
    renderRecs(recommendations);
}

function askBrowserLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            await setLocation(pos.coords.latitude, pos.coords.longitude);
            refresh();
        },
        () => {
            /* user denied — keep default */
        },
        { timeout: 4000 }
    );
}

$("#ask-btn").addEventListener("click", onAsk);
["mood", "craving"].forEach((id) =>
    $("#" + id).addEventListener("keydown", (e) => {
        if (e.key === "Enter") onAsk();
    })
);

refresh();
askBrowserLocation();
