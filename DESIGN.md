# DelveForge - Design Document

A roguelike dungeon crawler (Angband/Diablo lineage, our own IP) that is
BOTH a playable game and, primarily, a learning arena for NeuroForge
brains. Humans can play it; the real audience is an AI agent we watch
learn to survive it.

## Pillars

1. AI arena first, game second. Every mechanic must be expressible as
   sensors + actions + rewards. If a feature can't be sensed by the
   agent, it needs a sensor design before it ships.
2. Honest perception. No omniscience. The old quest demo cheated (agent
   knew where everything was). DelveForge agents see ONLY what their
   eyes and light allow. This is the core research theme.
3. Watchable. Everything renders. Training progress should be fun to
   spectate (brain overlay, trails, fog reveal).
4. Step by step. Small shippable slices, each playable.

## Perception spec (Justin's spec, formalized)

Vision is directional and light-gated:

- Facing-relative cone: ahead up to N tiles (class-dependent, ~5-7),
  widening with distance; sides 1 tile; behind 1 tile.
- Line of sight: walls block vision (Bresenham).
- Light gate: a tile must be LIT to be seen. Light sources: carried
  torch (radius by class), wall torches (radius ~3), later: spells,
  lava, etc. Darkness beyond light = invisible even inside the cone.
- Fog of war: explored architecture is remembered (drawn dim), but
  entities (monsters, loot) are only drawn when currently visible.
- Map: minimap renders remembered tiles only.

Future agent sensor vector (Phase 3 draft): K raycasts across the cone,
each returning distance-to-first-hit in channels (wall, monster, chest,
stairs, light level), plus proprioception (hp, facing, depth, gold,
has-seen-stairs compass to remembered location). Deliberately partial -
memory has to live in the agent or in remembered-map features we choose
to expose. This is the interesting part.

## World structure

- Start above ground in a building (the manor), descend level by level:
  cellars, catacombs, deep halls, mines, ember depths... procedurally
  generated rooms + corridors, stairs down on each level.
- Loot: gold, treasure chests (bump to open). Later: items, inventory.
- Monsters: melee bump combat v0.1 (rat, skeleton); deeper = more and
  meaner. Later: ranged, AI states (sleep/wander/hunt), factions.
- Classes (D&D-style, chosen at start, each a different sensor/stat
  tradeoff - which matters for AI experiments):
  - Warrior: high HP/damage, short sight cone, dim torch.
  - Ranger: long sight cone, mid stats.
  - Mage: bright light radius, fragile. (Later: spells.)

## Roadmap

- [x] P1 (v0.1): procgen dungeon, 3 classes with portraits, directional
      FOV + torch light + fog of war, minimap, chests, bump combat,
      stairs/descent, seeded runs, death/restart. Playable in browser
      (web/index.html) and as a chat widget.
- [x] P2 (partial, v0.2): class abilities (warrior smite AoE + cooldown,
      ranger arrows + ammo, mage bolt + mana regen), stats (ATK/DEF),
      loot table (gold/potions/arrows/weapon +1/armor +1), potions,
      message log, damage floaters, monster HP bars, hit flashes.
      Still open: doors + keys, monster AI states, full inventory.
- [~] P3 (started early, v0.2): in-browser AI mode. Sensor vector v1
      (19 inputs): 4 axis rays x (wall, visible monster, visible chest)
      + remembered-stairs compass (sgn dx, sgn dy, 1/dist, seen) + hp
      frac + depth + bias. Actions: 4 moves (abilities not in AI action
      space yet). Rewards: -0.02 step, +0.05 per newly seen tile,
      +2 kill, +1 chest, +0.05/gold, -0.5/dmg taken, +8 descend,
      -10 death. DQN-lite (replay 4000, batch 12, target sync 300,
      eps anneals per step 0.99993 + per death 0.98). Brain roster in
      localStorage (save/load/fresh). Same dungeon seed across AI lives
      = reproducible curriculum. Still open: Python port as NeuroForge
      Environment for serious training, ability actions, brain export
      to NeuroForge JSON, second player driven by a saved brain.
- [ ] P4: spectate mode - trained brain plays in the web client with
      live network overlay (port of the quest-brain inspector).
- [ ] P5: polish - real tile sprites, animations, meta-progression.

## Open questions

- Agent memory: raw recurrence (Phase 5 of NeuroForge?), or engineered
  memory features (compass-to-remembered-stairs)? Start engineered.
- Turn-based sim is RL-friendly (1 step = 1 decision). Keep it.
- Multi-agent later? (Two brains, one dungeon: race or fight.)
