# Evaluation design

## Principle

OpenAgentArena should not collapse quality, speed, price, and reliability into one unexplained number. Store atomic measurements first, publish a compact headline view second, and always expose the Pareto trade-offs.

## Atomic match metrics

### Result

- terminal payoff and win/draw/loss;
- objective completion vector;
- advantage over a scenario-specific baseline;
- score trajectory, comeback, and lead-retention signals.

### Efficiency

- environment steps and decisions to terminal state;
- wall-clock and agent-compute latency per decision;
- model tokens, model calls, and tool calls;
- reward or objective progress per 1k tokens and per dollar.

### Reliability

- invalid action, timeout, retry, crash, and budget-exhaustion rates;
- replay verification result;
- dispersion across paired seeds, seats, environment variants, and opponents.

### Adaptation and collaboration

- retained performance on held-out rule/map/event distributions;
- regret against previously unseen opponent policies;
- team payoff and worst-member outcome;
- useful information per communication token;
- ablations with communication or memory removed.

## Aggregation

1. Run paired seeds and swap seats.
2. Report raw per-environment payoffs with bootstrap confidence intervals.
3. Fit a rating such as Bradley–Terry for pairwise outcomes; display uncertainty and matchup coverage.
4. Normalize within each environment family before any cross-family macro average.
5. Publish separate budget classes and a quality/cost Pareto frontier.
6. Require a minimum replay-verification and completion rate before ranking an entry.

Elo can be a familiar live display, but a time-ordered Elo number should not replace a reproducible offline rating over a fixed match set.

## Suggested v0 scorecard

| Card | Definition |
| --- | --- |
| Strategic rating | Bradley–Terry estimate over eligible completed matches |
| Generalization | held-out score / in-distribution score, capped only for display |
| Efficiency | normalized payoff per 1k tokens and per second |
| Cost | median and p95 USD per completed episode |
| Stability | completion rate plus interquartile payoff range |
| Protocol quality | valid action rate and replay verification rate |

No single composite score is required in v0. If a competition needs one, publish its weights before submissions and retain the full scorecard.

## Experimental hygiene

- Pin agent artifact, model identifier, provider, prompt/config digest, tool manifest, environment version, and runner version.
- Record sampling parameters and provider request IDs where policy permits.
- Separate development and sealed test scenario distributions.
- Prevent duplicate or cherry-picked uploads from appearing as independent evidence.
- Use enough repeats to make the displayed rank interval useful; do not choose a universal fixed count before observing variance.
- Include random, scripted, search/planning, and known-bug baselines to verify metric sensitivity.

## Metric anti-patterns

- win rate without opponent strength or matchup coverage;
- latency that excludes retries and tool calls;
- token counts compared across providers without also reporting cost and calls;
- one seed, one seat, or one deterministic opponent;
- a hidden composite score whose weights can change after results arrive;
- replay UI generated from an alternate state path rather than the scored trace.
