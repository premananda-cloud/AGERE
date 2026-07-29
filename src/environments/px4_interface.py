"""
PX4 / MAVSDK interface for the R&D (SITL) path.

This is intentionally the *only* file that imports mavsdk or knows it's
talking over udpin://0.0.0.0:14540. Gymnasium's API is synchronous, MAVSDK's
is async — this class is the bridge, running a persistent asyncio event loop
in a background thread so `step()`/`reset()` in the env can stay plain
synchronous calls.

When the deployment path moves to ROS 2 / uXRCE-DDS, write a sibling class
(e.g. `ROS2Interface`) that exposes the same methods (connect, arm_and_takeoff,
get_state, send_velocity_body, land, disarm) and swap it in HoverEnv's
constructor. Nothing else should need to change.
"""

import asyncio
import math
import threading
from dataclasses import dataclass

from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityBodyYawspeed

from src.config import ControlConfig


@dataclass
class VehicleState:
    # Position relative to the local NED origin (set at EKF init / takeoff)
    north: float
    east: float
    down: float
    vx: float
    vy: float
    vz: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float


class PX4Interface:
    def __init__(self, config: ControlConfig):
        self.config = config
        self._drone = System()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._latest_state: VehicleState | None = None

    # ---- internal: run a coroutine on the background loop, block for result ----
    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    # ---- connection lifecycle ----
    def connect(self, timeout_s: float = 30.0):
        self._run(self._connect_async(timeout_s))

    async def _connect_async(self, timeout_s: float):
        await self._drone.connect(system_address=self.config.connection_url)
        connected = False
        elapsed = 0.0
        async for state in self._drone.core.connection_state():
            if state.is_connected:
                connected = True
                break
            await asyncio.sleep(0.5)
            elapsed += 0.5
            if elapsed >= timeout_s:
                break
        if not connected:
            raise TimeoutError(
                f"PX4 did not connect within {timeout_s}s on "
                f"{self.config.connection_url}. Check `hostname -I` / "
                "raw UDP arrival per the 2026-07-23 session notes before "
                "assuming this code is at fault."
            )
        # Start a background task that keeps _latest_state updated.
        asyncio.run_coroutine_threadsafe(self._telemetry_loop(), self._loop)

    async def _telemetry_loop(self):
        # NOTE: mavsdk streams position/velocity/attitude on separate
        # generators. For a first working version we poll odometry, which
        # bundles position + velocity + attitude in one message. Split into
        # separate generators later if you need higher-rate individual streams.
        async for odom in self._drone.telemetry.position_velocity_ned():
            pos = odom.position
            vel = odom.velocity
            att = await self._get_latest_attitude()
            self._latest_state = VehicleState(
                north=pos.north_m,
                east=pos.east_m,
                down=pos.down_m,
                vx=vel.north_m_s,
                vy=vel.east_m_s,
                vz=vel.down_m_s,
                roll_deg=att[0],
                pitch_deg=att[1],
                yaw_deg=att[2],
            )

    async def _get_latest_attitude(self):
        # Single-shot pull of the latest attitude Euler angle message.
        async for att in self._drone.telemetry.attitude_euler():
            return (att.roll_deg, att.pitch_deg, att.yaw_deg)
        return (0.0, 0.0, 0.0)

    # ---- flight lifecycle ----
    def arm_and_takeoff(self, altitude_m: float = 3.0):
        self._run(self._arm_and_takeoff_async(altitude_m))

    async def _arm_and_takeoff_async(self, altitude_m: float):
        await self._drone.action.arm()
        await self._drone.action.set_takeoff_altitude(altitude_m)
        await self._drone.action.takeoff()
        await asyncio.sleep(5)  # crude wait for takeoff to complete; replace
        # with an in_air/altitude telemetry check once this path is verified.
        await self._start_offboard()

    async def _start_offboard(self):
        # Offboard mode requires at least one setpoint before it will start.
        await self._drone.offboard.set_velocity_body(
            VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0)
        )
        try:
            await self._drone.offboard.start()
        except OffboardError as e:
            raise RuntimeError(f"Offboard start failed: {e._result.result}") from e

    def land_and_disarm(self):
        self._run(self._land_and_disarm_async())

    async def _land_and_disarm_async(self):
        try:
            await self._drone.offboard.stop()
        except OffboardError:
            pass
        await self._drone.action.land()
        await asyncio.sleep(5)
        try:
            await self._drone.action.disarm()
        except Exception:
            pass

    # ---- per-step control ----
    def send_velocity_body(self, vx: float, vy: float, vz: float, yaw_rate_deg: float):
        self._run(
            self._drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(vx, vy, vz, yaw_rate_deg)
            )
        )

    def get_state(self) -> VehicleState:
        if self._latest_state is None:
            # Telemetry hasn't produced a first sample yet; block briefly.
            self._run(asyncio.sleep(0.1))
        return self._latest_state
