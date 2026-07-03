# DelveForge - Claude Instructions

Roguelike dungeon crawler + NeuroForge AI arena. Read DESIGN.md first -
it holds the vision, the perception spec, and the roadmap. Follow the
roadmap phases; do not skip ahead to AI training before the sensor
vector design (P3) is agreed.

## Layout

- `web/index.html` - the entire v0.1 game, single self-contained file
  (no build step, no deps). Also inlined into chat widgets when showing
  Justin - keep file and widget in sync when editing.
- `DESIGN.md` - vision, perception spec, roadmap. Update when scope
  changes.
- (P3+) `delveforge/` - Python port of the core sim as a NeuroForge
  Environment. When it exists, PYTHON IS CANONICAL for game rules; the
  JS client must match it tile-for-tile.

## Rules

1. Perception honesty: agents and players see only cone + light + LOS.
   Never add a mechanic the agent can't sense (see DESIGN.md pillar 1).
2. Turn-based: 1 input = 1 world step. No real-time drift in the sim
   (rendering may animate freely).
3. Seeded: all generation flows from the seed shown in the HUD, via
   mulberry32(seed + depth * 7919). Reproducible bugs or it didn't
   happen.
4. ASCII-only in files; game canvas may draw whatever it likes.
5. NeuroForge is the only AI dependency (jchmiel123/NeuroForge).
