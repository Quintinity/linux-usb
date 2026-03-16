# Research: Robot Spatial Awareness and Collision Prevention

**Date:** 2026-03-16
**Context:** armOS citizenry — multiple SO-101 arms + cameras in shared/overlapping workspaces. Citizens currently have no awareness of each other's physical positions. Two arms could reach for the same spot simultaneously.

**Hardware:** SO-101 6-DOF arms (Feetech STS3215), known link lengths, forward kinematics from proprioception research. UDP multicast communication, <50ms LAN latency. Python, no GPU.

---

## 1. Workspace Management — "Air Traffic Control" for Robot Arms

### The Problem

Every robot arm has a reachable workspace — the set of all Cartesian positions its end-effector can reach. When two arms are co-located, their workspaces may overlap. Without management, both arms can claim the same physical space simultaneously.

### Workspace Representations

**Cartesian space** defines workspace as the set of (x, y, z) positions the end-effector can reach. For the SO-101, with link lengths of 104mm (upper arm), 88mm (forearm), 35mm (wrist), and 60mm (gripper), the maximum reach is approximately 287mm from the base. The actual reachable volume is a partial sphere, constrained by joint limits.

**Joint space** defines workspace as the N-dimensional volume of valid joint configurations. For 6-DOF, this is a 6D hyperrectangle bounded by joint limits. Joint space is more natural for servo-level control; Cartesian space is more natural for collision checking between robots.

### Zone Architecture

Industrial multi-robot systems typically define three zone types:

1. **Exclusive zones** — A region assigned to exactly one robot. No other robot may enter. Simplest to enforce: just check if a commanded position is within your zone. For our citizenry: each arm's "home" half of the table.

2. **Shared zones** — A region where multiple robots may operate, but with access control. Only one robot at a time (mutex), or time-sliced access. For our citizenry: the handoff area between two arms.

3. **Forbidden zones** — No robot may enter. Safety barriers, human work areas, fragile equipment. For our citizenry: the area where the camera is mounted, cable runs.

### Implementation for armOS

```
Workspace definition per arm citizen:

workspace:
  base_position: [x, y, z]       # Where the arm base is mounted (mm)
  base_orientation: rotation      # Which way the arm faces
  max_reach: 287                  # mm from base
  exclusive_zone:                 # Axis-aligned bounding box or convex hull
    min: [x0, y0, z0]
    max: [x1, y1, z1]
  shared_zones:                   # Named regions this arm can access
    - name: "handoff_zone"
      bounds: [...]
      max_occupants: 1
  forbidden_zones:                # Never enter
    - name: "camera_mount"
      bounds: [...]
```

**Enforcement levels:**
- **Soft limits:** Warn via mycelium when approaching zone boundary. Log it.
- **Hard limits:** Refuse to execute commands that would enter a forbidden zone. Clamp to boundary.
- **Emergency:** If a zone violation is detected (e.g., someone pushed an arm), broadcast emergency stop.

### Virtual Fences

Virtual fences are boundaries defined in software, not physical barriers. They work in two spaces:

**Cartesian fences:** Define a 3D boundary (box, sphere, convex hull). Before executing any motion, compute the end-effector position via forward kinematics. If the target position is outside the fence, reject the command or clamp to the boundary. Fast to check — a single point-in-box test.

**Joint-space fences:** Define limits on each joint independently. Simpler to enforce at the servo level (the STS3215 has hardware angle limits via registers 9-12), but the resulting Cartesian boundary is non-intuitive. Our constitution already distributes joint limits; these are effectively joint-space fences.

**Swept-volume fences:** The most thorough approach. Don't just check the target position — check every point along the trajectory. The swept volume is the union of all positions the arm occupies during a motion. More expensive to compute but catches cases where the arm passes through a forbidden zone on its way to a valid target.

---

## 2. Collision Avoidance Between Robots

### Bounding Volume Approaches

Real-time collision detection at servo rates (30-100Hz) requires fast geometric primitives. Full mesh collision checking is too expensive. The hierarchy from cheapest to most accurate:

**Bounding spheres:** Each link is enclosed in a sphere. Distance between two spheres = distance between centers minus sum of radii. A 6-DOF arm needs ~6 spheres. Checking two arms = 36 sphere-sphere distance calculations. At ~10ns each, this takes <1 microsecond. Very fast, very conservative (lots of false positives — spheres waste space on elongated links).

**Bounding capsules (recommended for SO-101):** A capsule is a cylinder capped with hemispheres at each end. Perfect for robot links, which are elongated cylinders. Distance between two capsules reduces to the distance between two line segments, minus the sum of their radii. Much tighter fit than spheres, still very fast.

```python
# Capsule representation for one SO-101 link
@dataclass
class Capsule:
    p0: np.ndarray   # Start point (3D), from forward kinematics
    p1: np.ndarray   # End point (3D), from forward kinematics
    radius: float     # Enclosing radius (mm)

# SO-101 capsule model (approximate radii)
SO101_CAPSULES = {
    "base":          {"radius": 30},   # Base housing
    "upper_arm":     {"radius": 20},   # 104mm link
    "forearm":       {"radius": 18},   # 88mm link
    "wrist":         {"radius": 15},   # 35mm link
    "gripper":       {"radius": 25},   # 60mm, wider due to fingers
}
```

