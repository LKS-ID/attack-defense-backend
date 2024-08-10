from typing import TypedDict

class ServiceManagerTaskSchema(TypedDict):
    action: str
    initiator: str
    artifact: str
    challenge_id: int
    team_id: int
    time_created: str

class ServiceDetailSchema(TypedDict):
    ServiceDetailPublish = TypedDict('ServiceDetailPublish', {'IP':str, 'Username':str, "Private Key":str})
    ServiceDetailChecker = TypedDict('ServiceDetailChecker', {'ip':str, 'username':str, 'private_key':str, 'instance_id':str})
    
    stack_name: str
    publish: ServiceDetailPublish
    checker: ServiceDetailChecker

class FlagrotatorTask(TypedDict):
    flag_value: str
    flag_order: int
    challenge_id: int
    team_id: int
    current_tick: int
    current_round: int
    time_created: str