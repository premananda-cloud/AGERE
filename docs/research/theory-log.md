# Theory Log

Append-only log of theories, hypotheses, and interpretation — the "why do we
think this happened" counterpart to `docs/training-log.md`'s "what actually
happened." Deliberately kept separate: training-log entries are facts (a run
happened, produced these numbers) and shouldn't be revised after the fact;
this file holds explanations, which are allowed to be wrong, get challenged,
and get superseded by a later entry without editing history out of the record.

Convention, mirroring training-log.md: entries are `Theory YYYY-MM-DD-N`,
append-only, never edited in place. If a later entry supersedes an earlier
one, say so explicitly and reference it — don't delete or rewrite the
original.

Relationship to existing docs/research/ files: `research_findings_01.md` and
`theoretical_framework.md` predate this file and cover broader/earlier
material. This file is specifically for the serial, dated, one-entry-per-
finding pattern — narrower scope, higher frequency, tied directly to
training-log entries by date. Not yet decided whether/how to fold the older
files in; leave as three separate documents until that's worth revisiting.

---

### Theory 2026-08-16-0 — mid-training crash spike as an overcorrection phase

**Observation** (see training-log.md Run 2026-08-16-0): the 500k-step
from-scratch hover run shows a crash-rate spike at 250k-350k steps (80% ->
50% -> 10%, then 0% by 450k) that happens WHILE mean position error over
the same window is actually good (0.034-0.044 m) — second only to the
eventual best checkpoint. Position error alone would not have surfaced this
window as a problem.

**Working hypothesis:** the policy passes through an aggressive, high-gain
correction strategy partway through training — one that reaches the target
fast (hence the good position-error numbers) but overshoots into
`max_tilt_rad` while doing so (hence the crashes), before later training
smooths this into a precise-but-stable strategy by 450k. In short: it
learns "get there fast" before it learns "get there fast AND controlled,"
and the crash window is that gap.

**Status: hypothesis, not confirmed.** This is inferred from the
crash-rate/position-error shape alone, not verified against training
internals. Falsification check, not yet done: pull `train/std` (action
distribution spread) from `tb_logs/hover_logs/PPO_7` or `PPO_8` (whichever
corresponds to this run) for the 250k-350k window specifically. If `std` is
elevated there relative to neighboring windows, that's consistent with the
overcorrection story. If `std` is flat/unremarkable through that window,
the mechanism is wrong and this needs a different explanation — e.g. a
value-function transient unrelated to action variance, or something
specific to a subset of start conditions rather than a general training-time
phase. Don't treat the hypothesis as settled until this check is done.

**Why this matters beyond curiosity:** the hover-robustness-curriculum plan
(`docs/planning/hover-robustness-curriculum-plan.md`) is about to introduce
disturbance kicks on top of whatever policy comes out of Stage 0. If this
window's mechanism is real, it implies the RISK isn't just "does the
policy recover from a kick" in general — it's that a kick landing during an
already-aggressive-correction phase could compound into a worse crash than
the same kick against a calmer policy. That's a reason to keep evaluating
crash rate (not just position error) at every curriculum stage, not a
one-off caveat specific to this run — this is the same "don't trust one
metric alone" lesson the crash-rate table itself just taught, generalized
forward.

**Not yet done:** the `train/std` check above. First thing to do before
citing this theory as settled in any future planning doc.


### Theory 2026-08-16-1 — mid-training crash spike, overcorrection hypothesis REFUTED

Checked via tb_logs/hover_logs/PPO_8, train/std across the 250k-350k crash
window: mean std 200k-250k=1.27, 250k-350k=1.04, 350k-400k=0.94 — strictly
decreasing throughout, no elevation during the crash window. This directly
contradicts Theory 2026-08-16-0's prediction (elevated action variance
during the crash window) and the hypothesis is rejected as stated.

Supersedes: Theory 2026-08-16-0's mechanism claim. The observation it was
explaining (crash spike coexisting with good position-error numbers at
250k-350k) still stands and is still unexplained.

Alternative directions, NOT investigated yet: since variance was falling
while crashes rose, a more likely mechanism is the policy's MEAN action
(not spread) becoming briefly more aggressive during this window — i.e. a
confident-but-wrong gain, not exploratory noise. Checking action magnitude
directly (not logged by default; would need a custom callback) or
`train/policy_gradient_loss` / `approx_kl` for a spike coinciding with
250k-350k would be the next falsifiable step, not done here. Low priority
relative to Stage 1 disturbance work — worth returning to only if a similar
crash-spike pattern reappears during the disturbance curriculum, where it
would matter more.

### Theory 2026-08-16-2 — possible recurrence of unexplained crash instability during 1a fine-tuning

Sub-stage 1a eval (seed=42, 20 episodes/checkpoint) shows 0% crash rate at
every checkpoint (50k-250k, and final ~301k) except the 300,000-step
checkpoint specifically, which shows 10% (2/20, both "tilt"). Structurally
similar to Stage 0's unexplained 250k-350k crash window (theory-log
2026-08-16-0/1) -- possibly the same underlying instability recurring
during continued/warm-started training, possibly independent noise on a
2-episode sample. NOT distinguished yet. Before trusting either
interpretation: re-run this specific checkpoint's eval with a different
seed (e.g. --seed 7) to see if the crash rate reproduces or was a
seed-42-specific artifact of which start conditions happened to align with
a kick badly. If it reproduces, this becomes a real, second occurrence of
the still-unexplained mechanism and is worth prioritizing over sub-stage
1b. If it doesn't reproduce, treat as noise and don't let it block
progression.

### Theory 2026-08-16-3 — Level 1 magnitude was set below the champion's competence floor

Supersedes the framing (not the data) of Theory 2026-08-16-2. That crash
spike at 300k is still unexplained, but the broader context has changed:
sub-stage 1a's entire premise -- that kicks in the 0.1-0.3 m/s range would
require the policy to learn something -- is not supported by data.
Confirmed by direct eval: the untouched hover_champion.zip (zero 1a
training) passes the exact same mastery gate the 1a-trained checkpoints
do -- 0% crash, 100% recovery, every recovery logged as "0 steps" across
every checkpoint including the untrained baseline (see training-log.md Run
2026-08-16-1). The champion already handles this range at baseline.

Practical implication: Theory 2026-08-16-2's proposed reproduction check
(rerun 300k under a different seed) is still worth doing, but low priority
-- even if it reproduces, it's noise/instability in a magnitude range that
doesn't matter for curriculum purposes, since Level 1 isn't teaching
anything regardless of whether that one checkpoint is genuinely flaky.

Actionable correction: Level 1 should be redefined higher, or dropped from
the sub-stage progression entirely in favor of starting at what was Level
2 (0.3-0.6 m/s) in the original plan doc table. Before choosing a new
number, worth a quick scan: try a single manual eval at ~0.4-0.5 m/s
against the untouched champion (no training) to find roughly where its
baseline competence actually breaks -- calibrate the curriculum's floor to
real data instead of the original "2-4% of max speed felt mild" reasoning,
which turned out to be too conservative by an unknown margin. Not yet
done.
