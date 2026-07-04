"""
Train a DelveForge player brain offline, export it for the web client.

Uses the DelveArena (behavioral twin of the game) and a DQN loop that
mirrors the JS training in web/index.html EXACTLY (HANDOFF section 2):
architecture 27 -> 32 -> 16 -> 7, double DQN targets, gamma 0.95,
lr 0.008, batch 12/step, buffer 4000, target sync every 300 steps,
epsilon 1.0 -> 0.05 annealing *0.99993/step and *0.98/episode.

Monsters are scripted (stationary env -> a clean, strong player brain).
Greedy evaluation runs on FRESH unseen seeds (HANDOFF pitfall: training
reward lies; judge greedy behavior). The best brain by eval descent
score is checkpointed and exported in the portable format the game's
Import button reads.

    python train.py                  # Warrior, sensible defaults
    python train.py Ranger 1200      # class, episodes

Output: trained/<cls>-trained.json  (Import this in the game)
"""

from __future__ import annotations

import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r"D:\CodeLab\NeuroForge")

from delve_arena import DelveArena
from neuroforge.core import Network
from delveforge_bridge import net_to_obj

GAMMA = 0.95
LR = 0.008
BATCH = 12
BUFMAX = 4000
SYNC = 300
EPS_MIN = 0.05
EPS_STEP = 0.99993
EPS_EP = 0.98


def argmax(a):
    bi = 0
    for i in range(1, len(a)):
        if a[i] > a[bi]:
            bi = i
    return bi


def greedy_eval(net, cls, seeds, max_steps=200):
    """Run the greedy policy on fresh seeds; return dict of metrics."""
    descents = 0
    depths = []
    survived = 0
    for s in seeds:
        env = DelveArena(cls=cls, max_steps=max_steps, seed=s)
        obs = env.reset()
        for _ in range(max_steps):
            a = argmax(net.activate(obs))
            obs, r, done = env.step(a)
            if done:
                break
        descents += env.depth
        depths.append(env.depth)
        if env.hp > 0:
            survived += 1
    n = len(seeds)
    return dict(avg_depth=sum(depths) / n,
                total_descents=descents,
                survival=survived / n,
                max_depth=max(depths))


SHAPE_K = 4.0       # potential-based shaping toward discovered stairs -
                    # the dominant pull once the stairs are in memory
EXPLORE_BONUS = 0.03  # small bootstrap only: enough to nudge the agent off
                      # a wall so it discovers the stairs, but well below the
                      # +8 descend reward so DESCENDING stays the goal.
                      # (Set too high -> agent explores forever, never dives.)


def greedy_eval_env(net, cls, seeds, frontier, max_steps=200):
    descents, depths, survived = 0, [], 0
    for s in seeds:
        env = DelveArena(cls=cls, max_steps=max_steps, seed=s, frontier=frontier)
        obs = env.reset()
        for _ in range(max_steps):
            obs, r, done = env.step(argmax(net.activate(obs)))
            if done:
                break
        descents += env.depth
        depths.append(env.depth)
        if env.hp > 0:
            survived += 1
    n = len(seeds)
    return dict(avg_depth=sum(depths) / n, total_descents=descents,
                survival=survived / n, max_depth=max(depths))


def train(cls="Warrior", episodes=1200, max_steps=200, report_every=100,
          eval_seeds=None, verbose=True, out_path=None, frontier=False):
    random.seed(12)
    if eval_seeds is None:
        eval_seeds = list(range(90000, 90020))  # 20 fresh dungeons, never trained

    obs_size = 31 if frontier else 27
    net = Network(obs_size, [32, 16], 7, task="regression")
    target = net.copy()
    env = DelveArena(cls=cls, max_steps=max_steps, frontier=frontier)
    buffer = []
    eps = 1.0
    steps = 0
    rewards = []
    best_score = -1.0
    best_obj = None
    t0 = time.time()

    for ep in range(1, episodes + 1):
        obs = env.reset()
        total = 0.0
        for _ in range(max_steps):
            if random.random() < eps:
                a = random.randrange(7)
            else:
                a = argmax(net.activate(obs))
            phi_prev = env.stairs_potential()
            nobs, r, done = env.step(a)
            # Potential-based shaping toward discovered stairs (policy-
            # invariant). Skip on the step we descended (level regenerated,
            # potential reference changed) - the +8 already rewards it.
            if not env._ev["descend"]:
                r += SHAPE_K * (GAMMA * env.stairs_potential() - phi_prev)
            r += EXPLORE_BONUS * env.last_fresh
            total += r
            buffer.append((obs, a, r, None if done else nobs, done))
            if len(buffer) > BUFMAX:
                buffer.pop(0)
            if len(buffer) >= BATCH:
                for _ in range(BATCH):
                    e = buffer[random.randrange(len(buffer))]
                    tq = list(net.activate(e[0]))
                    if e[4]:
                        tq[e[1]] = e[2]
                    else:
                        bi = argmax(net.activate(e[3]))       # online picks
                        tq[e[1]] = e[2] + GAMMA * target.activate(e[3])[bi]  # target grades
                    net.train_on(e[0], tq, LR)
            steps += 1
            if steps % SYNC == 0:
                target = net.copy()
            eps = max(EPS_MIN, eps * EPS_STEP)
            obs = nobs
            if done:
                break
        eps = max(EPS_MIN, eps * EPS_EP)
        rewards.append(total)

        if ep % report_every == 0 or ep == 1:
            ev = greedy_eval_env(net, cls, eval_seeds, frontier)
            avg_r = sum(rewards[-report_every:]) / len(rewards[-report_every:])
            score = ev["avg_depth"] + 0.5 * ev["survival"]
            tag = ""
            if score > best_score:
                best_score = score
                best_obj = net_to_obj(net, meta=dict(
                    cls=cls, bestDepth=int(ev["max_depth"]),
                    trainedEpisodes=ep, game="delveforge",
                    evalScore=round(score, 3)))
                tag = "  <-- new best (checkpointed)"
                if out_path:  # persist immediately so a bg run never loses it
                    try:
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(best_obj, f)
                    except OSError:
                        pass
            if verbose:
                print(f"ep {ep:5d}/{episodes} | eps {eps:.2f} | "
                      f"train_r {avg_r:7.2f} | GREEDY avg_depth {ev['avg_depth']:.2f} "
                      f"survive {ev['survival']:.0%} maxdepth {ev['max_depth']+1} "
                      f"| {steps/(time.time()-t0):.0f} st/s{tag}")

    dur = time.time() - t0
    if verbose:
        print(f"\nDone: {steps} steps in {dur:.0f}s "
              f"({steps/dur:.0f} steps/s). Best eval score {best_score:.3f}.")
    return best_obj, best_score


def main():
    cls = sys.argv[1] if len(sys.argv) > 1 else "Warrior"
    episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    out_dir = os.path.join(os.path.dirname(__file__), "trained")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{cls.lower()}-trained.json")
    best_obj, score = train(cls=cls, episodes=episodes, out_path=path)
    if best_obj is not None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(best_obj, f)
    print(f"Exported best brain (eval score {score:.3f}) to {path}")
    print("Import it in the game: Export / Import panel -> paste -> Import.")


if __name__ == "__main__":
    main()