**Capsule-capsule distance algorithm:**

The minimum distance between two capsules is the minimum distance between their central line segments, minus the sum of their radii. The line-segment distance algorithm:

1. Parameterize each segment: `P(s) = A + s*(B-A)`, `Q(t) = C + t*(D-C)`, where s,t in [0,1]
2. Find the s,t that minimize `|P(s) - Q(t)|`
3. This has a closed-form solution involving dot products and clamping

```python
def segment_distance(a0, a1, b0, b1):
    """Minimum distance between two line segments in 3D."""
    u = a1 - a0  # Direction of segment A
    v = b1 - b0  # Direction of segment B
    w = a0 - b0

    uu = np.dot(u, u)
    uv = np.dot(u, v)
    vv = np.dot(v, v)
    uw = np.dot(u, w)
    vw = np.dot(v, w)

    denom = uu * vv - uv * uv

    if denom < 1e-10:  # Parallel segments
        s = 0.0
        t = uw / uv if uv > 1e-10 else 0.0
    else:
        s = (uv * vw - vv * uw) / denom
        t = (uu * vw - uv * uw) / denom

    s = np.clip(s, 0.0, 1.0)
    t = np.clip(t, 0.0, 1.0)

    closest_a = a0 + s * u
    closest_b = b0 + t * v
    return np.linalg.norm(closest_a - closest_b)

def capsule_distance(cap_a: Capsule, cap_b: Capsule) -> float:
    """Distance between two capsules (negative = penetrating)."""
    seg_dist = segment_distance(cap_a.p0, cap_a.p1, cap_b.p0, cap_b.p1)
    return seg_dist - cap_a.radius - cap_b.radius
```

**Performance for multi-arm checking:** Two SO-101 arms, 5 capsules each = 25 capsule-capsule checks. Each check involves ~20 floating-point operations. Total: ~500 FLOPs. On any modern CPU, this runs in <10 microseconds. Easily supports 100Hz checking with <0.1% CPU usage.

### Minimum Separation Distance

Define a safety margin beyond the physical capsule radii:

- **Green zone (>50mm):** No action needed. Normal operation.
- **Yellow zone (20-50mm):** Slow down the approaching arm. Broadcast a warning on mycelium.
- **Red zone (<20mm):** Stop the approaching arm. Broadcast emergency. The closer arm yields.
- **Contact (<0mm):** Emergency stop both arms. Report collision.

### Available Python Libraries

**PyBullet** — Can be used purely for collision checking without running physics simulation. Load the robot URDF, set joint states with `resetJointState()`, call `getClosestPoints()`. No GPU needed. Runs headless. The recommended approach for our system.

**python-fcl** — Python bindings for the Flexible Collision Library. Supports collision detection, distance computation, and continuous collision detection between geometric primitives (boxes, spheres, capsules, meshes). Available on PyPI. Lightweight, no simulation overhead.

**hpp-fcl** — Enhanced fork of FCL with better Python bindings and additional features. Also on PyPI.

**Custom capsule checking** — For our specific case (two 6-DOF arms with known link lengths), a hand-rolled capsule checker is the fastest option. No library overhead, no URDF parsing, just the math above. ~50 lines of Python with NumPy.

---

## 3. Object Occupancy Tracking — "One Object, One Space"

### The Problem

When arm-1 picks up a block, arm-2 needs to know:
- The block is no longer on the table at position (x, y, z)
- The block is now "attached" to arm-1's gripper
- The space where arm-1's gripper is (and where the block is) is occupied
- Arm-2 should not try to pick from that location or move through that space

### Occupancy Grid

Discretize the workspace into a 3D voxel grid. Each cell is either FREE, OCCUPIED, or UNKNOWN.

```python
class OccupancyGrid:
    """3D voxel grid for tracking what's where."""

    def __init__(self, origin, size, resolution=10):
        """
        origin: (x, y, z) of grid corner in mm
        size: (width, height, depth) in mm
        resolution: mm per voxel (10mm = 1cm cubes)
        """
        self.origin = np.array(origin)
        self.resolution = resolution
        dims = (
            int(size[0] / resolution),
            int(size[1] / resolution),
            int(size[2] / resolution),
        )
        self.grid = np.zeros(dims, dtype=np.uint8)  # 0=free, 1=occupied, 2=reserved

    def world_to_grid(self, point):
        return tuple(((np.array(point) - self.origin) / self.resolution).astype(int))

    def mark_occupied(self, point, radius=0):
        """Mark a sphere of voxels as occupied."""
        center = self.world_to_grid(point)
        r = int(radius / self.resolution) + 1
        # Mark all voxels within radius
        for dx in range(-r, r+1):
            for dy in range(-r, r+1):
                for dz in range(-r, r+1):
                    if dx*dx + dy*dy + dz*dz <= r*r:
                        idx = (center[0]+dx, center[1]+dy, center[2]+dz)
                        if self._in_bounds(idx):
                            self.grid[idx] = 1
```

