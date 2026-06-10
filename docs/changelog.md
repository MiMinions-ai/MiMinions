# Changelog

All notable changes to MiMinions are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Initial project structure
- Basic user module with simple model and controller
- Simplified pull request template
- Code of Conduct, Changelog, and Security files

### Changed
- Simplified user module design to be leaner and more focused
- Replaced `sentence-transformers` with `fastembed` (ONNX Runtime) for `SQLiteMemory` embeddings, removing the PyTorch/CUDA dependency. Same `all-MiniLM-L6-v2` model and 384-dim output, so existing databases need no migration.

### Removed
- Complex user authentication and validation systems

## [0.1.0] - 2024-01-XX

### Added
- Core MiMinions package structure
- Generic tool system for AI frameworks
- Agent management capabilities
- Local data management system
- User module with basic CRUD operations
- Support for LangChain, AutoGen, and AGNO adapters
- CLI interface for basic operations
- Comprehensive test suite structure

---

## Version History

| Version | Notes |
|---------|-------|
| **Unreleased** | Development version with ongoing improvements |
| **0.1.0** | Initial release with core functionality |
