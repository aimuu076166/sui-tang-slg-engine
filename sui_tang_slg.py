# -*- coding: utf-8 -*-
"""
Sui-Tang SLG Dual-Core Engine (sui_tang_slg.py)

1. Turn-based battle simulation with head-general defeat and morale decay.
2. Hexagonal strategic map with adjacency checks.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# 1. 战斗系统核心模型 (Battle Core)


class SkillType:
    COMMAND = "指挥"
    ACTIVE = "主动"
    ASSAULT = "突击"
    PASSIVE = "被动"


@dataclass
class General:
    name: str
    is_head: bool              # 主将兵力归零时全队败北
    max_troops: int
    current_troops: int
    force: int                 # 武力
    intellect: int             # 智力
    defense: int               # 统率
    speed: int                 # 速度
    skills: List[str] = field(default_factory=list)
    stunned: bool = False      # 震慑状态
    silenced: bool = False     # 计穷状态字段


@dataclass
class Team:
    name: str
    generals: List[General]
    morale: int = 100

    @property
    def total_troops(self) -> int:
        return sum(g.current_troops for g in self.generals)

    @property
    def head_general(self) -> Optional[General]:
        for g in self.generals:
            if g.is_head:
                return g
        return self.generals[0] if self.generals else None

    @property
    def is_defeated(self) -> bool:
        head = self.head_general
        return (head is not None and head.current_troops <= 0) or self.total_troops <= 0


class BattleEngine:
    def __init__(self, attacker: Team, defender: Team):
        self.attacker = attacker
        self.defender = defender
        self.logs: List[str] = []

    def get_morale_factor(self, morale: int) -> float:
        # 100 士气对应 100% 系数，0 士气对应 30% 系数。
        return 0.3 + 0.7 * (max(0, min(100, morale)) / 100.0)

    def execute_turn(self, round_num: int):
        self.logs.append(f"\n--- 第 {round_num} 回合开始 ---")

        # 收集存活武将，按速度降序行动。
        all_generals: List[Tuple[General, Team, Team]] = []
        for g in self.attacker.generals:
            if g.current_troops > 0:
                all_generals.append((g, self.attacker, self.defender))
        for g in self.defender.generals:
            if g.current_troops > 0:
                all_generals.append((g, self.defender, self.attacker))

        all_generals.sort(key=lambda x: x[0].speed, reverse=True)

        for actor, my_team, opp_team in all_generals:
            if actor.current_troops <= 0 or my_team.is_defeated or opp_team.is_defeated:
                continue

            if actor.stunned:
                self.logs.append(f"[{actor.name}] 处于【震慑】状态，无法行动！")
                actor.stunned = False
                continue

            # 当前原型记录指挥战法提示。
            if "贞观之治" in actor.skills and round_num <= 3:
                self.logs.append(f"[{actor.name}] 施展【贞观之治】：三回合内己方全军减伤15%！")

            # 从敌方存活武将中随机选择目标。
            alive_targets = [tg for tg in opp_team.generals if tg.current_troops > 0]
            if not alive_targets:
                break
            target = random.choice(alive_targets)

            m_factor = self.get_morale_factor(my_team.morale)
            base_dmg = int(
                (actor.force * 1.5 - target.defense * 0.8)
                * (actor.current_troops / 1000.0)
                * m_factor
            )
            base_dmg = max(50, base_dmg)

            if "擂金瓮金锤" in actor.skills and random.random() < 0.35:
                crit_dmg = int(base_dmg * 2.2)
                target.current_troops = max(0, target.current_troops - crit_dmg)
                target.stunned = True
                self.logs.append(
                    f"★ 暴击！[{actor.name}] 发动【擂金瓮金锤】，"
                    f"对 [{target.name}] 造成 {crit_dmg} 点毁灭性杀伤！"
                    f"[{target.name}] 陷入【震慑】！"
                )
            else:
                defender_guards = [
                    g for g in opp_team.generals
                    if "撒手锏" in g.skills and g != target and g.current_troops > 0
                ]
                if defender_guards and random.random() < 0.4:
                    guard = defender_guards[0]
                    mitigated_dmg = int(base_dmg * 0.6)
                    guard.current_troops = max(0, guard.current_troops - mitigated_dmg)
                    self.logs.append(
                        f"🛡 [{guard.name}] 发动【撒手锏】飞身援护，"
                        f"替 [{target.name}] 承受 {mitigated_dmg} 伤害！"
                    )
                else:
                    target.current_troops = max(0, target.current_troops - base_dmg)
                    self.logs.append(
                        f"[{actor.name}] 发动普通突击，对 [{target.name}] 造成 {base_dmg} 点兵力损耗！"
                    )

            if target.is_head and target.current_troops <= 0:
                self.logs.append(
                    f"⚡ 斩首溃败！敌方主将 [{target.name}] 兵力归零！全队触发爆头崩溃！"
                )
                break

    def run_battle(self, max_rounds: int = 8) -> Tuple[bool, List[str]]:
        self.logs.append(f"=== 战斗打响：{self.attacker.name} VS {self.defender.name} ===")
        init_att_troops = self.attacker.total_troops
        init_def_troops = self.defender.total_troops

        for r in range(1, max_rounds + 1):
            self.execute_turn(r)
            if self.attacker.is_defeated or self.defender.is_defeated:
                break

        is_attacker_win = self.defender.is_defeated and not self.attacker.is_defeated
        self.logs.append("\n=== 战后结算 ===")
        result = "【攻击方大捷】" if is_attacker_win else "【防守方坚守成功/败退】"
        self.logs.append(f"战斗结果: {result}")

        att_loss = init_att_troops - self.attacker.total_troops
        def_loss = init_def_troops - self.defender.total_troops
        self.logs.append(f"{self.attacker.name} 阵亡/轻伤: {int(att_loss * 0.55)} / {int(att_loss * 0.45)}")
        self.logs.append(f"{self.defender.name} 阵亡/轻伤: {int(def_loss * 0.55)} / {int(def_loss * 0.45)}")
        return is_attacker_win, self.logs


# 2. 六角大地图与连地沙盘系统 (Map Core)


@dataclass
class MapTile:
    q: int
    r: int
    tile_type: str        # farmland, forest, iron, city, pass
    level: int
    owner: Optional[str] = None
    garrison_troops: int = 2000


class HexMap:
    def __init__(self, radius: int = 5):
        self.radius = radius
        self.tiles: Dict[Tuple[int, int], MapTile] = {}
        self._init_map()

    def _init_map(self):
        types = ["farmland", "forest", "iron"]
        for q in range(-self.radius, self.radius + 1):
            r1 = max(-self.radius, -q - self.radius)
            r2 = min(self.radius, -q + self.radius)
            for r in range(r1, r2 + 1):
                t_type = random.choice(types)
                lvl = random.randint(1, 5)
                self.tiles[(q, r)] = MapTile(
                    q=q, r=r, tile_type=t_type, level=lvl, garrison_troops=lvl * 1500
                )

        # 设置主城与关卡。
        if (0, 0) in self.tiles:
            self.tiles[(0, 0)] = MapTile(
                q=0, r=0, tile_type="city", level=5, owner="Player", garrison_troops=10000
            )
        if (2, -2) in self.tiles:
            self.tiles[(2, -2)] = MapTile(
                q=2, r=-2, tile_type="pass", level=4, owner="SuiGuards", garrison_troops=8000
            )

    def get_neighbors(self, q: int, r: int) -> List[Tuple[int, int]]:
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        return [(q + dq, r + dr) for dq, dr in directions if (q + dq, r + dr) in self.tiles]

    def can_attack(self, player_name: str, target_coord: Tuple[int, int]) -> bool:
        neighbors = self.get_neighbors(*target_coord)
        for n_coord in neighbors:
            if self.tiles[n_coord].owner == player_name:
                return True
        return False


# 3. 运行本地自测


if __name__ == "__main__":
    print("[Engine] 正在启动隋唐 SLG 核心逻辑自测...")

    li_shimin = General(
        name="李世民", is_head=True, max_troops=5000, current_troops=5000,
        force=92, intellect=96, defense=95, speed=88, skills=["贞观之治"],
    )
    li_yuanba = General(
        name="李元霸", is_head=False, max_troops=5000, current_troops=5000,
        force=108, intellect=35, defense=89, speed=94, skills=["擂金瓮金锤"],
    )
    qin_qiong = General(
        name="秦琼", is_head=False, max_troops=5000, current_troops=5000,
        force=95, intellect=78, defense=96, speed=72, skills=["撒手锏"],
    )
    tang_army = Team(name="太原铁骑", generals=[li_shimin, li_yuanba, qin_qiong], morale=100)

    yang_guang = General(
        name="杨广", is_head=True, max_troops=4500, current_troops=4500,
        force=80, intellect=85, defense=75, speed=70,
    )
    yuwen = General(
        name="宇文成都", is_head=False, max_troops=5500, current_troops=5500,
        force=102, intellect=72, defense=94, speed=90,
    )
    sui_army = Team(name="禁卫龙骧军", generals=[yang_guang, yuwen], morale=80)

    engine = BattleEngine(attacker=tang_army, defender=sui_army)
    is_win, battle_logs = engine.run_battle()
    print("\n".join(battle_logs))

    hmap = HexMap(radius=3)
    target = (1, 0)
    can_invade = hmap.can_attack("Player", target)
    verdict = "通过(可攻打)" if can_invade else "拒绝(未连地)"
    print(f"\n[Map] 连地规则测试: 对地块 {target} 发起出征许可判定 -> {verdict}")
