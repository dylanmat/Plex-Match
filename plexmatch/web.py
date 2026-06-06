from __future__ import annotations

import ipaddress
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
import jwt
from pydantic import BaseModel

from plexmatch.api.auth import (
    PinAuthServiceError,
    PinAuthSession,
    PinAuthSessionExpired,
    exchange_pin_for_token,
    load_pin_auth_session,
    start_pin_auth,
)
from plexmatch.cache import CacheError, CacheStore
from plexmatch.cli import update_env_plex_token
from plexmatch.refresh import refresh_once_with_auth_recovery
from plexmatch.service import CachedComparisonService, match_to_dict, ranked_user_to_dict


class RandomRequest(BaseModel):
    user_id: str
    mode: str = "high"
    media_type: str = "all"
    top: int | None = None


@dataclass
class WebAuthController:
    cache: CacheStore | None = None
    _lock: Lock = field(default_factory=Lock)
    _last_payload: dict | None = None

    def start(self) -> dict:
        with self._lock:
            token_status = plex_token_status()
            if token_status["state"] != "expired":
                raise HTTPException(status_code=409, detail="Plex reauthorization is available only when PLEX_TOKEN is expired.")
            session = load_pin_auth_session() or start_pin_auth()
            self._last_payload = self._pending_payload(session)
            return dict(self._last_payload)

    def status(self) -> dict:
        with self._lock:
            session = load_pin_auth_session()
            if session is None:
                return self._last_payload or {"state": "idle", "message": "No active Plex authorization session."}
            try:
                token = exchange_pin_for_token(session)
            except PinAuthSessionExpired as exc:
                self._last_payload = {"state": "expired", "message": str(exc)}
                return dict(self._last_payload)
            except PinAuthServiceError as exc:
                self._last_payload = {"state": "failed", "message": str(exc)}
                return dict(self._last_payload)
            if not token:
                self._last_payload = self._pending_payload(session)
                return dict(self._last_payload)

            update_env_plex_token(token)
            os.environ["PLEX_TOKEN"] = token
            refreshed_token, stats = refresh_once_with_auth_recovery(token, cache=self.cache)
            if refreshed_token != token:
                update_env_plex_token(refreshed_token)
                os.environ["PLEX_TOKEN"] = refreshed_token
            self._last_payload = {
                "state": "complete",
                "message": "Plex authorization complete. PLEX_TOKEN updated in .env and cache refresh finished.",
                "cache": {
                    "checked": stats.checked,
                    "refreshed": stats.refreshed,
                    "skipped": stats.skipped,
                    "failed": stats.failed,
                    "messages": stats.messages,
                },
            }
            return dict(self._last_payload)

    @staticmethod
    def _pending_payload(session: PinAuthSession) -> dict:
        return {
            "state": "pending",
            "message": "Open the Plex authorization link, then wait for completion.",
            "auth_url": session.auth_url,
            "fallback_auth_url": session.fallback_auth_url,
        }


