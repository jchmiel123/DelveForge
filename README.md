# DelveForge

A roguelike dungeon crawler that doubles as a NeuroForge AI arena.
Procedurally generated descending dungeons, D&D-style classes, honest
perception (directional vision cone, torch light, fog of war), turn-based
sim built so a NeuroForge brain can eventually play it - and we can watch
it learn.

## Play it

Open `web/index.html` in any browser. No build step, no dependencies.

- Pick a class (Warrior / Ranger / Mage - different sight and light).
- Arrows or WASD to move (click the game first), Space to wait, M for map.
- On a phone the camera follows you: tap the dungeon to step that way,
  hold to keep walking, tap your hero to wait, pinch (or Zoom -/+) to
  zoom, Map for the whole level. An optional visible d-pad is one toggle
  away. On desktop, + / - / 0 zoom in, out and back to the whole map.
- Bump monsters to fight, bump chests to loot, find the stairs, descend.
- Gear (I, or the Gear key on a phone): eleven equipment slots and a
  twelve-slot pack. Empty slots fill themselves; anything else waits in the
  pack with a "better / not better" note. Uncommon and rare finds grow
  with your kills (+1 ... +5); common gear does not.
- Menu (top right) opens the AI, brains, monsters and settings panel.
- You see only what your facing cone AND your light allow. The dark is real.

## Status

v0.1 - playable world slice (P1 in DESIGN.md). AI integration is P3.

See DESIGN.md for the full vision, perception spec, and roadmap.
