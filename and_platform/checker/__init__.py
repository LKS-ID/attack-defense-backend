from and_platform.core.config import get_config
from and_platform.core.constant import CHECKER_TIMEOUT
from and_platform.core.ssh import create_ssh_from_server
# from and_platform.core.service import get_remote_service_path
from and_platform.core.challenge import get_challenges_dir_fromid
from and_platform.models import db, Teams, CheckerQueues, CheckerVerdict, ServerAWSInfos
# from and_platform.models import Services
from flask import Flask
from fulgens import ChallengeHelper, Verdict
from importlib.machinery import SourceFileLoader
from multiprocessing import TimeoutError
from multiprocessing.pool import ThreadPool
import traceback

class Helper():
    def __init__(self, addresses, local_chall_dir, team_id):
        self.team_id = team_id
        self.addresses = addresses
        self.local_chall_dir = local_chall_dir
    
class CheckerExecutor():
    def __init__(self, app: Flask):
        self.app = app

    def run_check(self, team_id: int, chall_id: int):
        with self.app.app_context():
            try:
                team = Teams.query.filter(Teams.id == team_id).scalar()
                # chall = Challenges.query.filter(Challenges.id == chall_id).scalar()
                
                server = team.server
                awsinfo = db.session.query(ServerAWSInfos.instance_id).filter(
                    ServerAWSInfos.server_id == server.id
                ).scalar()
                addresses = [
                    server.host,
                    awsinfo
                ]
                # server_mode = get_config("SERVER_MODE")
                # if server_mode == "private":
                #     server = team.server
                # else:
                #     server = chall.server
                
                # addresses = db.session.query(Services.address).filter(
                #     Services.challenge_id == chall_id,
                #     Services.team_id == team.id
                # ).order_by(Services.order).all()
                # addresses = [elm[0] for elm in addresses]
                
                # ssh_conn = create_ssh_from_server(server)
                chall_dir = get_challenges_dir_fromid(str(chall_id))
                script_path = chall_dir.joinpath("test", "test.py").as_posix()

                helper = Helper(
                    addresses=addresses,
                    local_chall_dir=chall_dir,
                    team_id=team_id,
                )
                
                test_script = SourceFileLoader("checker_test", script_path).load_module()
                print(f"Running test for {team_id}:{addresses}")
                pool = ThreadPool(processes=1)
                job = pool.apply_async(test_script.do_check, args=(helper, ))
                pool.close()
                
                verdict = job.get(CHECKER_TIMEOUT.total_seconds())
            except TimeoutError:
                verdict = Verdict.FAIL("timeout")
            except Exception as ex:
                verdict = Verdict.ERROR(traceback.format_exc())            

            current_round = get_config("CURRENT_ROUND", 0)
            current_tick = get_config("CURRENT_TICK", 0)

            if verdict.is_ok():
                result = CheckerVerdict.VALID
            else:
                result = CheckerVerdict.FAULTY

            checkerqueue = CheckerQueues(
                team_id = team_id,
                challenge_id = chall_id,
                round = current_round,
                tick = current_tick,
                result = result,
                message = verdict.message,
            )
            
            db.session.add(checkerqueue)
            db.session.commit()
