import os
import boto3
import json
from and_platform.core.config import get_config

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION_NAME = os.getenv('AWS_REGION_NAME', 'ap-southeast-1')
AWS_STACK_PREFIX = os.getenv('AWS_STACK_PREFIX', 'lks-warmup')

GLOBAL_TEMPLATE_PARAMETERS = {
    'Vpc': os.getenv('VPC_ID', 'vpcid'),
    'PublicRouteTable': os.getenv('PUBLIC_ROUTE_TABLE', 'routetable'),
    'EnvironmentName': AWS_STACK_PREFIX,
    'FlagServerHost': os.getenv('FLAG_SERVER_HOST', 'https://flaggy.free.beeceptor.com'),
}

TEAM_TEMPLATE_PARAMETERS = {
    'EnvironmentName': AWS_STACK_PREFIX,
    'CTFMachineAMI1': os.getenv('AMI_ID1', 'CTFMachineAMI1'),
    'CTFMachineAMI2': os.getenv('AMI_ID2', 'CTFMachineAMI2'),
}

stack_suffixes = {
    0: 'global',
    1: 'team',
}

aws_session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME,
)

cf_client = aws_session.client('cloudformation')

def create_key_pair(name):
    ec2_client = aws_session.client('ec2')
    try:
        response = ec2_client.create_key_pair(KeyName=name)
        return response['KeyMaterial']
    except Exception:
        ec2_client.delete_key_pair(KeyName=name)
        response = ec2_client.create_key_pair(KeyName=name)
        return response['KeyMaterial']

def get_stack_name(stack_type, suffix=''):
    if suffix != '':
        return '%s-%s-%s' % (AWS_STACK_PREFIX, stack_suffixes[stack_type], suffix)
    return '%s-%s' % (AWS_STACK_PREFIX, stack_suffixes[stack_type])

def deploy_stack(stack_name, template_body, params):
    parameters = [{'ParameterKey': x, 'ParameterValue': params[x]} for x in params.keys()]

    print('Deploying stack %s' % stack_name)

    stack_exists = False
    try:
        cf_client.describe_stacks(StackName=stack_name)
        stack_exists = True
    except cf_client.exceptions.ClientError as e:
        stack_exists = False
    
    try:
        if stack_exists:
            print('Stack exists, updating...')
            cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_AUTO_EXPAND', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                Parameters=parameters,
            )
            
            print('Waiting until stack %s deployed...' % stack_name)
            cf_client.get_waiter('stack_update_complete').wait(StackName=stack_name)
            
            stack_info = cf_client.describe_stacks(StackName=stack_name)
            if stack_info['Stacks'][0]['StackStatus'] == 'UPDATE_COMPLETE':
                print(f'Stack {stack_name} updated successfully!')
                return stack_info['Stacks'][0]['Outputs']
            else:
                print(f'Stack update failed. Status: {stack_info["Stacks"][0]["StackStatus"]}')
        else:
            print('Stack not exists, creating...')
            cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_AUTO_EXPAND', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                Parameters=parameters,
            )

            print('Waiting until stack %s deployed...' % stack_name)
            cf_client.get_waiter('stack_create_complete').wait(StackName=stack_name)
            
            stack_info = cf_client.describe_stacks(StackName=stack_name)
            if stack_info['Stacks'][0]['StackStatus'] == 'CREATE_COMPLETE':
                print(f'Stack {stack_name} created successfully!')
                return stack_info['Stacks'][0]['Outputs']
            else:
                print(f'Stack creation failed. Status: {stack_info["Stacks"][0]["StackStatus"]}')
                return None
    except Exception as e:
        print(f'Stack creation failed. Status: %s' % e)
        return None

def delete_stack(stack_name):
    try:
        cf_client.delete_stack(StackName=stack_name)
        print(f'Stack {stack_name} deletion initiated.')
    except cf_client.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f'Stack {stack_name} does not exist.')
        return

    print('Waiting until stack %s deleted...' % stack_name)
    cf_client.get_waiter('stack_delete_complete').wait(StackName=stack_name)

    try:
        stack_info = cf_client.describe_stacks(StackName=stack_name)
        if stack_info['Stacks'][0]['StackStatus'] == 'DELETE_COMPLETE':
            print(f'Stack {stack_name} deleted successfully!')
        else:
            print(f'Stack deletion failed. Status: {stack_info["Stacks"][0]["StackStatus"]}')
    except cf_client.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f'Stack {stack_name} deleted successfully!')
        else:
            print('Stack deletion failed.')

def rollback(team_id):
    stack_name = get_stack_name(1, 'team' + str(team_id))
    
    response = cf_client.describe_stacks(StackName=stack_name)
    stack_parameters = response['Stacks'][0]['Parameters']

    response = cf_client.get_template(StackName=stack_name)
    template_body = response['TemplateBody']
    if template_body['Resources']['CTFMachineEC2Instance']['Properties']['ImageId']['Ref'] == get_config('AMI_ID1', 'CTFMachineAMI1'):
        template_body['Resources']['CTFMachineEC2Instance']['Properties']['ImageId']['Ref'] = get_config('AMI_ID2', 'CTFMachineAMI2')
    else:
        template_body['Resources']['CTFMachineEC2Instance']['Properties']['ImageId']['Ref'] = get_config('AMI_ID1', 'CTFMachineAMI1')

    parameters = {x['ParameterKey']: x['ParameterValue'] for x in stack_parameters}
    modified = json.dumps(template_body)

    print('Rollback instance for %s' % stack_name)
    delete_stack(stack_name)
    return deploy_stack(stack_name, modified, parameters)