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
    # CHANGED 2026-08-08 (second pass, was 0.05, same as hover): lowered
    # to test the pacing hypothesis directly via a training run rather
    # than via instrumentation first. Reasoning: at position_error_weight
    # =1.0 dominating the per-step reward while far from target, even a
    # moderate 1-2 m/s cruise speed cost -0.05 to -0.1/step under the old
    # weight — non-trivial relative to the position term on a 1-1.5m
    # approach. Lowering to 0.02 cuts that cost by 60%, giving the policy
    # more room to prefer committing to speed over a slow, cautious
    # approach, while the landing phase's own separate, heavier
    # landing_velocity_penalty_weight (0.3, unchanged) still discourages
    # a fast/unsafe touchdown once _in_landing.
    #
    # NOTE: this is a THIRD lever stacked onto the same experiment as the
    # ent_coef/gamma fix and the waypoint_bonus increase (see
    # waypoint_ppo_config() and the note below) — if this run's result is
    # ambiguous, the next step should isolate this change alone, starting
    # fresh from the entropy-fixed-but-pre-this-change checkpoint
    # (archived under model/model_weights/history/), not stack a fourth
    # change on top.
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.02
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
    siblings) explicitly pass task=WaypointTaskConfig() instead."""

    sim: SimConfig = field(default_factory=SimConfig)
    task: HoverTaskConfig | WaypointTaskConfig = field(default_factory=HoverTaskConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)
