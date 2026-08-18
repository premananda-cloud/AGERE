"""
Central configuration for AGERE's RL tasks (hover/stabilize, waypoint
navigation + landing).

No PX4/MAVSDK config here — AGERE is PyBullet + Gymnasium only. Anything
PX4-related lives in AGERE_sims, a separate repo entirely.
"""

from dataclasses import dataclass, field


@dataclass
class SimConfig:
    """Low-level PyBullet simulation settings — owned by environments/,
    read by DroneSim. No RL concepts here (no reward, no episode length)."""

    pyb_freq: int = 240   # PyBullet physics step rate (Hz)
    ctrl_freq: int = 30   # How often the sim accepts a new action (Hz);
                           # must evenly divide pyb_freq
    gui: bool = False     # True to render the PyBullet window locally
    record: bool = False  # True to save video output (added 2026-08-16).
        # Passed straight through to gym-pybullet-drones' HoverAviary,
        # which handles this itself: with gui=True, produces a real .mp4
        # via PyBullet's own p.startStateLogging(STATE_LOGGING_VIDEO_MP4);
        # with gui=False, saves per-step PNG frames instead (no built-in
        # mp4 muxing in that mode -- needs ffmpeg to stitch afterward).
        # CONFIRMED (read gym-pybullet-drones source directly, 2026-08-16):
        # output always lands in ./results/ relative to the process's cwd
        # -- HoverAviary never exposes output_folder to its own
        # constructor, so it can't be redirected from here regardless of
        # what's passed in DroneSim.


@dataclass
class HoverTaskConfig:
    """RL task definition for hover/stabilize — owned by training/, read by
    the Gymnasium wrapper. Reward, episode length, and termination bounds
    are RL design choices, not physics facts, so they live here rather
    than in SimConfig."""

    target_position: tuple = (0.0, 0.0, 1.0)   # meters, world frame
    episode_len_sec: float = 8.0

    # Reset randomization around target_position. Non-zero on purpose:
    # a fixed start teaches "memorize one trajectory," randomized start
    # teaches "stabilize from anywhere nearby."
    reset_position_jitter: float = 0.3
    reset_yaw_jitter_deg: float = 15.0

    # Truncation bounds (episode ends as failure if exceeded)
    max_xy_distance: float = 1.5     # meters from origin, x or y
    max_altitude: float = 2.0        # meters
    max_tilt_rad: float = 0.4        # roll or pitch, radians (~23 degrees)

    # Reward shaping weights
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01

    # --- Disturbance injection (Stage 1, added 2026-08-16) ---------------
    # Off by default -- existing hover_train.py/hover_evaluate.py runs with
    # no flags are byte-for-byte unaffected. See
    # docs/planning/hover-robustness-curriculum-plan.md "Stage 1" section
    # for the full reasoning behind every number below; this is the
    # implementation of that design, not a fresh decision.
    disturbance_enabled: bool = False

    # How many apply_velocity_kick() events per episode, and where in the
    # episode (control steps) each is allowed to land. Sub-stage 1a uses
    # exactly one kick; later sub-stages (1e/1f) raise
    # disturbance_kicks_per_episode and this generalizes without further
    # wrapper changes -- see hover_gym_wrapper.py's reset().
    disturbance_kicks_per_episode: int = 1
    disturbance_kick_step_min: int = 60    # 2s into an 8s/240-step episode
    disturbance_kick_step_max: int = 150   # 5s in -- leaves room to observe recovery
    disturbance_min_kick_spacing_steps: int = 30   # only matters when kicks_per_episode > 1

    # Magnitude range, m/s -- uniform-sampled per kick, direction random.
    # Grounded in the platform's own max controllable speed (~8.3 m/s, see
    # plan doc): sub-stage 1a = Level 1 (~2-4% of max speed).
    disturbance_kick_min_mps: float = 0.1
    disturbance_kick_max_mps: float = 0.3

    # "Recovered" = position error back under this threshold, sustained for
    # this many consecutive steps, not just touched once. threshold reuses
    # hover_evaluate.py's existing tail_threshold (0.2m) rather than a new
    # disconnected number; hold_steps=60 -> 2s at 30Hz ctrl_freq.
    recovery_threshold_m: float = 0.2
    recovery_hold_steps: int = 60


