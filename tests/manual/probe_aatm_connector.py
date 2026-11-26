"""Manual behavioural probe of AATM's Arena connector (evidence tool, NOT part of the test suite).

The filename does not start with ``test_``, so ``unittest``/``pytest`` discovery ignores it.

Why it exists: ``docs/AATM_ARENA_EVALUATION.md`` claims a limited set of connector behaviours
were "verified by execution" rather than only read from source. This script is how that was
done, so the claim can be reproduced.

What it measures (against an AATM checkout the operator provides, unmodified):
  * ConnectorHub registration gates (real origins need two independent flags),
  * WebSocket ``hello`` authentication (per-profile token hash + page/header origin match),
  * ``needs_human`` stop semantics (write commands refused, read-only commands allowed,
    ``reset()`` required to resume),
  * the closed command allow-list, repo/prompt/URL validation,
  * the bridge admin surface bearer auth and fail-closed behaviour.

It never touches Arena, never opens a browser, never reads cookies and never writes to the
AATM checkout: it only imports ``bridge.connector`` / ``bridge.server`` and drives them with a
fake WebSocket plus FastAPI's TestClient.

Requirements: ``fastapi``, ``pydantic>=2``, ``httpx`` and an AATM checkout (nothing else).
It does NOT need AATM's ``backend/requirements.txt`` because it imports the bridge package only.

Usage:
    AATM_REPO=/path/to/AATM python3 tests/manual/probe_aatm_connector.py [--verbose]

Exit code 0 = every probe passed, 1 = at least one probe failed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

BRIDGE_TOKEN = "probe-bridge-token"
PROFILE_TOKEN = "probe-profile-token"
PROFILE_HASH = hashlib.sha256(PROFILE_TOKEN.encode("utf-8")).hexdigest()
LOOPBACK_ORIGIN = "http://127.0.0.1:8765"


class Probe:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.results: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))
        line = ("PASS " if ok else "FAIL ") + name
        if detail and (self.verbose or not ok):
            line += " :: " + detail
        print(line, flush=True)

    def summary(self) -> int:
        passed = sum(1 for _, ok, _ in self.results if ok)
        print(f"\nSUMMARY {passed}/{len(self.results)} passed")
        return 0 if passed == len(self.results) else 1


class FakeWebSocket:
    """Minimal stand-in for fastapi.WebSocket: one ``hello`` frame, then silence."""

    def __init__(self, hello: dict, header_origin: str = LOOPBACK_ORIGIN) -> None:
        self._hello = hello
        self.headers = {"origin": header_origin}
        self.sent: list[dict] = []
        self.closed: tuple[int, str] | None = None
        self._hello_sent = False

    async def accept(self) -> None:
        return None

    async def receive_text(self) -> str:
        if not self._hello_sent:
            self._hello_sent = True
            return json.dumps(self._hello)
        await asyncio.sleep(3600)  # block until the caller cancels the socket task

    async def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = (code, reason)


async def _open(hub, hello: dict, header_origin: str = LOOPBACK_ORIGIN):
    ws = FakeWebSocket(hello, header_origin)
    task = asyncio.create_task(hub.handle_socket(ws))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if ws.sent or ws.closed:
            break
    return ws, task


async def _probe_connector(probe: Probe) -> None:
    from bridge.connector import ConnectorError, ConnectorHub, ProfileRegistration

    def registration(**overrides):
        body = {
            "token_sha256": PROFILE_HASH,
            "agent_id": "worker-1",
            "allowed_origins": [LOOPBACK_ORIGIN],
            "real_enabled": False,
            "mode": "agent",
        }
        body.update(overrides)
        return ProfileRegistration.model_validate(body)

    hub = ConnectorHub()
    hub.register("p1", registration())
    probe.record("register loopback profile", "p1" in hub.profiles)

    for name, overrides in (
        ("real origin without ARENA_CONNECTOR_ENABLED refused", {"allowed_origins": ["https://arena.ai"], "real_enabled": True}),
        ("real origin without real_enabled refused", {"allowed_origins": ["https://arena.ai"], "real_enabled": False}),
    ):
        try:
            hub.register("probe", registration(**overrides))
            probe.record(name, False, "no error raised")
        except ConnectorError as exc:
            probe.record(name, exc.code == "not_enabled" and exc.http_status == 403, f"{exc.code}/{exc.http_status}")

    # --- websocket authentication ---------------------------------------------------------
    bad_ws, bad_task = await _open(hub, {"type": "hello", "profile_id": "p1", "token": "wrong", "page_origin": LOOPBACK_ORIGIN})
    await asyncio.sleep(0.05)
    probe.record("wrong profile token closes 4401", (bad_ws.closed or (None,))[0] == 4401, str(bad_ws.closed))
    bad_task.cancel()

    hello = {"type": "hello", "profile_id": "p1", "token": PROFILE_TOKEN,
             "page_origin": LOOPBACK_ORIGIN, "script_version": "2.3.1"}
    good_ws, good_task = await _open(hub, hello)
    probe.record("valid token receives config frame", bool(good_ws.sent) and good_ws.sent[0].get("type") == "config",
                 str(good_ws.sent[0].get("commands")) if good_ws.sent else "no frame")
    probe.record("config frame carries no token", PROFILE_TOKEN not in json.dumps(good_ws.sent))

    other_hub = ConnectorHub()
    other_hub.register("p4", registration())
    evil_ws, evil_task = await _open(other_hub, {**hello, "profile_id": "p4", "page_origin": "https://evil.example"})
    await asyncio.sleep(0.05)
    probe.record("page origin outside the allow-list closes 4401", (evil_ws.closed or (None,))[0] == 4401, str(evil_ws.closed))
    evil_task.cancel()

    # --- human-check stop semantics -------------------------------------------------------
    await hub._on_message(hub.profiles["p1"], {"type": "status", "status": "needs_human", "reason": "captcha iframe"})
    state = hub.profiles["p1"]
    probe.record("needs_human sets the profile status", state.status == "needs_human" and state.health() == "red",
                 f"{state.status}/{state.health()}/{state.needs_human_reason}")

    try:
        await hub.command("p1", "submit", {"text": "hello"})
        probe.record("submit refused while needs_human", False, "accepted")
    except ConnectorError as exc:
        probe.record("submit refused while needs_human", exc.code == "needs_human" and exc.http_status == 409,
                     f"{exc.code}/{exc.http_status}")

    read_task = asyncio.create_task(hub.command("p1", "read_last_reply", None, timeout=0.2))
    await asyncio.sleep(0.05)
    commands_sent = [frame for frame in good_ws.sent if frame.get("type") == "command"]
    probe.record("read_last_reply still allowed while needs_human",
                 bool(commands_sent) and commands_sent[-1].get("command") == "read_last_reply",
                 str(commands_sent[-1]) if commands_sent else "no command frame")
    read_task.cancel()

    hub.reset("p1")
    probe.record("reset() clears needs_human", hub.profiles["p1"].status != "needs_human", hub.profiles["p1"].status)

    # --- closed command allow-list and input validation ------------------------------------
    for bad_command in ("eval_js", "click_captcha", "solve", "read_cookies"):
        try:
            hub._validate_command(hub.profiles["p1"], bad_command, {})
            probe.record(f"command '{bad_command}' refused", False, "accepted")
        except ConnectorError as exc:
            probe.record(f"command '{bad_command}' refused", exc.code == "unknown_command" and exc.http_status == 422,
                         f"{exc.code}/{exc.http_status}")

    for name, command, args in (
        ("repo format validated", "submit", {"text": "x", "repo": "../../etc/passwd"}),
        ("oversized prompt refused", "submit", {"text": "x" * 200_001}),
        ("new_session URL restricted to allowed origins", "new_session", {"url": "https://elsewhere.example/agent"}),
    ):
        try:
            hub._validate_command(hub.profiles["p1"], command, args)
            probe.record(name, False, "accepted")
        except ConnectorError as exc:
            probe.record(name, True, f"{exc.code}/{exc.http_status}")

    good_ws_task_cancel = good_task
    good_ws_task_cancel.cancel()


def _probe_http_surface(probe: Probe) -> None:
    from fastapi.testclient import TestClient

    from bridge.server import create_app

    auth = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}
    app = create_app(connector_state_file=None)
    with TestClient(app) as client:
        health = client.get("/health", headers=auth)
        probe.record("/health with bearer", health.status_code == 200, str(health.status_code))
        probe.record("/health reports connector_profiles", "connector_profiles" in health.json(),
                     str(health.json().get("connector_profiles")))
        probe.record("/health without bearer refused", client.get("/health").status_code == 401,
                     str(client.get("/health").status_code))
        probe.record("GET /v1/connector/profiles without token refused",
                     client.get("/v1/connector/profiles").status_code == 401)
        probe.record("GET /v1/connector/profiles with wrong token refused",
                     client.get("/v1/connector/profiles", headers={"Authorization": "Bearer nope"}).status_code == 401)
        listed = client.get("/v1/connector/profiles", headers=auth)
        probe.record("GET /v1/connector/profiles with correct token allowed",
                     listed.status_code == 200 and "real_arena_allowed" in listed.json(), str(listed.status_code))
        registered = client.put("/v1/connector/profiles/probe-profile",
                                json={"token_sha256": PROFILE_HASH, "allowed_origins": [LOOPBACK_ORIGIN]}, headers=auth)
        probe.record("PUT profile registers", registered.status_code == 200, str(registered.status_code))
        probe.record("invalid token hash rejected",
                     client.put("/v1/connector/profiles/probe-bad",
                                json={"token_sha256": "zz", "allowed_origins": [LOOPBACK_ORIGIN]},
                                headers=auth).status_code == 422)
        real = client.put("/v1/connector/profiles/probe-real",
                          json={"token_sha256": PROFILE_HASH, "allowed_origins": ["https://arena.ai"], "real_enabled": True},
                          headers=auth)
        probe.record("real origin refused over HTTP", real.status_code == 403, str(real.status_code))

    os.environ.pop("ARENA_BRIDGE_TOKEN", None)
    app_without_token = create_app(connector_state_file=None)
    with TestClient(app_without_token) as client:
        probe.record("no ARENA_BRIDGE_TOKEN -> 503 fail closed",
                     client.get("/v1/connector/profiles").status_code == 503,
                     str(client.get("/v1/connector/profiles").status_code))


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe AATM's Arena connector behaviour (read-only).")
    parser.add_argument("--verbose", action="store_true", help="print details for passing probes too")
    parser.add_argument("--repo", default=os.environ.get("AATM_REPO", ""), help="path to an AATM checkout")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser() if args.repo else None
    if repo is None or not (repo / "bridge" / "connector.py").is_file():
        print("AATM_REPO must point at an AATM checkout that contains bridge/connector.py", file=sys.stderr)
        return 2

    sys.path.insert(0, str(repo))
    os.environ["ARENA_BRIDGE_TOKEN"] = BRIDGE_TOKEN
    os.environ.pop("ARENA_CONNECTOR_ENABLED", None)  # the probe expects real Arena to be off
    os.chdir(repo)

    probe = Probe(verbose=args.verbose)
    asyncio.run(_probe_connector(probe))
    _probe_http_surface(probe)
    return probe.summary()


if __name__ == "__main__":
    sys.exit(main())
