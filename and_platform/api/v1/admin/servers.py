from and_platform.models import db, Servers, Teams, Challenges, CheckerQueues, CheckerVerdict
from and_platform.api.helper import convert_model_to_dict
from and_platform.core.server import do_server_provision
from flask import Blueprint, jsonify, request

servers_blueprint = Blueprint("servers_manager", __name__, url_prefix="/servers")

@servers_blueprint.get("/")
def get_all_servers():
    servers = Servers.query.all()
    servers = convert_model_to_dict(servers)

    return jsonify(status="success", data=servers), 200

@servers_blueprint.get("/<int:server_id>")
def get_by_id(server_id):
    server = Servers.query.filter_by(id=server_id).first()

    if server is None:
        return jsonify(status="not found", message="server not found"), 404
    server = convert_model_to_dict(server)

    return jsonify(status="success", data=server), 200

@servers_blueprint.post("/provision")
def provision_all_servers():
    req = request.get_json()
    provision_challs = req.get("challenges")
    provision_teams = req.get("teams")
    if not provision_challs or not provision_teams:
        return jsonify(status="failed", message="invalid body."), 400
    
    teams_query = Teams.query
    challs_query = Challenges.query
    if isinstance(provision_teams, list):
        teams_query = teams_query.where(Teams.id.in_(provision_teams))
    if isinstance(provision_challs, list):
        challs_query = challs_query.where(Challenges.id.in_(provision_challs))
    
    teams = teams_query.all()
    challenges = challs_query.all()
    if (isinstance(provision_teams, list) and len(teams) != len(provision_teams)) \
        or (isinstance(provision_challs, list) and len(challenges) != len(provision_challs)):
        return jsonify(status="failed", message="challenge or team cannot be found."), 400
    
    for team in teams:
        for chall in challenges:
            do_server_provision(team.id, chall.id)
    return jsonify(status="success", message="provisioning server is on progress"), 200

@servers_blueprint.get("/<int:team_id>/status")
def admin_server_getstatus(team_id):
    team = Teams.query.filter_by(id=team_id).first()
    if team is None:
        return jsonify(status="not found", message="team not found"), 404
    
    checker_result = CheckerQueues.query.filter(
        CheckerQueues.team_id == team_id,
        CheckerQueues.result.in_([CheckerVerdict.FAULTY, CheckerVerdict.VALID, CheckerVerdict.FLAG_MISSING]),
    ).order_by(CheckerQueues.id.desc()).first()
    
    # If the checker_result return empty data
    response = CheckerVerdict.VALID.value
    if checker_result:
        response = checker_result.result.value
    return jsonify(status="success", data=response)
  

# @servers_blueprint.post("/")
# def add_server():
#     req_body = request.get_json()

#     if Servers.is_exist_with_host(req_body.get("host", "127.0.0.1")):
#         return jsonify(status="failed", message="server host must be unique."), 400
#     try:
#         new_server = Servers(
#             host = req_body["host"],
#             sshport = req_body["sshport"],
#             username = req_body["username"],
#             auth_key = req_body["auth_key"]
#         )
#     except KeyError:
#         return jsonify(status="failed", message="missing required attributes.")
    
#     db.session.add(new_server)
#     db.session.commit()
#     db.session.refresh(new_server) # update the object with newest commit
#     new_server = convert_model_to_dict(new_server)

#     return jsonify(status="success", message="succesfully added new server.", data=new_server), 200

# @servers_blueprint.patch("/<int:server_id>")
# def update_server(server_id):
#     req_body = request.get_json()

#     server = Servers.query.filter_by(id=server_id).first()
#     if server is None:
#         return jsonify(status="not found", message="server not found"), 404
    
#     new_host = req_body.get("host", server.host)

#     if server.host != new_host:
#         if Servers.is_exist_with_host(new_host):
#             return jsonify(status="failed", message="host must be unique"), 400
        
#     if 'host' in req_body:
#         server.host = req_body['host']
#     if 'sshport' in req_body:
#         server.sshport = req_body['sshport']
#     if 'username' in req_body:
#         server.username = req_body['username']
#     if 'auth_key' in req_body:
#         server.auth_key = req_body['auth_key']

#     db.session.commit()
#     db.session.refresh(server)
#     updated_server_data = convert_model_to_dict(server)

#     return jsonify(status="success", message="successfully updated server info.", data=updated_server_data), 200

# @servers_blueprint.delete("/<int:server_id>")
# def delete(server_id):
    
#     server = Servers.query.filter_by(id=server_id).first()
#     if server is None:
#         return jsonify(status="not found", message="server not found"), 404
    
#     db.session.delete(server)
#     db.session.commit()

#     return jsonify(status="success", message=f"successfully deleted server with id : {server_id}"), 200
