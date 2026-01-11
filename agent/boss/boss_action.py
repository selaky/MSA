from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from . import boss_manager
import logging
import json

@AgentServer.custom_action("reset_boss_data")
class ResetPotionData(CustomAction):
    """重置BOSS数据"""
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        boss_manager.boss_stats.current_battles = 0
        logging.info(f"[{argv.node_name}] 重置BOSS已战斗次数")
        return CustomAction.RunResult(success=True)
    
@AgentServer.custom_action("load_boss_data")
class LoadBossData(CustomAction):
    """加载用户对boss战的设置"""
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.custom_action_param:
            logging.error(f"[{argv.node_name}] 未收到任何参数")
            return CustomAction.RunResult(success=False)
        params = json.loads(argv.custom_action_param)
        boss_manager.boss_stats.max_battles = int(params.get("max_battles",-1))
        boss_manager.boss_stats.target_rank = int(params.get("target_rank",-1))
        msg = f"[{argv.node_name}] boss 战设置已载入:\n战斗次数上限{boss_manager.boss_stats.max_battles}\n目标排名{boss_manager.boss_stats.target_rank}"
        logging.info(msg)
        return CustomAction.RunResult(success=True)
    
@AgentServer.custom_action("boss_judgement")
class BossJudgement(CustomAction):
    """判断接下来 boss 战应该怎么做"""
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if boss_manager.boss_stats.should_stop: # 战斗次数达到上限
            context.override_pipeline({
                "进入BOSS分支":{
                    "next":"结束BOSS战"
                }
            })
            return CustomAction.RunResult(success=True)
        
        rank_roi = [112,240,110,33]

        

        if boss_manager.boss_stats.should_pause:
            context.override_pipeline({
                "进入BOSS分支":{
                    "next":"暂停BOSS战"
                }
            })
            return CustomAction.RunResult(success=True)
        