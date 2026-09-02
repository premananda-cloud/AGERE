"""
HoverGymEnv: the Gymnasium environment for the hover/stabilize task.

This is where Gymnasium lives — action_space, observation_space, reward,
episode termination/truncation. It wraps DroneSim (pure PyBullet, no RL
concepts) and adds everything RL-specific on top. See docs/code-structure.md
for the reasoning behind this split.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import ACTION_DIM, normalize_action
from src.config import ProjectConfig, DISTURBANCE_TYPES, DISTURBANCE_LEVELS
from src.environments.drone_sim import DroneSim


class HoverGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None, forced_disturbance: dict | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task
        # Demo-only override (2026-08-25): bypasses the normal random
        # type/level/magnitude sampling in _sample_disturbance_event() so a
        # specific case can be reproduced on demand -- e.g. reliably
        # triggering "kick L4" to inspect the late-episode instability
        # pattern flagged in training-log.md instead of waiting for a
        # random draw to land on it. None (default) preserves normal
        # training/eval sampling behavior unchanged. Keys: "type" (required,
        # one of DISTURBANCE_TYPES), "level" (optional, else random 1-5),
        # "magnitude" (optional, else sampled within the level's range),
        # "onset_step" (optional, else sampled within the normal window).
        self._forced_disturbance = forced_disturbance

        self.sim = DroneSim(self.config.sim)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
        # 9 floats: pos_error (3), velocity (3), roll/pitch/yaw_error (3).
        # Relative pos_error and yaw_error (not absolute position/yaw) so
        # the policy generalizes to any target rather than memorizing one.
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32
        )

        self._step_count = 0
        self._max_steps = int(self.task.episode_len_sec * self.config.sim.ctrl_freq)
        self._target_yaw_rad = 0.0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        # --- Disturbance (3-type / 5-level scoped design, superseding the
        # single-kick-only Stage 1a mechanism) ------------------------------
        # ONE disturbance event per episode, type + level sampled uniformly
        # from DISTURBANCE_TYPES/config.task.disturbance_types_active; see
        # _sample_disturbance_event() for the full reasoning. All reset in
        # reset(); step() applies the event at the right step(s) and tracks
        # recovery. Kept as plain instance state, same pattern as
        # _step_count/_prev_action above.
        self._disturbance_event: dict | None = None
        self._last_event_step: int | None = None
        self._recovery_hold_counter = 0
        self._recovery_achieved = False
        self._recovery_time_steps: int | None = None
        self._disturbance_fired = False
        self._wind_errors_during_window: list[float] = []
        # Sustained-tilt crash tracking (2026-08-25 fix) -- see
        # config.py's max_tilt_hold_steps docstring for why this exists.
        self._tilt_breach_counter = 0

    def _sample_disturbance_event(self) -> dict | None:
        """Sample this episode's single disturbance event: which of the 3
        scoped types (kick/torque/wind), which of the 5 magnitude levels,
        the concrete magnitude within that level's range, a randomized
        direction, and the onset step (plus, for wind, the active window).

        Design note — bounded, not open-ended: rather than a strict
        cumulative curriculum of narrow sub-stage presets (1a -> 1b ->
        1c -> ...), which already produced one wasted 300k-step run on an
        under-powered single-level preset (training-log.md Run
        2026-08-16-1), this samples the whole scoped 3-type x 5-level
        space directly in one training run. Levels exist for EVAL
        reporting granularity, not separate training phases.

        Level is sampled uniformly over 1..5 (not magnitude sampled
        uniformly over the type's full range) so severe levels get equal
        training exposure regardless of how wide their raw span is.

        Only called from reset(); step() just consumes the returned dict.
        Returns None if disturbance is disabled or no type/window is
        available this episode.
        """
        if self._forced_disturbance is not None:
            return self._build_forced_disturbance_event()
        if not getattr(self.task, "disturbance_enabled", False):
            return None

        active_types = list(self.task.disturbance_types_active)
        if not active_types:
            return None
        type_name = active_types[int(self.np_random.integers(0, len(active_types)))]
        type_cfg = DISTURBANCE_TYPES[type_name]

        level = int(self.np_random.integers(1, DISTURBANCE_LEVELS + 1))  # 1..5 inclusive
        lo, hi = type_cfg.level_bounds[level - 1], type_cfg.level_bounds[level]
        magnitude = float(self.np_random.uniform(lo, hi))

        direction = self.np_random.normal(size=3)
        norm = np.linalg.norm(direction)
        direction = direction / norm if norm > 1e-6 else np.array([1.0, 0.0, 0.0])

        lo_step = self.task.disturbance_kick_step_min
        hi_step = self.task.disturbance_kick_step_max
        # Clamp so onset + duration + a full recovery-hold window all fit
        # inside this episode. Reserving room for recovery_hold_steps here
        # (not just duration_steps) matters for sustained types (wind):
        # without it, an event ending late in the sampling window leaves
        # no room for the required recovery hold before the episode ends,
        # making "recovered" structurally unreachable regardless of policy
        # quality -- this is exactly what happened before this fix (see
        # WIND_CONFIG's 2026-08-25 comment in config.py). Applies to all
        # types uniformly so this can't silently recur for a future type,
        # even though it's a no-op correction for instantaneous types
        # (duration_steps=1) whose onset was already comfortably clear of
        # this constraint.
        hi_step = min(hi_step, self._max_steps - 1 - type_cfg.duration_steps - self.task.recovery_hold_steps)
        if lo_step >= hi_step:
            return None
        onset_step = int(self.np_random.integers(lo_step, hi_step + 1))

        return {
            "type": type_name,
            "level": level,
            "magnitude": magnitude,
            "direction": direction,
            "onset_step": onset_step,
            "duration_steps": type_cfg.duration_steps,
            "end_step": onset_step + type_cfg.duration_steps - 1,
        }

    def _build_forced_disturbance_event(self) -> dict:
        """Build a disturbance event from self._forced_disturbance instead
        of random sampling -- see __init__'s docstring for the accepted
        keys. Unset optional keys (level/magnitude/onset_step) still get
        randomized the normal way, so e.g. forcing only "type": "kick"
        gives a random level/magnitude/onset each episode, same variety
        as normal sampling, just restricted to one type.
        """
        forced = self._forced_disturbance
        type_name = forced["type"]
        type_cfg = DISTURBANCE_TYPES[type_name]

        level = forced.get("level")
        if level is None:
            level = int(self.np_random.integers(1, DISTURBANCE_LEVELS + 1))

        magnitude = forced.get("magnitude")
        if magnitude is None:
            lo, hi = type_cfg.level_bounds[level - 1], type_cfg.level_bounds[level]
            magnitude = float(self.np_random.uniform(lo, hi))
        else:
            magnitude = float(magnitude)

        direction = self.np_random.normal(size=3)
        norm = np.linalg.norm(direction)
        direction = direction / norm if norm > 1e-6 else np.array([1.0, 0.0, 0.0])

        onset_step = forced.get("onset_step")
        if onset_step is None:
            lo_step = self.task.disturbance_kick_step_min
            hi_step = min(
                self.task.disturbance_kick_step_max,
                self._max_steps - 1 - type_cfg.duration_steps - self.task.recovery_hold_steps,
            )
            onset_step = int(self.np_random.integers(lo_step, hi_step + 1)) if lo_step < hi_step else lo_step

        return {
            "type": type_name,
            "level": level,
            "magnitude": magnitude,
            "direction": direction,
            "onset_step": onset_step,
            "duration_steps": type_cfg.duration_steps,
            "end_step": onset_step + type_cfg.duration_steps - 1,
        }

    # ------------------------------------------------------------------
    def _obs_from_state(self, state) -> np.ndarray:
        pos_error = np.asarray(self.task.target_position, dtype=np.float32) - state.position
        yaw_error = self._target_yaw_rad - state.orientation_rpy[2]
        # wrap to [-pi, pi]
        yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi
        return np.concatenate(
            [
                pos_error,
                state.velocity,
                np.array([state.orientation_rpy[0], state.orientation_rpy[1], yaw_error], dtype=np.float32),
            ]
        ).astype(np.float32)

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray) -> float:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(obs[3:6]))
        action_delta = float(np.linalg.norm(action - self._prev_action))

        return (
            -self.task.position_error_weight * pos_error_norm
            - self.task.velocity_penalty_weight * vel_norm
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
        )

    def _truncation_reason(self, obs: np.ndarray, state) -> str | None:
        """Returns why an episode ended, or None if it's still going.

        Distinguishing "crash" (out_of_bounds/tilt) from "timeout" matters
        for evaluation — see docs/hover-model-plan.md Stage 2, which
        requires <10% crash rate specifically, not just "episode ended."

        Tilt uses self._tilt_breach_counter (updated in step(), BEFORE this
        is called) rather than an instantaneous roll/pitch check -- requires
        max_tilt_hold_steps CONSECUTIVE steps over the line, not a single
        momentary touch. See config.py's max_tilt_hold_steps docstring:
        hover_tilt_diagnostic.py found the old single-step check was
        truncating legitimate hard-tilt recovery maneuvers (68% of
        tilt-truncated episodes recovered cleanly when just given room),
        not catching real crashes. out_of_bounds/altitude remain
        single-step checks deliberately -- there's no equivalent "brief
        excursion that self-corrects" case for physically leaving the
        bounded volume the way there is for a transient tilt spike.
        """
        x, y = state.position[0], state.position[1]
        if (
            abs(x) > self.task.max_xy_distance
            or abs(y) > self.task.max_xy_distance
            or state.position[2] > self.task.max_altitude
        ):
            return "out_of_bounds"
        if self._tilt_breach_counter >= self.task.max_tilt_hold_steps:
            return "tilt"
        if self._step_count >= self._max_steps:
            return "timeout"
        return None

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        jitter = self.task.reset_position_jitter
        start_position = np.asarray(self.task.target_position, dtype=np.float32) + self.np_random.uniform(
            -jitter, jitter, size=3
        )
        start_position[2] = max(start_position[2], 0.1)  # never spawn below ground

        yaw_jitter_rad = np.deg2rad(self.task.reset_yaw_jitter_deg)
        self._target_yaw_rad = 0.0
        start_yaw = self.np_random.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        state = self.sim.reset_episode(start_position, start_yaw)

        self._step_count = 0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        # Disturbance state, per-episode -- sampled AFTER super().reset()
        # seeds self.np_random, so this respects the same seed as the rest
        # of the episode's randomization (position/yaw jitter above).
        self._disturbance_event = self._sample_disturbance_event()
        self._last_event_step = None
        self._recovery_hold_counter = 0
        self._recovery_achieved = False
        self._recovery_time_steps = None
        self._disturbance_fired = False
        self._wind_errors_during_window = []
        self._tilt_breach_counter = 0

        obs = self._obs_from_state(state)
        # Exposed so callers (evaluate.py's tail diagnostics, in particular)
        # can correlate final outcome with the randomized start condition,
        # rather than only ever seeing the post-jitter obs.
        info = {
            "start_position": start_position.copy(),
            "start_yaw_rad": float(start_yaw),
        }
        return obs, info

    def step(self, action: np.ndarray):
        command = normalize_action(action)
        state = self.sim.apply_action(command)

        obs = self._obs_from_state(state)
        reward = self._compute_reward(obs, action)

        self._step_count += 1

        # --- Disturbance: fire/sustain the scheduled event, if this is the
        # step (or step range) for it. Applied AFTER apply_action() advances
        # physics for this step, so the effect is visible starting next
        # step's observation -- matches apply_velocity_kick()'s own
        # semantics (instantaneous velocity add, not routed through this
        # step's control command); apply_sustained_force() for wind carries
        # the analogous caveat (see DroneSim docstring).
        ev = self._disturbance_event
        if ev is not None:
            if ev["type"] in ("kick", "torque") and self._step_count == ev["onset_step"]:
                delta = ev["direction"] * ev["magnitude"]
                if ev["type"] == "kick":
                    self.sim.apply_velocity_kick(delta)
                else:
                    self.sim.apply_torque_kick(delta)
                self._disturbance_fired = True
                self._last_event_step = self._step_count
                self._recovery_hold_counter = 0
                self._recovery_achieved = False

            elif ev["type"] == "wind" and ev["onset_step"] <= self._step_count <= ev["end_step"]:
                force = ev["direction"] * ev["magnitude"]
                self.sim.apply_sustained_force(force)
                self._disturbance_fired = True
                self._wind_errors_during_window.append(float(np.linalg.norm(obs[0:3])))
                if self._step_count == ev["end_step"]:
                    # Wind has just stopped this step -- start the same
                    # recovery-hold tracking used for kick/torque, anchored
                    # to the END of the window (recovery from a sustained
                    # push is measured from when the push stops, not from
                    # when it started).
                    self._last_event_step = self._step_count
                    self._recovery_hold_counter = 0
                    self._recovery_achieved = False

        # --- Recovery tracking, relative to the most recent event -------
        if self._last_event_step is not None and not self._recovery_achieved:
            pos_error_norm = float(np.linalg.norm(obs[0:3]))
            if pos_error_norm < self.task.recovery_threshold_m:
                self._recovery_hold_counter += 1
                if self._recovery_hold_counter >= self.task.recovery_hold_steps:
                    self._recovery_achieved = True
                    # Steps from event to the START of the sustained-recovery
                    # window, not to when the hold finished -- same
                    # convention as the original Stage 1a tracking.
                    self._recovery_time_steps = (
                        self._step_count - self._recovery_hold_counter + 1 - self._last_event_step
                    )
            else:
                self._recovery_hold_counter = 0  # violation resets the streak, same
                                                   # non-momentary-touch pattern as
                                                   # landing_hold_time_sec elsewhere

        # Update sustained-tilt breach counter BEFORE checking truncation,
        # so _truncation_reason() sees this step's value. Uses `state`
        # (world-frame roll/pitch), not `obs` (which holds yaw_error, not
        # raw yaw, in that slot) -- see _obs_from_state().
        tilt_now = max(abs(state.orientation_rpy[0]), abs(state.orientation_rpy[1]))
        if tilt_now > self.task.max_tilt_rad:
            self._tilt_breach_counter += 1
        else:
            self._tilt_breach_counter = 0

        reason = self._truncation_reason(obs, state)
        truncated = reason is not None
        terminated = False  # this task has no early-success condition; it
        # ends via truncation (out of bounds / tilt / timeout) only

        info = {}
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt")
        info["position_error_norm"] = float(np.linalg.norm(obs[0:3]))

        # Disturbance summary info, only meaningful (and only populated)
        # once the episode has actually seen its event fire -- callers
        # should check "disturbance_fired" before reading recovery fields.
        if self._disturbance_fired:
            info["disturbance_fired"] = True
            info["disturbance_type"] = ev["type"]
            info["disturbance_level"] = ev["level"]
            info["disturbance_magnitude"] = ev["magnitude"]
            info["recovered"] = self._recovery_achieved
            info["recovery_time_steps"] = self._recovery_time_steps
            if ev["type"] == "wind" and self._wind_errors_during_window:
                info["wind_steady_state_error_mean"] = float(np.mean(self._wind_errors_during_window))

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
