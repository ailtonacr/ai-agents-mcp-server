import inspect
import json
from typing import Callable, Any, get_type_hints, get_origin
from collections.abc import Mapping, Sequence
from mcp import types as mcp_types

try:
    from docstring_parser import parse
    HAS_DOCSTRING_PARSER = True
except ImportError:
    HAS_DOCSTRING_PARSER = False


class MCPFunctionTool:
    """
    Automatically generates a tool for MCP based on a Python function.
    """

    def __init__(self, func: Callable, name: str | None = None, description: str | None = None):
        self.func = func
        self.name = name or func.__name__
        self.description = description or self._extract_full_description()
        self._input_schema = None

    def _extract_full_description(self) -> str:
        """Extracts the full description from the docstring using docstring-parser if available."""
        if not self.func.__doc__:
            return f"Function {self.func.__name__}"

        if HAS_DOCSTRING_PARSER:
            try:
                parsed = parse(self.func.__doc__)
                if parsed.short_description:
                    description = parsed.short_description
                    if parsed.long_description:
                        description += f" {parsed.long_description}"
                    return description
            except Exception:
                pass

        # Fallback to manual parsing
        docstring = self.func.__doc__.strip()
        if "Args:" in docstring:
            description = docstring.split("Args:")[0].strip()
        elif "Parameters:" in docstring:
            description = docstring.split("Parameters:")[0].strip()
        else:
            description = docstring

        lines = [line.strip() for line in description.split('\n') if line.strip()]
        return ' '.join(lines) if lines else f"Function {self.func.__name__}"

    @property
    def input_schema(self) -> dict[str, Any]:
        """Automatically generates the input schema based on the function signature."""
        if self._input_schema is None:
            self._input_schema = self._generate_input_schema()
        return self._input_schema

    def _generate_input_schema(self) -> dict[str, Any]:
        """Generates the JSON schema based on the function signature."""
        sig = inspect.signature(self.func)
        type_hints = get_type_hints(self.func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, str)
            json_type = self._python_type_to_json_type(param_type)

            param_description = self._extract_param_description_robust(param_name)

            param_info = {
                "type": json_type,
                "description": param_description
            }

            if json_type == "object":
                param_info["additionalProperties"] = True

            properties[param_name] = param_info

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _extract_param_description_robust(self, param_name: str) -> str:
        """
        Extracts parameter description using docstring-parser if available,
        with fallback to manual parsing for robustness.
        """
        if not self.func.__doc__:
            return f"Parameter {param_name}"

        if HAS_DOCSTRING_PARSER:
            try:
                parsed = parse(self.func.__doc__)
                for param in parsed.params:
                    if param.arg_name == param_name:
                        return param.description or f"Parameter {param_name}"
            except Exception:
                pass

        # Fallback to manual parsing with improved robustness
        lines = self.func.__doc__.split('\n')
        patterns = [
            f"{param_name} (",      # Google style: param_name (type): description
            f"{param_name}:",       # Simple style: param_name: description
            f":param {param_name}", # Sphinx style: :param param_name: description
            f"- {param_name}",      # Markdown style: - param_name: description
        ]

        for i, line in enumerate(lines):
            line = line.strip()

            for pattern in patterns:
                if pattern in line:
                    if ':' in line:
                        colon_pos = line.rfind(':')
                        desc = line[colon_pos + 1:].strip()

                        if desc.startswith('(') and ')' in desc:
                            paren_pos = desc.find(')')
                            desc = desc[paren_pos + 1:].strip()

                        # Check next line if description is empty
                        if not desc and i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line and not any(p in next_line for p in patterns):
                                desc = next_line

                        if desc:
                            return desc

        return f"Parameter {param_name}"

    @staticmethod
    def _python_type_to_json_type(python_type) -> str:
        """
        Converts Python types to JSON Schema using robust type inspection.
        Uses typing.get_origin and collections.abc for better reliability.
        """
        # Basic types mapping
        basic_types = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            dict: "object",
            list: "array",
            type(None): "null"
        }

        if python_type in basic_types:
            return basic_types[python_type]

        origin = get_origin(python_type)
        if origin is not None:
            if origin in basic_types:
                return basic_types[origin]

            try:
                if issubclass(origin, Mapping):
                    return "object"
                elif issubclass(origin, Sequence) and not issubclass(origin, (str, bytes)):
                    return "array"
            except TypeError:
                pass

        try:
            if hasattr(python_type, '__mro__'):
                if issubclass(python_type, Mapping):
                    return "object"
                elif issubclass(python_type, Sequence) and not issubclass(python_type, (str, bytes)):
                    return "array"
                elif issubclass(python_type, (int, float)):
                    return "number"
                elif issubclass(python_type, str):
                    return "string"
                elif issubclass(python_type, bool):
                    return "boolean"
        except TypeError:
            pass

        type_name = getattr(python_type, '__name__', str(python_type)).lower()

        if any(keyword in type_name for keyword in ['dict', 'mapping']):
            return "object"
        elif any(keyword in type_name for keyword in ['list', 'sequence', 'array', 'tuple']):
            return "array"
        elif any(keyword in type_name for keyword in ['int', 'integer']):
            return "integer"
        elif any(keyword in type_name for keyword in ['float', 'number', 'decimal']):
            return "number"
        elif any(keyword in type_name for keyword in ['bool', 'boolean']):
            return "boolean"

        return "string"  # Safe fallback

    def to_mcp_tool(self) -> mcp_types.Tool:
        """Converts to MCP Tool type."""
        return mcp_types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )

    async def run_async(self, args: dict[str, Any]) -> str:
        """Executes the function with the provided arguments."""
        if inspect.iscoroutinefunction(self.func):
            result = await self.func(**args)
        else:
            result = self.func(**args)

        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
