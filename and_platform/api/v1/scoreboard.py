from and_platform.cache import cache
from and_platform.models import Teams
from and_platform.core.config import get_config
from and_platform.core.score import get_leaderboard
from flask import Blueprint, jsonify
from datetime import datetime

public_scoreboard_blueprint = Blueprint("public_scoreboard", __name__, url_prefix="/scoreboard")


@public_scoreboard_blueprint.get("/")
@cache.cached(timeout=60)
def get_public_scoreboard():
    freeze_time = get_config("FREEZE_TIME")
    is_freeze = freeze_time and datetime.now().astimezone() > freeze_time
    leaderboard = get_leaderboard(freeze_time)
    return jsonify(status="success", is_freeze=is_freeze, data=leaderboard)
