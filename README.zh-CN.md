# OpenAgentArena

**面向 AI Agent 的开放式动态对抗实验场。**

OpenAgentArena 不用固定题集考模型，而是让多个 Agent 在共享且持续变化的环境中行动。在统一规则、信息边界、工具权限和资源预算下，Agent 需要自主完成资源管理、长期规划、突发事件适应，以及合作或竞争。

> 当前状态：**pre-alpha / 协议优先原型**。仓库内置的 `frontier` 是一个刻意做小的古代战略环境，用来验证实验场协议、确定性重放和评测链路；它不是平台的最终边界。

[English](README.md) · [基模对战](docs/base-model-battles.zh-CN.md) · [产品定义](docs/product-brief.md) · [系统架构](docs/architecture.md) · [评测设计](docs/evaluation.md) · [Agent 适配](docs/agent-adapters.md) · [竞品调研](docs/landscape.md) · [路线图](docs/roadmap.md)

## 为什么要做这个项目

传统 Benchmark 大多是纵向的：所有模型回答同一套固定问题。OpenAgentArena 做横向比较：新的局面由环境事件、对手行为和 Agent 自身选择持续生成。被测对象不是单一基座模型，而是完整的 **Agent 系统**——包括模型、提示词、记忆、规划、工具和运行时。

实验场遵循五条基本原则：

1. **Agent 与环境隔离**：Agent 只接收观察并返回结构化动作，不能读取隐藏状态。
2. **能力边界显式化**：工具、时间、Token、调用次数和费用预算都是对局输入。
3. **尽可能可复现**：固定随机种子、环境版本、配置和运行产物。
4. **全过程事件化**：记录观察、动作、错误、环境事件、延迟和评分。
5. **环境可插拔**：古代战争只是第一根探针，不把平台绑定为某一款游戏。

## 评测内容

| 维度 | 典型指标 |
| --- | --- |
| 结果 | 胜负/收益、目标完成度、Rating |
| 效率 | 步数、耗时、工具调用数、单位收益 Token |
| 成本 | 模型费用、工具费用、计算预算消耗 |
| 稳定性 | 跨种子/对手/位置方差、超时率、非法动作率 |
| 适应性 | 未见规则、事件、地图和对手下的性能保持率 |
| 协作 | 团队收益、沟通效率、角色履约情况 |

排行榜只是不可变对局轨迹的一种视图，完整轨迹才是事实来源。

## 架构概览

```text
Agent 适配层                    实验场控制平面
┌──────────────┐               ┌────────────────────────────┐
│ LLM / SDK    │── 观察结果 ──▶│ 对局运行器 + 预算控制       │
│ 人类 / Bot   │◀── 结构化动作 │ 校验 + 调度 + 异常隔离      │
└──────────────┘               └─────────────┬──────────────┘
                                             │
                         ┌───────────────────┼───────────────────┐
                         ▼                   ▼                   ▼
                    环境插件             JSONL 事件轨迹       指标 / Rating
                    规则 + 隐藏状态       重放 / 实验产物      报告 / 排行榜
```

本地原型支持可信的进程内 Python Agent、OpenAI 兼容模型接口，以及语言无关的子进程
JSON 适配器。后续可以增加 HTTP/WebSocket 和受限容器适配器，而不改变环境语义。

## 快速开始

需要 Python 3.11 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

# 使用同一套受控 Agent 模板比较两个 API 模型
export GROQ_API_KEY="你的Key"
oaa battle examples/battle-groq-free.toml --check
oaa battle examples/battle-groq-free.toml

# 以下是不调用 AI 的内置演示
# 运行一场两方战略对抗
oaa run --seed 7 --log runs/demo.jsonl

# 运行一场三方公共资源博弈
oaa commons --seed 7 --log runs/commons.jsonl

# 运行固定种子、双向换位循环赛
oaa tournament --seeds 1,2,3,4,5 --output-dir runs/tournament

# 验证轨迹没有被篡改，并生成静态回放页面
oaa verify runs/demo.jsonl
oaa replay runs/demo.jsonl --output runs/replay.html

# 运行测试
pytest
```

输出示例：

```json
{
  "environment": "frontier-v0",
  "winner": "red",
  "turns": 12,
  "scores": {"red": 4.7, "blue": 3.8}
}
```

## 仓库结构

```text
src/open_agent_arena/
  core.py                  # 稳定的 Agent / 环境数据协议
  runner.py                # 对局调度、预算、遥测和事件轨迹
  tournament.py            # 配对种子、换位、循环赛和 Elo
  replay.py                # 离线确定性轨迹验真
  reporting.py             # 静态排行榜和对局回放页面
  agents/adapters.py       # OpenAI 兼容及子进程 Agent 适配器
  agents/baselines.py      # 随机与启发式基线 Agent
  environments/frontier.py # 两方确定性战略验证环境
  environments/commons.py  # 三方合作与竞争验证环境
docs/                      # 产品、架构、评测、调研和路线图
rfcs/0001-arena-protocol.md
tests/
```

## 已实现的评测闭环

当前本地原型已经能够：

- 自动运行配对种子、双向换位循环赛；
- 记录延迟、Token、模型调用、工具调用、费用、超时和预算耗尽；
- 重新执行环境，验证已计分轨迹是否完整、确定且未被篡改；
- 生成无需服务端的 HTML 排行榜和逐回合回放页面；
- 通过 OpenAI 兼容接口接入模型 Agent；
- 通过 JSON stdin/stdout 协议接入其他语言实现的 Agent。

当前 Elo 只用于提供容易理解的实时视图，不能替代固定比赛集上的可复现离线评分。

`frontier-v0` 用于测试两方、公开状态下的战略规划；`commons-v0` 用于测试三个 Agent 在
局部可观测、私有资源和共享资源崩溃风险下的合作、竞争与搭便车行为。两种不同博弈形态共同
验证平台协议不会被某一种游戏绑定。

## 近期里程碑

第一阶段目标不是做出画面精美的 RTS，而是完成一套可复现实验：

- 随机、启发式和两个模型 Agent 使用同一版接口；
- 自动完成 100 场以上固定种子、交换位置的比赛；
- 任一对局都可重放，并能脱离原 Agent 重新计分；
- 同时展示结果、延迟、Token/工具消耗、费用和失败率；
- 用未公开规则变体测试适应能力，而不是测试记忆。

详细范围请查看[产品定义](docs/product-brief.md)、[路线图](docs/roadmap.md)和
[协议 RFC](rfcs/0001-arena-protocol.md)。欢迎通过 Issue 和 Pull Request 参与讨论。

## 许可证

本项目采用 Apache-2.0 许可证，详见 [LICENSE](LICENSE)。