For a 600mm x 600mm x 400mm workspace at 10mm resolution: 60x60x40 = 144,000 voxels = 144KB. Trivially small.

### Spatial Hash Map (Alternative)

For sparse environments (few objects, lots of empty space), a spatial hash map is more efficient than a dense grid:

```python
class SpatialHashMap:
    """Sparse 3D spatial indexing using hash buckets."""

    def __init__(self, cell_size=20):  # 20mm cells
        self.cell_size = cell_size
        self.buckets: dict[tuple, list] = {}  # (ix,iy,iz) -> list of objects

    def _key(self, point):
        return (
            int(point[0] // self.cell_size),
            int(point[1] // self.cell_size),
            int(point[2] // self.cell_size),
        )

    def insert(self, obj_id, position, radius=0):
        """Insert an object at a position, filling all cells it touches."""
        # ... mark all cells within radius

    def query(self, position, radius=0):
        """Find all objects near a position."""
        # ... check this cell and neighbors

    def remove(self, obj_id):
        """Remove an object from all cells."""
```

### Object Registry

Higher-level than occupancy grids — track named objects with ownership:

```python
@dataclass
class TrackedObject:
    obj_id: str              # "red_block_01"
    position: np.ndarray     # Current (x, y, z) in mm
    owner: str | None        # pubkey of citizen holding it, or None if on table
    last_updated: float      # timestamp
    bounding_radius: float   # mm

class ObjectRegistry:
    """Track what objects are where, and who owns them."""
    objects: dict[str, TrackedObject] = {}

    def claim(self, obj_id: str, citizen_pubkey: str):
        """A citizen claims ownership of an object (picked it up)."""

    def release(self, obj_id: str, position: np.ndarray):
        """A citizen releases an object at a position (put it down)."""

    def query_near(self, position: np.ndarray, radius: float) -> list[TrackedObject]:
        """What objects are near this position?"""
```

### Integration with Citizenry Protocol

Objects enter the registry via:
1. **Camera detection** — Camera citizen detects objects and broadcasts REPORT with positions
2. **Gripper contact** — Arm citizen detects load change when gripping, claims the object
3. **Manual registration** — Governor tells citizens what objects are in the workspace

---

## 4. Flight Plans and Intent Broadcasting

### The Concept

Before moving, a robot declares: "I intend to move my end-effector from A to B over the next 2 seconds." Other robots check for conflicts. If there's a conflict, the lower-priority robot yields (waits, replans, or takes an alternate route).

This is analogous to air traffic control flight plans — declare intent, get clearance, then move.

### Trajectory Envelope

A trajectory envelope is the swept volume of a robot during a planned motion, inflated by a safety margin. It represents all the space the robot will occupy during the motion.

For capsule-based arms, the trajectory envelope for a single link moving from configuration A to configuration B is the convex hull of the capsule at A and the capsule at B, inflated by the safety margin. For the whole arm, it's the union of envelopes for all links.

A simpler approximation: compute the end-effector path from A to B, then inflate it by the arm's maximum link radius + safety margin. This creates a "tube" through space that the arm will pass through.

### Reservation Protocol Design for Citizenry

Using the existing 7-message protocol:

```
FLIGHT PLAN FLOW:
1. Arm-1 sends PROPOSE (broadcast) with intent:
   {
     "task": "flight_plan",
     "trajectory": {
       "start": {"joint_positions": {...}, "cartesian": [x,y,z]},
       "end":   {"joint_positions": {...}, "cartesian": [x,y,z]},
       "duration_ms": 2000,
       "envelope": {  # Simplified bounding box of swept volume
         "min": [x0, y0, z0],
         "max": [x1, y1, z1]
       },
       "priority": 5,   # Higher = more important
     }
   }

2. Other arms check for conflicts:
   - Does this envelope overlap with my current position?
   - Does this envelope overlap with my planned trajectory?
   - Does this envelope overlap with my exclusive zone?

3. Each arm responds with ACCEPT_REJECT:
   {
     "accepted": true,    # No conflict, go ahead
     "flight_plan_id": "...",
   }
   OR
   {
     "accepted": false,
     "reason": "envelope_conflict",
     "my_priority": 3,     # Lower priority, but I'm already moving
     "conflict_zone": [x, y, z],
   }

4. Priority arbitration:
   - If all accept: execute immediately
   - If conflict with lower-priority arm: execute, other arm yields
   - If conflict with higher-priority arm: wait for that arm to finish
   - If equal priority: arm with lower pubkey yields (deterministic tiebreaker)

5. On completion, broadcast REPORT:
   {
     "type": "flight_plan_complete",
     "flight_plan_id": "...",
   }
```

### Priority Scheme

