"""Read stored treadmill workouts and manually finalize current session (admin only)."""
from __future__ import annotations

import asyncio
import base64
import re
from datetime import datetime

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .fit_export import export_fit, PROFILES, validate_fit
from .workout import write_metadata


@websocket_api.require_admin
@websocket_api.websocket_command({
    probatio.Required("type"): "homefitnesscode/workouts",
    probatio.Required("entry_id"): str,
    probatio.Required("action"): str,
    probatio.Optional("hr_source"): str,
    probatio.Optional("session_id"): str,
    probatio.Optional("profile"): str,
    probatio.Optional("name"): str,
    probatio.Optional("idle_seconds"): int,
})
@websocket_api.async_response
async def ws_workouts(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if state is None or not hasattr(state, "workouts"):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "No workout journal for this equipment")
        return
    if msg["action"] not in ("status", "save", "hr_source", "fit_download", "rename", "fit_settings", "keep_paused"):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Unknown workout command")
        return
    journal = state.workouts
    if msg["action"] == "fit_settings":
        try:
            await journal.set_fit_profile(msg.get("profile"), msg.get("idle_seconds"))
        except (OSError, ValueError, TypeError) as err:
            connection.send_error(msg["id"], "fit_error", str(err)[:160])
            return
        connection.send_result(msg["id"], journal.status())
        return
    if msg["action"] == "rename":
        session = next((x for x in journal.history if x.get("id") == msg.get("session_id")), None)
        if not session:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Unknown session")
            return
        try:
            updated = await asyncio.to_thread(_rename_session, journal.directory, session, msg.get("name", ""))
        except (OSError, ValueError, TypeError) as err:
            connection.send_error(msg["id"], "rename_error", str(err)[:160])
            return
        session.update(updated)
        connection.send_result(msg["id"], journal.status())
        return
    if msg["action"] == "fit_download":
        session = next((x for x in journal.history if x.get("id") == msg.get("session_id")), None)
        profile = msg.get("profile", journal.fit_profile)
        if not session or not session.get("complete") or profile not in PROFILES:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Invalid session or profile")
            return
        try:
            result = await asyncio.to_thread(_download_fit, journal.directory, session, profile, msg.get("name", session.get("session_name", "")))
        except (OSError, ValueError, TypeError) as err:
            connection.send_error(msg["id"], "fit_error", str(err)[:160])
            return
        connection.send_result(msg["id"], result)
        return
    if msg["action"] == "hr_source":
        source = msg.get("hr_source", "")
        band = hass.data.get(DOMAIN, {}).get(source)
        if source and (band is None or band.data.get("machine_type") != "heart_rate_monitor"):
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Invalid heart rate source")
            return
        if journal.active:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Heart rate source locked during workout")
            return
        state.hr_preference = source
    elif msg["action"] == "keep_paused":
        journal.keep_paused()
    elif msg["action"] == "save":
        journal.close("manual")
    else:
        journal.tick()
    connection.send_result(msg["id"], journal.status())


def _rename_session(directory, session, name):
    label = name.strip()[:80] or "Löpband"
    if any(ord(c) < 32 for c in label):
        raise ValueError("Invalid session name")
    path = directory / (session["id"] + ".summary.json")
    if path.resolve().parent != directory.resolve():
        raise ValueError("Invalid session path")
    updated = dict(session, session_name=label)
    write_metadata(path, updated)
    return updated


def _download_fit(directory, session, profile, name):
    """Export a named download without modifying the archived original."""
    from tempfile import TemporaryDirectory
    from pathlib import Path
    raw = directory / session["file"]
    if raw.resolve().parent != directory.resolve() or raw.suffix != ".jsonl":
        raise ValueError("Invalid journal path")
    label = re.sub(r"[^\w -]", "_", name.strip(), flags=re.UNICODE)[:60].strip(" _-") or "Löpband"
    day = datetime.fromisoformat(session["started_at"]).astimezone().strftime("%Y%m%d")
    suffix = session["id"].rsplit("-", 1)[-1]
    filename = f"{day}_{label.replace(' ', '_')}_{suffix}.fit"
    with TemporaryDirectory() as temp:
        target = Path(temp) / "activity.fit"
        if raw.is_file():
            export_fit(raw, session, profile=profile, target=target)
            data = target.read_bytes()
        elif profile == session.get("fit_profile", "native"):
            archived = raw.with_suffix(".fit")
            if archived.resolve().parent != directory.resolve():
                raise ValueError("Invalid FIT path")
            data = archived.read_bytes()
        else:
            raise ValueError("Raw data unavailable: export archived profile instead")
        if not validate_fit(data):
            raise ValueError("FIT integrity check failed")
    return {"filename": filename, "base64": base64.b64encode(data).decode("ascii")}


def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_workouts)
