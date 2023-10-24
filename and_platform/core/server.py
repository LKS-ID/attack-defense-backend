import celery
from and_platform.aws import GLOBAL_TEMPLATE_PARAMETERS, TEAM_TEMPLATE_PARAMETERS, AWS_STACK_PREFIX, deploy_stack, get_stack_name, create_key_pair, rollback
from and_platform.core.config import get_app_config, get_config
import os
from and_platform.models import db, Teams, Servers, ServerAWSInfos

def generate_team_private_ip(team_id):
    num = team_id + 100
    return f"10.0.64.{num}"

def generate_team_keypairname(team_id):
    return f"lks2023Team{team_id}"

def replace_template(content, team_id = 0):
    content = content.replace("__GATEFLAG__", AWS_STACK_PREFIX)
    content = content.replace("__TEAM__", f'team{team_id}')
    return content

@celery.shared_task
def do_server_provision():
    template_dir = os.path.join(get_app_config("TEMPLATE_DIR"), "server")
    
    with open(os.path.join(template_dir, "global.yml")) as f:
        stack_global_template = f.read()
        stack_global_template = replace_template(stack_global_template)

    global_template_params = GLOBAL_TEMPLATE_PARAMETERS
    global_template_params["GateFlagSecret"] = "'" + get_config("GATEFLAG_SECRET") + "'"

    output_stack_global = deploy_stack(
        get_stack_name(0),
        stack_global_template,
        global_template_params,
    )

    team_parameters = TEAM_TEMPLATE_PARAMETERS
    for output in output_stack_global:
        team_parameters[output['OutputKey']] = output['OutputValue']

    teams = Teams.query.all()
    for team in teams:
        team_id = team.id
        team_keypairname = generate_team_keypairname(team_id)
        team_parameters['CTFEC2KeyPair'] = team_keypairname
        team_parameters['PrivateIpAddress'] = generate_team_private_ip(team_id)

        ssh_privkey = create_key_pair(team_keypairname)
        with open(os.path.join(template_dir, "team.yml")) as f:
            stack_team_template = f.read()
            stack_team_template = replace_template(stack_team_template, team_id)
        
        output_stack_team = deploy_stack(
            get_stack_name(1, f'team{team_id}'),
            stack_team_template,
            team_parameters,
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

        team.server_id = server.id
        team.server_host = result_stack["CTFMachinePrivateIp"]
        db.session.flush([team])
        
        awsinfo = ServerAWSInfos(
            server_id = server.id,
            instance_id = result_stack["CTFMachineInstanceId"]
        )
        db.session.add(awsinfo)
        db.session.commit()

@celery.shared_task
def do_one_provision(team_id):
    template_dir = os.path.join(get_app_config("TEMPLATE_DIR"), "server")
    
    with open(os.path.join(template_dir, "global.yml")) as f:
        stack_global_template = f.read()
        stack_global_template = replace_template(stack_global_template)

    global_template_params = GLOBAL_TEMPLATE_PARAMETERS
    global_template_params["GateFlagSecret"] = "'" + get_config("GATEFLAG_SECRET") + "'"

    output_stack_global = deploy_stack(
        get_stack_name(0),
        stack_global_template,
        global_template_params,
    )

    team_parameters = TEAM_TEMPLATE_PARAMETERS
    for output in output_stack_global:
        team_parameters[output['OutputKey']] = output['OutputValue']

        team_keypairname = generate_team_keypairname(team_id)
        team_parameters['CTFEC2KeyPair'] = team_keypairname
        team_parameters['PrivateIpAddress'] = generate_team_private_ip(team_id)

    ssh_privkey = create_key_pair(team_keypairname)
    with open(os.path.join(template_dir, "team.yml")) as f:
        stack_team_template = f.read()
        stack_team_template = replace_template(stack_team_template, team_id)
        
    output_stack_team = deploy_stack(
        get_stack_name(1, f'team{team_id}'),
        stack_team_template,
        team_parameters,
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
    print("New instance id " + result_stack["CTFMachineInstanceId"])
    db.session.flush([awsinfo])
    db.session.commit()
