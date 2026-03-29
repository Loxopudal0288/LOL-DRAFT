# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import uuid

app = FastAPI(title="LoL Draft")

# === ОФИЦИАЛЬНЫЙ ПОРЯДОК ДРАФТА ===
DRAFT_ORDER = [
    # Ban Phase 1 (6)
    {"action": "ban", "team": "blue"},
    {"action": "ban", "team": "red"},
    {"action": "ban", "team": "blue"},
    {"action": "ban", "team": "red"},
    {"action": "ban", "team": "blue"},
    {"action": "ban", "team": "red"},
    # Pick Phase 1 (6)
    {"action": "pick", "team": "blue"},
    {"action": "pick", "team": "red"},
    {"action": "pick", "team": "red"},
    {"action": "pick", "team": "blue"},
    {"action": "pick", "team": "blue"},
    {"action": "pick", "team": "red"},
    # Ban Phase 2 (4)
    {"action": "ban", "team": "blue"},
    {"action": "ban", "team": "red"},
    {"action": "ban", "team": "blue"},
    {"action": "ban", "team": "red"},
    # Pick Phase 2 (4)
    {"action": "pick", "team": "red"},
    {"action": "pick", "team": "blue"},
    {"action": "pick", "team": "blue"},
    {"action": "pick", "team": "red"},
]

def get_current_phase(action_index: int) -> str:
    if action_index < 6:
        return "banning_1"
    elif action_index < 12:
        return "picking_1"
    elif action_index < 16:
        return "banning_2"
    elif action_index < 20:
        return "picking_2"
    else:
        return "finished"

# === Хранилище ===
drafts = {}

# === Статика ===
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("app/static/index.html")

@app.get("/join")
async def get_join():
    return FileResponse("app/static/join.html")

@app.get("/draft")
async def get_draft():
    return FileResponse("app/static/draft.html")

# === Модели ===
class CreateDraftRequest(BaseModel):
    team_name: str
    side: Literal["blue", "red"]

class JoinRequest(BaseModel):
    team_name: str

class ActionRequest(BaseModel):
    champion: str

# === API ===
@app.post("/api/draft")
async def create_draft(req: CreateDraftRequest):
    draft_id = str(uuid.uuid4())[:8]
    drafts[draft_id] = {
        "team_blue_name": req.team_name if req.side == "blue" else None,
        "team_red_name": req.team_name if req.side == "red" else None,
        "ready_blue": False,
        "ready_red": False,
        "phase": "lobby",
        "current_action_index": 0,
        "bans": [],
        "picks_blue": [None] * 5,
        "picks_red": [None] * 5,
    }
    return {"draft_id": draft_id, "side": req.side}

@app.post("/api/draft/{draft_id}/join")
async def join_draft(draft_id: str, req: JoinRequest):
    if draft_id not in drafts:
        raise HTTPException(404, "Draft not found")
    state = drafts[draft_id]
    if state["team_blue_name"] and state["team_red_name"]:
        raise HTTPException(400, "Draft is full")

    if state["team_blue_name"] is None:
        state["team_blue_name"] = req.team_name
        assigned_side = "blue"
    else:
        state["team_red_name"] = req.team_name
        assigned_side = "red"

    state["phase"] = "ready_check"
    return {"status": "ok", "assigned_side": assigned_side}

@app.get("/api/draft/{draft_id}")
async def get_state(draft_id: str):
    if draft_id not in drafts:
        raise HTTPException(404, "Draft not found")
    state = drafts[draft_id]
    if state["phase"] not in ("lobby", "ready_check"):
        state["phase"] = get_current_phase(state["current_action_index"])
        if state["phase"] != "finished":
            state["current_turn"] = DRAFT_ORDER[state["current_action_index"]]["team"]
        else:
            state["current_turn"] = None
    return state

@app.post("/api/draft/{draft_id}/ready")
async def set_ready(draft_id: str, request: Request):
    body = await request.json()
    team = body.get("team")
    if team not in ("blue", "red"):
        raise HTTPException(400, "Invalid team")
    state = drafts[draft_id]
    state[f"ready_{team}"] = True

    if state["ready_blue"] and state["ready_red"]:
        state["phase"] = "banning_1"
        state["current_turn"] = "blue"

    return {"status": "ok"}

@app.post("/api/draft/{draft_id}/action")
async def perform_action(draft_id: str, action: ActionRequest):
    if draft_id not in drafts:
        raise HTTPException(404, "Draft not found")
    state = drafts[draft_id]

    if state["phase"] in ("lobby", "ready_check", "finished"):
        raise HTTPException(400, "Not in draft phase")

    current_step = DRAFT_ORDER[state["current_action_index"]]
    expected_team = current_step["team"]
    expected_action = current_step["action"]

    # 🔥 Защита от дублей
    if action.champion in state["bans"]:
        raise HTTPException(400, "Champion already banned")
    if action.champion in state["picks_blue"] or action.champion in state["picks_red"]:
        raise HTTPException(400, "Champion already picked")

    if expected_action == "ban":
        if len(state["bans"]) >= 10:
            raise HTTPException(400, "Max bans reached")
        state["bans"].append(action.champion)
    else:  # pick
        picks = state["picks_blue"] if expected_team == "blue" else state["picks_red"]
        slot = next((i for i, p in enumerate(picks) if p is None), -1)
        if slot == -1:
            raise HTTPException(400, "No free pick slot")
        picks[slot] = action.champion

    state["current_action_index"] += 1
    if state["current_action_index"] >= len(DRAFT_ORDER):
        state["phase"] = "finished"
        state["current_turn"] = None

    return {"status": "ok"}