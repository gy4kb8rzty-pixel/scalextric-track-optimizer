# What this project taught the optimizer

Written after the 2–3 Sep 2026 hairpin cycle. The next change must pass these tests before it ships.

## The one rule that beat every clever idea

**A complete ribbon that skips Loews is a valid D result. A stub, knot, or triangle is not.**

If a candidate change can return fewer pieces than the current full-lap follower, do not merge it. Deploy `084f28a` / `7e04d1a` sequential.py is the last known full-lap Monaco D.

## What actually worked

- Sequential follow along the scaled red centreline, one piece at a time, score = distance-to-line + heading error − progress.
- Unlimited catalogue on C and D (`unlimited=True`). Shop caps belong on A/B only.
- One moulding per curve (C8201, not C156). Left/right is the same part rotated.
- Hide ambition 0 and A in the wrapper only. Do not delete them from `/levels`.
- Hide broken maps (`charlotte_roval`, `gateway`) with `HIDDEN_FROM_MENU`, do not delete files.
- When a hairpin experiment fails, **revert sequential.py to the full-lap file**. Do not pile another gate on the failed gate.
- Render Free: always check the deploy **source SHA**. Logs of an old row are not the new code.

## What repeatedly failed (do not repeat)

1. **`if best is None: break` plus extra bans at a U-turn.**  
   That is how we got the stump, the triangle, and the empty red outline. The follow dies at Loews and never reaches the swimming pool.

2. **Banning every radius > 280 mm when peak heading ≥ 70–95°.**  
   Street circuits have many kinks. The gate fires in the wrong place, then nothing legal remains.

3. **`s_idx += 2; continue` as a substitute for a piece.**  
   The plastic leaves the red line. The next snap is a chord across Loews or a knot.

4. **`_loops_back` with a 95 mm radius on history.**  
   Hairpins *are* close to earlier points. The check treats Loews as a knot and refuses the only piece that fits.

5. **Changing the follower and the shop cap in the same commit.**  
   Cannot tell which one made the PNG worse.

6. **Hand-tracing a map in 40 points and calling it official.**  
   Charlotte Roval C-shape. If the user supplied a diagram, either sample it densely or hide the track.

7. **Judging a PNG from the previous SHA.**  
   `ffedc55`, `635a61c`, `74fca40`, `d5812b6` were all live while we talked about a newer commit.

## Hairpin strategy that is still allowed

Do this only as a **post-pass**:

1. Run the full-lap sequential follower unchanged (`084f28a`).
2. Detect Loews on the *centreline* (heading change ≥ ~150° over ≤ 200 mm of path).
3. If the plastic already stays within ~80 mm of that arc, stop.
4. Else try to splice 1–2 × C8201 at that s-range and re-follow only the tail.
5. Keep the splice **only if** `len(new) >= 0.85 * len(old)` and the tail still reaches the last 15 % of the centreline.
6. If the splice fails, return the original full lap. Never return the splice stub.

Do not put those rules inside the main `while` until a local Monaco fixture proves the splice keeps the pool.

## Ambition ladder (do not reshuffle without a PNG)

| Letter | Role | Must not do |
| --- | --- | --- |
| 0 / A | Hidden in UI | Tight shop + loose snap = scribble |
| B | Living-room silhouette | 18 pieces is too few for Interlagos |
| C | Near D, modest shop | Do not drop max_pieces below ~400 |
| D | Unlimited follow | Do not add hairpin bans |
| E | True 1:32 length | Will time out on Render Free; warning required |

## Deploy checklist

- Push one concern per commit.
- Manual Deploy → latest.
- Confirm source SHA on the **new** row.
- Rebuild Monaco D and one other road course before calling it good.
- If the PNG is a stub, revert sequential.py in the next commit. Do not "fix forward" with another gate.
