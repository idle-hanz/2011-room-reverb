# UI1 — preamp and compressor controls

Inventory of the desktop controls at `36e15b5` and its parent `2f23d9a`, and where each one posts now. Talkback stays in `compressor_presets.json` only.

## What each commit showed

VERIFIED. Parent `2f23d9a` (`explain the three mix checks`) draws one Routing panel on the Mix page, three strips (Array, Room, Master). `software/static/index.html` in that commit. No gain-reduction meter, no separate bypass button, and no talkback option.

VERIFIED. `36e15b5` (`replace routing and the host fader with bypass`) removes that panel. The only Mix control it adds is the Buses Bypass button (`wetBypass`), which zeros Direct, FDN, and Early. That button is not a preamp or compressor control. `routing_scene.js` remains and still maps the page keys.

## Controls restored

Page keys are the ones the parent inputs used. They are still in `settings_table.py`. Play and Render read the engine keys. `routing_scene.js` maps one to the other. Off posts nothing.

| Strip | Control | Page id | Range and values | Engine id |
| --- | --- | --- | --- | --- |
| Array | Preamp | `route_array_pre` | `none` (label Off), `u610a` (610-A), `neve1073` (Neve). Default `none` | `array_pre` |
| Array | Drive | `route_array_drive` | 0 to 12 dB, step 0.5. Default 0 | `array_drive_db` |
| Array | Comp | `route_array_comp` | `off`, `natural`, `glue`, `room_crush`, `nuke`, `swell`. Default `off` | `array_preset` |
| Array | Amount | `route_array_amount` | 0 to 100, step 1. Default 0 | `array_amount` |
| Room | Preamp | `route_room_pre` | same as Array preamp | `room_pre` |
| Room | Drive | `route_room_drive` | same as Array drive | `room_drive_db` |
| Room | Comp | `route_room_comp` | same as Array comp | `room_preset` |
| Room | Amount | `route_room_amount` | same as Array amount | `room_amount` |
| Master | Preamp | `route_master_pre` | same as Array preamp | `pre_colour` |
| Master | Drive | `route_master_drive` | same as Array drive | `pre_drive_db` |
| Master | Comp | `route_master_comp` | same as Array comp | `bloom_preset` |
| Master | Amount | `route_master_amount` | same as Array amount | `bloom_amount` |

VERIFIED. Drive 0–12 step 0.5 and Amount 0–100 step 1 are the parent `<input>` attributes. Amount 0–100 is also `settings_table.py`. The drive row in the table has no numeric range. The slider keeps the parent range.

## Mapping

VERIFIED. Page preamp `none` is not an engine token. The engine preamp off token is `off` (`pre_colour`, `array_pre`, `room_pre`). A strip that is Off omits its keys. A compressor that is on with the preamp Off posts the engine pre as `off`.

VERIFIED. Page compressor `off` is not an engine preset id. The engine default preset name is `natural` with amount 0, and that stays off (`bloom_is_on`). Off omits `bloom_preset`, `array_preset`, and `room_preset`.

VERIFIED. 610-A is `u610a` on the page and in the engine. Neve is `neve1073` on both. Those ids were not renamed.

VERIFIED. Choosing a compressor model when Amount is 0 sets Amount to 100 (`armStrip`). Amount 0 with a model selected still posts nothing.

## Left out

VERIFIED absent. No meter at either commit. Nothing to restore.

VERIFIED absent. No per-strip bypass. Off is the bypass. The Buses Bypass button stays the dry-input switch from `36e15b5`.

UNKNOWN. Talkback. Neither commit has a talkback control or a page param id. `handoff_build_support_2/roadmap/bloom/compressor_presets.json` still has bloom preset id `talkback`. It is not in the Comp menu.

Not exposed at these two commits, so not restored: `bloom_menu`, `bloom_on`, `bloom_amount_ui`, `pre_drive_ui`, `bloom_colour_ui`, `glue_colour_ui`, `bloom_attack_ui`, `bloom_release_ui`, `predelay_ui`. `routing_scene.js` `migrate` still reads an old saved scene that has no `route_master_*` keys.

## Defaults

VERIFIED. Table defaults are preamp `none`, drive 0, compressor `off`, amount 0 on all three strips. Boot state copies those. Reset copies the boot snapshot and then clears the twelve keys. `loadDeskPreset` and the hall snapshot clear them too, so a shipped mic preset or the hall snapshot loads with both off. Array and room inserts still run on Render only. The default scene posts no preamp or compressor keys.
