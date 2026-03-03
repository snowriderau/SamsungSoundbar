const commandsBody = document.getElementById("commandsBody");
const pingResponse = document.getElementById("pingResponse");
const statusCard = document.getElementById("statusCard");
const statusText = document.getElementById("statusText");
const statusDetail = document.getElementById("statusDetail");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed: ${res.status}`);
  }
  return data;
}

function setStatus(ok, text, detail) {
  statusCard.classList.remove("status-ok", "status-bad", "status-unknown");
  statusCard.classList.add(ok === true ? "status-ok" : ok === false ? "status-bad" : "status-unknown");
  statusText.textContent = text;
  statusDetail.textContent = detail || "";
}

function statusPill(status) {
  const safe = status || "untested";
  return `<span class="pill pill-${safe}">${safe}</span>`;
}

function when(ts) {
  if (!ts) return "Never";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

async function loadConfig() {
  const cfg = await api("/api/config");
  document.getElementById("ipInput").value = cfg.ip || "";
  document.getElementById("portInput").value = cfg.port || 56001;
}

async function saveConfig() {
  const ip = document.getElementById("ipInput").value.trim();
  const port = Number(document.getElementById("portInput").value || 56001);
  await api("/api/config", {
    method: "POST",
    body: JSON.stringify({ ip, port }),
  });
  setStatus(null, "Config saved", `${ip || "No IP"}:${port}`);
}

async function ping() {
  pingResponse.textContent = "Checking...";
  const result = await api("/api/ping", { method: "POST" });
  if (result.ok) {
    setStatus(true, "Soundbar is responding", `HTTP ${result.http_status || "?"} in ${result.latency_ms}ms`);
  } else {
    setStatus(false, "Soundbar is not responding", result.error || "No response from probe commands");
  }
  pingResponse.textContent = result.response || result.error || "No body";
}

async function loadCommands() {
  const commands = await api("/api/commands");
  commandsBody.innerHTML = "";

  for (const cmd of commands) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${cmd.name}</strong><br />
        <small>${cmd.expected || ""}</small>
      </td>
      <td><code>${cmd.xml_command.replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</code></td>
      <td>${statusPill(cmd.status)}</td>
      <td>
        ${when(cmd.last_tested_at)}<br />
        <small>${cmd.last_http_status ? `HTTP ${cmd.last_http_status}` : ""} ${cmd.last_error || ""}</small>
      </td>
      <td>
        <div class="actions">
          <button class="btn" data-action="edit" data-id="${cmd.id}">Edit</button>
          <button class="btn" data-action="test" data-id="${cmd.id}">Test</button>
          <button class="btn" data-action="mark-working" data-id="${cmd.id}">Working</button>
          <button class="btn" data-action="mark-bad" data-id="${cmd.id}">Not Working</button>
          <button class="btn" data-action="delete" data-id="${cmd.id}">Delete</button>
        </div>
        <details>
          <summary>Last response</summary>
          <pre class="response-box">${(cmd.last_response || "").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</pre>
        </details>
      </td>
    `;
    commandsBody.appendChild(tr);
  }
}

async function addCommand() {
  const name = document.getElementById("addName").value.trim();
  const expected = document.getElementById("addExpected").value.trim();
  const xml_command = document.getElementById("addXml").value.trim();
  if (!name || !xml_command) {
    alert("Name and XML command are required.");
    return;
  }
  await api("/api/commands", {
    method: "POST",
    body: JSON.stringify({ name, expected, xml_command }),
  });
  document.getElementById("addName").value = "";
  document.getElementById("addExpected").value = "";
  document.getElementById("addXml").value = "";
  await loadCommands();
}

async function commandAction(action, id) {
  if (action === "edit") {
    const commands = await api("/api/commands");
    const cmd = commands.find((item) => item.id === id);
    if (!cmd) {
      throw new Error("Command not found");
    }

    const name = prompt("Edit command name:", cmd.name);
    if (name === null) return;
    const expected = prompt("Edit expected outcome:", cmd.expected || "");
    if (expected === null) return;
    const xml = prompt("Edit XML command payload:", cmd.xml_command);
    if (xml === null) return;

    await api(`/api/commands/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({
        name: name.trim(),
        expected: expected.trim(),
        xml_command: xml.trim(),
      }),
    });
    await loadCommands();
    return;
  }

  if (action === "test") {
    const result = await api(`/api/commands/${encodeURIComponent(id)}/test`, { method: "POST" });
    const ok = !!result.result.ok;
    setStatus(ok, ok ? "Command worked" : "Command failed", result.result.error || `HTTP ${result.result.http_status || "?"}`);
    pingResponse.textContent = result.result.response || result.result.error || "No body";
    await loadCommands();
    return;
  }

  if (action === "mark-working") {
    await api(`/api/commands/${encodeURIComponent(id)}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "working" }),
    });
    await loadCommands();
    return;
  }

  if (action === "mark-bad") {
    await api(`/api/commands/${encodeURIComponent(id)}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "not_working" }),
    });
    await loadCommands();
    return;
  }

  if (action === "delete") {
    if (!confirm("Delete this command?")) return;
    await api(`/api/commands/${encodeURIComponent(id)}`, { method: "DELETE" });
    await loadCommands();
  }
}

document.getElementById("saveConfigBtn").addEventListener("click", async () => {
  try {
    await saveConfig();
  } catch (e) {
    setStatus(false, "Failed to save config", e.message);
  }
});

document.getElementById("pingBtn").addEventListener("click", async () => {
  try {
    await ping();
  } catch (e) {
    setStatus(false, "Ping failed", e.message);
  }
});

document.getElementById("addBtn").addEventListener("click", async () => {
  try {
    await addCommand();
  } catch (e) {
    alert(e.message);
  }
});

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    await loadCommands();
  } catch (e) {
    alert(e.message);
  }
});

commandsBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (!action || !id) return;
  try {
    await commandAction(action, id);
  } catch (e) {
    alert(e.message);
  }
});

(async function init() {
  try {
    await loadConfig();
    await loadCommands();
  } catch (e) {
    setStatus(false, "Init failed", e.message);
  }
})();
