from flask import Blueprint, request

checker_agent_blueprint = Blueprint("checker_agent", __name__, url_prefix="/api/v2/checkeragent")

@checker_agent_blueprint.post("/")
def receive_checker_agent_report():
    if 'X-Forwarded-For' in request.headers:
        source_ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        source_ip = request.remote_addr
    
    # TODO: complete this