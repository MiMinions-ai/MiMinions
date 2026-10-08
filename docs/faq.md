# Frequently Asked Questions

Everything you need to know about MiMinions.

???+ question "What is MiMinions?"

    **MiMinions is an open-source Python framework for building autonomous AI agents.**
    It enables developers to create, deploy, and manage agentic AI systems that
    can think, plan, and execute tasks. Built on top of the python open source eco-system, it provides
    the building blocks for agentic systems: an LLM-powered [Agent](for-dev/modules/agent.md),
    a [Tools](for-dev/modules/tools.md) registry, a [Memory](for-dev/modules/memory.md),
    [Workspaces](for-dev/modules/workspaces.md), and MCP server integration.

??? question "How do I get started?"

    **Getting started is easy.** Install the framework with
    `pip install miminions`, then create your first agent in just a few lines of
    code. See the [Getting Started](for-dev/getting-started.md) guide for step-by-step
    instructions on building your first autonomous AI agent.

??? question "Is MiMinions free to use?"

    **Yes — MiMinions is open-source and free to use.** You can use it for
    personal projects, commercial applications, and contribute to its
    development. Check out the
    [GitHub repository](https://github.com/MiMinions-ai/MiMinions) to see the
    source and contribute to the project.

??? question "Which LLM providers are supported?"

    MiMinions selects models through a `ModelFactory`. The default provider is
    **OpenRouter** (free model), and you can switch to
    **OpenAI**, **Anthropic**, **Gemini**, or an offline **test** model by passing
    `provider=` to `create_minion`:

    ```python
    from miminions.agent import create_minion

    agent = create_minion("assistant", provider="openai",model="gpt-6-sol")
    ```

    Each real provider needs its API key in the environment
    (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, etc.).  See [Agent](for-dev/modules/agent.md) for the full provider matrix.

??? question "Do I need a GPU?"

    **No.** MiMinions system runs on CPU — no GPU or CUDA setup required. The LLM itself runs
    remotely via your chosen provider's API.

??? question "Where can I find the documentation?"

    Full guides and API references live in the [Documentation](for-dev/getting-started.md)
    section, covering the following modules:
    - [Agent](for-dev/modules/agent.md)
    - [Memory](for-dev/modules/memory.md)
    - [Context Builder](for-dev/modules/context.md)
    - [Tools](for-dev/modules/tools.md)
    - [Workspaces](for-dev/modules/workspaces.md)

!!! tip "Working offline?"
    Pass `provider="test"` to `create_minion` to use `TestModel`
    and run without any API key — handy for tests and experiments.

---

Still have a question? [Get in touch](contact.md).
