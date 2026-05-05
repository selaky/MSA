# input: 暂无
# output: 为 boss_action 提供数据管理。
# pos: 管理 boss 战相关数据。

from dataclasses import dataclass

@dataclass
class BossStats:
    max_battles: int = -1 # 战斗次数上限,负数表示无限
    current_battles: int = 0 # 当前已战斗次数
    target_rank: int = -1 # 目标排名,负数表示无论当前什么排名都继续战斗
    current_rank: int = 999 # 当前排名

    @property
    def should_stop(self) -> bool:
        """
        返回True代表已经达到战斗次数上限，任务可以结束了。
        使用 @property 装饰器后，可以像调用变量一样调用它
        """
        if self.max_battles != -1 and self.current_battles >= self.max_battles:
            return True
        else:
            return False
        
    @property
    def should_pause(self) -> bool:
        """
        返回True代表当前已经达到目标排名,战斗暂停。让程序等待一会儿再来查看排名是否掉了。
        """
        if self.current_rank <= self.target_rank:
            return True
        else:
            return False
        
boss_stats = BossStats()

