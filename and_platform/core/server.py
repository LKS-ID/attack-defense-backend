import celery

@celery.shared_task
def do_server_provision(team_id, chall_id):
    pass

@celery.shared_task
def do_rollback(server_id):
    pass