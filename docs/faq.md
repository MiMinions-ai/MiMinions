# Frequently Asked Questions

Everything you need to know about MiMinions.

???+ question "What is MiMinions?"

    **MiMinions is an open-source Python framework for building autonomous AI agents.**
    It enables developers to create, deploy, and manage agentic AI systems that
    can think, plan, and execute tasks. Built on top of `pydantic_ai`, it provides
    the building blocks for agentic systems: an LLM-powered [Agent](modules/agent.md),
    a [Tools](modules/tools.md) registry, vector and markdown [Memory](modules/memory.md),
    [Workspaces](modules/workspaces.md), and MCP server integration.

??? question "How do I get started?"

    **Getting started is easy.** Install the framework with
    `pip install miminions`, then create your first agent in just a few lines of
    code. See the [Getting Started](getting-started.md) guide for step-by-step
    instructions on building your first autonomous AI agent.

??? question "Is MiMinions free to use?"

    **Yes — MiMinions is open-source and free to use.** You can use it for
    personal projects, commercial applications, and contribute to its
    development. Check out the
    [GitHub repository](https://github.com/MiMinions-ai/MiMinions) to see the
    source and contribute to the project.

??? question "Which LLM providers are supported?"

    MiMinions selects models through a `ModelFactory`. The default provider is
    **OpenRouter** (free `openai/gpt-oss-20b:free` model), and you can switch to
    **OpenAI**, **Anthropic**, **Gemini**, or an offline **test** model by passing
    `provider=` to `create_minion`:

    ```python
    from miminions.agent import create_minion

    agent = create_minion("assistant", provider="anthropic")
    ```

    Each real provider needs its API key in the environment
    (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, etc.). The `test` provider runs fully
    offline. See [Agent](modules/agent.md) for the full provider matrix.

??? question "Do I need a GPU?"

    **No.** MiMinions runs on CPU. The optional SQLite vector memory
    (`pip install miminions[sqlite]`) uses `fastembed`, which runs embeddings
    through ONNX on the CPU — no GPU or CUDA setup required. The LLM itself runs
    remotely via your chosen provider's API.

??? question "What safety features are included?"

    MiMinions takes a pragmatic, local-first approach to safety:

    - **Sign-in gating on the CLI.** Commands are wrapped with `require_auth`, so
      they refuse to run until you sign in with `miminions auth signin`. An opt-in
      public-access mode can relax this for trusted, local-only use.
    - **Local-first data.** Agents, workspaces, and memory persist under
      `~/.miminions/` on your own machine — nothing is sent to a third party
      beyond your chosen LLM provider.
    - **Auditable data operations.** The [Data Management](modules/data.md) layer
      keeps an append-only transaction log of every write, giving you a complete
      audit trail of changes.
    - **Per-channel allow-lists.** The optional [Gateway Runtime](modules/gateway.md)
      enforces an `allow_from` allow-list per channel: an empty list denies all
      senders, and you explicitly opt callers in (or use `"*"` to allow everyone).

??? question "Where can I find the documentation?"

    Full guides and API references live in the [Documentation](getting-started.md)
    section, covering the [Agent](modules/agent.md), [Memory](modules/memory.md),
    [Context Builder](modules/context.md), [Tools](modules/tools.md),
    [Workspaces](modules/workspaces.md), [Tasks & Workflows](modules/tasks.md),
    [Data Management](modules/data.md), [Gateway Runtime](modules/gateway.md), and
    [CLI & Chat](modules/cli.md) modules.

---

Still have a question? [Get in touch](contact.md).
