from ailurus.models import (
    db,
    Flag,
    Team,
    Challenge,
)
from ailurus.utils.config import get_config, set_config
from datetime import datetime, timezone
from secrets import choice
from string import ascii_lowercase, digits
from sqlalchemy.exc import IntegrityError
import json

def update_paused_status(newvalue: bool | str):
    if isinstance(newvalue, str):
        newvalue = json.loads(newvalue)
    
    if get_config("IS_CONTEST_PAUSED") and not newvalue:
        tick_duration = get_config("TICK_DURATION")
        last_tick_change = get_config("LAST_TICK_CHANGE")
        last_paused = get_config("LAST_PAUSED")
        
        if last_tick_change != None and last_paused != None:
            diff_minutes = last_paused - last_tick_change
            pivot_last_tick_change = datetime.now(timezone.utc).replace(microsecond=0, second=0) - diff_minutes
            set_config("LAST_TICK_CHANGE", pivot_last_tick_change.isoformat())

        set_config("IS_CONTEST_PAUSED", "false")
    elif not get_config("IS_CONTEST_PAUSED") and newvalue:
        time_now = datetime.now(timezone.utc).replace(microsecond=0, second=0)
        set_config("LAST_PAUSED", time_now.isoformat())
        set_config("IS_CONTEST_PAUSED", "true")

def calculate_submission_score(attacker: Team, defender: Team, challenge: Challenge, flag: Flag):
    return 1.0

def generate_flag(current_round: int, current_tick: int, team: Team, challenge: Challenge, order: int = 0) -> Flag:
    CHARSET = ascii_lowercase + digits
    flag_format = get_config("FLAG_FORMAT")
    flag_rndlen = get_config("FLAG_RNDLEN", 0)
    
    flag_format = flag_format.replace("__ROUND__", str(current_round))
    
    SUBRULE = {
        "__TEAM__": str(team.id),
        "__PROBLEM__": str(challenge.id),
        "__RANDOM__": "".join([choice(CHARSET) for _ in range(flag_rndlen)]),
    }
    new_flag = flag_format
    for k, v in SUBRULE.items():
        new_flag = new_flag.replace(k, v)
            
    return Flag(
        team_id = team.id,
        challenge_id = challenge.id,
        round = current_round,
        tick = current_tick,
        value = new_flag,
        order = order
    )

def generate_or_get_flag(current_round: int, current_tick: int, team: Team, challenge: Challenge, order: int = 0):
    try:
        flag = generate_flag(current_round, current_tick, team, challenge, order)
        db.session.add(flag)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        flag = db.session.query(Flag).filter_by(
            team_id=team.id,
            challenge_id=challenge.id,
            round=current_round,
            tick=current_tick,
            order=order
        ).first()
    
    return flag