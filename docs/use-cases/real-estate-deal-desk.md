# Use case: Real-estate deal desk (underwrite + memory)

This guide shows a concrete starter path for **MiMinions** after `pip install miminions`: run a small deal-desk agent that underwrites wholesale-style offers and keeps durable facts in the three-tier memory layout.

It is based on a live South Florida zero-capital wholesaling / bird-dog desk that uses MiMinions ideas without requiring you to rebuild their product.

## What you will build

1. A workspace with `memory/HISTORY.md` + `memory/MEMORY.md`
2. A `Minion` that calls a typed underwrite tool
3. Session distillation that promotes stable facts (formulas, buy boxes) into `MEMORY.md`

## Prerequisites

```bash
pip install "miminions[sqlite]"
export OPENROUTER_API_KEY="sk-or-..."   # or use provider="test" offline
```

Python **3.12+**.

## Step 1 — Workspace layout

```bash
miminions workspace add --name "deal-desk" --init-files
# Files appear under ~/.miminions/ (or your configured root):
#   prompt/   memory/HISTORY.md   memory/MEMORY.md   skills/   sessions/   data/
```

Seed durable facts into `MEMORY.md` (Tier 2):

```markdown
# Memory

## Underwriting
- MAO ≈ (ARV × 0.70) − rehab − assignment_fee
- Rehab tiers (per sqft): cosmetic $20, medium $35, heavy $55, structural $75

## Integrity
- Never sell synthetic / practice CRM rows as verified leads
- Bird-dog fees require public-record or seller-confirmed addresses
```

## Step 2 — Register an underwrite tool

```python
import asyncio
from miminions.agent import create_minion

REHAB = {"cosmetic": 20.0, "medium": 35.0, "heavy": 55.0, "structural": 75.0}

def underwrite_wholesale(
    arv: float,
    sqft: float,
    condition: str = "medium",
    assignment_fee: float = 10000.0,
    rule: float = 0.70,
) -> dict:
    """Deterministic wholesale MAO calculator."""
    rate = REHAB.get(condition.lower(), 35.0)
    rehab = sqft * rate
    investor_buy = (arv * rule) - rehab
    mao = max(0.0, investor_buy - assignment_fee)
    return {
        "arv": arv,
        "sqft": sqft,
        "condition": condition,
        "rehab": rehab,
        "investor_buy": investor_buy,
        "assignment_fee": assignment_fee,
        "mao": mao,
    }

async def main():
    agent = create_minion("DealDesk", provider="test")  # swap to openrouter/openai later
    agent.register_tool(
        "underwrite_wholesale",
        "Compute wholesale MAO from ARV, sqft, condition, fee",
        underwrite_wholesale,
    )
    print(await agent.run(
        "Underwrite ARV 350000, 1600 sqft, medium rehab, 10k fee. Return MAO."
    ))

asyncio.run(main())
```

## Step 3 — Three-tier memory (the MiMinions pattern)

| Tier | File / store | What goes here |
|------|----------------|----------------|
| 1 | `memory/HISTORY.md` | Chronological session bullets |
| 2 | `memory/MEMORY.md` | Stable facts (formulas, buy boxes, integrity rules) |
| 3 | `~/.miminions/global_memory.db` | Cross-workspace searchable insights |

After chat, run distillation (CLI chat already distills on exit) so session noise does not pollute Tier 2.

## Step 4 — Cash-path integrity checklist

When adapting this to a real desk:

- Tools must be deterministic for money math (MAO, fees)
- CRM rows without county/public-record verification stay **demo-only**
- Paid offers should describe the deliverable honestly (e.g. underwrite of **client-provided** addresses)

## Related modules

- [Memory](../modules/memory.md) — tiers + distiller
- [Agent](../modules/agent.md) — `create_minion` + tools
- [Workspaces](../modules/workspaces.md) — on-disk layout
- [CLI & Chat](../modules/cli.md) — `miminions chat start`

## Feedback

If this guide helps (or fails on first run), comment on [issue #97](https://github.com/MiMinions-ai/MiMinions/issues/97) with your OS, Python version, and the exact command that broke.
