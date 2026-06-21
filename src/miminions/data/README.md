# MiMinions Data

`miminions.data` provides local-first data management.

The implementation lives in the [`local/`](local/README.md) subpackage and is
re-exported here:

```python
from miminions.data import LocalDataManager
```

`LocalDataManager` is a content-addressable (SHA-256) file store with automatic
deduplication, a JSON master index of file metadata, an append-only transaction
log for an audit trail, and pluggable text/markdown/CSV file handlers. It is
pure Python with no extra dependencies.

See [`local/README.md`](local/README.md) for the full API and the
[Data Management](https://miminions.ai/modules/data/) documentation.
