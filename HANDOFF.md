# DelveForge HANDOFF - read this before touching anything

Written 2026-07-03 (v0.7.0) as a high-context brain dump so any future
session can continue mid-stride. DESIGN.md holds the vision; THIS file
holds the engineering truth: contracts, workflow, pitfalls, and exact
specs for the next phases. When they disagree, HANDOFF wins.

## 1. State of the world (v0.7.0)

Single-file game: `web/index.html` (~1100 lines). Everything below
refers to functions in that file.

| System | Anchor functions | Notes |
|--------|------------------|-------|
| Procgen | genLevel | rooms+L-corridors, torches, chests, stairs; seeded |
| Perception | computeVis, los, lightR | facing cone + light gate + fog memory |
| Combat/loot | hitMonster, lootChest, ability, attackPlayer | XP via gainXp; poison via tickPoison |
| Player agent | aiTick, aiMove, aiUse, sensor, turnUpkeep | DQN-lite, arch-adaptive |
| Monster brains | monBrainAct, monTrainAll, monSensor, specGet | one hive-brain per species |
| NF runtime | nfForwardAll, nfForward, nfTrain, nfRandom, nfCopy | generic N-layer backprop |
| Brain roster | brainStore, refreshBrainList, save/load/delete handlers | localStorage |
| Overlay | drawNet | renders ANY architecture from lastActs |
| Theme | THEMES, applyTheme | self-contained --df-* vars, never host colors |

## 2. Data contracts - DO NOT BREAK

### Brain format
A brain is `[{w:[[...]],b:[...],a:"tanh"|"linear"}, ...]` (array of
layers). Same `layers` shape as inside NeuroForge `Network.save()` JSON
(see `NeuroForge/web/neuroforge.js` `fromNetworkJSON`). The agent is
ARCH-ADAPTIVE: it reads `brainIn(b)`/`brainOut(b)` and feeds
`sensor().slice(0, nIn)`, choosing among `nOut` actions. This is what
keeps old brains loadable. Consequences:

- Sensor vector is APPEND-ONLY. Never reorder, remove, or change the
  meaning/scale of an existing index. New senses go at the END.
- Action indices are FROZEN: 0=up 1=down 2=left 3=right 4=ability
  5=potion 6=scroll. New actions append (index 7+).

### Sensor vector v2.1 (player, 27 entries, in order)
0-11: per direction (up,down,left,right) x (1/dist wall, 1/dist visible
monster else 0, 1/dist visible chest else 0), rays max 10, gated by
visCache (perception honesty).
12-15: remembered-stairs compass: sgn(dx), sgn(dy), 1/(1+manhattan),
seen flag (uses `explored`, not current vision - engineered memory).
16: hp/maxHp. 17: min(1, depth/6). 18: bias 1.
19-26 (Mk II block): min(1,potions/3), scroll flag, class resource
(arrows/12 | mana/12 | smite-ready), light-blazing flag, weapon.atk/4,
armor.def/3, min(1, adjacent monsters/3), poisoned flag.

### Monster sensor (11): 4 wall rays (max 6) + player compass
(sgn dx, sgn dy, 1/(1+dist), LOS<=9 flag) + own hp frac +
min(1,adjacent allies/3) + bias.

### Rewards (tuned, change with care)
Player: -0.02/step, +0.05/newly-seen tile, +2 kill, +1 chest,
+0.05/gold, -0.5/dmg taken, -0.05 wasted item action, +8 descend,
-10 death (terminal). Monster: -0.02/step, +0.8/dmg dealt, +6 player
kill (terminal), +0.15/tile closed toward player, -6 own death
(terminal lesson pushed by monDeathLesson).

### Learning constants
Player: gamma 0.95, lr 0.008, batch 12/step, buffer 4000, target sync
300 steps, Double DQN targets, eps: training anneals *0.99993/step and
*0.98/death, floor 0.05. Modes: training (explore+learn), playing
(greedy+learn), locked (greedy only). Monsters: gamma 0.92, lr 0.006,
batch 6/turn, buffer 3000, sync 400, eps *0.9999/step *0.97/death,
floor 0.08.

