"""
WaypointGymEnv: the Gymnasium environment for waypoint navigation +
landing.

Mirrors HoverGymEnv's split (Gymnasium concerns here, pure physics in
DroneSim) — see hover_gym_wrapper.py and docs/code-structure.md. Two
things are genuinely different from hover, not just cosmetic:

1. There's a moving target. "Target" for observation/reward purposes is
   the current waypoint's position while the route is in progress, and
   switches to a fixed landing target (xy of the final waypoint, low
   altitude) once the route completes. self._current_target() is the
   single place that decides which.

2. This task has a real endpoint. Hover always ends via truncation
   (timeout/out_of_bounds/tilt) — there's no "done, succeeded" state,
   just "still going" or "failed/timed out." Waypoint nav can actually
   finish: reach every waypoint, then hold a soft landing for
   landing_hold_time_sec, and the episode TERMINATES (not truncates) as
   a success. This is why `terminated` is no longer hardcoded False here
   the way it is in hover_gym_wrapper.py.

Observation space is intentionally IDENTICAL in shape to HoverGymEnv's (9
floats: pos_error, velocity, roll/pitch/yaw_error) — an earlier draft of
this file added a 10th "landing_phase" flag, but that breaks weight
transfer from a hover checkpoint (SB3's PPO.load() rebuilds the policy's
input layer from the saved obs shape; a 9-vs-10 mismatch fails to load).
Keeping the shapes identical means waypoint_train.py's --init-from can
warm-start directly from a trained hover_stabilize checkpoint — the
policy already knows "minimize position error, don't move too fast,"
which is most of what waypoint-following needs anyway. The landing phase
is tracked internally (self._in_landing) and used for reward/termination
logic; the policy just isn't told about it explicitly via a dedicated
obs dimension.

BUGFIX 2026-08-08 — stale obs on intermediate waypoint transitions:
waypoint_evaluate.py's per-leg "closest approach" diagnostic (added the
same day) reported every stuck episode getting within ~0.148m of its
target regardless of actual outcome — including episodes that timed out
1.4m from the landing target, which is impossible if the number were
real. Root cause: step() only re-derived obs after a transition into the
LANDING phase (self._in_landing guard below), not after an intermediate
waypoint transition (1->2, 2->3, 3->4). On any transition step, obs (and
therefore that step's reward and info["position_error_norm"]) was left
computed against the just-passed target instead of the new one — the
exact staleness the original comment already described for the landing
case, just not generalized to every case that has it. Fixed by dropping
the self._in_landing condition: any waypoint_bonus > 0 means a
transition just happened and obs needs re-deriving, landing or not. This
also means training itself was getting a (narrow — one step out of ~600
per episode) wrong observation/reward on every intermediate transition;
not expected to be a major factor in the low route-completion rate, but
worth being aware of if re-evaluating older checkpoints trained before
this fix.

ADDED 2026-08-09 — potential-based progress shaping: after the
entropy-runaway fix, the best checkpoint found (802,816 cumulative steps,
3.00/5 waypoints on a fixed eval seed) turned out to be a local best —
every subsequent training attempt made it worse, almost immediately,
regardless of which reward-weight lever was tried (velocity penalty both
lowered and reverted). Diagnosis: the existing per-step penalty punishes
absolute distance but never directly rewards closing it, so a policy can
lower cumulative penalty via a "reasonably positioned but unhurried"
trajectory rather than committing to route completion. Added a
potential-based shaping term (Ng, Harada & Russell 1999) that rewards
distance closed each step, with careful handling of the reward cliff
that would otherwise occur at the exact step a waypoint is reached (see
_progress_reward()'s docstring). See config.py's
WaypointTaskConfig.progress_shaping_weight for full reasoning and the
weight-magnitude estimate. This is a bigger, less-tested change than
anything applied so far — the 802,816-step checkpoint remains archived
as a fallback if this doesn't pan out.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import ACTION_DIM, normalize_action
from src.config import ProjectConfig
from src.environments.drone_sim import DroneSim


class WaypointGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task

        self.sim = DroneSim(self.config.sim)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
        # 9 floats: pos_error (3), velocity (3), roll/pitch/yaw_error (3).
        # Deliberately identical shape to HoverGymEnv's observation_space —
        # see module docstring for why (weight transfer via --init-from).
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32
        )

        self._waypoints = [np.asarray(wp, dtype=np.float32) for wp in self.task.waypoints]
        self._step_count = 0
        self._max_steps = int(self.task.episode_len_sec * self.config.sim.ctrl_freq)
        self._target_yaw_rad = 0.0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        self._waypoint_idx = 0          # index into self._waypoints of the
                                          # current target; == len(waypoints)
                                          # once the route is complete
        self._in_landing = False
        self._landing_hold_steps = 0     # consecutive steps meeting the
                                          # soft-landing condition

        # ADDED 2026-08-09: distance to the current target as of the end
        # of the previous step, used by the potential-based progress
        # shaping term in step(). Set properly in reset(); the value
        # here is just a placeholder before the first reset() call.
        self._prev_dist_to_target = 0.0

    # ------------------------------------------------------------------
    def _landing_target(self) -> np.ndarray:
        """xy of the final waypoint, at the configured landing altitude."""
        last_wp = self._waypoints[-1]
        return np.array([last_wp[0], last_wp[1], self.task.landing_target_altitude], dtype=np.float32)

    def _current_target(self) -> np.ndarray:
        if self._in_landing:
            return self._landing_target()
        return self._waypoints[self._waypoint_idx]

    def _obs_from_state(self, state) -> np.ndarray:
        pos_error = self._current_target() - state.position
        yaw_error = self._target_yaw_rad - state.orientation_rpy[2]
        yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi  # wrap to [-pi, pi]
        return np.concatenate(
            [
                pos_error,
                state.velocity,
                np.array([state.orientation_rpy[0], state.orientation_rpy[1], yaw_error], dtype=np.float32),
            ]
        ).astype(np.float32)

    def _advance_waypoint_if_reached(self, obs: np.ndarray) -> float:
        """Checks distance to the current waypoint; advances the index and
        returns a one-time bonus if reached. Returns 0.0 otherwise (and
        always 0.0 once in the landing phase — this only governs the
        waypoint-following part of the route).

        Called once per step, before reward is computed, so the bonus
        lands in the same step the waypoint was reached rather than one
        step later.
        """
        if self._in_landing:
            return 0.0

        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        if pos_error_norm > self.task.waypoint_reach_radius:
            return 0.0

        self._waypoint_idx += 1
        if self._waypoint_idx >= len(self._waypoints):
            self._in_landing = True
            self._landing_hold_steps = 0
        return self.task.waypoint_bonus

    def _progress_reward(self, dist_to_target_this_step: float) -> float:
        """ADDED 2026-08-09 — potential-based progress shaping. See
        config.py's WaypointTaskConfig.progress_shaping_weight docstring
        for the full reasoning.

        Returns progress_shaping_weight * (distance closed this step),
        i.e. positive if the drone got closer to its CURRENT target since
        the last step, negative if it moved away, ~zero once in landing
        (see below).

        CRITICAL: dist_to_target_this_step must be measured against the
        SAME target as self._prev_dist_to_target (both relative to
        whatever target was active at the START of this step), NOT a
        target that was just switched to mid-step. Call this BEFORE
        _advance_waypoint_if_reached() has caused any target switch to
        take effect in the caller's understanding of "current target" —
        in practice, call it with the pos_error_norm from the ORIGINAL
        (pre-transition-recompute) obs. Using a post-transition distance
        here would create a reward cliff at the exact moment a waypoint
        is reached (large negative spike from "very close to old target"
        to "far from new target"), punishing success instead of ignoring
        it — the discrete waypoint_bonus is what's supposed to reward
        that event, not this term.

        DISABLED DURING LANDING (added 2026-08-09, same session): a
        magnitude check found this term is roughly comparable in size to
        landing_velocity_penalty_weight's safety penalty at unsafe
        descent speeds, not clearly dominated by it — at 1.0 m/s descent
        (well above landing_max_velocity=0.15), progress reward is
        ~+0.33/step against a velocity penalty of ~-0.3/step, a net
        +0.03/step bias toward descending faster than the safety limit
        allows. velocity_penalty_weight already gets swapped for a
        heavier landing-specific value once self._in_landing — this term
        wasn't given the same phase-aware treatment when first added.
        Since no episode has reached the landing phase in any run so
        far, there's no empirical track record to catch this kind of
        bias if it exists; zeroing it out here removes the risk before
        it's ever exercised, rather than finding out during the first
        run that actually reaches landing. The landing phase already has
        purpose-built machinery for a controlled descent (the heavier
        velocity penalty, the hold-timer, the hard_landing failure mode)
        — this term's job (encouraging commitment across long route
        legs) doesn't meaningfully apply to a ~0.45m final descent
        anyway.
        """
        if self._in_landing:
            return 0.0
        return self.task.progress_shaping_weight * (self._prev_dist_to_target - dist_to_target_this_step)

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray, waypoint_bonus: float) -> float:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(obs[3:6]))
        action_delta = float(np.linalg.norm(action - self._prev_action))

        # Landing phase uses a heavier velocity penalty (per config docstring:
        # specifically to punish crashing into the ground fast) in place of
        # the general one — not in addition to it, since both terms penalize
        # the same vel_norm and stacking them would double-count.
        vel_weight = (
            self.task.landing_velocity_penalty_weight if self._in_landing
            else self.task.velocity_penalty_weight
        )

        return (
            -self.task.position_error_weight * pos_error_norm
            - vel_weight * vel_norm
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
            + waypoint_bonus
        )

    def _check_landing(self, state) -> bool:
        """Updates the landing hold-timer and returns True on a completed
        (successful) soft landing. Only called while self._in_landing.

        Contact is modeled as altitude at-or-below landing_target_altitude
        (see config.py's note on why that's not exactly 0) — a deliberate
        altitude+velocity simplification rather than real PyBullet contact
        detection; flagged in the handoff as fine for a demo, worth
        revisiting for more precision later.
        """
        vel_norm = float(np.linalg.norm(state.velocity))
        touched_down = state.position[2] <= self.task.landing_target_altitude

        if not touched_down:
            self._landing_hold_steps = 0
            return False

        if vel_norm > self.task.landing_max_velocity:
            # Ground contact at unsafe speed — handled as a hard_landing
            # truncation by the caller, not treated as a hold-timer reset;
            # the caller checks this same condition separately.
            return False

        self._landing_hold_steps += 1
        hold_steps_needed = int(round(self.task.landing_hold_time_sec * self.config.sim.ctrl_freq))
        return self._landing_hold_steps >= hold_steps_needed

    def _truncation_reason(self, state) -> str | None:
        """Same out_of_bounds/tilt/timeout pattern as hover_gym_wrapper.py,
        plus hard_landing: fast ground contact during the landing phase.
        Does NOT check for successful landing — that's a termination
        (see step()), handled separately since it's a success, not a
        failure/timeout end.
        """
        x, y = state.position[0], state.position[1]
        roll, pitch = state.orientation_rpy[0], state.orientation_rpy[1]
        if (
            abs(x) > self.task.max_xy_distance
            or abs(y) > self.task.max_xy_distance
            or state.position[2] > self.task.max_altitude
        ):
            return "out_of_bounds"
        if abs(roll) > self.task.max_tilt_rad or abs(pitch) > self.task.max_tilt_rad:
            return "tilt"
        if self._in_landing:
            vel_norm = float(np.linalg.norm(state.velocity))
            touched_down = state.position[2] <= self.task.landing_target_altitude
            if touched_down and vel_norm > self.task.landing_max_velocity:
                return "hard_landing"
        if self._step_count >= self._max_steps:
            return "timeout"
        return None

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        first_wp = self._waypoints[0]
        jitter = self.task.reset_position_jitter
        start_position = first_wp + self.np_random.uniform(-jitter, jitter, size=3)
        start_position[2] = max(start_position[2], 0.1)  # never spawn below ground

        yaw_jitter_rad = np.deg2rad(self.task.reset_yaw_jitter_deg)
        self._target_yaw_rad = 0.0
        start_yaw = self.np_random.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        state = self.sim.reset_episode(start_position, start_yaw)

        self._step_count = 0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self._waypoint_idx = 0
        self._in_landing = False
        self._landing_hold_steps = 0

        obs = self._obs_from_state(state)
        # ADDED 2026-08-09: seed the progress-shaping baseline with the
        # starting distance, so the very first step's delta reflects real
        # progress made rather than a spurious jump from 0.
        self._prev_dist_to_target = float(np.linalg.norm(obs[0:3]))

        info = {
            "start_position": start_position.copy(),
            "start_yaw_rad": float(start_yaw),
        }
        return obs, info

    def step(self, action: np.ndarray):
        command = normalize_action(action)
        state = self.sim.apply_action(command)

        obs = self._obs_from_state(state)

        # ADDED 2026-08-09: progress shaping computed from THIS obs
        # (relative to whatever target was active at the START of this
        # step) BEFORE any waypoint transition below can switch the
        # target — see _progress_reward()'s docstring for why computing
        # this against a post-transition target would create a reward
        # cliff at the exact moment of success.
        dist_this_step = float(np.linalg.norm(obs[0:3]))
        progress_reward = self._progress_reward(dist_this_step)

        waypoint_bonus = self._advance_waypoint_if_reached(obs)
        # BUGFIX 2026-08-08: re-derive obs on ANY waypoint transition, not
        # just the transition into landing. pos_error in obs above was
        # computed against the *pre-advance* target, which is one step
        # stale (still the just-reached waypoint, not the new current
        # target) for the step ANY waypoint is reached — intermediate
        # waypoints included, not just the final one. Previously this
        # only fired on `self._in_landing and waypoint_bonus > 0.0`,
        # which silently left every intermediate transition (1->2, 2->3,
        # 3->4) stale — found via waypoint_evaluate.py's per-leg
        # diagnostic reporting impossible "closest approach" values
        # (~0.148m on legs that actually ended 1.4m from target).
        if waypoint_bonus > 0.0:
            obs = self._obs_from_state(state)

        reward = self._compute_reward(obs, action, waypoint_bonus) + progress_reward

        # ADDED 2026-08-09: cache THIS step's distance to whatever target
        # is current NOW (post-transition if one happened) as the
        # baseline for next step's progress delta. Using the
        # (possibly-recomputed) obs here, not dist_this_step, is
        # deliberate — next step's target is the new one if a transition
        # just happened, and next step's delta needs a same-target
        # baseline to compare against.
        self._prev_dist_to_target = float(np.linalg.norm(obs[0:3]))

        self._step_count += 1

        success = self._in_landing and self._check_landing(state)
        reason = None if success else self._truncation_reason(state)
        terminated = success
        truncated = (not success) and (reason is not None)

        info = {
            "position_error_norm": float(np.linalg.norm(obs[0:3])),
            "waypoints_reached": min(self._waypoint_idx, len(self._waypoints)),
            "success": success,
            "progress_reward": progress_reward,
        }
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt", "hard_landing")

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