```
Priority levels:
  10 — Emergency stop / safety maneuver
   8 — Active handoff (committed to a multi-arm task)
   6 — Ongoing task execution
   4 — New task start
   2 — Return to home position
   1 — Idle repositioning
```

### Optimistic vs. Pessimistic Locking

**Pessimistic (ask first, then move):** Always request clearance before moving. Safer but adds latency (one round-trip minimum). Good for high-stakes operations.

**Optimistic (move and announce simultaneously):** Broadcast intent and start moving. If a conflict is detected, the lower-priority arm stops and replans. Lower latency for the common case (no conflict). Risk of wasted motion if conflicts are common.

**Recommendation for armOS:** Use pessimistic locking for shared zones (handoff areas) and optimistic locking for exclusive zones (your own half of the table). The 50ms round-trip on LAN is acceptable for most tasks.

---

## 5. Self-Collision Avoidance

### The Problem

A 6-DOF arm can reach configurations where it hits itself — e.g., the gripper crashes into the base, or the forearm collides with the upper arm at certain elbow angles.

### Joint Limit Enforcement

The first line of defense. The SO-101 joint limits from the proprioception research:

```python
JOINT_LIMITS = {
    "shoulder_pan":  (1024, 3072),   # ~90 to ~270 degrees
    "shoulder_lift": (1200, 2200),
    "elbow_flex":    (2000, 3200),
    "wrist_flex":    (1024, 3072),
    "wrist_roll":    (1024, 3072),
    "gripper":       (1400, 2600),
}
```

These limits are already enforced by the STS3215's hardware angle limit registers. But they only prevent individual joints from going too far — they don't prevent combinations of joint angles that cause self-collision.

### Capsule-Based Self-Collision

Use the same capsule model as inter-arm collision, but check links of the same arm against each other. Not all pairs need checking:

```
Skip pairs (always safe due to mechanical constraints):
- Adjacent links (connected by a joint — they can't collide)
- base ↔ upper_arm (connected via shoulder)
- upper_arm ↔ forearm (connected via elbow)
- forearm ↔ wrist (connected via wrist_flex)

Check pairs (can potentially collide):
- base ↔ forearm
- base ↔ wrist
- base ↔ gripper
- upper_arm ↔ wrist
- upper_arm ↔ gripper
```

For a single arm: 5 pairs to check. At capsule-checking speed, this takes <5 microseconds.

### Pre-Computed Self-Collision Map

For offline planning, you can pre-compute a lookup table in joint space. Sample the 6D joint space and mark configurations as "self-colliding" or "safe." At runtime, interpolate to check any configuration. This trades memory for speed but is overkill for 6-DOF — the direct capsule check is fast enough.

### Integration with Servo Commands

Every time a servo command is issued (either from teleop or from task execution), run the self-collision check before sending the command to the servo bus:

```python
def safe_move(target_positions: dict[str, int], body_model) -> dict[str, int]:
    """Check for self-collision before moving. Returns clamped positions."""
    # 1. Enforce joint limits
    clamped = enforce_joint_limits(target_positions)

    # 2. Compute forward kinematics for proposed configuration
    capsules = compute_capsules(clamped)

    # 3. Check self-collision pairs
    for (link_a, link_b) in SELF_COLLISION_PAIRS:
        dist = capsule_distance(capsules[link_a], capsules[link_b])
        if dist < SELF_COLLISION_MARGIN:  # e.g., 10mm
            # Option 1: Reject the move entirely
            # Option 2: Scale back toward current position until safe
            return scale_back(current_positions, clamped, capsules)

    return clamped
```

---

## 6. Shared Workspace Protocols — Object Handoff

### The Handoff Problem

When arm-1 needs to pass an object to arm-2:
1. Both arms must coordinate to be in the handoff zone at the right time
2. Only one arm should grip the object at any moment (or both must grip simultaneously during transfer)
3. The handoff zone must be "locked" — no other arm should enter during the handoff

### Staged Handoff Sequence

```
Phase 1: NEGOTIATE
  Arm-1 (holder) → broadcast PROPOSE: "I have red_block, need handoff to arm-2"
  Arm-2 (receiver) → ACCEPT: "Ready for handoff"
  All other arms → note the handoff zone is reserved

Phase 2: APPROACH
  Arm-1 moves to handoff position (its side of the zone)
  Arm-2 moves to handoff position (its side of the zone)
  Both broadcast flight plans for these moves
  Both confirm arrival via REPORT

Phase 3: TRANSFER
  Arm-1 extends into shared zone (holding object)
  Arm-2 closes gripper on object
  Arm-1 senses load increase on arm-2's side (or arm-2 reports grip contact)
  Arm-1 releases gripper
  Arm-2 confirms grip via REPORT

Phase 4: RETREAT
  Arm-1 retreats from handoff zone
  Arm-2 retreats with object
  Handoff zone unlocked
  Object registry updated: owner changed from arm-1 to arm-2
```

### Token-Based Access Control

For the handoff zone, implement a simple mutex:

