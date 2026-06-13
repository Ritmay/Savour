const $ = (sel) => document.querySelector(sel);
const sessionId = crypto.randomUUID();
let sending = false;

/* ---- API ---- */

async function api(path, body) {
    const opts = body
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
        : {};
    const res = await fetch(path, opts);
    return res.json();
}

/* ---- Sidebar ---- */

function renderFolders(folders) {
    const el = $("#folders");
    const names = Object.keys(folders);
    if (!names.length) {
        el.innerHTML = `<div class="empty-state"><p>no saved restaurants yet</p></div>`;
        return;
    }
    el.innerHTML = names.map((name) => {
        const items = folders[name].map((r) =>
            `<div class="folder-item">
                <span>${esc(r.name)}</span>
                ${r.cuisine ? `<span class="cuisine">${esc(r.cuisine)}</span>` : ""}
            </div>`
        ).join("");
        return `<div class="folder">
            <div class="folder-header">${esc(name)}</div>
            <div class="folder-items">${items}</div>
        </div>`;
    }).join("");
}

function renderLocation(loc) {
    const where = loc.neighborhood
        ? `${loc.neighborhood}, ${loc.city || ""}`
        : loc.city || `${loc.latitude.toFixed(3)}, ${loc.longitude.toFixed(3)}`;
    $("#location-chip span").textContent = `${where} · ${loc.search_radius_km}km radius`;
}

/* ---- Chat ---- */

function addMessage(role, text) {
    const container = $("#messages");

    if (role === "assistant") {
        const html = `
            <div class="message assistant">
                <div class="avatar-ring">
                    <div class="avatar-sm">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
                    </div>
                </div>
                <div class="message-content">
                    <div class="message-name">Savourtaste</div>
                    <div class="message-bubble">${formatReply(text)}</div>
                </div>
            </div>`;
        container.insertAdjacentHTML("beforeend", html);
    } else {
        const html = `
            <div class="message user">
                <div class="message-content">
                    <div class="message-name">You</div>
                    <div class="message-bubble">${esc(text)}</div>
                </div>
            </div>`;
        container.insertAdjacentHTML("beforeend", html);
    }

    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const container = $("#messages");
    const html = `
        <div class="typing-wrapper" id="typing">
            <div class="avatar-ring">
                <div class="avatar-sm">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
                </div>
            </div>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>`;
    container.insertAdjacentHTML("beforeend", html);
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
    $("#send-btn").disabled = true;

    addMessage("user", text);
    showTyping();

    try {
        const data = await api("/api/chat", { message: text, session_id: sessionId });
        hideTyping();
        addMessage("assistant", data.reply);
        if (data.folders) renderFolders(data.folders);
    } catch {
        hideTyping();
        addMessage("assistant", "Something went wrong. Make sure the server is running and ANTHROPIC_API_KEY is set.");
    } finally {
        sending = false;
        $("#send-btn").disabled = false;
        $("#chat-box").focus();
    }
}

/* ---- Init ---- */

async function init() {
    const state = await api("/api/state");
    renderLocation(state.location);
    renderFolders(state.folders);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                await api("/api/location", {
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                });
                const updated = await api("/api/state");
                renderLocation(updated.location);
            },
            () => {},
            { timeout: 4000 }
        );
    }
}

/* ---- Events ---- */

$("#chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#chat-box");
    const text = input.value;
    input.value = "";
    sendMessage(text);
});

$("#sidebar-toggle").addEventListener("click", () => {
    $("#sidebar").classList.toggle("open");
    $("#sidebar-overlay").classList.toggle("visible");
});

$("#sidebar-overlay").addEventListener("click", () => {
    $("#sidebar").classList.remove("open");
    $("#sidebar-overlay").classList.remove("visible");
});

$("#add-folder-btn").addEventListener("click", () => {
    $("#folder-modal").hidden = false;
    setTimeout(() => $("#folder-name-input").focus(), 50);
});

function closeModal() {
    $("#folder-modal").hidden = true;
    $("#folder-name-input").value = "";
}

$("#folder-cancel").addEventListener("click", closeModal);
$("#folder-cancel-2").addEventListener("click", closeModal);

$("#folder-modal").addEventListener("click", (e) => {
    if (e.target === $("#folder-modal")) closeModal();
});

$("#folder-create").addEventListener("click", async () => {
    const name = $("#folder-name-input").value.trim();
    if (!name) return;
    await api("/api/save", { folder: name, restaurant: { name: "(empty)" } });
    const state = await api("/api/state");
    renderFolders(state.folders);
    closeModal();
});

$("#folder-name-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        $("#folder-create").click();
    }
});

init();
