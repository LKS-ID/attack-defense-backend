from flask import Blueprint, send_file, after_this_request, jsonify
from and_platform.api.v1.admin import adminapi_blueprint
from and_platform.api.v1.submission import submission_blueprint
from and_platform.api.v1.contest import public_contest_blueprint
from and_platform.api.v1.teams import public_teams_blueprint
from and_platform.api.v1.authenticate import authenticate_blueprint
from and_platform.api.v1.challenge import public_challenge_blueprint
# from and_platform.api.v1.service import public_service_blueprint
from and_platform.api.v1.server import public_server_blueprint
from and_platform.api.v1.my import myapi_blueprint
from and_platform.api.v1.scoreboard import public_scoreboard_blueprint
from and_platform.api.v1.docs import public_docs_blueprint
from and_platform.api.v1.flagserver import flagserverapi_blueprint
from and_platform.core.config import get_app_config
import os
import re

apiv1_blueprint = Blueprint("apiv1", __name__, url_prefix="/v1")
apiv1_blueprint.register_blueprint(adminapi_blueprint)
apiv1_blueprint.register_blueprint(flagserverapi_blueprint)
apiv1_blueprint.register_blueprint(submission_blueprint)
apiv1_blueprint.register_blueprint(public_contest_blueprint)
apiv1_blueprint.register_blueprint(public_teams_blueprint)
apiv1_blueprint.register_blueprint(authenticate_blueprint)
apiv1_blueprint.register_blueprint(public_challenge_blueprint)
apiv1_blueprint.register_blueprint(public_server_blueprint)
# apiv1_blueprint.register_blueprint(public_service_blueprint)
apiv1_blueprint.register_blueprint(public_scoreboard_blueprint)
apiv1_blueprint.register_blueprint(public_docs_blueprint)
apiv1_blueprint.register_blueprint(myapi_blueprint)

@apiv1_blueprint.get("/download-vpn/<string:claim_token>")
def get_vpn(claim_token):
    vpnzip_path = os.path.join(get_app_config("DATA_DIR"), "vpn-zip", f"{claim_token}.zip")
    for c in claim_token:
        if not (ord('a') <= ord(c) <= ord("f")) and not (ord('0') <= ord(c) <= ord("9")):
            return jsonify(status="failed", message="invalid claim token")
    @after_this_request
    def delete_zip(response):
        try:
            os.remove(vpnzip_path)
        except Exception as ex:
            print(ex)
        return response
    
    return send_file(vpnzip_path)