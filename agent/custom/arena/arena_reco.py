# input: arena_helper 提供竞技场数据管理
# output: 暂无
# pos: 竞技场相关的识别,包括 OCR 识别积分和判断是否继续竞技场。

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from utils.logger import logger
from custom.general import general_func

from . import arena_manager

stats = arena_manager.arena_stats # 简写

@AgentServer.custom_recognition("store_arena_points")
class StoreArenaPoints(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        """使用通用工具 OCR 识别竞技场积分并存储"""
        try:
            points = general_func.extract_number_from_ocr(context, argv.image, task_name="ArenaPoints")
        except ValueError as e:
            msg = f"[{argv.node_name}] {e}"
            logger.error(msg)
            return CustomRecognition.AnalyzeResult(box=None, detail=msg)

        stats.current_points = points
        msg = f"[{argv.node_name}] OCR 识别积分为 {points}"
        logger.debug(msg)
        return CustomRecognition.AnalyzeResult(box=(0, 0, 100, 100), detail=msg)

@AgentServer.custom_recognition("should_continue_arena")
class ShouldContinueArena(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        """判断当前积分是否已达到目标积分，如果达到就停止竞技场。"""
        try:
            current_points = stats.current_points
            target_points = stats.target_points
            if current_points < target_points:
                msg = f"[判断继续竞技场]当前积分{current_points}, 小于目标积分{target_points},继续战斗"
                logger.debug(msg)
                return CustomRecognition.AnalyzeResult(box=(0, 0, 100, 100), detail=msg)
            else:
                msg = f"[判断继续竞技场]当前积分{current_points}, 满足目标积分{target_points},停止战斗"
                logger.debug(msg)
                return CustomRecognition.AnalyzeResult(box=None, detail=msg)
        except Exception as e:
            msg = f"[判断继续竞技场]出错: {e}"
            logger.error(msg)
            return CustomRecognition.AnalyzeResult(box=None, detail=msg)
