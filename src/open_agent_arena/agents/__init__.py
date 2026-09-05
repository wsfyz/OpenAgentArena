"""Reference agents used to validate environments and metrics."""

from .adapters import OpenAICompatibleAgent, SubprocessAgent
from .baselines import (
    CommonsCooperatorAgent,
    CommonsFreeRiderAgent,
    GreedyFrontierAgent,
    RandomAgent,
)

__all__ = [
    "CommonsCooperatorAgent",
    "CommonsFreeRiderAgent",
    "GreedyFrontierAgent",
    "OpenAICompatibleAgent",
    "RandomAgent",
    "SubprocessAgent",
]
