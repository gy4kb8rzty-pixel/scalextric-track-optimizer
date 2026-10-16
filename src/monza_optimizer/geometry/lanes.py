"""Lane topology validation for multi-lane Scalextric pieces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LaneTopology:
    """Describes how lanes pass through a piece."""

    lane_count: int = 2
    # True if lane order is reversed relative to entry (rare crossover pieces)
    reverses_lanes: bool = False
    # Lane indices 0..n-1 at entry map to these indices at exit
    exit_permutation: tuple[int, ...] = (0, 1)

    def __post_init__(self) -> None:
        if self.lane_count < 1:
            raise ValueError("lane_count must be >= 1")
        if len(self.exit_permutation) != self.lane_count:
            # allow default for simple two-lane
            if self.exit_permutation == (0, 1) and self.lane_count != 2:
                object.__setattr__(
                    self,
                    "exit_permutation",
                    tuple(range(self.lane_count)),
                )


def validate_lane_continuity(
    topologies: list[LaneTopology],
) -> list[str]:
    """Return list of lane continuity issues (empty = OK)."""
    issues: list[str] = []
    if not topologies:
        return issues
    expected = topologies[0].lane_count
    for i, topo in enumerate(topologies):
        if topo.lane_count != expected:
            issues.append(
                f"piece {i}: lane_count {topo.lane_count} != expected {expected}"
            )
        if sorted(topo.exit_permutation) != list(range(topo.lane_count)):
            issues.append(f"piece {i}: exit_permutation is not a valid permutation")
    return issues
