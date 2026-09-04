# Open-source landscape and lessons

Reviewed 2026-09-04. This is a product/architecture scan, not a claim that the projects are interchangeable.

## Closest references

| Project | What it demonstrates | What OpenAgentArena should borrow | Remaining gap for this thesis |
| --- | --- | --- | --- |
| [AI Battle Arena](https://github.com/Infini-AI-Lab/aibattle) | Modular strategic games, hidden information, seat swapping, step logs, reports and replays | clean game/agent/model/runner/logging/eval separation; runner speaks to agents, not raw models | mostly compact game collection; capability budgets and broader tool-using agent systems are not the center |
| [Planet Wars RTS](https://github.com/SimonLucas/planet-wars-rts) | Parameterized RTS family, full/partial observability, simultaneous moves, stable agent API, containers | vary rules and observability inside one environment family; headless competition path | scenario-specific platform and conventional bot interface |
| [LGeneral-bench](https://github.com/koryaga/lgeneral-bench) | Long-horizon stateful REST control under fog of war and resource constraints | keep legal actions close to state; freeze API docs; own the engine process and liveness checks | single game and largely agent-vs-built-in-CPU evaluation |
| [CATArena](https://github.com/AGI-Eval-Official/CATArena) | Agents write strategies, compete, inspect past rounds, and improve in iterative tournaments | measure adaptation over seasons; repeat and seat/group matches | emphasizes code-generation agents and board/card game strategy code |
| [KantBench / OpenEnv](https://github.com/wisent-ai/OpenEnv) | Many configurable game-theory environments, communication, bargaining and social behavior | composable rule variants; cheap-talk channel; broad payoff structures | breadth of small games more than grounded tool use and operational reliability |
| [PettingZoo](https://github.com/Farama-Foundation/PettingZoo) | Widely used multi-agent environment API with sequential AEC and parallel-action modes | compatible mental model; explicit support for sequential and simultaneous environments; strict versioning | designed primarily for MARL policies, not LLM tool/memory/cost telemetry |
| [OpenSpiel](https://github.com/google-deepmind/open_spiel) | Formal coverage of n-player, zero/general-sum, cooperative, sequential/simultaneous, perfect/imperfect-information games | borrow taxonomy and baseline algorithms; consider an adapter instead of reimplementing classic games | research game framework rather than agent-system operations platform |
| [Melting Pot](https://github.com/google-deepmind/meltingpot) | Held-out social scenarios testing interaction with familiar and unfamiliar agents | train/test social generalization; evaluate cooperation, deception, trust and reciprocity | 2D MARL stack is heavy for an initial LLM-agent MVP |
| [AgentBench](https://github.com/THUDM/AgentBench) | Cross-domain LLM agent evaluation spanning OS, DB, KG, games, browsing and embodied tasks | agent-system framing and heterogeneous environment coverage | mostly task completion against environments, not persistent strategic co-adaptation among agents |

## Strategic conclusion

The idea is validated, but the generic phrase “agent arena” is crowded. The differentiator cannot be “LLMs play games.” The defensible product definition is:

> **A protocol and evidence system for dynamic, multi-agent, tool-using evaluations, with games as the first reproducible environment family.**

Three choices follow:

1. **Protocol first.** Define observations, actions, lifecycle, capabilities, budgets, and trace semantics before investing in a game client.
2. **System metrics first.** Treat cost, latency, invalid actions, tool use, and recovery as co-equal with payoff.
3. **Generalization first.** Separate environment templates from generated instances and reserve sealed variants/opponents for evaluation.

## Build, adapt, or integrate

- Implement the small core protocol and trace format locally; these embody the product thesis.
- Offer adapters to PettingZoo/OpenSpiel later rather than cloning their catalogs.
- Use compact original environments for end-to-end tests and contamination resistance.
- Study AI Battle Arena's modular runner/report pipeline and Planet Wars' parameterized family design.
- Avoid coupling the core to one model provider, one agent SDK, or one transport.

## Naming note

`OpenAgentArena` is descriptive for the bootstrap phase, while `AgentArena` alone is already heavily used. A separate brand search and trademark check should precede any commercial launch.
