# OpenAgentArena

**面向 AI Agent 的开放式动态对抗实验场。**

OpenAgentArena 不用固定题集考模型，而是让多个 Agent 在共享且持续变化的环境中行动。在统一规则、信息边界、工具权限和资源预算下，Agent 需要自主完成资源管理、长期规划、突发事件适应，以及合作或竞争。

> 当前状态：**pre-alpha / 协议优先原型**。仓库内置的 `frontier` 是一个刻意做小的古代战略环境，用来验证接口、确定性重放和评测链路；它不是平台的最终形态。

[English](README.md) · [产品定义](docs/product-brief.md) · [系统架构](docs/architecture.md) · [评测设计](docs/evaluation.md) · [Agent 适配](docs/agent-adapters.md) · [竞品调研](docs/landscape.md) · [路线图](docs/roadmap.md)

## 核心判断

传统 Benchmark 多是纵向的：所有模型回答同一套固定问题。OpenAgentArena 做横向比较：新的局面由环境事件、对手行为和 Agent 自身选择持续生成。被测对象不是单一基座模型，而是完整的 **Agent 系统**——模型、提示词、记忆、规划、工具和运行时。

项目遵循五条不变量：

1. **Agent 与环境隔离**：Agent 只接收观察并返回结构化动作，不得读取隐藏状态。
2. **能力边界显式化**：工具、时间、Token、调用次数和费用预算都是对局输入。
3. **尽可能可复现**：固定随机种子、环境版本、配置和运行产物。
4. **全过程事件化**：记录观察、动作、错误、环境事件、延迟与评分。
5. **环境可插拔**：古代战争只是第一根探针，不把平台绑定为某款游戏。

## 评测维度

| 维度 | 典型指标 |
| --- | --- |
| 结果 | 胜负/收益、目标完成度、综合 Rating |
| 效率 | 步数、耗时、工具调用数、单位收益 Token |
| 成本 | 模型费用、工具费用、计算预算消耗 |
| 稳定性 | 跨种子/对手/位置方差、超时率、非法动作率 |
| 适应性 | 未见规则、事件、地图和对手下的性能保持率 |
| 协作 | 团队收益、沟通效率、角色履约情况 |

排行榜只是不可变对局轨迹的一种视图，轨迹才是事实来源。

## 快速开始

需要 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
oaa run --seed 7 --log runs/demo.jsonl
oaa commons --seed 7 --log runs/commons.jsonl
oaa tournament --seeds 1,2,3,4,5 --output-dir runs/tournament
oaa verify runs/demo.jsonl
oaa replay runs/demo.jsonl --output runs/replay.html
pytest
```

当前原型已支持配对种子、双向换位循环赛、Elo、Token/工具/费用/超时遥测、预算执行、
离线确定性验真，以及无需服务端的排行榜和对局回放 HTML。模型可通过 OpenAI 兼容接口接入，
其他语言的 Agent 可通过 JSON stdin/stdout 子进程协议接入。

仓库现在包含两种不同博弈形态：`frontier-v0` 是两方公开状态战略对抗；`commons-v0` 是三方、
局部可观测的公共资源困境，能观察合作、搭便车与集体崩溃，避免平台被古代战争单一形态绑定。

## 首个有效里程碑

第一阶段目标不是做出精美 RTS，而是完成一次可复现实验：

- 随机、启发式和两个模型 Agent 使用同一版接口；
- 自动完成 100+ 场固定种子、交换出生位的比赛；
- 任一对局都可重放，并能脱离原 Agent 重新计分；
- 同时展示结果、延迟、Token/工具消耗、费用和失败率；
- 用未公开规则变体测适应，而不是测记忆。

详细范围见[产品定义](docs/product-brief.md)和[路线图](docs/roadmap.md)。

## License

Apache-2.0，见 [LICENSE](LICENSE)。
