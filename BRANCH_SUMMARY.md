# Branch Comparison Summary: Dev vs Development

## Quick Overview

| Aspect | Dev Branch | Development Branch |
|--------|------------|-------------------|
| **Alignment with README** | 0% (0/14 features) | 100% (14/14 features) |
| **Version** | 0.1.0 | 0.0.1 |
| **Python Files** | 3 files | 50+ files |
| **Architecture** | Simple Gradio chatbot | Full agentic framework |
| **Tests** | None | Comprehensive test suite |
| **Documentation** | Empty README | Complete documentation |
| **Dependencies** | 2 (openai, gradio) | 10+ including framework adapters |

## Key Differences

### Dev Branch - Simple Chatbot
- Basic Gradio web interface (`app.py`)
- Simple OpenAI integration (`supplier.py`)
- No agent framework capabilities
- No alignment with README scope

### Development Branch - Complete Framework
- ✅ Multi-agent systems with BaseAgent
- ✅ Framework adapters (LangChain, AutoGen, AGNO)
- ✅ Knowledge management with vector search
- ✅ CLI interface and workspace management
- ✅ Async support and session tracking
- ✅ Complete test coverage and examples

## Recommendation

**Use Development Branch** as the canonical implementation. It fully realizes the MiMinions vision described in the README while the dev branch appears to be an early prototype that has been superseded.

## Files Added in Development Branch

- Complete `/src/miminions/` package structure
- `/examples/` directory with usage examples  
- `/tests/` directory with comprehensive test suite
- Framework adapter modules
- CLI interface components
- Data management system
- Agent and tool implementations

The development branch represents the complete MiMinions agentic framework as specified in the project documentation.