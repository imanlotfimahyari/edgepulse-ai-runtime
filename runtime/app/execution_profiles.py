from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ExecutionProfileName = Literal[
    "eco",
    "balanced",
]

ExecutionModeName = Literal["sequential"]


@dataclass(frozen=True)
class ExecutionProfile:
    name: ExecutionProfileName
    intra_op_num_threads: int
    inter_op_num_threads: int
    execution_mode: ExecutionModeName
    allow_spinning: bool

    def as_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


EXECUTION_PROFILES: dict[
    ExecutionProfileName,
    ExecutionProfile,
] = {
    "eco": ExecutionProfile(
        name="eco",
        intra_op_num_threads=1,
        inter_op_num_threads=1,
        execution_mode="sequential",
        allow_spinning=False,
    ),
    "balanced": ExecutionProfile(
        name="balanced",
        intra_op_num_threads=0,
        inter_op_num_threads=0,
        execution_mode="sequential",
        allow_spinning=True,
    ),
}


def get_execution_profile(
    name: ExecutionProfileName,
) -> ExecutionProfile:
    return EXECUTION_PROFILES[name]
