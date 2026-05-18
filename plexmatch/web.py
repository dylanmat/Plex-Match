from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from plexmatch.cache import CacheError, CacheStore
from plexmatch.service import CachedComparisonService, match_to_dict, ranked_user_to_dict


class RandomRequest(BaseModel):
    user_id: str
    mode: str = "high"
    media_type: str = "all"
    top: int | None = None


def create_app(cache: CacheStore | None = None) -> FastAPI:
    app = FastAPI(title="PlexMatch")
    service = CachedComparisonService(cache)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return APP_HTML

    @app.get("/api/status")
    def status() -> dict:
        payload = asdict(service.status())
        if payload["ready"]:
            payload.update(service.metadata())
        return payload

    @app.get("/api/users/top")
    def top_users(media_type: str = "all") -> dict:
        try:
            users = [ranked_user_to_dict(user) for user in service.ranked_users(media_type)]
            return {
                "users": users,
                "result_count": len(users),
                **service.metadata(),
            }
        except CacheError as exc:
            return _cache_error_payload(exc)

    @app.get("/api/compare/{user_id}")
    def compare(user_id: str, media_type: str = "all", top: int | None = None) -> dict:
        try:
            matches = [match_to_dict(match) for match in service.compare(user_id, media_type, top)]
            return {
                "matches": matches,
                "result_count": len(matches),
                **service.metadata(),
            }
        except CacheError as exc:
            return _cache_error_payload(exc)

    @app.post("/api/random")
    def random_match(request: RandomRequest) -> dict:
        if request.mode not in {"high", "low"}:
            raise HTTPException(status_code=400, detail="mode must be high or low")
        try:
            return {
                "match": match_to_dict(service.random_match(request.user_id, request.mode, request.media_type, request.top)),
                **service.metadata(),
            }
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CacheError as exc:
            return _cache_error_payload(exc)

    return app


def _cache_error_payload(exc: CacheError) -> dict:
    status = {
        "ready": False,
        "message": str(exc),
        "commands": [
            "python -m plexmatch --list-users",
            'python -m plexmatch --user-a self --user-b "Friend Name"',
        ],
    }
    return {"status": status, "users": [], "matches": [], "result_count": 0}


