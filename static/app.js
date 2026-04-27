const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const sessionId = crypto.randomUUID();
let sending = false;

// ---- API helpers ----

async function api(path, body) {
    const opts = body
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
        : {};
    const res = await fetch(path, opts);
    return res.json();
}

// ---- Sidebar: folders ----

function renderFolders(folders) {
    const el = $("#folders");
    const names = Object.keys(folders);
    if (!names.length) {
        el.innerHTML = `<p class="muted" style="padding:12px">no saved restaurants yet. start chatting to build your food memory.</p>`;
        return;
    }
    el.innerHTML = names.map((name) => {
        const items = folders[name].map((r) =>
            `<div class="folder-item">
                <span>${esc(r.name)}</span>
                <span class="cuisine">${esc(r.cuisine || "")}</span>
            </div>`
        ).join("");
        return `<div class="folder">
            <div class="folder-header">${esc(name)}</div>
            <div class="folder-items">${items}</div>
        </div>`;
    }).join("");
}

function renderLocation(loc) {
    const where = loc.neighborhood || loc.city || `${loc.latitude.toFixed(3)}, ${loc.longitude.toFixed(3)}`;
    $("#location-chip").textContent = `${where} · ${loc.search_radius_km}km radius`;
}

// ---- Chat ----

function addMessage(role, text) {
    const container = $("#messages");
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerHTML = `<div class="message-bubble">${formatReply(text)}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const container = $("#messages");
    const div = document.createElement("div");
    div.className = "typing-indicator";
    div.id = "typing";
    div.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const el = $("#typing");
    if (el) el.remove();
}

function formatReply(text) {
    return esc(text)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

async function sendMessage(text) {
    if (sending || !text.trim()) return;
    sending = true;
    const btn = $("#send-btn");
    btn.disabled = true;

    addMessage("user", text);
    showTyping();

    try {
        const data = await api("/api/chat", { message: text, session_id: sessionId });
        hideTyping();
        addMessage("assistant", data.reply);
        if (data.folders) renderFolders(data.folders);
    } catch (err) {
        hideTyping();
        addMessage("assistant", "Something went wrong. Make sure the server is running and ANTHROPIC_API_KEY is set.");
    } finally {
        sending = false;
        btn.disabled = false;
    }
}

// ---- Init ----

async function init() {
    const state = await api("/api/state");
    renderLocation(state.location);
    renderFolders(state.folders);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                await api("/api/location", { latitude: pos.coords.latitude, longitude: pos.coords.longitude });
                const updated = await api("/api/state");
                renderLocation(updated.location);
            },
            () => {},
            { timeout: 4000 }
        );
    }
}

// ---- Events ----

$("#chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#chat-box");
    const text = input.value;
    input.value = "";
    sendMessage(text);
});

$("#sidebar-toggle").addEventListener("click", () => {
    $("#sidebar").classList.toggle("open");
});

$("#add-folder-btn").addEventListener("click", () => {
    $("#folder-modal").hidden = false;
    $("#folder-name-input").focus();
});

$("#folder-cancel").addEventListener("click", () => {
    $("#folder-modal").hidden = true;
    $("#folder-name-input").value = "";
});

$("#folder-create").addEventListener("click", async () => {
    const name = $("#folder-name-input").value.trim();
    if (!name) return;
    await api("/api/save", { folder: name, restaurant: { name: "(empty)" } });
    const state = await api("/api/state");
    renderFolders(state.folders);
    $("#folder-modal").hidden = true;
    $("#folder-name-input").value = "";
});

init();
