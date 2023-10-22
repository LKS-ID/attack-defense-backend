import math
from and_platform.cache import cache
from and_platform.models import (
    db,
    ScorePerTicks,
    Submissions,
    CheckerQueues,
    Flags,
    Challenges,
    Teams,
    CheckerVerdict,
)
from typing import List, TypedDict
from sqlalchemy.sql import func
from datetime import datetime

TeamID = int
ChallID = int


class TeamData(TypedDict):
    captured: list[TeamID]
    stolen: int
    sla: dict[ChallID, float]


class SLAData(TypedDict):
    faulty: int
    valid: int


@cache.memoize()
def calculate_score_tick(round: int, tick: int):
    # Prevent duplicate data
    ScorePerTicks.query.filter(
        ScorePerTicks.round == round, ScorePerTicks.tick == tick
    ).delete()
    
    teams = Teams.query.all()
    challenges = Challenges.query.all()
    for challenge in challenges:
        for team in teams:
            num_user_flag_captured = db.session.query(Submissions.id).join(Flags, Flags.id == Submissions.flag_id).filter(
                Submissions.team_id == team.id,
                Submissions.challenge_id == challenge.id,
                Submissions.tick == tick,
                Submissions.round == round,
                Flags.subid == 1,
            ).count()
            num_root_flag_captured = db.session.query(Submissions.id).join(Flags, Flags.id == Submissions.flag_id).filter(
                Submissions.team_id == team.id,
                Submissions.challenge_id == challenge.id,
                Submissions.tick == tick,
                Submissions.round == round,
                Flags.subid == 2,
            ).count()

            num_stolen = db.session.query(Submissions.id).join(Flags, Flags.id == Submissions.flag_id).filter(
                Submissions.challenge_id == challenge.id,
                Submissions.team_id != team.id,
                Submissions.tick == tick,
                Submissions.round == round,
                Flags.team_id == team.id,
            ).count()

            num_faulty = db.session.query(
                CheckerQueues.id
            ).filter(
                CheckerQueues.challenge_id == challenge.id,
                CheckerQueues.team_id == team.id,
                CheckerQueues.round == round,
                CheckerQueues.tick == tick,
                CheckerQueues.result == CheckerVerdict.FAULTY,
            ).count()

            num_valid = db.session.query(
                CheckerQueues.id
            ).filter(
                CheckerQueues.challenge_id == challenge.id,
                CheckerQueues.team_id == team.id,
                CheckerQueues.round == round,
                CheckerQueues.tick == tick,
                CheckerQueues.result == CheckerVerdict.VALID,
            ).count()

            attack_score = num_root_flag_captured * 100 + num_user_flag_captured * 50
            defense_score = num_faulty * (-50) + num_valid * 90
            if num_stolen == 0:
                defense_score += 100
            sla = 1
            if num_valid + num_faulty != 0:
                sla = num_valid / (num_faulty + num_valid)

            scoretick = ScorePerTicks(
                round = round,
                tick = tick,
                challenge_id = challenge.id,
                team_id = team.id,
                attack_score = attack_score,
                defense_score = defense_score,
                sla = sla,
            )
            db.session.add(scoretick)   
    db.session.commit()


class TeamChallengeScore(TypedDict):
    challenge_id: int
    flag_captured: int
    flag_stolen: int
    attack: float
    defense: float
    sla: float


class TeamScore(TypedDict):
    team_id: int
    total_score: float
    challenges: List[TeamChallengeScore]
    position: int


@cache.memoize()
def get_total_stolen(
    team_id: int,
    challenge_id: int,
    current_round: int,
    current_tick: int,
) -> float:
    return (
        db.session.query(
            Submissions.id,
        )
        .join(Flags, Flags.id == Submissions.flag_id)
        .filter(
            Submissions.round == current_round,
            Submissions.tick == current_tick,
            Submissions.verdict == True,
            Flags.team_id == team_id,
            Submissions.team_id != team_id,
            Submissions.challenge_id == challenge_id,
        )
        .count()
    )


@cache.memoize()
def get_overall_team_challenge_score(
    team_id: int, challenge_id: int, before: datetime | None = None
) -> TeamChallengeScore:
    flag_captured_filters = [
        Submissions.verdict == True,
        Submissions.team_id == team_id,
        Flags.team_id != team_id,
        Submissions.challenge_id == challenge_id,
    ]
    flag_stolen_filters = [
        Submissions.verdict == True,
        Flags.team_id == team_id,
        Submissions.team_id != team_id,
        Submissions.challenge_id == challenge_id,
    ]
    if before:
        flag_captured_filters.append(Submissions.time_created < before)
        flag_stolen_filters.append(Submissions.time_created < before)

    all_flag_captured = (
        db.session.query(
            Submissions.id,
            Flags.team_id,
        )
        .join(Flags, Flags.id == Submissions.flag_id)
        .filter(*flag_captured_filters)
        .count()
    )

    all_flag_stolen = (
        db.session.query(
            Submissions.id,
            Submissions.team_id,
        )
        .join(Flags, Flags.id == Submissions.flag_id)
        .filter(*flag_stolen_filters)
        .count()
    )

    score_filters = [
        ScorePerTicks.challenge_id == challenge_id,
        ScorePerTicks.team_id == team_id,
    ]
    if before:
        score_filters.append(ScorePerTicks.time_created < before)

    scores = (
        db.session.query(
            func.avg(ScorePerTicks.sla),
            func.sum(ScorePerTicks.attack_score),
            func.sum(ScorePerTicks.defense_score),
        )
        .filter(*score_filters)
        .group_by(ScorePerTicks.challenge_id, ScorePerTicks.team_id)
        .first()
    )

    return TeamChallengeScore(
        challenge_id=challenge_id,
        flag_captured=all_flag_captured,
        flag_stolen=all_flag_stolen,
        sla=scores[0] if scores and len(scores) == 3 else 1,
        attack=scores[1] if scores and len(scores) == 3 else 0,
        defense=scores[2] if scores and len(scores) == 3 else 0,
    )


@cache.memoize()
def get_overall_team_score(team_id: int, before: datetime | None = None) -> TeamScore:
    challs = Challenges.query.all()
    team_score = TeamScore(
        team_id=team_id, position=-1, total_score=0, challenges=list()
    )
    for chall in challs:
        tmp = get_overall_team_challenge_score(team_id, chall.id, before)
        team_score["total_score"] += tmp["attack"] + tmp["defense"]
        team_score["challenges"].append(tmp)
    return team_score


def get_leaderboard(before: datetime | None = None):
    teams = Teams.query.all()
    scoreboard: list[TeamScore] = []
    for team in teams:
        team_score = get_overall_team_score(team.id, before)
        tmp_chall = {}
        for chall in team_score["challenges"]:
            chall_id = chall["challenge_id"]
            chall.pop("challenge_id")
            tmp_chall[chall_id] = chall

        team_score.pop("team_id")
        team_score.update({
            "id": team.id,
            "name": team.name,
            "challenges": tmp_chall
        })

        scoreboard.append(team_score)

    scoreboard_sort = sorted(scoreboard, key=lambda x: x["total_score"], reverse=True)
    scoreboard_sort[0]["rank"] = 1
    for i in range(1, len(scoreboard_sort)):
        scoreboard_sort[i]["rank"] = scoreboard_sort[i - 1]["rank"]
        if scoreboard_sort[i]["total_score"] != scoreboard_sort[i - 1]["total_score"]:
            scoreboard_sort[i]["rank"] += 1
    return scoreboard_sort