APP_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PlexMatch</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #1f2328;
      --muted: #68707a;
      --line: #d9ded8;
      --accent: #0f766e;
      --accent-soft: #d9f0ec;
      --warn: #9a3412;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { font-size: 18px; margin: 0; font-weight: 650; }
    main {
      min-height: calc(100vh - 56px);
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
    }
    aside {
      border-right: 1px solid var(--line);
      background: #fbfbf9;
      padding: 16px;
      overflow: auto;
    }
    section { padding: 18px 22px; min-width: 0; }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    select, input, button {
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      padding: 0 10px;
      font: inherit;
    }
    button {
      cursor: pointer;
      background: var(--accent);
      color: white;
      border-color: var(--accent);
      font-weight: 600;
    }
    button.secondary {
      background: var(--panel);
      color: var(--text);
      border-color: var(--line);
    }
    .user-list { display: grid; gap: 8px; }
    .user {
      width: 100%;
      min-height: 58px;
      text-align: left;
      color: var(--text);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
    }
    .user.active {
      border-color: var(--accent);
      background: var(--accent-soft);
    }
    .name, .title { font-weight: 650; }
    .meta, .sub { color: var(--muted); font-size: 13px; margin-top: 3px; }
    .status {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
      margin-bottom: 16px;
    }
    .status.warn { border-color: #fed7aa; color: var(--warn); }
    .results { display: grid; gap: 8px; }
    .result {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) repeat(5, minmax(70px, auto));
      gap: 12px;
      align-items: center;
      min-height: 52px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }
    code {
      display: block;
      color: var(--text);
      background: #f2f4f3;
      border: 1px solid var(--line);
      padding: 8px;
      border-radius: 6px;
      margin-top: 8px;
      overflow-wrap: anywhere;
    }
    @media (max-width: 780px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .result { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>PlexMatch</h1>
    <div class="sub">self comparisons from cache</div>
  </header>
  <main>
    <aside>
      <div class="toolbar">
        <select id="mediaType">
          <option value="all">All</option>
          <option value="movie">Movies</option>
          <option value="show">Shows</option>
        </select>
      </div>
      <div id="users" class="user-list"></div>
    </aside>
    <section>
      <div id="status"></div>
      <div class="toolbar">
        <input id="topLimit" type="number" min="1" value="20" aria-label="Top limit">
        <button class="secondary" id="randomLow">Random Low</button>
        <button id="randomHigh">Random High</button>
      </div>
      <div id="selected" class="status"></div>
      <div id="results" class="results"></div>
    </section>
  </main>
  <script>
    let selectedUserId = null;
    let rankedUsers = [];
    let isLoading = false;
    const usersEl = document.getElementById("users");
    const resultsEl = document.getElementById("results");
    const statusEl = document.getElementById("status");
    const selectedEl = document.getElementById("selected");
    const mediaTypeEl = document.getElementById("mediaType");
    const topLimitEl = document.getElementById("topLimit");

    function availabilityLabel(value) {
      if (value === true) return "local yes";
      if (value === false) return "local no";
      return "local unknown";
    }

    function showStatus(status) {
      if (!status || status.ready) {
        statusEl.innerHTML = "";
        return;
      }
      const commands = (status.commands || []).map(command => `<code>${command}</code>`).join("");
      statusEl.innerHTML = `<div class="status warn"><div class="title">${status.message}</div>${commands}</div>`;
    }

    function setLoading(value) {
      isLoading = value;
      document.getElementById("randomLow").disabled = value || !selectedUserId;
      document.getElementById("randomHigh").disabled = value || !selectedUserId;
      if (value) selectedEl.innerHTML = "Loading cached results...";
    }

    function renderUsers() {
      usersEl.innerHTML = "";
      rankedUsers.forEach((entry, index) => {
        const button = document.createElement("button");
        button.className = `user ${entry.user.id === selectedUserId ? "active" : ""}`;
        button.innerHTML = `<div class="name">${entry.user.title}</div><div class="meta">${entry.total_score} total score | ${entry.match_count} results</div>`;
        button.onclick = () => selectUser(entry.user.id);
        usersEl.appendChild(button);
        if (index === 0 && !selectedUserId) selectedUserId = entry.user.id;
      });
    }

    async function loadUsers() {
      setLoading(true);
      const mediaType = mediaTypeEl.value;
      const response = await fetch(`/api/users/top?media_type=${encodeURIComponent(mediaType)}`);
      const data = await response.json();
      showStatus(data.status);
      rankedUsers = data.users || [];
      renderUsers();
      if (selectedUserId) await loadComparison();
      if (!selectedUserId && !rankedUsers.length) {
        selectedEl.innerHTML = "No cached comparisons available.";
        resultsEl.innerHTML = "";
      }
      setLoading(false);
    }

    async function selectUser(userId) {
      selectedUserId = userId;
      renderUsers();
      await loadComparison();
    }

    async function loadComparison() {
      if (!selectedUserId) return;
      setLoading(true);
      const mediaType = mediaTypeEl.value;
      const top = topLimitEl.value;
      const response = await fetch(`/api/compare/${encodeURIComponent(selectedUserId)}?media_type=${encodeURIComponent(mediaType)}&top=${encodeURIComponent(top)}`);
      const data = await response.json();
      showStatus(data.status);
      selectedEl.innerHTML = `${(data.matches || []).length} cached results`;
      resultsEl.innerHTML = "";
      (data.matches || []).forEach(match => {
        const row = document.createElement("div");
        row.className = "result";
        row.innerHTML = `
          <div><div class="title">${match.title}</div><div class="meta">${match.year || ""} ${match.media_type || ""}</div></div>
          <div>score ${match.score}</div>
          <div>${match.source}</div>
          <div>support ${match.support_count}</div>
          <div>${availabilityLabel(match.available_locally)}</div>
        `;
        resultsEl.appendChild(row);
      });
      setLoading(false);
    }

    async function randomPick(mode) {
      if (!selectedUserId || isLoading) return;
      setLoading(true);
      const response = await fetch("/api/random", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user_id: selectedUserId, mode, media_type: mediaTypeEl.value, top: Number(topLimitEl.value) || null})
      });
      const data = await response.json();
      if (data.match) {
        selectedEl.innerHTML = `<div class="title">${data.match.title}</div><div class="meta">Random ${mode} | score ${data.match.score} | ${availabilityLabel(data.match.available_locally)}</div>`;
      }
      setLoading(false);
    }

    mediaTypeEl.onchange = () => { selectedUserId = null; loadUsers(); };
    topLimitEl.onchange = loadComparison;
    document.getElementById("randomLow").onclick = () => randomPick("low");
    document.getElementById("randomHigh").onclick = () => randomPick("high");
    loadUsers();
  </script>
</body>
</html>
"""
