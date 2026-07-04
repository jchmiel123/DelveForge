"""
DelveForge Python arena - the game sim as a NeuroForge Environment.

This is the headless twin of web/index.html so brains can train offline
at thousands of steps/sec instead of the browser's ~40. Per HANDOFF
section 5 (N3) the target is BEHAVIORAL EQUIVALENCE, not seed parity:
the sensor vector, action space, reward function, and combat/loot rules
mirror the JS exactly (HANDOFF section 2), but RNG uses Python's random
(sequences will differ from JS - that's fine and intended).

Design choices for clean training:
- Monsters are SCRIPTED (never learning) so the environment is
  stationary for the player brain (HANDOFF pitfall: a learning opponent
  makes training nonstationary). The web client keeps its learning
  hive-brains; this arena is for producing a strong PLAYER brain.
- No rival delver here.
- Descending regenerates the level and CONTINUES the episode (matches
  JS aiRespawn semantics); only death ends the episode.

Sensor: 27 dims, exactly HANDOFF section 2. Actions: 0-3 move,
4 ability, 5 potion, 6 scroll. Reward per HANDOFF section 2 table.

    env = DelveArena(cls="Warrior")
    obs = env.reset()                 # 27-vector
    obs, reward, done = env.step(a)   # a in 0..6
"""

from __future__ import annotations

import math
import random

TW, TH = 40, 26
WALL, FLOOR, STAIRS, CHEST, CHESTO = 0, 1, 3, 5, 6

CLASSES = {
    "Warrior": dict(hp=16, atk=3, defense=1, light=3.2, cone=5),
    "Ranger":  dict(hp=11, atk=2, defense=0, light=3.0, cone=7),
    "Mage":    dict(hp=9,  atk=1, defense=0, light=4.6, cone=5),
}
WEAPONS = [("Dagger", 1), ("Sword", 2), ("War axe", 3), ("Runeblade", 4)]
ARMORS = [("Leather", 1), ("Chain", 2), ("Plate", 3)]


def _idx(x, y):
    return y * TW + x


def _inb(x, y):
    return 0 <= x < TW and 0 <= y < TH


def _sign(v):
    return 0 if v == 0 else (1 if v > 0 else -1)


