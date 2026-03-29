from pydantic import BaseModel
from typing import List, Optional, Literal

class DraftState(BaseModel):
    # Названия команд
    team_blue_name: Optional[str] = None
    team_red_name: Optional[str] = None

    # Готовность
    ready_blue: bool = False
    ready_red: bool = False

    # Фазы и очередь
    phase: Literal[
        "lobby",           # ожидание второй команды
        "ready_check",     # обе команды присоединились, ждём "готов"
        "banning_1",       # 1-я фаза банов (3+3)
        "picking_1",       # 1-я фаза пиков (1-2-2-1)
        "banning_2",       # 2-я фаза банов (2+2)
        "picking_2",       # 2-я фаза пиков (1-2-1)
        "finished"
    ] = "lobby"

    current_turn: Literal["blue", "red"] = "blue"

    # Баны (максимум 10)
    bans: List[str] = []

    # Пики: по 5 на команду
    picks_blue: List[Optional[str]] = [None] * 5
    picks_red: List[Optional[str]] = [None] * 5

    # Индексы для отслеживания прогресса
    ban_index: int = 0          # сколько уже забанено (0..10)
    pick_index: int = 0         # сколько уже выбрано (0..10)

    # Таймеры (опционально можно хранить, но лучше управлять на фронтенде)
    # Для MVP — не храним, фронтенд сам запускает таймер при получении хода

class CreateDraftRequest(BaseModel):
    team_name: str
    side: Literal["blue", "red"]

class JoinRequest(BaseModel):
    team_name: str

class ActionRequest(BaseModel):
    champion: str
    action_type: Literal["ban", "pick"]