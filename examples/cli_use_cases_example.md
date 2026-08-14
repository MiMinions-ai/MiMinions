# MiMinions CLI Use Cases: Fit Guide

This example maps common AI-assistant use cases to MiMinions CLI workflows,
including when the fit is strong and when extra integration is needed.

## 1. Writing and Editing Content

**Fit:** Strong

Use a one-off prompt for quick drafts, or interactive chat for iterative edits.

```bash
# One-off draft
miminions prompt ask "Draft a launch update for our weekly team newsletter."

# Iterative editing session
miminions chat start
```

## 2. Coding Support

**Fit:** Strong

Use prompt/chat for generation, explanations, and refactor suggestions. Add a
coding-focused agent when you want a reusable setup.

```bash
# Ask for code help directly
miminions prompt ask "Explain this stack trace and suggest a fix strategy."

# Interactive coding loop
miminions chat start

# Optional: create a dedicated coding agent
miminions agent add
```

## 3. Research and Summarization

**Fit:** Strong

Use prompt/chat to summarize content, compare options, and extract key points.

```bash
miminions prompt ask "Summarize the key tradeoffs between option A and option B."
miminions chat start
```

## 4. Customer Support Automation

**Fit:** Partial

MiMinions is strong for drafting responses and FAQ content. Full support
automation (routing, triggers, ticket lifecycle) typically needs integration via
custom tools and execution workflows.

```bash
# Draft support replies or FAQ content
miminions prompt ask "Draft a friendly reply for a delayed order complaint."

# Add workflow/tool integration for deeper automation
miminions execution --help
```

## 5. Personal Productivity

**Fit:** Strong

Use tasks for planning and prioritization, knowledge for notes, and chat for
ongoing planning.

```bash
# Explore task and knowledge commands
miminions task --help
miminions knowledge --help

# Planning session
miminions chat start
```

## 6. Data Analysis Help

**Fit:** Partial to strong

MiMinions is strong for explanation, query drafting, and insight summaries. More
automated/deep analysis depends on connecting data sources and tools through
execution workflows.

```bash
# Ask for analysis framing or query drafting
miminions prompt ask "Draft SQL to compare weekly active users month over month."

# Extend with custom tooling/data integration
miminions execution --help
```

## Practical Pattern

Use this progression for most teams:

1. Start with `prompt ask` for quick wins.
2. Move to `chat start` for iterative workflows.
3. Add dedicated agents and execution-integrated tools for automation.