### localStorage keys
`df_brains` {name:{brain,eps,episodes,bestDepth,cls}},
`df_species` {rat|spider|skeleton:{brain,eps,steps,deaths,kills}},
`df_theme` "dark"|"light". Note: chat-widget storage is sandboxed per
conversation; the hosted artifact and web/index.html get durable
browser storage.

### Seeding
All generation from `mulberry32(baseSeed + depth*7919)`. Human death
re-rolls baseSeed; AI respawn KEEPS it (reproducible curriculum).

## 3. Workflow - how to make changes cheaply

1. CANONICAL SOURCE is `web/index.html`. Edit it via a python
   replace-script written to the session scratchpad (pattern: def
   rep(old,new) with `assert old in src`; all-or-nothing, write at
   end). NEVER hand-retype the game. See git history commit messages
   for the per-version patch summaries.
2. VERIFY with preview tools: launch config `delveforge` (python
   http.server 8321, defined in D:\CodeLab\.claude\launch.json).
   The preview tab is backgrounded: requestAnimationFrame stalls, so
   the game has a 250ms setInterval fallback that only fires when rAF
   is stalled (>400ms). Test by preview_eval driving the game
   directly: click a class card, set `ai.mode="training"`, loop
   `aiTick()` thousands of times in one eval, then assert on state
   (ai.episodes, species stats, localStorage). Screenshots time out in
   background tabs - use getImageData color counts instead.
3. DEMO to Justin: redeploy the hosted Artifact (URL below) - DO NOT
   paste the game into chat as a widget anymore (it burned his usage
   limits). Regenerate the artifact fragment from the canonical file:
   strip the doctype/html/head/body wrapper, keep the style block and
   everything between the body tags (a python transform, ~10 lines),
   then call the Artifact tool with the SAME file path to update the
   SAME url.
4. SHIP: bump VERSION (SemVer), commit with a detailed message, push
   to origin master (github.com/jchmiel123/DelveForge, credentials via
   git credential manager). Update project memory
   (project_delveforge.md) with one line.

Artifact URL: https://claude.ai/code/artifact/d817b246-70f7-424b-80a3-423df7e0c500 (redeploy by regenerating the fragment and calling Artifact with the SAME scratchpad file path, or pass url= from a fresh session)

## 4. Hard-won pitfalls (do not relearn these)

- Deep-copy invariant: any brain clone must deep-copy weights.
  NeuroForge's Layer.to_dict once returned live references; elites got
  corrupted by mutation. JS side uses JSON round-trip (nfCopy).
- Training reward LIES about policy quality: exploration noise masks
  broken greedy behavior. Always evaluate greedy on unseen seeds.
- Sparse-reward Q-gaps drown in function-approx noise. Fixes that
  worked: sign features in sensors, potential-based shaping, lower
  gamma. (grid_quest went 2% -> 100% with these.)
- Epsilon must anneal per-STEP too; per-death only stalls at ~100%
  exploration for tanky classes.
- Monsters learning = nonstationary environment for the player brain.
  For controlled player-training experiments, set Monsters: scripted.
- Widget iframes: keyboard needs focus (click canvas first); 680px
  max width; localStorage sandboxed; CSP blocks ALL external hosts.
- SonicOS-style deep-link taboo does not apply here, but the chat
  host's colors DO leak into widgets: the game must keep its own
  --df-* theme variables and never use host var(--...) colors.
- PowerShell/bash on this box: long heredocs break; write patch
  scripts to files. Shell cwd resets between some calls - `cd` inside
  the same command, and never create files at D:\CodeLab root.

## 5. Next phases - specs ready to execute

### N1. Rival delver - DONE in v0.8.0 (kept for reference)
Goal: a saved brain plays a second character in the SAME dungeon;
race to the stairs / compete for loot.
Implementation note: chose DUPLICATED perception helpers (rivalVis/rivalSensor mirror computeVis/sensor) instead of parameterizing the player path - zero regression risk to the sensor contract. Rival is greedy-only, moves-only (q sliced to 4), no items (Mk II sensor block fed zeros except adjacency), own explored memory, monsters target nearest delver via nearestDelverTo, first-to-stairs descends both. Original design notes:
- Do NOT fully generalize to an actors array (too invasive). Add a
  `rival` object {x,y,fx,fy,hp,cls,brain,vx,vy, light,cone} and
  parameterize ONLY the perception helpers: computeVisFor(actor) and
  sensorFor(actor) (player keeps thin wrappers so existing code and
  brains are untouched).
