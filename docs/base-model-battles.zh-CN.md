# 基模对战模式

[English](base-model-battles.md)

这个模式面向“只有模型 API Key、还没有开发 Agent”的普通用户。OpenAgentArena 给两种模型
套上完全相同的受控 Agent 外壳：同一版系统提示词、同一观察与动作格式、无外部工具、相同
预算、相同随机种子，并自动交换红蓝位置再赛一局。因此，结果衡量的是模型在这套统一外壳
下的实时决策能力，并不代表围绕每个模型能构建出的最强 Agent 系统。

## 最快的免费测试：Groq

截至 2026 年 9 月，Groq 官方提供 Free Plan，并列出 `openai/gpt-oss-20b` 和
`qwen/qwen3.8-27b` 均为每分钟 30 次、每天 1,000 次请求。免费限制和模型可用性会变化，
大量运行前请查看[官方限额表](https://console.groq.com/docs/rate-limits)。

1. 在 [Groq Console](https://console.groq.com/keys) 申请 Key。
2. 把 Key 放在环境变量中，不要写入仓库：

   ```bash
   export GROQ_API_KEY="你的Key"
   ```

3. 先只检查配置和 Key，再开始对战：

   ```bash
   oaa battle examples/battle-groq-free.toml --check
   oaa battle examples/battle-groq-free.toml
   ```

示例使用一个随机种子，自动交换位置后共进行两局；每局六回合，总共最多发出 24 次 API
请求。结果保存在 `runs/groq-free-smoke-test/`，其中包括逐回合 JSONL 轨迹、比赛汇总 JSON
和可直接打开的 `leaderboard.html`。

## 其他免费预设

| 服务 | 环境变量 | 说明 |
| --- | --- | --- |
| Google Gemini | `GEMINI_API_KEY` | Developer API 有免费层，并提供[官方 OpenAI 兼容接口](https://ai.google.dev/gemini-api/docs/openai)。免费层内容可能用于改进 Google 产品，请阅读[官方价格与数据说明](https://ai.google.dev/gemini-api/docs/pricing)。 |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` 会自动选择免费模型，适合验证产品链路；但路由模型会变化，不适合严谨的指定基模比较。参见[官方 FAQ](https://openrouter.ai/docs/faq)。 |
| Ollama | 无 | 本地 OpenAI 兼容接口，不消耗 API 额度，但需要本机算力并自行下载模型。 |

对应配置都在 `examples/` 下。服务商的模型目录会变化；如果接口提示模型下线，请更新配置中
的 `model` 字段。

## 平台究竟把什么发给 AI

每一回合只发送：

- 版本固定的 `base-model-v1` 系统提示词；
- 当前允许模型看到的观察，包括回合、公开状态、私有提示、合法动作和剩余预算；
- 只返回一个 JSON 动作的要求，例如 `{"kind":"attack","payload":{}}`。

模型通过 Chat Completions 模式调用，不需要 ChatGPT 产品、Assistant/Thread API、函数调用、
浏览器或用户自写代码。实验场负责解析并校验 JSON 动作、推进权威环境，以及记录 Token、
延迟、错误、得分和服务商返回的模型/请求标识。

API Key 只从环境变量读取，不会写入配置、日志或比赛轨迹。

## 如何理解结果

单个种子只能验证产品能否跑通，不是正式 Benchmark。有效比较应固定具体模型 ID，使用多个
随机种子，保持模板和预算不变，重复运行以观察服务波动，并同时比较胜率、Token、延迟、
非法动作和失败率。下一版协议还应在服务商支持时记录并固定采样随机种子。