class DelveArena:
    observation_size = 27
    action_size = 7

    def __init__(self, cls: str = "Warrior", max_steps: int = 120,
                 seed: int | None = None):
        if cls not in CLASSES:
            raise ValueError(f"unknown class {cls}")
        self.cls_name = cls
        self.cls = CLASSES[cls]
        self.max_steps = max_steps
        self._rng = random.Random(seed)

    # -- helpers mirroring the JS -----------------------------------------

    def _R(self):
        return self._rng.random()

    def _ri(self, n):
        return int(self._rng.random() * n)

    def atk(self):
        return self.cls["atk"] + self.weapon[1] + (self.level - 1) // 2

    def def_total(self):
        return self.cls["defense"] + self.armor[1]

    def light_r(self):
        return self.cls["light"] + (2 if self.light_timer > 0 else 0)

    def max_hp(self):
        return self.cls["hp"] + (self.level - 1) * 2

    def monster_at(self, x, y):
        for m in self.monsters:
            if m["x"] == x and m["y"] == y:
                return m
        return None

    def walkable(self, x, y):
        if not _inb(x, y):
            return False
        t = self.grid[_idx(x, y)]
        return t != WALL and t != CHEST

    def los(self, x0, y0, x1, y1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while not (x == x1 and y == y1):
            if not (x == x0 and y == y0) and self.grid[_idx(x, y)] == WALL:
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return True

    # -- generation --------------------------------------------------------

    def _gen_level(self):
        self.grid = [WALL] * (TW * TH)
        self.rooms = []
        self.torches = []
        self.monsters = []
        self.explored = [0] * (TW * TH)
        rooms = self.rooms
        for _ in range(80):
            if len(rooms) >= 9:
                break
            w = 4 + self._ri(7)
            h = 3 + self._ri(4)
            x = 1 + self._ri(TW - w - 2)
            y = 1 + self._ri(TH - h - 2)
            ok = True
            for r in rooms:
                if (x < r["x"] + r["w"] + 1 and r["x"] < x + w + 1
                        and y < r["y"] + r["h"] + 1 and r["y"] < y + h + 1):
                    ok = False
                    break
            if not ok:
                continue
            rooms.append(dict(x=x, y=y, w=w, h=h))
            for j in range(y, y + h):
                for i in range(x, x + w):
                    self.grid[_idx(i, j)] = FLOOR
        for r in range(1, len(rooms)):
            a, b = rooms[r - 1], rooms[r]
            x0 = a["x"] + self._ri(a["w"])
            y0 = a["y"] + self._ri(a["h"])
            x1 = b["x"] + self._ri(b["w"])
            y1 = b["y"] + self._ri(b["h"])
            while x0 != x1:
                if self.grid[_idx(x0, y0)] == WALL:
                    self.grid[_idx(x0, y0)] = FLOOR
                x0 += 1 if x0 < x1 else -1
            while y0 != y1:
                if self.grid[_idx(x0, y0)] == WALL:
                    self.grid[_idx(x0, y0)] = FLOOR
                y0 += 1 if y0 < y1 else -1
            if self.grid[_idx(x1, y1)] == WALL:
                self.grid[_idx(x1, y1)] = FLOOR
        for r in rooms:
            for _ in range(1 + self._ri(2)):
                tx = r["x"] + self._ri(r["w"])
                ty = r["y"] if r["y"] == 0 else r["y"] + self._ri(r["h"])
                self.torches.append((tx, ty))
        for _ in range(3 + self._ri(2)):
            r = rooms[1 + self._ri(len(rooms) - 1)]
            self.grid[_idx(r["x"] + self._ri(r["w"]),
                           r["y"] + self._ri(r["h"]))] = CHEST
        last = rooms[-1]
        self.grid[_idx(last["x"] + last["w"] // 2,
                       last["y"] + last["h"] // 2)] = STAIRS
        self.stairs = (last["x"] + last["w"] // 2, last["y"] + last["h"] // 2)
        self.px = rooms[0]["x"] + rooms[0]["w"] // 2
        self.py = rooms[0]["y"] + rooms[0]["h"] // 2
        self.grid[_idx(self.px, self.py)] = FLOOR
        for _ in range(3 + self.depth):
            r = rooms[1 + self._ri(len(rooms) - 1)]
            mx = r["x"] + self._ri(r["w"])
            my = r["y"] + self._ri(r["h"])
            if self.grid[_idx(mx, my)] != FLOOR:
                continue
            roll = self._R()
            kind = "rat"
            if self.depth >= 2 and roll < 0.4:
                kind = "skeleton"
            elif self.depth >= 1 and 0.45 <= roll < 0.75:
                kind = "spider"
            khp = 5 if kind == "skeleton" else 3 if kind == "spider" else 2
            self.monsters.append(dict(
                x=mx, y=my, hp=khp, maxhp=khp,
                atk=2 if kind == "skeleton" else 1,
                skel=(kind == "skeleton"), spider=(kind == "spider")))
        self.lit = set()
        for (tx, ty) in self.torches:
            for y in range(TH):
                for x in range(TW):
                    if (math.hypot(x - tx, y - ty) <= 3
                            and self.los(tx, ty, x, y)):
                        self.lit.add(_idx(x, y))
        self._compute_vis()

    def _compute_vis(self):
        self.vis = set()
        fresh = 0
        cone = self.cls["cone"]
        lr = self.light_r()
        for y in range(TH):
            for x in range(TW):
                dx, dy = x - self.px, y - self.py
                d = math.hypot(dx, dy)
                f = dx * self.fx + dy * self.fy
                l = dx * (-self.fy) + dy * self.fx
                in_cone = 0 <= f <= cone and abs(l) <= 1 + f * 0.7
                near = abs(dx) <= 1 and abs(dy) <= 1
                if not in_cone and not near:
                    continue
                if not self.los(self.px, self.py, x, y):
                    continue
                if d <= lr or _idx(x, y) in self.lit:
                    self.vis.add(_idx(x, y))
                    if not self.explored[_idx(x, y)]:
                        fresh += 1
                    self.explored[_idx(x, y)] = 1
        self.vis.add(_idx(self.px, self.py))
        self.explored[_idx(self.px, self.py)] = 1
        return fresh

    # -- sensor (27 dims, HANDOFF section 2) ------------------------------

    def sensor(self):
        v = []
        for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            wall = mon = chest = 0.0
            for s in range(1, 11):
                x, y = self.px + dx * s, self.py + dy * s
                if not _inb(x, y) or self.grid[_idx(x, y)] == WALL:
                    wall = 1.0 / s
                    break
                idx = _idx(x, y)
                if idx in self.vis:
                    if not mon and self.monster_at(x, y):
                        mon = 1.0 / s
                    if not chest and self.grid[idx] == CHEST:
                        chest = 1.0 / s
            v.extend((wall, mon, chest))
        sx = sy = sd = seen = 0.0
        stx, sty = self.stairs
        if self.explored[_idx(stx, sty)]:
            seen = 1.0
            sx = _sign(stx - self.px)
            sy = _sign(sty - self.py)
            sd = 1.0 / (1 + abs(stx - self.px) + abs(sty - self.py))
        v.extend((sx, sy, sd, seen, self.hp / self.max_hp(),
                  min(1.0, self.depth / 6), 1.0))
        adj = sum(1 for m in self.monsters
                  if abs(m["x"] - self.px) <= 1 and abs(m["y"] - self.py) <= 1)
        if self.cls_name == "Ranger":
            res = min(1.0, self.arrows / 12)
        elif self.cls_name == "Mage":
            res = self.mana / 12
        else:
            res = 1.0 if self.cd == 0 else 0.0
        v.extend((min(1.0, self.inv_potion / 3), 1.0 if self.inv_scroll > 0 else 0.0,
                  res, 1.0 if self.light_timer > 0 else 0.0,
                  self.weapon[1] / 4, self.armor[1] / 3,
                  min(1.0, adj / 3), 1.0 if self.poison_timer > 0 else 0.0))
        return v

    # -- combat / loot -----------------------------------------------------

    def _gain_xp(self, n):
        self.xp += n
        while self.xp >= self.level * 10:
            self.xp -= self.level * 10
            self.level += 1
            self.hp = min(self.max_hp(), self.hp + 4)

    def _hit_monster(self, m, dmg):
        m["hp"] -= dmg
        if m["hp"] <= 0:
            self.monsters.remove(m)
            self._gain_xp(5 if m["skel"] else 3 if m["spider"] else 2)
            if self._R() < (0.2 if m["skel"] else 0.12):
                self.inv_potion += 1
            self._ev["kill"] += 1

    def _loot_chest(self, x, y):
        self.grid[_idx(x, y)] = CHESTO
        roll = self._R()
        if roll < 0.3:
            g = 5 + self._ri(6) + self.depth * 3
            self.gold += g
            self._ev["gold"] += g
        elif roll < 0.5:
            self.inv_potion += 1
        elif roll < 0.62:
            self.arrows += 6
        elif roll < 0.74:
            self.inv_scroll += 1
        elif roll < 0.88:
            tier = min(4, 1 + self._ri(2) + (self._ri(2) if self.depth >= 2 else 0))
            w = WEAPONS[tier - 1]
            if w[1] > self.weapon[1]:
                self.weapon = w
            else:
                self.gold += 3
        else:
            tier = min(3, 1 + (self._ri(2) if self.depth >= 2 else 0)
                       + (1 if self._R() < 0.3 else 0))
            a = ARMORS[tier - 1]
            if a[1] > self.armor[1]:
                self.armor = a
            else:
                self.gold += 3
        self._ev["chest"] += 1

    def _nearest_visible_monster(self, rng):
        best, bd = None, rng + 0.001
        for m in self.monsters:
            d = math.hypot(m["x"] - self.px, m["y"] - self.py)
            if (d <= bd and _idx(m["x"], m["y"]) in self.vis
                    and self.los(self.px, self.py, m["x"], m["y"])):
                bd = d
                best = m
        return best

    # -- monster turn (scripted) ------------------------------------------

    def _attack_player(self, m):
        dmg = max(1, m["atk"] - self.def_total() + (1 if self._R() < 0.3 else 0))
        self.hp -= dmg
        self._ev["dmg"] += dmg
        if m["spider"] and self._R() < 0.5 and self.poison_timer <= 0:
            self.poison_timer = 3

    def _monsters_turn(self):
        for m in list(self.monsters):
            if self.hp <= 0:
                break
            d = max(abs(m["x"] - self.px), abs(m["y"] - self.py))
            if d <= 1:
                self._attack_player(m)
                continue
            sx = sy = 0
            if (math.hypot(m["x"] - self.px, m["y"] - self.py) < 8
                    and self.los(m["x"], m["y"], self.px, self.py)):
                sx = _sign(self.px - m["x"])
                sy = _sign(self.py - m["y"])
                if abs(m["x"] - self.px) < abs(m["y"] - self.py):
                    sx = 0
                else:
                    sy = 0
            elif self._R() < 0.4:
                dx, dy = self._rng.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
                sx, sy = dx, dy
            nx, ny = m["x"] + sx, m["y"] + sy
            if ((sx or sy) and self.walkable(nx, ny)
                    and not self.monster_at(nx, ny)
                    and not (nx == self.px and ny == self.py)):
                m["x"], m["y"] = nx, ny

    def _tick_poison(self):
        if self.poison_timer > 0:
            self.poison_timer -= 1
            self.hp -= 1
            self._ev["dmg"] += 1

    def _turn_upkeep(self):
        if self.cd > 0:
            self.cd -= 1
        if self.light_timer > 0:
            self.light_timer -= 1
        if self.cls_name == "Mage":
            self.mana = min(12, self.mana + 1)
        self._tick_poison()
        self._monsters_turn()
        return self._compute_vis()

    def _use(self, a):
        wasted = False
        if a == 4:
            if self.cls_name == "Warrior":
                hit = 0
                if self.cd == 0:
                    for m in list(self.monsters):
                        if abs(m["x"] - self.px) <= 1 and abs(m["y"] - self.py) <= 1:
                            self._hit_monster(m, self.atk() + 1)
                            hit += 1
                if hit > 0:
                    self.cd = 6
                else:
                    wasted = True
            else:
                tgt = self._nearest_visible_monster(7 if self.cls_name == "Ranger" else 5)
                if self.cls_name == "Ranger" and tgt and self.arrows > 0:
                    self.arrows -= 1
                    self._hit_monster(tgt, self.atk() + 2)
                elif self.cls_name == "Mage" and tgt and self.mana >= 3:
                    self.mana -= 3
                    self._hit_monster(tgt, 4)
                else:
                    wasted = True
        elif a == 5:
            if self.inv_potion > 0 and self.hp < self.max_hp():
                self.inv_potion -= 1
                self.hp = min(self.max_hp(), self.hp + 6)
            else:
                wasted = True
        else:
            if self.inv_scroll > 0 and self.light_timer <= 0:
                self.inv_scroll -= 1
                self.light_timer = 40
            else:
                wasted = True
        return wasted

    def _move(self, dx, dy):
        self.fx, self.fy = dx, dy
        nx, ny = self.px + dx, self.py + dy
        if _inb(nx, ny):
            m = self.monster_at(nx, ny)
            t = self.grid[_idx(nx, ny)]
            if m:
                self._hit_monster(m, self.atk() + (1 if self._R() < 0.3 else 0))
            elif t == CHEST:
                self._loot_chest(nx, ny)
            elif self.walkable(nx, ny):
                self.px, self.py = nx, ny
                if t == STAIRS:
                    self.depth += 1
                    self.hp = min(self.max_hp(), self.hp + 3)
                    self._ev["descend"] = True
                    self._gen_level()
                    return 0
        return self._turn_upkeep()

    # -- Environment interface --------------------------------------------

    def reset(self):
        self.depth = 0
        self.level = 1
        self.xp = 0
        self.gold = 0
        self.weapon = ("Fists", 0)
        self.armor = ("Cloth", 0)
        self.inv_potion = 1
        self.inv_scroll = 0
        self.light_timer = 0
        self.poison_timer = 0
        self.cd = 0
        self.fx, self.fy = 1, 0
        self.arrows = 12 if self.cls_name == "Ranger" else 0
        self.mana = 12 if self.cls_name == "Mage" else 0
        self.hp = self.max_hp()
        self.steps = 0
        self.best_depth = 0
        self._gen_level()
        return self.sensor()

    def stairs_potential(self):
        """Normalized -manhattan distance to the stairs, but only once the
        stairs have been discovered (mirrors the sensor's 'seen' gate).
        Returns 0.0 when not yet seen. Used ONLY for potential-based
        reward shaping during training - it is policy-invariant, so a
        brain trained with it behaves identically in the unshaped game."""
        stx, sty = self.stairs
        if not self.explored[_idx(stx, sty)]:
            return 0.0
        return -(abs(stx - self.px) + abs(sty - self.py)) / (TW + TH)

    def step(self, action):
        self.steps += 1
        self._ev = dict(gold=0, kill=0, chest=0, dmg=0, descend=False)
        if action < 4:
            fresh = self._move(*((0, -1), (0, 1), (-1, 0), (1, 0))[action])
            wasted = False
        else:
            wasted = self._use(action)
            fresh = self._turn_upkeep()
        ev = self._ev
        self.last_fresh = fresh  # exposed for training-only exploration bonus
        r = (-0.02 + fresh * 0.05 + ev["kill"] * 2 + ev["chest"] * 1
             + ev["gold"] * 0.05 - ev["dmg"] * 0.5)
        if wasted:
            r -= 0.05
        if ev["descend"]:
            r += 8
        died = self.hp <= 0
        if died:
            r -= 10
        if self.depth > self.best_depth:
            self.best_depth = self.depth
        done = died or self.steps >= self.max_steps
        return self.sensor(), r, done