def create_app(cache: CacheStore | None = None) -> FastAPI:
    app = FastAPI(title="PlexMatch")
    service = CachedComparisonService(cache)
    auth_controller = WebAuthController(cache)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return APP_HTML

    @app.get("/api/status")
    def status() -> dict:
        payload = asdict(service.status())
        if payload["ready"]:
            payload.update(service.metadata())
        return payload

    @app.post("/api/auth/start")
    def auth_start(request: Request) -> dict:
        _require_local_request(request)
        return auth_controller.start()

    @app.get("/api/auth/status")
    def auth_status(request: Request) -> dict:
        _require_local_request(request)
        return auth_controller.status()

    @app.get("/api/auth/availability")
    def auth_availability(request: Request) -> dict:
        _require_local_request(request)
        status = plex_token_status()
        return {
            "reauthorization_available": status["state"] == "expired",
            "token_status": status,
        }

    @app.get("/api/users/top")
    def top_users(media_type: str = "all") -> dict:
        try:
            users = [ranked_user_to_dict(user) for user in service.ranked_users(media_type)]
            return {
                "status": asdict(service.status()),
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
                "status": asdict(service.status()),
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
                "status": asdict(service.status()),
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


def _require_local_request(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host == "testclient":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        if host.lower() == "localhost":
            return
    raise HTTPException(status_code=403, detail="Plex authorization can only be initiated from a local browser.")


def plex_token_status() -> dict:
    token = _current_plex_token()
    if not token:
        return {"state": "missing", "message": "PLEX_TOKEN is not configured."}
    try:
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except jwt.PyJWTError:
        return {"state": "unknown", "message": "PLEX_TOKEN is not a decodable JWT."}
    exp = payload.get("exp")
    if not isinstance(exp, int | float):
        return {"state": "unknown", "message": "PLEX_TOKEN does not include a JWT expiration."}
    if exp <= time.time():
        return {"state": "expired", "message": "PLEX_TOKEN is expired."}
    return {"state": "valid", "message": "PLEX_TOKEN is valid."}


def _current_plex_token(env_path: Path = Path(".env")) -> str:
    token = (os.getenv("PLEX_TOKEN") or "").strip()
    if token:
        return token
    if not env_path.exists():
        return ""
    for line in env_path.read_text().splitlines():
        if line.startswith("PLEX_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


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
    button:disabled {
      cursor: not-allowed;
      opacity: 0.65;
    }
    .hidden { display: none !important; }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .user-list { display: grid; gap: 8px; }
    .mobile-user-select { display: none; }
    .user {
      width: 100%;
      min-height: 58px;
      text-align: left;
      color: var(--text);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
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
    .loading {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      color: var(--muted);
    }
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid var(--line);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .results { display: grid; gap: 8px; }
    .result {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) repeat(3, 96px);
      gap: 12px;
      align-items: center;
      min-height: 52px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }
    .metric {
      display: flex;
      justify-content: center;
      min-width: 0;
    }
    .result.both {
      border-left: 5px solid var(--accent);
    }
    .result.user_a {
      border-left: 5px solid #2563eb;
    }
    .result.user_b {
      border-left: 5px solid #9333ea;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 56px;
      height: 24px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .badge.both {
      color: #115e59;
      background: #ccfbf1;
    }
    .badge.user_a {
      color: #1e40af;
      background: #dbeafe;
    }
    .badge.user_b {
      color: #6b21a8;
      background: #f3e8ff;
    }
    .score-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      min-width: 62px;
      height: 26px;
      padding: 0 9px;
      border-radius: 999px;
      color: #334155;
      background: #eef2f7;
      border: 1px solid #d7dee8;
      font-size: 12px;
      font-weight: 750;
    }
    .info {
      position: relative;
      display: inline-grid;
      place-items: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      color: #64748b;
      background: #dfe6ef;
      border: 1px solid #cbd5e1;
      font-size: 10px;
      font-weight: 800;
      cursor: help;
    }
    .info::after {
      content: attr(data-tip);
      position: absolute;
      right: 0;
      bottom: calc(100% + 8px);
      width: max-content;
      max-width: 220px;
      padding: 7px 9px;
      border-radius: 6px;
      color: white;
      background: #26323f;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.3;
      opacity: 0;
      pointer-events: none;
      transform: translateY(4px);
      transition: opacity 0.12s ease, transform 0.12s ease;
      z-index: 3;
    }
    .info:hover::after,
    .info:focus::after {
      opacity: 1;
      transform: translateY(0);
    }
    .availability {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-width: 78px;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid transparent;
    }
    .availability .mark {
      display: inline-grid;
      place-items: center;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      font-size: 10px;
      line-height: 1;
    }
    .availability.yes {
      color: #2f5d46;
      background: #eef8f1;
      border-color: #cfe8d7;
    }
    .availability.yes .mark {
      color: #2f5d46;
      background: #d7efde;
    }
    .availability.no {
      color: #7a4a4a;
      background: #faf0f0;
      border-color: #efd6d6;
    }
    .availability.no .mark {
      color: #7a4a4a;
      background: #efdada;
    }
    .availability.unknown {
      color: #5f6368;
      background: #f2f3f4;
      border-color: #dddee0;
    }
    .availability.unknown .mark {
      color: #5f6368;
      background: #e3e5e7;
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
      aside {
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 12px 14px;
      }
      aside .toolbar { margin-bottom: 0; }
      .user-list { display: none; }
      .mobile-user-select {
        display: block;
        width: 100%;
        margin-top: 10px;
      }
      section { padding: 14px; }
      .result { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>PlexMatch</h1>
    <div class="header-actions">
      <button class="secondary hidden" id="reauthButton">Reauthorize</button>
      <div class="sub">self comparisons from cache</div>
    </div>
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
      <select id="mobileUserSelect" class="mobile-user-select" aria-label="Select user"></select>
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
    let selectedUserId = "all";
    let rankedUsers = [];
    let isLoading = false;
    const usersEl = document.getElementById("users");
    const resultsEl = document.getElementById("results");
    const statusEl = document.getElementById("status");
    const selectedEl = document.getElementById("selected");
    const mediaTypeEl = document.getElementById("mediaType");
    const mobileUserSelectEl = document.getElementById("mobileUserSelect");
    const topLimitEl = document.getElementById("topLimit");
    const reauthButtonEl = document.getElementById("reauthButton");
    let authPollTimer = null;

    function availabilityLabel(value) {
      if (value === true) return `<span class="availability yes"><span class="mark">✓</span><span>Local</span></span>`;
      if (value === false) return `<span class="availability no"><span class="mark">×</span><span>Missing</span></span>`;
      return `<span class="availability unknown"><span class="mark">?</span><span>Unknown</span></span>`;
    }

    function showStatus(status) {
      if (!status || (status.ready && status.freshness !== "stale")) {
        statusEl.innerHTML = "";
        return;
      }
      if (status.ready && status.freshness === "stale") {
        statusEl.innerHTML = `<div class="status warn"><div class="title">${status.message}</div><div class="meta">Run <code>python -m plexmatch --refresh-cache</code> or keep <code>python -m plexmatch --cache-scheduler</code> running.</div></div>`;
        return;
      }
      const commands = (status.commands || []).map(command => `<code>${command}</code>`).join("");
      statusEl.innerHTML = `<div class="status warn"><div class="title">${status.message}</div>${commands}</div>`;
    }

    function showAuthStatus(payload) {
      if (!payload || payload.state === "idle") return;
      if (payload.state === "pending") {
        statusEl.innerHTML = `
          <div class="status warn">
            <div class="title">${payload.message}</div>
            <code><a href="${payload.auth_url}" target="_blank" rel="noreferrer">Open Plex authorization</a></code>
            <code><a href="${payload.fallback_auth_url}" target="_blank" rel="noreferrer">Fallback authorization link</a></code>
          </div>
        `;
        return;
      }
      if (payload.state === "complete") {
        const cache = payload.cache || {};
        statusEl.innerHTML = `<div class="status"><div class="title">${payload.message}</div><div class="meta">checked=${cache.checked || 0} refreshed=${cache.refreshed || 0} skipped=${cache.skipped || 0} failed=${cache.failed || 0}</div></div>`;
        return;
      }
      statusEl.innerHTML = `<div class="status warn"><div class="title">${payload.message || "Plex authorization failed."}</div></div>`;
    }

    function setLoading(value) {
      isLoading = value;
      document.getElementById("randomLow").disabled = value || !selectedUserId;
      document.getElementById("randomHigh").disabled = value || !selectedUserId;
      if (value) selectedEl.innerHTML = `<div class="loading"><span class="spinner" aria-hidden="true"></span><span>Refreshing from cache...</span></div>`;
    }

    function sourceLabel(value) {
      if (value === "both") return "Both";
      if (value === "user_a") return "Self";
      if (value === "user_b") return "Other";
      return value || "unknown";
    }

    function supportInfo(count) {
      const value = Number(count) || 0;
      const noun = value === 1 ? "other cached user" : "other cached users";
      return `<span class="info" tabindex="0" data-tip="Support: ${value} ${noun} also have this item.">i</span>`;
    }

    function renderUsers() {
      usersEl.innerHTML = "";
      mobileUserSelectEl.innerHTML = "";
      rankedUsers.forEach((entry, index) => {
        const button = document.createElement("button");
        button.className = `user ${entry.user.id === selectedUserId ? "active" : ""}`;
        button.innerHTML = `<div class="name">${entry.user.title}</div><div class="meta">${entry.total_score} total score | ${entry.match_count} results</div>`;
        button.onclick = () => selectUser(entry.user.id);
        usersEl.appendChild(button);
        const option = document.createElement("option");
        option.value = entry.user.id;
        option.textContent = `${entry.user.title} (${entry.total_score})`;
        mobileUserSelectEl.appendChild(option);
      });
      if (!rankedUsers.some(entry => entry.user.id === selectedUserId)) selectedUserId = "all";
      mobileUserSelectEl.value = selectedUserId || "";
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
        row.className = `result ${match.source || ""}`;
        row.innerHTML = `
          <div><div class="title">${match.title}</div><div class="meta">${match.year || ""} ${match.media_type || ""}</div></div>
          <div class="metric"><span class="score-pill">${match.score}${supportInfo(match.support_count)}</span></div>
          <div class="metric"><span class="badge ${match.source || ""}">${sourceLabel(match.source)}</span></div>
          <div class="metric">${availabilityLabel(match.available_locally)}</div>
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
        selectedEl.innerHTML = `<div class="title">${data.match.title}</div><div class="meta">Random ${mode} | score ${data.match.score}</div><div style="margin-top: 8px;">${availabilityLabel(data.match.available_locally)}</div>`;
      }
      setLoading(false);
    }

    async function startReauth() {
      reauthButtonEl.disabled = true;
      statusEl.innerHTML = `<div class="status"><div class="loading"><span class="spinner" aria-hidden="true"></span><span>Starting Plex authorization...</span></div></div>`;
      const response = await fetch("/api/auth/start", {method: "POST"});
      if (!response.ok) {
        reauthButtonEl.disabled = false;
        const error = await response.json();
        statusEl.innerHTML = `<div class="status warn"><div class="title">${error.detail || "Plex reauthorization is not available."}</div></div>`;
        await loadAuthAvailability();
        return;
      }
      const payload = await response.json();
      showAuthStatus(payload);
      if (authPollTimer) clearInterval(authPollTimer);
      authPollTimer = setInterval(pollReauth, 2000);
    }

    async function pollReauth() {
      const response = await fetch("/api/auth/status");
      const payload = await response.json();
      showAuthStatus(payload);
      if (payload.state === "complete" || payload.state === "failed" || payload.state === "expired") {
        clearInterval(authPollTimer);
        authPollTimer = null;
        reauthButtonEl.disabled = false;
      }
      if (payload.state === "complete") {
        await loadAuthAvailability();
        await loadUsers();
      }
    }

    async function loadAuthAvailability() {
      const response = await fetch("/api/auth/availability");
      if (!response.ok) return;
      const payload = await response.json();
      reauthButtonEl.classList.toggle("hidden", !payload.reauthorization_available);
    }

    mediaTypeEl.onchange = () => loadUsers();
    mobileUserSelectEl.onchange = () => selectUser(mobileUserSelectEl.value);
    topLimitEl.onchange = loadComparison;
    reauthButtonEl.onclick = startReauth;
    document.getElementById("randomLow").onclick = () => randomPick("low");
    document.getElementById("randomHigh").onclick = () => randomPick("high");
    loadAuthAvailability();
    loadUsers();
  </script>
</body>
</html>
"""