- Rival acts greedy-only (locked) in v1; no learning, no items
  (actions 0-3 clamped) - keeps scope small.
- Monsters target the NEAREST of the two delvers (attackPlayer gains
  a target param; monster sensor player-compass points at nearest).
- Rival is visible only when inside the player's visCache (fog rules
  apply to rivals too). Draw with its class color + white ring.
- Scoring: first to stairs descends both (rival vanishes to next
  level with you); HUD shows rival gold/depth; message log narrates.
- UI: "Rival" button next to brain roster: pick a saved brain, spawn
  it at a far room. Rival death = it stays dead until next level.

### N2. Brain export/import - DONE in v0.9.0
Implemented: Export/Import panel (toggle button in AI row) with a copyable textarea. Export serializes ai.brain (or selected roster brain) using ACTUAL dims via brainIn/brainOut (Mk I brains export too). Import accepts my envelope OR a raw NeuroForge Network.save() JSON, saves to roster + makes active. Python side: NeuroForge/delveforge_bridge.py (net_from_obj/load_brain/net_to_obj/save_brain) - verified JS export -> Python load is bit-identical (drift 0.0). Bridge DelveEnv is a stub until N3. Original spec: JSON.stringify({format:"neuroforge-network-v1",
layers:[{weights:l.w,biases:l.b,activation:l.a}], meta:{game:
"delveforge", sensors:27, actions:7, cls, bestDepth}}) into a copyable
textarea (and Import reverse). Python side: NeuroForge Network.load
already reads this shape if given input_size/hidden/output metadata -
write a tiny converter in NeuroForge (delveforge_bridge.py) rather
than changing the format.

### N3. Python arena port - IN PROGRESS (v0.9, infra done)
DONE: py/delve_arena.py (DelveArena, NeuroForge Environment, scripted monsters for stationarity, ~3800 steps/s raw / ~180 with training = ~100x/5x browser), py/train.py (double-DQN loop mirroring the JS constants + potential-based stairs shaping + small exploration bootstrap + greedy-eval-on-fresh-seeds + best-checkpoint-to-disk, exports via bridge). Verified: arena 27-dim sensor, episodes terminate, trains (survival 100%, greedy depth climbing, reaches depth 3). KNOWN CEILING: reliable deep descent is hard for a reactive DQN on a cone-limited 40x26 map - it explores+survives well but descends slowly; needs long training and/or curriculum for depth. Reward-shaping lesson relearned: exploration bonus must stay BELOW the +8 descend reward or the agent explores forever (bug hit + fixed). Original decision: behavioral equivalence, NOT seed parity (JS/py RNG call
order will drift; do not chase it). Port order: grid/procgen ->
perception -> combat/loot -> turn loop -> Environment adapter
(reset/step matching neuroforge.evolve.Environment). Mirror the
constants tables from section 2 EXACTLY. Then overnight training with
neuroforge.qlearn.QAgent (or evolve), export brains via N2 format,
load in web client. Training curriculum (from DESIGN): 1) find
stairs, 2) loot+stairs, 3) survive fights, 4) deep descent.

### N4. Doors + keys; monster AI states (sleep/wander/hunt);
sound toggle. Gameplay filler - good low-risk tasks.

Priority rationale: N1 is Justin's most-repeated wish and pure JS.
N2 is tiny and unlocks N3. N3 is the real research payoff (browser
training is capped at ~40 steps/s UI; Python runs headless at
thousands/s). N4 anytime.

## 6. Links

- Repo: https://github.com/jchmiel123/DelveForge
- NeuroForge (brains library): https://github.com/jchmiel123/NeuroForge
- JS runtime: NeuroForge/web/neuroforge.js (game currently inlines an
  equivalent nf* copy; converge on the shared file during N3).
- Hosted artifact: https://claude.ai/code/artifact/d817b246-70f7-424b-80a3-423df7e0c500
