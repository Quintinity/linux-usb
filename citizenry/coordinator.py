"""Task Coordinator — orchestrates multi-citizen composite tasks.

Handles tasks that require multiple citizens working together:
- visual_pick_and_place: camera detects → arm picks
- color_sorting: camera detects all → arm sorts each by color
- visual_inspection: camera captures → governor analyzes

The coordinator breaks composite tasks into sequential sub-tasks
and dispatches them through the marketplace.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from .visual_tasks import plan_pick_and_place, plan_sort_sequence, camera_to_arm_position, HOME_POSITION, WORKSPACE


@dataclass
class CompositeTaskResult:
    """Result of a multi-step composite task."""
    success: bool = False
    steps_completed: int = 0
    steps_total: int = 0
    detections: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    error: str = ""
    details: dict = field(default_factory=dict)


class TaskCoordinator:
    """Coordinates multi-citizen tasks for the governor."""

    def __init__(self, governor):
        self.governor = governor

    async def execute_visual_pick_and_place(
        self,
        target_color: str | None = None,
        timeout: float = 30.0,
    ) -> CompositeTaskResult:
        """Camera detects object → arm picks it up.

        Steps:
        1. Ask camera to detect colors
        2. Plan pick position from largest matching detection
        3. Ask arm to move to pick position, close gripper, lift
        """
        result = CompositeTaskResult(steps_total=3)
        t0 = time.time()

        # Step 1: Camera detection
        self.governor._log("visual_pick_and_place: step 1 — camera detection")
        detection_task = self.governor.create_task(
            "color_detection",
            params={"target_color": target_color} if target_color else {},
            priority=0.9,
            required_capabilities=["color_detection"],
        )

        detections = await self._wait_for_task_result(detection_task.id, timeout=10)
        if detections is None:
            result.error = "camera detection failed or timed out"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        result.steps_completed = 1
        result.detections = detections.get("detections", [])

        if not result.detections:
            result.error = "no objects detected"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        self.governor._log(f"visual_pick_and_place: {len(result.detections)} objects detected")

        # Step 2: Plan pick position
        target, arm_pos = plan_pick_and_place(
            result.detections,
            target_color=target_color,
        )

        if target is None or arm_pos is None:
            result.error = f"no {target_color or 'any'} object found"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        result.steps_completed = 2
        self.governor._log(f"visual_pick_and_place: target={target.color} at ({target.center_x:.2f}, {target.center_y:.2f})")

        # Step 3: Arm picks up object
        pick_task = self.governor.create_task(
            "pick_and_place",
            params={
                "pick_position": arm_pos,
                "target_color": target.color,
                "target_center": [target.center_x, target.center_y],
            },
            priority=0.9,
            required_capabilities=["6dof_arm"],
            required_skills=["basic_grasp"],
        )

        pick_result = await self._wait_for_task_result(pick_task.id, timeout=15)
        if pick_result is None:
            result.error = "arm pick failed or timed out"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        result.steps_completed = 3
        result.success = True
        result.duration_ms = int((time.time() - t0) * 1000)
        result.details = {
            "target_color": target.color,
            "target_position": [target.center_x, target.center_y],
            "arm_position": arm_pos,
        }
        self.governor._log(f"visual_pick_and_place: complete in {result.duration_ms}ms")
        return result

    async def execute_color_sorting(
        self,
        timeout: float = 60.0,
    ) -> CompositeTaskResult:
        """Camera detects all objects → arm sorts each by color.

        Steps:
        1. Camera detects all colored objects
        2. For each object: plan pick + place positions
        3. Arm picks each object and places in color-specific bin
        """
        result = CompositeTaskResult()
        t0 = time.time()

        # Step 1: Camera detection
        self.governor._log("color_sorting: step 1 — camera detection")
        detection_task = self.governor.create_task(
            "color_detection",
            priority=0.9,
            required_capabilities=["color_detection"],
        )

        detections = await self._wait_for_task_result(detection_task.id, timeout=10)
        if detections is None:
            result.error = "camera detection failed"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        result.detections = detections.get("detections", [])
        result.steps_completed = 1

        if not result.detections:
            result.error = "no objects to sort"
            result.duration_ms = int((time.time() - t0) * 1000)
            return result

        # Step 2: Plan sort sequence
        sequence = plan_sort_sequence(result.detections)
        result.steps_total = 1 + len(sequence)

        self.governor._log(f"color_sorting: {len(sequence)} objects to sort")

        # Step 3: Execute each pick-and-place
        sorted_count = 0
        for obj, pick_pos, place_pos in sequence:
            if time.time() - t0 > timeout:
                result.error = "timeout"
                break

            self.governor._log(f"color_sorting: picking {obj.color} object")

            sort_task = self.governor.create_task(
                "pick_and_place",
                params={
                    "pick_position": pick_pos,
                    "place_position": place_pos,
                    "target_color": obj.color,
                },
                priority=0.8,
                required_capabilities=["6dof_arm"],
                required_skills=["basic_grasp"],
            )

            sort_result = await self._wait_for_task_result(sort_task.id, timeout=15)
            if sort_result is not None:
                sorted_count += 1
                result.steps_completed += 1
                self.governor._log(f"color_sorting: {obj.color} sorted ({sorted_count}/{len(sequence)})")
            else:
                self.governor._log(f"color_sorting: {obj.color} pick failed, skipping")

        result.success = sorted_count > 0
        result.duration_ms = int((time.time() - t0) * 1000)
        result.details = {"sorted": sorted_count, "total": len(sequence)}
        self.governor._log(f"color_sorting: {sorted_count}/{len(sequence)} sorted in {result.duration_ms}ms")
        return result

    async def _wait_for_task_result(self, task_id: str, timeout: float = 10.0) -> dict | None:
        """Wait for a task to complete and return its result."""
        start = time.time()
        while time.time() - start < timeout:
            task = self.governor.marketplace.tasks.get(task_id)
            if task and task.status.value == "completed" and task.result:
                return task.result
            if task and task.status.value == "failed":
                return None
            await asyncio.sleep(0.2)
        return None