# Stage 1 sub-stage presets, per docs/planning/hover-robustness-curriculum-plan.md.
# Single source of truth for hover_train.py AND hover_evaluate.py -- both import
# this rather than each keeping their own copy, so training and evaluation can
# never silently drift onto different disturbance configs for "the same" stage.
# Only 1a is defined so far -- add 1b/1c/etc. here as each becomes the active
# sub-stage. Values here must match the plan doc; if they diverge, one of the
# two is wrong.
HOVER_STAGE_PRESETS: dict[str, dict] = {
    "1a": dict(
        disturbance_enabled=True,
        disturbance_kicks_per_episode=1,
        disturbance_kick_step_min=60,
        disturbance_kick_step_max=150,
        disturbance_kick_min_mps=0.1,
        disturbance_kick_max_mps=0.3,
        recovery_threshold_m=0.2,
        recovery_hold_steps=60,
    ),
}


@dataclass
class WaypointTaskConfig:
    """RL task definition for waypoint navigation + landing. Mirrors
    HoverTaskConfig's structure — same reset randomization, truncation
    bounds, and reward-shaping pattern — but adds a waypoint sequence and
    a distinct landing phase. See
    training/gym_wrapper/waypoint_gym_wrapper.py for how these fields are
    used."""

    waypoints: tuple = (
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 1.5),
        (0.0, 1.5, 1.5),
        (-1.0, 1.0, 1.0),
        (0.0, 0.0, 0.5),
    )   # meters, world frame, visited in order

    waypoint_reach_radius: float = 0.15   # meters — within this = "reached," advance to next
    # NOT changed in this pass. tb_logs analysis (2026-08-07/08) shows the
    # policy's route failures are a pacing/entropy problem, not a
    # precision problem (see waypoint_evaluate.py's new "closest approach
    # on the stuck leg" report, added this session) — widen this only if
    # that report shows episodes getting within radius and failing to
    # register, or getting close-but-not-close-enough on their stuck leg.
    # Don't change it blind.
    episode_len_sec: float = 20.0          # longer than hover's 8s — more ground to cover

    # Reset randomization — same idea as hover: don't memorize one exact
    # start, learn to reach waypoint 1 from a nearby range of starts.
    reset_position_jitter: float = 0.2
    reset_yaw_jitter_deg: float = 15.0

    # Truncation bounds — wider than hover's since the route itself
    # covers more xy space; these should comfortably contain all waypoints
    # plus some margin, not hug them tightly.
    max_xy_distance: float = 3.0
    max_altitude: float = 2.5
    max_tilt_rad: float = 0.4

    # Landing phase — begins once the final waypoint is reached.
    landing_target_altitude: float = 0.05   # near-ground, not exactly 0 (avoids
                                              # divide-by-zero / degenerate reward near contact)
    landing_max_velocity: float = 0.15      # m/s — vertical speed at touchdown to count as "soft"
    landing_hold_time_sec: float = 2.0      # must stay down + stable for this long to count as success

    # Reward shaping weights — same pattern as hover, plus one new term.
    #
    # velocity_penalty_weight: TRIED 0.02 (2026-08-08, second pass),
    # REVERTED back to 0.05. Hypothesis going in: the penalty was
    # suppressing commitment to travel across 1-1.5m waypoint gaps.
    # Result: mean waypoints reached DROPPED (3.00/5 -> 1.35/5). tb_logs
    # showed a healthy, normally-adapting training curve (std flat,
    # ep_rew_mean recovering-then-climbing, no instability) — ruling out
    # "just needed more steps to adapt" as the explanation. The stuck-leg
    # diagnostic showed why: with the lower penalty, episodes stalled
    # much CLOSER to target on average (0.271m vs 0.850m) but still
    # failed to durably enter the 0.15m reach radius, mostly on the
    # early/short legs rather than the long ones. Read: the penalty's
    # real job wasn't suppressing travel commitment, it was forcing
    # deceleration/stabilization precisely at each target — removing it
    # made the drone faster but less precise, and precision near-target
    # mattered more for completion than travel speed did. Do not
    # re-lower this without new evidence pointing the other way.
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01

    # CHANGED 2026-08-08 (was 5.0): a one-time +5 bonus is small relative
    # to the per-step position-error penalty accumulated while closing a
    # 1-1.5m gap. At position_error_weight=1.0 and a plausible ~0.4-0.5m
    # average approach distance (consistent with the -0.49/step average
    # implied by the 300k run's -291 ep_rew_mean over 600 steps), each
    # leg accumulates roughly -40 to -50 in per-step penalty before a
    # waypoint bonus can ever land. +5 barely registers against that, and
    # after gamma-discounting back to earlier approach states (see
    # waypoint_ppo_config()'s gamma note) it registers even less. Raised
    # to make "reached and advanced" a reward event actually comparable
    # in scale to the per-step cost of getting there, independent of the
    # entropy/gamma fix below. This is the second lever bundled into this
    # experiment — if the next run's result is ambiguous, un-bundle this
    # from the ent_coef/gamma change before iterating further.
    waypoint_bonus: float = 15.0
    landing_velocity_penalty_weight: float = 0.3   # only active during landing phase — much
                                                     # heavier than the general velocity penalty,
                                                     # specifically to punish crashing into the ground fast

    # ADDED 2026-08-09 — potential-based progress shaping (bigger swing,
    # per-checkpoint decision to try after the 802,816-step checkpoint
    # (3.00/5, archived) turned out to be a local best that every
    # subsequent training attempt made worse, immediately, regardless of
    # which of the smaller reward-weight levers was tried. Diagnosis: the
    # existing per-step penalty (position_error_weight * distance)
    # penalizes absolute distance every step but never directly rewards
    # CLOSING distance — a policy can lower its cumulative penalty by
    # settling into a "reasonably positioned" trajectory without urgency,
    # which is consistent with what was observed (ep_rew_mean improving
    # while waypoints-reached got worse).
    #
    # progress_shaping_weight scales a potential-based shaping term added
    # in WaypointGymEnv.step() (Ng, Harada & Russell 1999): the reward
    # gains +progress_shaping_weight * (distance_closed_this_step). This
    # is positive when the drone got closer to its current target this
    # step, negative when it moved away, ~zero when holding still — a
    # direct, correctly-scaled urgency signal that the raw distance
    # penalty doesn't provide. Potential-based shaping of this form is
    # proven not to change what the OPTIMAL policy is (unlike ad-hoc
    # shaping, which can introduce exploitable side incentives) — it only
    # changes how fast a learner finds it. See waypoint_gym_wrapper.py's
    # step() for the implementation, including the target-switch-cliff
    # handling this needs (naively computing the potential against a
    # NEW target on the exact step a waypoint is reached would punish
    # the moment of success — handled by keeping both sides of the delta
    # relative to the same target the step started with).
    #
    # Weight reasoning: at a plausible ~1-2 m/s cruise, distance closed
    # per step (30Hz) is roughly 0.03-0.07m. At weight 1.0 that's a
    # reward contribution of ~0.03-0.07/step — negligible next to
    # position_error_weight=1.0's typical ~0.3-1.0/step penalty while far
    # from target, i.e. too weak to change behavior. Set to 10.0 so a
    # typical cruise contributes roughly +0.3-0.7/step, comparable in
    # scale to the static penalty it's meant to counteract. This is the
    # single most uncertain new number here — worth a short/GUI sanity
    # check before committing to a full training run, and the first
    # thing to retune if the resulting behavior looks wrong (e.g. reckless
    # straight-line rushing that ignores precision, which would show up
    # as MORE crashes than the 0% seen in every run so far).
    #
    # LANDING PHASE EXCLUSION (added 2026-08-09, same session, before any
    # training run used this weight): this term is DISABLED during the
    # landing phase (self._in_landing) in waypoint_gym_wrapper.py — see
    # _progress_reward()'s docstring there for the magnitude check that
    # motivated it. At realistic unsafe descent speeds (~1 m/s), this
    # term's pull (~+0.33/step) is comparable to, not clearly dominated
    # by, landing_velocity_penalty_weight's safety penalty (~-0.3/step)
    # — a real bias toward rushing the touchdown that velocity_penalty_
    # weight's existing landing-phase swap doesn't cover, since this term
    # wasn't given the same phase-aware treatment when first written.
    # Caught before any run ever reached the landing phase, so this is a
    # design correction, not an observed failure.
    #
    # Simplification note: strict Ng et al. potential-based shaping
    # multiplies the future term by the learner's discount factor gamma
    # (F = gamma*Phi(s') - Phi(s)). This implementation uses the
    # undiscounted difference instead (gamma implicitly 1) for
    # simplicity — waypoint_ppo_config()'s gamma=0.995 is close enough to
    # 1 that the exact optimality-preservation guarantee's violation is
    # negligible, and threading the PPO-level gamma into the environment
    # (which doesn't otherwise know about it) isn't worth the coupling
    # for a demo-scoped project.
    progress_shaping_weight: float = 10.0



