# DelveForge - Python arena (offline brain training)

The headless twin of the browser game, so brains can train at ~100x
browser speed and then be Imported back into the web client.

## Files

- `delve_arena.py` - `DelveArena`, a NeuroForge `Environment` that mirrors
  the JS game's sensor (27 dims), 7 actions, reward function, combat and
  loot (HANDOFF.md section 2). Monsters are scripted here (stationary
  environment = clean player-brain training). Behavioral equivalence with
  the JS, NOT seed parity.
- `train.py` - a double-DQN training loop matching the JS learning
  constants, plus potential-based shaping toward discovered stairs and a
  small exploration bootstrap. Evaluates the GREEDY policy on fresh unseen
  seeds and checkpoints the best brain to disk continuously.
- `trained/<cls>-trained.json` - exported brains, in the portable format
  the game's Export/Import panel reads.

## Requirements

Pure Python 3, plus NeuroForge on the path (the scripts add
`D:\CodeLab\NeuroForge` automatically). No numpy needed.

## Train a brain

```bash
cd D:\CodeLab\DelveForge\py
python train.py Warrior 3000       # class, episodes -> trained/warrior-trained.json
python train.py Ranger 3000
python train.py Mage 3000
```

Watch the `GREEDY avg_depth` / `survive` columns - those are the honest
metrics (evaluated on unseen dungeons). The `train_r` column includes
shaping and exploration bonuses, so it is NOT comparable to in-game score.

## Get a trained brain into the game

1. Open `trained/<cls>-trained.json`, copy its contents.
2. In the game, open the **Export / Import** panel, paste into the box,
   press **Import**. The brain is saved to your roster and made active.
3. Set the AI to **locked** (or **playing**) and watch it delve. Or add it
   as a **rival** to race your browser-trained brains.

The bridge (`NeuroForge/delveforge_bridge.py`) guarantees a brain produces
bit-identical decisions in Python and in the browser (verified drift 0.0).

## Tuning notes (learned the hard way)

- Finding the far stairs on a 40x26 map is a long-horizon sparse task for
  a reactive DQN. Survival hits 100% quickly; deep descent is the hard part
  and needs long training and/or curriculum.
- Reward shaping caution: the exploration bonus MUST stay well below the +8
  descend reward, or the agent learns to explore forever and never dives.
  Potential-based stairs shaping is policy-invariant (safe); the flat
  exploration bonus is not, so keep it a small bootstrap.
- Always judge the GREEDY policy on fresh seeds - training reward lies.

See ../HANDOFF.md for the full contracts and the N3 status.
