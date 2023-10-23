# from and_platform.models import db, Challenges, Teams, Services, Servers, CheckerQueues, CheckerVerdict
# from and_platform.core.config import get_config
# from and_platform.core.service import do_provision, do_manage, do_start, do_stop, do_patch, do_restart, do_reset, get_service_path, get_service_metadata
# from flask import Blueprint, jsonify, request, views, current_app as app
# from sqlalchemy import delete

# import os

# service_blueprint = Blueprint("service", __name__, url_prefix="/services")

# @service_blueprint.post("/provision")
# def service_provision():
#     req = request.get_json()
#     provision_challs = req.get("challenges")
#     provision_teams = req.get("teams")
#     if not provision_challs or not provision_teams:
#         return jsonify(status="failed", message="invalid body."), 400
    
#     teams_query = Teams.query
#     challs_query = Challenges.query
#     if isinstance(provision_teams, list):
#         teams_query = teams_query.where(Teams.id.in_(provision_teams))
#     if isinstance(provision_challs, list):
#         challs_query = challs_query.where(Challenges.id.in_(provision_challs))
    
#     teams = teams_query.all()
#     challenges = challs_query.all()
#     if (isinstance(provision_teams, list) and len(teams) != len(provision_teams)) \
#         or (isinstance(provision_challs, list) and len(challenges) != len(provision_challs)):
#         return jsonify(status="failed", message="challenge or team cannot be found."), 400
    
#     server_mode = get_config("SERVER_MODE")
#     for team in teams:
#         for chall in challenges:
#             if server_mode == "private": server = team.server
#             else: server = chall.server
            
#             try:
#                 services = do_provision(team, chall, server)
#             except Exception as ex:
#                 error_msg = f"error when provisioning challenge id={chall.id} for team id={team.id}: {ex}"
#                 app.logger.error(ex, exc_info=True)
#                 return jsonify(status="failed", message=error_msg), 500
            
#             # Remove old data
#             db.session.execute(
#                 delete(Services).filter(Services.team_id == team.id, Services.challenge_id == chall.id)
#             )
#             db.session.add_all(services)
#             db.session.commit()
    
#     return jsonify(status="success", message="successfully provision all requested services.")

# @service_blueprint.post("/manage")
# def service_manage():
#     req = request.get_json()
#     provision_challs = req.get("challenges")
#     provision_teams = req.get("teams")
#     action = req.get("action")
#     if not provision_challs or not provision_teams or \
#         not action or action not in ["start", "stop", "restart", "reset"]:
#         return jsonify(status="failed", message="invalid body."), 400
    
#     teams_query = db.session.query(Teams.id)
#     challs_query = db.session.query(Challenges.id)
#     if isinstance(provision_teams, list):
#         teams_query = teams_query.where(Teams.id.in_(provision_teams))
#     if isinstance(provision_challs, list):
#         challs_query = challs_query.where(Challenges.id.in_(provision_challs))
    
#     teams = teams_query.all()
#     challenges = challs_query.all()
#     if (isinstance(provision_teams, list) and len(teams) != len(provision_teams)) \
#         or (isinstance(provision_challs, list) and len(challenges) != len(provision_challs)):
#         return jsonify(status="failed", message="challenge or team cannot be found."), 400

#     team_ids = [elm[0] for elm in teams]
#     chall_ids = [elm[0] for elm in challenges]

#     for team_id in team_ids:
#         for chall_id in chall_ids:
#             do_manage(action, team_id, chall_id)

#     return jsonify(status="success", message=f"successfully {action} all requested services.")


# @service_blueprint.get("/")
# def admin_service_getall():
#     response = {}
#     services = Services.query.order_by(Services.challenge_id, Services.team_id, Services.order).all()
#     for service in services:
#         resp_tmp = response.get(service.challenge_id, {})
#         team_svc_tmp = resp_tmp.get(service.team_id, [])
#         team_svc_tmp.append(service.address)
        
#         resp_tmp[service.team_id] = team_svc_tmp
#         response[service.challenge_id] = resp_tmp
#     return jsonify(status="success", data=response)


# @service_blueprint.post("/<int:challenge_id>/teams/<int:team_id>/patch")
# def admin_service_patch(challenge_id, team_id):
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404
    
#     patch_dest = os.path.join(get_service_path(team_id, challenge_id), "patch", "service.patch")
#     patch_file = request.files.get("patchfile")
#     if not patch_file:
#         return jsonify(status="failed", message="patch file is missing."), 400    
#     patch_file.save(patch_dest)
    
#     do_patch(
#         team_id,
#         challenge_id,
#         Servers.get_server_by_mode(get_config("SERVER_MODE"), team_id, challenge_id)
#     )

#     return jsonify(status="success", message="patch submitted.")

# @service_blueprint.post("/<int:challenge_id>/teams/<int:team_id>/manage")
# def admin_service_manage(challenge_id, team_id):
#     confirm_data: dict = request.get_json()
#     action = confirm_data.get("action")
#     if not action or action not in ["start", "stop", "restart", "reset"]:
#         return jsonify(status="bad request", message="invalid action"), 400
    
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404

#     do_manage(action, team_id, challenge_id)

#     return jsonify(status="success", message=f"{action} request submitted.")


# @service_blueprint.post("/<int:challenge_id>/teams/<int:team_id>/restart")
# def admin_service_restart(challenge_id, team_id):
#     confirm_data: dict = request.get_json()
#     if not confirm_data.get("confirm"):
#         return jsonify(status="bad request", message="action not confirmed"), 400
    
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404
    
#     do_restart(
#         team_id,
#         challenge_id,
#         Servers.get_server_by_mode(get_config("SERVER_MODE"), team_id, challenge_id)
#     )
    
#     return jsonify(status="success", message="restart request submitted.")


# @service_blueprint.post("/<int:challenge_id>/teams/<int:team_id>/reset")
# def admin_service_reset(challenge_id, team_id):
#     confirm_data: dict = request.get_json()
#     if not confirm_data.get("confirm"):
#         return jsonify(status="bad request", message="action not confirmed"), 400
    
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404
    
#     do_reset(
#         team_id,
#         challenge_id,
#         Servers.get_server_by_mode(get_config("SERVER_MODE"), team_id, challenge_id)
#     )
    
#     return jsonify(status="success", message="reset request submitted.")

# @service_blueprint.get("/<int:challenge_id>/teams/<int:team_id>/status")
# def admin_service_getstatus(challenge_id, team_id):
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404

#     checker_result = CheckerQueues.query.filter(
#         CheckerQueues.challenge_id == challenge_id,
#         CheckerQueues.team_id == team_id,
#         CheckerQueues.result.in_([CheckerVerdict.FAULTY, CheckerVerdict.VALID]),
#     ).order_by(CheckerQueues.id.desc()).first()
    
#     response = CheckerVerdict.VALID.value
#     if checker_result:
#         response = checker_result.result.value
#     return jsonify(status="success", data=response)
  
# @service_blueprint.get("/<int:challenge_id>/teams/<int:team_id>/meta")
# def admin_service_getmeta(challenge_id, team_id):
#     if not Services.is_teamservice_exist(team_id, challenge_id):
#         return jsonify(status="not found", message="service not found."), 404

#     response = get_service_metadata(
#         team_id,
#         challenge_id,
#         Servers.get_server_by_mode(get_config("SERVER_MODE"), team_id, challenge_id)
#     )
#     return jsonify(status="success", data=response)
