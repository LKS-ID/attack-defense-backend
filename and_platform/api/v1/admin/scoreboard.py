from and_platform.models import Teams
from and_platform.core.score import get_leaderboard
from flask import Blueprint, jsonify
from datetime import datetime

scoreboard_blueprint = Blueprint("admin_scoreboard", __name__, url_prefix="/scoreboard")


@scoreboard_blueprint.get("/")
def get_admin_scoreboard():
    leaderboard = get_leaderboard()
    return jsonify(status="success", data=leaderboard)
