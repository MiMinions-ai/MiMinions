from agents.agent_output import AgentOutputSchemaBase
from typing import Dict, Any
import json
from pathlib import Path
from jsonschema import validate as js_validate, ValidationError
from agents.exceptions import ModelBehaviorError

class QuizAgentOutputSchema(AgentOutputSchemaBase):
    """
    Custom output schema that:
      - returns your JSON Schema (for Structured Outputs)
      - validates and parses the model's JSON into a Python object
    """

    def __init__(self, schema_path: Path = SCHEMA_PATH):
        self._schema_path = schema_path
        self._schema: Dict[str, Any] = json.loads(
            self._schema_path.read_text(encoding="utf-8")
        )
        # tip: assert top-level shape matches Structured Outputs support
        # (only supported/strict JSON Schema features) per docs:
        # https://platform.openai.com/docs/guides/structured-outputs/supported-schemas
        # The uploaded file uses only supported constructs (object/array/string/integer). :contentReference[oaicite:1]{index=1}

    # --- AgentOutputSchemaBase methods required by the SDK ---
    def is_plain_text(self) -> bool:
        return False

    def name(self) -> str:
        return "QuizJSON"

    def json_schema(self) -> Dict[str, Any]:
        # The SDK will pass this to the model as the response schema. :contentReference[oaicite:2]{index=2}
        return self._schema

    def is_strict_json_schema(self) -> bool:
        # Opt into strict mode so the SDK enforces the subset supported by Structured Outputs. :contentReference[oaicite:3]{index=3}
        return True

    def validate_json(self, json_str: str) -> Any:
        """
        Must return the validated object or raise ModelBehaviorError.
        """
        try:
            obj = json.loads(json_str)
        except Exception as e:
            raise ModelBehaviorError(f"Invalid JSON: {e}") from e

        try:
            js_validate(instance=obj, schema=self._schema)  # runtime guardrail
        except ValidationError as e:
            # Signal to the SDK that the model misbehaved. :contentReference[oaicite:4]{index=4}
            raise ModelBehaviorError(
                f"JSON failed schema validation: {e.message}"
            ) from e

        return obj