```python
class WorkspaceToken:
    """Mutex for a shared workspace region."""
    zone_name: str
    holder: str | None = None       # pubkey of the citizen holding the token
    granted_at: float = 0.0
    timeout: float = 10.0           # Auto-release after 10 seconds

    def request(self, citizen_pubkey: str) -> bool:
        if self.holder is None or self._is_expired():
            self.holder = citizen_pubkey
            self.granted_at = time.time()
            return True
        return False

    def release(self, citizen_pubkey: str) -> bool:
        if self.holder == citizen_pubkey:
            self.holder = None
            return True
        return False
```

In a distributed system, token management needs consensus. Options:

1. **Governor holds the token** — Citizens request access from the governor. Governor grants/denies. Simple, centralized. Single point of failure.

2. **Token passing** — The token circulates. Whoever holds it can enter the zone. Pass it to the next requester when done. Decentralized but requires reliable delivery.

3. **PROPOSE/ACCEPT with priority** — Use the existing citizenry protocol. PROPOSE access, other citizens ACCEPT/REJECT. If all accept, you have the lock. Fits naturally into the protocol.

**Recommendation:** Option 3, using the existing protocol. The governor can override in case of deadlock.

---

## 7. Camera-Assisted Spatial Awareness

### The Camera Citizen's Role

The camera citizen is uniquely positioned to provide ground-truth spatial awareness. It can see the entire workspace and detect:
- Where objects are (object detection)
- Where arms currently are (arm tracking)
- Whether the scene matches expectations (verification)
- New obstacles or people entering the workspace (safety)

### Real-Time Occupancy from Depth

If using a depth camera (USB depth cameras work on the Surface Pro 7), the camera citizen can maintain a live 3D occupancy map:

```python
class DepthOccupancyMapper:
    """Convert depth frames into 3D occupancy grid updates."""

    def __init__(self, camera_intrinsics, camera_extrinsics, grid: OccupancyGrid):
        self.K = camera_intrinsics      # 3x3 camera matrix
        self.T = camera_extrinsics      # 4x4 camera-to-world transform
        self.grid = grid

    def update_from_depth(self, depth_frame: np.ndarray):
        """Project depth pixels into 3D and update occupancy grid."""
        h, w = depth_frame.shape
        # Subsample for speed (every 4th pixel)
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                d = depth_frame[y, x]
                if d <= 0:
                    continue
                # Back-project to 3D
                point_cam = np.array([
                    (x - self.K[0,2]) * d / self.K[0,0],
                    (y - self.K[1,2]) * d / self.K[1,1],
                    d
                ])
                point_world = (self.T @ np.append(point_cam, 1))[:3]
                self.grid.mark_occupied(point_world)
```

At 640x480, subsampled 4x = 19,200 points per frame. At 30fps, this is ~576K point updates/second. With NumPy vectorization, this is feasible on CPU.

### RGB Object Detection for Occupancy

Without a depth camera, use the existing 2D camera with the calibrated homography to estimate object positions:

1. Camera detects objects using color/contour detection (already implemented in `visual_tasks.py`)
2. Map pixel positions to workspace coordinates using the calibration homography
3. Objects are tracked as 2D positions on the table surface (z = table height)
4. Broadcast detected objects as REPORT messages

### Visual Verification

The camera can verify the spatial model:
- "Arm-1 says it's at position X — does the camera confirm?"
- "The object registry says there's a block at Y — is it really there?"
- "Nothing should be at position Z — is there an unexpected object?"

This creates a feedback loop: arms report their state via heartbeat, camera verifies via vision, discrepancies trigger warnings on the mycelium network.

### Broadcast Format

```python
# Camera citizen spatial report (broadcast every 100-200ms)
{
    "type": "spatial_report",
    "objects": [
        {"id": "red_block_01", "position": [x, y, z], "confidence": 0.95},
        {"id": "blue_cup_01", "position": [x, y, z], "confidence": 0.87},
    ],
    "arm_positions": [
        {"citizen": "arm-alpha", "gripper_pixel": [px, py], "gripper_world": [x, y, z]},
    ],
    "workspace_clear": true,   # No unexpected objects detected
    "frame_id": 12345,
}
```

---

## 8. Practical Multi-Arm Implementations and Libraries

### PyBullet for Collision Checking (No Physics)

PyBullet can be used purely as a collision checker. Create a headless simulation, load the robot URDFs, set joint states, and query distances — without running any physics steps.

```python
import pybullet as p

# Create headless physics server (no GUI, no simulation)
client = p.connect(p.DIRECT)

# Load two SO-101 arms at different positions
arm1 = p.loadURDF("so101.urdf", basePosition=[0, -150, 0])
arm2 = p.loadURDF("so101.urdf", basePosition=[0, 150, 0])

# Set joint states (no simulation step needed)
for i, pos in enumerate(arm1_positions):
    p.resetJointState(arm1, i, pos)
for i, pos in enumerate(arm2_positions):
    p.resetJointState(arm2, i, pos)

# Check for collisions between the two arms
contacts = p.getClosestPoints(arm1, arm2, distance=50)  # 50mm threshold
if contacts:
    min_dist = min(c[8] for c in contacts)  # c[8] is contact distance
    print(f"Minimum distance between arms: {min_dist}mm")
```

