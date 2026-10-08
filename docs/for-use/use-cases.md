# Common Use Cases

## 1. Writing and editing content

**Fit:** Strong

Use `prompt ask` for one-off drafts and `chat start` for iterative editing.

    # One-off draft
    miminions prompt ask "Draft a launch update for our weekly team newsletter."

    # Iterative editing session
    miminions chat start

## 2. Coding support

**Fit:** Strong

Use chat/prompt for code generation, bug explanation, and refactor suggestions.
Optionally create a coding-focused agent for a reusable setup.

    # Ask for code help directly
    miminions prompt ask "Explain this stack trace and suggest a fix strategy."

    # Interactive coding loop
    miminions chat start

    # Optional: create a dedicated coding agent
    miminions agent add

## 3. Research and summarization

**Fit:** Strong

Use chat/prompt to summarize text, compare options, and extract key points.

    miminions prompt ask "Summarize the key tradeoffs between option A and option B."
    miminions chat start

## 4. Customer support automation

**Fit:** Partial

MiMinions is strong for drafting replies and FAQ content. Full ticket routing
and automation typically needs extra workflow/tool integration.

    # Draft support replies or FAQ content
    miminions prompt ask "Draft a friendly reply for a delayed order complaint."

    # Add workflow/tool integration for deeper automation
    miminions tool --help

## 5. Personal productivity

**Fit:** Strong

Use `task` commands for planning/prioritization, `knowledge` for notes, and
`chat` for ongoing planning.

    miminions task --help
    miminions knowledge --help
    miminions chat start

## 6. Data analysis help

**Fit:** Partial to strong

MiMinions is strong for explanation, query drafting, and insight summaries.
Deeper automated analysis depends on connecting data/tools through execution.

    # Ask for analysis framing or query drafting
    miminions prompt ask "Draft SQL to compare weekly active users month over month."

    # Extend with custom tooling/data integration
    miminions tool --help

