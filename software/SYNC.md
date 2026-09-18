# SYNC — Mic desk drag + pattern/yaw placement

**When:** 2026-09-18 ~19:50 BST  
**Dest:** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\`  
**machineId:** `9595fbf3-7e9f-488a-b70d-ab0e29294c12`

## Change

### A. Diagram drag (Top / Side) — `mic_desk.js`
- Larger hit radii: body **26px**, stand **30px**, side heights **28px**, yaw tip/arc **16px**.
- Sticky selection: click selects a handle (highlight); empty click clears — **no accidental stand jump**.
- Drag threshold (~5px) before placement moves.
- **Body** (Stand / L / R): place array or adjust space. L/R drag along X adjusts `space` symmetrically; does **not** move stand Z.
- **Yaw**: dedicated amber arc + diamond tip (visually distinct). Hit-test prefers bodies over yaw so grabbing a capsule never starts yaw by mistake.
- **Side**: Src H / Mic H only — height changes, never XZ.
- Cursor grab / grabbing / crosshair (yaw). Live readout while dragging (space m, yaw °, height m, stand xz).

### B. Pattern + yaw placement
- Per-capsule **Pattern** + **Yaw** now sit under each polar plot (**Left / Centre / Right**), same IDs (`pattern_l/c/r`, `yaw_*_deg`).
- On Mic tab, `#capsuleStackListen` rows relocate into `#micCapSlotL/C/R`; sidebar stack + yaw hint hidden.
- Other tabs (Polar / Lattice / Paths) get the rows back in Listen.
- RoomMath uses per-capsule yaw → polars + 3D look cones update immediately.

### C. Polish
- Hint: “Drag body to place · drag amber arc to yaw · Side for heights · pattern/yaw under each plot”.
- Floor / Lattice / Mix gating / sy unlink unchanged.

## Files (CopyFromBox → software\)
- `static/js/mic_desk.js`
- `static/js/room_math.js`
- `static/js/app.js`
- `static/index.html`
- `static/css/app.css`
- `SYNC.md`

## User
Restart app + **Ctrl+F5**. Open **Mic**:
1. Top — click Stand / L / R (highlight), drag body to place; drag amber arc for yaw; live readout while dragging.
2. Side — only height handles move sy/my.
3. Polar trio — Pattern + Yaw under each plot; Listen sidebar keeps setup/space/stand/heights only (no duplicate pattern/yaw on Mic).


## Vendor note (GitHub clone)

`software/static/js/vendor/three.min.js` is **not** in this public repo (too large for text push).

After clone, either:
1. Copy `three.min.js` from the Desktop pack at `software/static/js/vendor/`, or
2. Download Three.js r160 `three.min.js` into `software/static/js/vendor/`.

Without it the 3D room view will not load; Floor / Side / Lattice / Paths / Mic still work.
