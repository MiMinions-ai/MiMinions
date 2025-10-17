from typing import Any

class Config:
    def __init__(self,**kwargs):
        self.max_memory_tokens = kwargs.get("max_memory_tokens", 8000)
        self.config = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value