@dataclass
class PPOConfig:
    """Hyperparameters passed to stable-baselines3 PPO."""

    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.01
    net_arch: dict = field(default_factory=lambda: {"pi": [64, 64], "vf": [64, 64]})
    total_timesteps: int = 200_000


def waypoint_ppo_config() -> PPOConfig:
    """PPO hyperparameters for the waypoint task specifically — NOT the
    same as hover's default PPOConfig(). Added 2026-08-08 after tb_logs
    analysis of the 2026-08-06/07 waypoint runs showed train/std climbing
    monotonically (0.85 -> 1.18) and entropy_loss growing more negative
    the entire 300k-step run, instead of converging the way it did for
    hover (std settled to 0.68-0.85). approx_kl and clip_fraction stayed
    in healthy ranges throughout and explained_variance stayed high
    (0.96-0.98) — so this isn't PPO instability or a bad value function,
    it's specifically the policy's action distribution failing to
    sharpen. Two changes address the two candidate mechanisms:

    - ent_coef lowered (0.01 -> 0.003): ent_coef applies a constant pull
      toward higher entropy every update. Hover's position-error gradient
      was strong enough to overpower that pull as the policy improved.
      Waypoint's gradient is weaker/more ambiguous (see gamma note below),
      so the entropy term was winning by default rather than being
      overridden. Lowering it directly weakens that pull.
    - gamma raised (0.99 -> 0.995): 0.99 gives an effective credit horizon
      of ~100 steps (1/(1-gamma)); closing a single 1-1.5m waypoint gap
      takes roughly that many steps on the current pace (~108 steps for
      an even 5-way split of the 600-step/20s episode budget). That means
      the one-time waypoint_bonus was landing right at the edge of, or
      past, the horizon over which it could meaningfully shape earlier
      approach states — it was arriving "too late" in credit-assignment
      terms even when the bonus fired. 0.995 extends the effective
      horizon to ~200 steps, giving the (now-larger, see
      WaypointTaskConfig.waypoint_bonus) bonus more reach into the states
      that most need it.

    CRITICAL: PPO.load() restores hyperparameters (including gamma and
    ent_coef) from the checkpoint file itself, NOT from whatever
    PPOConfig is passed alongside it — this is already documented in
    waypoint_train.py's module docstring. That means simply changing
    the values here has NO effect on an --init-from (warm-started) run
    unless waypoint_train.py explicitly overrides model.gamma and
    model.ent_coef on the loaded model after PPO.load() — which it now
    does. See waypoint_train.py for that override. Forgetting this step
    is exactly how a fix like this one would silently do nothing.
    """
    return PPOConfig(gamma=0.995, ent_coef=0.003)


@dataclass
class ProjectConfig:
    """task defaults to HoverTaskConfig for backward compatibility —
    hover_train.py/hover_evaluate.py/hover_demo.py calling ProjectConfig()
    with no args are unaffected. waypoint_train.py (and its evaluate/demo
    siblings) explicitly pass task=WaypointTaskConfig() instead.

    PrecisionFlightTaskConfig (added 2026-08-11) was removed 2026-08-16 --
    judged not worth keeping (design/code quality), discarded rather than
    archived. Its checkpoints/tb_logs/gym_wrapper/train/evaluate files were
    removed in the same pass. If disturbance injection for hover is needed,
    see HoverTaskConfig's disturbance_* fields (added the same day, a
    from-scratch design per docs/planning/hover-robustness-curriculum-plan.md
    Stage 1 -- not a revival of this class's continuous per-step-probability
    model)."""

    sim: SimConfig = field(default_factory=SimConfig)
    task: HoverTaskConfig | WaypointTaskConfig = field(default_factory=HoverTaskConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)
