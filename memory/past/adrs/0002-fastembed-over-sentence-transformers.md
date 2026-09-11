# 0002. fastembed over sentence-transformers

Date: 2026-06-06
Status: reconstructed (2026-09-01)

## Context

`SQLiteMemory` needs local text embeddings. The original implementation used
`sentence-transformers`, which pulls in PyTorch and, on many platforms, CUDA
tooling. That is a multi-gigabyte install for a package whose core value is a
local-first CLI.

## Decision

Replace `sentence-transformers` with `fastembed`, which runs the same
`all-MiniLM-L6-v2` model through ONNX Runtime. Keep the model identifier and the
384-dimension output unchanged.

## Consequences

- The PyTorch/CUDA stack is gone. Install size drops by orders of magnitude.
- **Existing databases need no migration**, because both the model and the
  vector dimensionality are unchanged. This was the constraint that made the
  swap safe, and it is why the model name is not a free parameter: changing it
  silently invalidates every stored embedding.
- `sqlite.py` carries a name-mapping table (`all-MiniLM-L6-v2` ->
  `sentence-transformers/all-MiniLM-L6-v2`) because fastembed identifies models
  by fully-qualified Hub name. The short name is kept for backward
  compatibility.
- `onnxruntime` is now a transitive dependency of the `sqlite` extra. Still
  large, but far smaller than the alternative.
