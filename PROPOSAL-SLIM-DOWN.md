# Proposal: Slim Down MiMinions

> Related Issue: #44

## TL;DR

Replace custom implementations with battle-tested OSS tools. Reduce ~5,600 lines to <1,000 lines. Focus on **integration value**, not reimplementation.

## Current vs Proposed

### Dependencies

| Current | Proposed | Reason |
|---------|----------|--------|
| `faiss-cpu` + custom wrapper | `chromadb` | Better API, built-in persistence, metadata filtering |
| `sentence-transformers` | (included in chromadb) | ChromaDB handles embeddings |
| `openai-agents` + wrapper | `openai-agents` directly | Wrapper adds no value |
| `pdfplumber` + custom chunker | `chonkie` + `pdfplumber` | Dedicated chunking library |
| `mcp`, `fastmcp` | `mcp`, `fastmcp` | **Keep** - thin wrapper adds convenience |
| `authlib`, `werkzeug` | Remove from SDK | App-level concern, not SDK |
| `starlette`, `python-multipart` | Remove from SDK | App-level concern |

### Module Changes

| Module | Lines | Action | Reason |
|--------|-------|--------|--------|
| `data/local/*` | 2,139 | **Remove** | Over-engineered; use SQLite or filesystem directly |
| `interface/cli/*` | 1,609 | **Remove** | CLI belongs in app layer, not SDK |
| `memory/faiss.py` | ~150 | **Replace** | Use ChromaDB |
| `memory/sqlite.py` | ~150 | **Replace** | Use ChromaDB or LanceDB |
| `agent/simple_agent.py` | ~100 | **Remove** | Use `openai-agents` directly |
| `utils/chunker.py` | 82 | **Replace** | Use `chonkie` |
| `user/*` | 162 | **Remove** | App-level concern |
| `tools/mcp_adapter.py` | ~100 | **Keep** | Useful convenience wrapper |

## Proposed New Structure

```
miminions/
├── __init__.py          # Clean public API
├── memory/
│   ├── __init__.py      # get_memory(backend="chromadb"|"lancedb")
│   └── chromadb.py      # Thin wrapper with opinionated defaults
├── tools/
│   ├── __init__.py
│   └── mcp.py           # MCP adapter (existing, cleaned up)
├── ingest/
│   ├── __init__.py      # ingest_document(path) -> chunks
│   └── pdf.py           # PDF ingestion using pdfplumber + chonkie
└── py.typed             # PEP 561 marker
```

**Target: ~800 lines** of MiMinions code (down from 5,600)

## New pyproject.toml

```toml
[project]
name = "miminions"
version = "0.2.0"
description = "Lightweight SDK for AI agent capabilities - memory, tools, and document ingestion"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "chromadb>=0.4.0",      # Vector memory with embeddings
    "mcp>=1.23.0",          # MCP protocol
    "fastmcp>=2.13.0",      # MCP convenience
    "chonkie>=0.1.0",       # Text chunking
    "pdfplumber>=0.9.0",    # PDF extraction
]

[project.optional-dependencies]
lancedb = ["lancedb>=0.4.0"]  # Alternative vector DB
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]
```

## Migration Path

### For Nanobot (primary consumer)

```python
# Before (current)
from miminions.memory.faiss import FAISSMemory
from miminions.agent import Agent

memory = FAISSMemory()
agent = Agent(memory=memory)

# After (proposed)
from miminions import get_memory
from openai_agents import Agent  # Use directly

memory = get_memory("chromadb", path="./data")
agent = Agent(...)  # Configure with openai-agents directly
```

### For MCP Tools

```python
# Before
from miminions.tools.mcp_adapter import MCPToolAdapter

# After (unchanged - we keep this)
from miminions.tools import MCPToolAdapter
```

## What MiMinions Becomes

**Before:** A collection of reimplemented wheels (~5,600 lines)

**After:** A thin, opinionated integration layer (~800 lines) that:

1. **Provides sensible defaults** for common AI agent needs
2. **Wraps OSS tools** with consistent interfaces
3. **Handles configuration** so you don't have to
4. **Stays out of the way** for advanced use cases

## Benefits

| Benefit | Description |
|---------|-------------|
| **Less maintenance** | OSS communities maintain the hard parts |
| **Better features** | ChromaDB, chonkie, etc. are more feature-rich |
| **Clearer purpose** | MiMinions = integration layer, not reimplementation |
| **Easier onboarding** | Smaller codebase, clearer value prop |
| **Faster iteration** | Less code = faster changes |

## Open Questions

1. Should we keep any of `data/local/*`? What unique value does it provide?
2. Should `memory/` support multiple backends, or just pick one (ChromaDB)?
3. Should we vendor `chonkie` or keep as dependency?

---

## Next Steps

1. [ ] Review this proposal
2. [ ] Decide on open questions
3. [ ] Implement Phase 1 (remove obvious redundancies)
4. [ ] Release as v0.2.0
