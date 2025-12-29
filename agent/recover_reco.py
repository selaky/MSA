# input: recover_helper
# output: 暂无
# pos: 这里是恢复流程中识别的方式

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import recover_helper
import logging

logging.basicConfig(level=logging.INFO) 

@AgentServer.custom_recognition("should_use_potion")
class ShouldUsePotion(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        """判断是否使用当前节点对应的药水"""
        try:
            # 获得节点名并提取相应类型
            node_name = argv.node_name
            potion_type = recover_helper.node_name_extract(node_name)
            logging.info(f"开始判断是否使用{potion_type.name}")
            
            # 条件A: 库存大于 0
            has_stock = potion_type.stock > 0
            
            # 条件B: 限制为 -1 (无限用) 或者 使用量小于限制
            can_use_more = (potion_type.limit == -1) or (potion_type.usage < potion_type.limit)

            if has_stock and can_use_more:
                # 可以使用药水的情况
                msg = f"{potion_type.name}有余量"
                logging.info(msg)
                return CustomRecognition.AnalyzeResult(box=(0, 0, 100, 100), detail=msg)
            
            else:
                # 失败的情况：要么没库存，要么到上限
                # 为了日志清楚，可以简单区分一下
                if not has_stock:
                    msg = f"{potion_type.name}数量为 0，药水用尽"
                else:
                    msg = f"{potion_type.name}使用已达到上限"
                
                logging.info(msg)
                # 返回失败 (坐标全 0)
                return CustomRecognition.AnalyzeResult(box=(0, 0, 0, 0), detail=msg)

        except Exception as e:
            # 出错时捕捉异常
            logging.error(f"{argv.node_name}出现错误: {e}")
            return CustomRecognition.AnalyzeResult(box=(0, 0, 0, 0), detail=str(e))
