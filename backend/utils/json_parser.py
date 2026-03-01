"""
NexusTrade — Safe JSON Parser for LLM Outputs
Handles common LLM issues: unescaped control characters, markdown fences, etc.
"""

import json
import re


def safe_parse_json(text: str) -> dict:
    """Parse JSON from LLM output, handling common issues.
    
    Handles:
    - Unescaped newlines/tabs/control chars in string values
    - Markdown ```json fences
    - Leading/trailing text around JSON
    """
    content = text.strip()

    # Strip markdown code fences
    content = re.sub(r'^```(?:json)?\s*\n?', '', content)
    content = re.sub(r'\n?```\s*$', '', content)

    # Try parsing directly first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try finding JSON object in the text
    start = content.find('{')
    end = content.rfind('}')
    if start >= 0 and end > start:
        block = content[start:end + 1]
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass

        # Replace control characters inside string values
        cleaned = _clean_control_chars(block)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Last resort: return raw text as a dict
    return {"raw_response": content}


def _clean_control_chars(text: str) -> str:
    """Remove or escape control characters that break JSON parsing."""
    # Replace literal newlines, tabs, carriage returns inside strings
    result = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                # Skip other control characters
                continue
            else:
                result.append(char)
        else:
            result.append(char)

    return ''.join(result)
