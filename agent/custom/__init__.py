# 导入所有自定义模块，触发 @AgentServer 装饰器注册
from .general import general_action, general_reco
from .recover import recover_action, recover_reco
from .arena import arena_action, arena_reco
from .boss import boss_action, boss_reco
from .battle import battle_action, battle_reco
from .lab import lab_action, lab_reco
