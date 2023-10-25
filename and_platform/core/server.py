import celery
from and_platform.aws import get_global_template_params, TEAM_TEMPLATE_PARAMETERS, AWS_STACK_PREFIX, deploy_stack, get_stack_name, create_key_pair, rollback, delete_stack
from and_platform.core.config import get_app_config, get_config, set_config
import os
import json
from and_platform.models import db, Teams, Servers, ServerAWSInfos

def get_template_filename(prefix, team_id):
    if team_id <= 8:
        return prefix + ".1"
    else:
        return prefix + ".2"

def generate_team_private_ip(team_id):
    num = team_id + 100
    if team_id <= 8:
        return f"10.0.0.{num}"
    else:
        return f"10.0.128.{num}"

def generate_team_keypairname(team_id):
    return f"lks2023Team{team_id}"

def replace_template(content, team_id = 0):
    content = content.replace("__GATEFLAG__", AWS_STACK_PREFIX)
    content = content.replace("__TEAM__", f'team{team_id}')
    return content

def provision_or_get_global_stack(is_force=False, fname="global.yml", team_id=-1):
    template_dir = os.path.join(get_app_config("TEMPLATE_DIR"), "server")

    with open(os.path.join(template_dir, fname)) as f:
        stack_global_template = f.read()
        stack_global_template = replace_template(stack_global_template)

    global_template_params = get_global_template_params(team_id)
    global_template_params["GateFlagSecret"] = "'" + get_config("GATEFLAG_SECRET") + "'"
    # print(fname)
    output_stack_global = deploy_stack(
        get_stack_name(0),
        stack_global_template,
        global_template_params,
        team_id=team_id,
    )
    
    output_stack_global_json = {}
    for output in output_stack_global:
        output_stack_global_json[output['OutputKey']] = output['OutputValue']
    return output_stack_global_json

def do_server_bulk_provision(is_force):
    provision_or_get_global_stack(is_force, "global.yml.1", 1)
    provision_or_get_global_stack(is_force, "global.yml.2", 16)
    teams = Teams.query.all()
    for team in teams:
        do_server_bulk_provision.apply_async(team.id)

@celery.shared_task
def do_server_provision(team_id):
    template_dir = os.path.join(get_app_config("TEMPLATE_DIR"), "server")
    
    output_stack_global = provision_or_get_global_stack(fname=get_template_filename("global.yml", team_id), team_id=team_id)

    team_parameters = TEAM_TEMPLATE_PARAMETERS
    team_parameters.update(output_stack_global)

    team_keypairname = generate_team_keypairname(team_id)
    team_parameters['CTFEC2KeyPair'] = team_keypairname
    team_parameters['PrivateIpAddress'] = generate_team_private_ip(team_id)

    ssh_privkey = create_key_pair(team_keypairname, team_id)
    with open(os.path.join(template_dir, get_template_filename("team.yml", team_id))) as f:
        stack_team_template = f.read()
        stack_team_template = replace_template(stack_team_template, team_id)
        
    output_stack_team = deploy_stack(
        get_stack_name(1, f'team{team_id}'),
        stack_team_template,
        team_parameters,
        team_id=team_id
    )
        
    result_stack = {}
    for output in output_stack_team:
        result_stack[output['OutputKey']] = output['OutputValue']
    server = Servers.query.filter(Servers.host == result_stack["CTFMachinePrivateIp"]).scalar()
    if server == None:
        server = Servers(
            host = result_stack["CTFMachinePrivateIp"],
            sshport = 22,
            username = "ubuntu",
            auth_key = ssh_privkey,
        )
        db.session.add(server)
        db.session.commit()
        db.session.refresh(server)
    else:
        server.auth_key = ssh_privkey
        db.session.flush([server])

    team = Teams.query.filter(Teams.id == team_id).scalar()
    team.server_id = server.id
    team.server_host = result_stack["CTFMachinePrivateIp"]
    db.session.flush([team])
        
    awsinfo = ServerAWSInfos(
        server_id = server.id,
        instance_id = result_stack["CTFMachineInstanceId"]
    )
    db.session.add(awsinfo)
    db.session.commit()

def do_server_bulk_destroy():
    teams = Teams.query.all()
    for team in teams:
        team_id = team.id
        do_server_destroy.apply_async(args=(team_id, ), queue='contest')

@celery.shared_task
def do_server_destroy(team_id):
    stack_name = get_stack_name(1, 'team' + str(team_id))
    delete_stack(stack_name, team_id)

@celery.shared_task
def do_rollback(team_id):
    output_stack_team = rollback(team_id)
    
    result_stack = {}
    for output in output_stack_team:
        result_stack[output['OutputKey']] = output['OutputValue']
    
    awsinfo = db.session.query(ServerAWSInfos).join(
        Teams,
        Teams.server_id == ServerAWSInfos.server_id
    ).filter(
        Teams.id == team_id
    ).scalar()

    awsinfo.instance_id = result_stack["CTFMachineInstanceId"]
    db.session.flush([awsinfo])
    db.session.commit()
