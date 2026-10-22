# Package 5: parameter reconciliation (the 10 CSV conflicts + K5 server/client defaults)

**Update 28 Sep 2026:** Idle locked K1, K2, K3, K4, diffusion_master, headroom and colour rates. See the LOCKED table at the top of `RECONCILED_PARAMETERS.md` and `../DECISIONS_LOCKED_2026-09-28.md`. Still open: confirm decay 1.8 s by ear.

- **`RECONCILED_PARAMETERS.md`**: one agreed table. For each key it gives the recommended value, the source of truth, the rationale, the files to change, and whether it is a **DECISION FOR IDLE**.
- **`tools/defaults_diff.py`** (read-only): evaluates the `app.js` state in node and diffs it against `params_from_body({})` / `DEFAULTS`. Output: `results/defaults_diff.json` (62 differing keys, most of them client-only UI keys).

## Key findings (VERIFIED)

- **9 shared keys differ between server and client.** Server value first, client value second:

  | Key | Server | Client |
  |---|---|---|
  | `space` | 0.25 | 0.17 |
  | `humidity` | 0 | 0.35 |
  | `decay_lock` | false | true |
  | `decay_s` | 0 | 1.8 |
  | `mirror_b` | false | true |
  | `yaw_l` | None | −55 |
  | `yaw_r` | None | +55 |
  | `toe_half_deg` | None | 55 |
  | `mic_proximity` | 0 | 0.25 |

- `mic_proximity` is dead code in both Render and Play.
- `early_wet` is 0 on both sides (K4).
- Six server fallbacks are hard-coded literals in `params_from_body`, not `DEFAULTS` entries (humidity, decay_s, decay_lock, mirror_b, mic_proximity, diffusion_master).
- The client never calls `/api/defaults`.
- Because the page always sends its full state, adopting the client values on the server is **inaudible in the app**.
- The sound-changing choices are all marked DECISION FOR IDLE:
  - K1 yaw sign
  - decay 1.8 s after F2
  - diffusion_master −0.25 vs −0.5
  - humidity / air_lp (K2)
  - early level (K4)
  - default geometry (K3)
