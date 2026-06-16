"""Serializer for B+ Tree values supporting multiple data types."""

from __future__ import annotations

import json
from typing import Any


class Serializer:
    """Serialize and deserialize values for storage in the B+ tree.

    Supported types: str, int, float, bool, None, list, dict.
    Serialized values are stored as JSON strings with a type tag.
    """

    TYPE_TAG = "__bplus_type__"
    VALUE_TAG = "__bplus_value__"

    def serialize_value(self, value: Any) -> str:
        """Serialize a Python value to a string for storage."""
        if value is None:
            return json.dumps({self.TYPE_TAG: "none", self.VALUE_TAG: None})
        elif isinstance(value, bool):
            return json.dumps({self.TYPE_TAG: "bool", self.VALUE_TAG: value})
        elif isinstance(value, int):
            return json.dumps({self.TYPE_TAG: "int", self.VALUE_TAG: value})
        elif isinstance(value, float):
            return json.dumps({self.TYPE_TAG: "float", self.VALUE_TAG: value})
        elif isinstance(value, str):
            return json.dumps({self.TYPE_TAG: "str", self.VALUE_TAG: value})
        elif isinstance(value, (list, dict)):
            return json.dumps({self.TYPE_TAG: "json", self.VALUE_TAG: value})
        else:
            # Fall back to JSON serialization for other types
            return json.dumps({self.TYPE_TAG: "object", self.VALUE_TAG: str(value)})

    def deserialize_value(self, data: str) -> Any:
        """Deserialize a stored string back to a Python value."""
        try:
            tagged = json.loads(data)
            if isinstance(tagged, dict) and self.TYPE_TAG in tagged:
                type_name = tagged[self.TYPE_TAG]
                raw_value = tagged[self.VALUE_TAG]
                if type_name == "none":
                    return None
                elif type_name == "bool":
                    return bool(raw_value)
                elif type_name == "int":
                    return int(raw_value)
                elif type_name == "float":
                    return float(raw_value)
                elif type_name == "str":
                    return str(raw_value)
                elif type_name == "json":
                    return raw_value
                elif type_name == "object":
                    return raw_value
            # If not tagged, return as-is (backward compatibility)
            return tagged
        except (json.JSONDecodeError, TypeError):
            # If not JSON, return raw string (backward compatibility)
            return data