**Pros:** Robust, handles arbitrary geometries, well-tested.
**Cons:** Requires URDF (we'd need to create one for SO-101), PyBullet dependency.

### python-fcl

```python
import fcl

# Create capsule geometries for arm links
upper_arm = fcl.Capsule(20, 104)  # radius 20mm, length 104mm
forearm = fcl.Capsule(18, 88)

# Create collision objects with transforms
obj1 = fcl.CollisionObject(upper_arm, fcl.Transform(rotation, translation))
obj2 = fcl.CollisionObject(forearm, fcl.Transform(rotation, translation))

# Distance query
request = fcl.DistanceRequest()
result = fcl.DistanceResult()
distance = fcl.distance(obj1, obj2, request, result)
```

**Pros:** Designed for collision checking, supports capsules natively, continuous collision detection.
**Cons:** C++ library with Python bindings — installation can be finicky.

### OMPL (Open Motion Planning Library)

OMPL provides sampling-based motion planning (RRT, PRM, etc.) with Python bindings. It does NOT include collision checking — you provide a `isStateValid()` callback that uses your own collision checker (e.g., FCL or custom capsules).

For multi-arm planning, OMPL's `CompoundStateSpace` combines the joint spaces of multiple arms into a single planning space. The planner then finds collision-free paths in this combined space.

**Verdict for armOS:** Overkill for now. Our motions are simple point-to-point moves. Direct capsule checking + reservation protocol is sufficient. OMPL becomes valuable if we need complex path planning around obstacles.

### Recommended Stack for armOS

```
Layer 1 (Servo): Joint limits in STS3215 registers (hardware enforcement)
Layer 2 (Citizen): Custom capsule-based collision checking (self + inter-arm)
Layer 3 (Protocol): Flight plan reservation via PROPOSE/ACCEPT
Layer 4 (Camera): Visual verification of occupancy and arm positions
Layer 5 (Governor): Zone definitions, priority scheme, deadlock resolution
```

No external collision library needed for the initial implementation. The custom capsule approach is 50 lines of NumPy, runs at >10kHz, and matches our specific arm geometry exactly.

---

## 9. Distributed Spatial Coordination for the Citizenry Protocol

### Current Protocol Gaps

The existing 7-message protocol has no concept of spatial position. Heartbeats carry state ("idle", "moving") but not WHERE the citizen physically is. There's no mechanism to declare intent before moving, or to claim a region of space.

### Proposed Extensions

#### Option A: Extend HEARTBEAT with Position Data

Add spatial data to every heartbeat:

```python
# Extended heartbeat body
{
    "name": "arm-alpha",
    "state": "moving",
    "health": 0.95,
    "unicast_port": 7771,
    "uptime": 3600,
    # NEW: Spatial awareness fields
    "spatial": {
        "base_position": [0, -150, 55],       # mm, fixed
        "gripper_position": [120, -80, 100],   # mm, from FK
        "joint_positions": {                    # Raw servo ticks
            "shoulder_pan": 2100,
            "shoulder_lift": 1600,
            "elbow_flex": 2500,
            "wrist_flex": 2048,
            "wrist_roll": 2048,
            "gripper": 1400,
        },
        "velocity": [10, -5, 3],              # mm/s, estimated
        "holding_object": "red_block_01",      # or null
    },
}
```

**Pros:** Every citizen gets continuous spatial updates automatically. No extra messages. Simple.
**Cons:** Increases heartbeat size. 2Hz update rate (heartbeat interval) may be too slow for collision avoidance.

#### Option B: New Spatial REPORT Type

Add a new high-frequency spatial report:

```python
# Broadcast at 10-30Hz (separate from heartbeat)
{
    "type": "spatial_report",
    "gripper_position": [120, -80, 100],
    "capsules": [                          # Current capsule positions
        {"link": "upper_arm", "p0": [...], "p1": [...], "r": 20},
        {"link": "forearm",   "p0": [...], "p1": [...], "r": 18},
        # ...
    ],
    "velocity": [10, -5, 3],
    "holding_object": "red_block_01",
}
```

**Pros:** High-frequency updates independent of heartbeat. Other citizens can do their own collision checking.
**Cons:** More network traffic. At 30Hz with 5 capsules, each ~200 bytes = 6KB/s per arm. Fine for LAN.

#### Option C: Flight Plan via PROPOSE/ACCEPT (Recommended)

Use the existing protocol mechanisms:

1. **HEARTBEAT** carries current position (Option A, low frequency, for general awareness)
2. **PROPOSE** carries flight plans (trajectory intent, before moving)
3. **ACCEPT_REJECT** carries clearance/conflict (other arms respond)
4. **REPORT** carries spatial reports from cameras and completion notifications

This requires no new message types. It uses the existing protocol exactly as designed — PROPOSE for intent, ACCEPT for clearance. The "task" field just becomes a flight plan instead of a high-level task.

#### Workspace Definition via GOVERN

The governor distributes workspace configuration as part of the constitution:

```python
# Constitution extension
{
    "version": 2,
    "name": "Workspace Alpha",
    "workspace": {
        "table_bounds": {"min": [-300, -300, 0], "max": [300, 300, 400]},
        "arms": {
            "arm-alpha": {
                "base_position": [0, -150, 55],
                "orientation": 0,         # degrees, facing +x
                "exclusive_zone": {"min": [-300, -300, 0], "max": [300, 0, 400]},
            },
            "arm-beta": {
                "base_position": [0, 150, 55],
                "orientation": 180,       # facing -x
                "exclusive_zone": {"min": [-300, 0, 0], "max": [300, 300, 400]},
            },
        },
        "shared_zones": [
            {
                "name": "handoff",
                "bounds": {"min": [-100, -50, 0], "max": [100, 50, 200]},
                "max_occupants": 1,
                "access_policy": "request",  # Must PROPOSE access
            },
        ],
        "forbidden_zones": [
            {
                "name": "camera_mount",
                "bounds": {"min": [-50, -50, 350], "max": [50, 50, 420]},
            },
        ],
        "safety": {
            "min_separation_mm": 30,
            "approach_slowdown_mm": 60,
            "flight_plan_required": true,    # Must declare intent before moving in shared zones
        },
    },
}
```

### Recommended Architecture

```
                    ┌─────────────────────────────────┐
                    │         GOVERNOR                 │
                    │  Distributes workspace config    │
                    │  Resolves deadlocks              │
                    │  Sets priority scheme            │
                    └──────────┬──────────────────────┘
                               │ GOVERN (constitution)
                    ┌──────────▼──────────────────────┐
                    │      WORKSPACE MODEL             │
                    │  (Each citizen maintains local)  │
                    │                                  │
                    │  - Zone boundaries               │
                    │  - Neighbor positions (from HB)  │
                    │  - Active flight plans           │
                    │  - Object registry               │
                    │  - Occupancy grid (from camera)  │
                    └──────────┬──────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
    │   ARM-ALPHA    │ │  ARM-BETA    │ │   CAMERA     │
    │                │ │              │ │              │
    │ FK → capsules  │ │ FK → capsules│ │ Depth/RGB →  │
    │ Self-collision │ │ Self-coll.   │ │ occupancy    │
    │ Flight plans   │ │ Flight plans │ │ Object detect│
    │ Zone checking  │ │ Zone check.  │ │ Arm tracking │
    └────────────────┘ └──────────────┘ └──────────────┘
         │                    │                │
         └────────────────────┼────────────────┘
                              │
                    UDP Multicast (239.67.84.90:7770)
                    HEARTBEAT: current position
                    PROPOSE:   flight plans
                    REPORT:    spatial reports, completions
```

---

## 10. Implementation Roadmap

### Phase 1: Self-Awareness (Single Arm)

Already partially done in the proprioception research. Complete:
- [x] Forward kinematics (SO-101 link lengths, tick-to-radian conversion)
- [ ] Capsule model for all links
- [ ] Self-collision checking
- [ ] Joint limit proximity warnings on mycelium

### Phase 2: Position Broadcasting

- [ ] Add `spatial` field to heartbeat body
- [ ] Each arm citizen computes FK every heartbeat and includes gripper position
- [ ] Camera citizen broadcasts spatial reports with detected objects
- [ ] Neighbors table records last-known positions

### Phase 3: Workspace Zones

- [ ] Define zone data structures (exclusive, shared, forbidden)
- [ ] Governor distributes zones via constitution
- [ ] Each arm citizen validates commands against zones before execution
- [ ] Virtual fence enforcement (Cartesian + joint space)

### Phase 4: Inter-Arm Collision Checking

- [ ] Capsule-capsule distance computation (the ~50 lines of NumPy from section 2)
- [ ] Each arm maintains capsule model of all known arms (from heartbeat positions)
- [ ] Minimum separation distance monitoring
- [ ] Yellow/red zone alerts on mycelium

### Phase 5: Flight Plans

- [ ] Flight plan PROPOSE format
- [ ] Swept volume approximation (bounding box of start and end capsule positions)
- [ ] Conflict detection (envelope overlap checking)
- [ ] Priority arbitration
- [ ] Timeout and deadlock handling

### Phase 6: Object Handoff

- [ ] Handoff zone token/mutex
- [ ] Staged handoff sequence (negotiate, approach, transfer, retreat)
- [ ] Object registry with ownership tracking
- [ ] Camera verification of handoff success

### Phase 7: Camera Integration

- [ ] Occupancy grid from depth camera (if available)
- [ ] Visual verification of arm positions vs. FK
- [ ] Unexpected object detection
- [ ] Dynamic obstacle avoidance

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Collision geometry | Capsules | Best fit for cylindrical arm links; tight bound; fast math |
| Collision library | Custom NumPy | 50 lines, no dependencies, >10kHz, matches our geometry |
| Spatial coordination | PROPOSE/ACCEPT | Uses existing protocol; no new message types |
| Position updates | Heartbeat extension | Low overhead; 2Hz sufficient for general awareness |
| Flight plans | Pre-move PROPOSE | Pessimistic in shared zones, optimistic in exclusive zones |
| Zone management | Governor via constitution | Centralized definition, distributed enforcement |
| Occupancy tracking | Sparse hash map + object registry | Few objects, large workspace; registry for ownership |
| Workspace representation | Cartesian (mm) | Natural for collision checking; convert from joint space via FK |

---

## References and Libraries

### Python Libraries (no GPU required)
- **python-fcl** (PyPI) — FCL bindings for collision/distance queries on primitives and meshes
- **hpp-fcl** (PyPI) — Enhanced FCL fork with better Python bindings
- **PyBullet** (PyPI) — Headless collision checking via `getClosestPoints()`, requires URDF
- **OMPL** (ompl.kavrakilab.org) — Sampling-based motion planning, Python bindings, overkill for now
- **NumPy** — All we need for custom capsule collision checking

### Key Research
- FCL (Flexible Collision Library): general purpose proximity and collision queries on geometric models, supports capsules, meshes, continuous collision detection
- Swept volume collision detection: convex hull of capsule at start and end configuration, inflated by safety margin
- Capsule-capsule minimum distance: reduces to line-segment distance minus radii, closed-form solution
- MoveIt dual-arm planning: combines arms into single URDF, shared planning scene, synchronous planning
- Prioritized trajectory coordination: decentralized planning where robots broadcast trajectories and resolve conflicts by priority
- Occupancy grid mapping: probabilistic voxel grids updated from depth/lidar, exchangeable between robots
- Spatial hashing: O(n) collision detection for sparse environments, 20mm cells appropriate for arm workspaces

Sources:
- [Collision/Obstacle Avoidance Coordination of Multi-Robot Systems: A Survey](https://www.mdpi.com/2076-0825/14/2/85)
- [Multi-robot collaborative manipulation framework (Frontiers, 2025)](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1585544/full)
- [Survey on Collision Avoidance Algorithms for Multi-robot Systems](https://link.springer.com/content/pdf/10.1007/s12555-024-1104-9.pdf)
- [Dual Arms with MoveIt Tutorial](https://moveit.picknik.ai/main/doc/examples/dual_arms/dual_arms_tutorial.html)
- [Multi-Robot MoveIt collision management](https://answers.ros.org/question/374248/multi-robot-moveit-collision-management/)
- [python-fcl (GitHub)](https://github.com/BerkeleyAutomation/python-fcl)
- [FCL: Flexible Collision Library (GitHub)](https://github.com/flexible-collision-library/fcl)
- [hpp-fcl (PyPI)](https://pypi.org/project/hpp-fcl/)
- [PyBullet collision detection blog](https://adamheins.com/blog/collision-detection-pybullet)
- [PyBullet collision detection for planning (Discussion)](https://github.com/bulletphysics/bullet3/discussions/3813)
- [OMPL: Open Motion Planning Library](https://ompl.kavrakilab.org/)
- [Real-time swept volume and distance computation for self collision detection (IEEE)](https://ieeexplore.ieee.org/document/6094611/)
- [Real-Time Kinematics-Based Self-Collision Avoidance Algorithm for Dual-Arm Robots](https://www.mdpi.com/2076-3417/10/17/5893)
- [Efficient Calculation of Minimum Distance Between Capsules (IEEE)](https://ieeexplore.ieee.org/document/8586786/)
- [Capsule collision detection model (Aldebaran/NAO)](http://doc.aldebaran.com/2-1/naoqi/motion/reflexes-collision-avoidance.html)
- [Online and Scalable Motion Coordination for Multiple Robot Manipulators in Shared Workspaces (IEEE)](https://ieeexplore.ieee.org/document/10103893/)
- [Unified Framework for Coordinated Multi-Arm Motion Planning](https://nbfigueroa.github.io/multi-arm-coordination/)
- [Prioritized Planning Algorithms for Trajectory Coordination](https://arxiv.org/pdf/1409.2399)
- [Optimized Spatial Hashing for Collision Detection](https://matthias-research.github.io/pages/publications/tetraederCollision.pdf)
- [Multi-view Real-time 3D Occupancy Map for Collision Avoidance](https://www.researchgate.net/publication/349389770_Multi-view_Real-time_3D_Occupancy_Map_for_Machine-patient_Collision_Avoidance)
- [PythonRobotics](https://atsushisakai.github.io/PythonRobotics/)
- [Workspace of a Six-Axis Industrial Robot Arm (Mecademic)](https://mecademic.com/insights/academic-tutorials/workspace-six-axis-industrial-robot-arm/)
