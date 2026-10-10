def parse_commit(message: str) -> dict:
    """Parse a conventional commit message into components.

    Args:
        message: The commit message string.

    Returns:
        A dictionary with keys 'type', 'scope', 'description'.
        If a part is missing, it is set to None.
    """
    # Initialize result
    result = {"type": None, "scope": None, "description": None}

    # Split by ': ' to separate header and description
    if ": " not in message:
        # No description? Then treat whole message as header with empty description?
        # According to conventional commits, there must be a colon and space.
        # We'll return the parsed header and empty description.
        header = message
        description = ""
    else:
        header, description = message.split(": ", 1)

    # Now parse header for type and optional scope
    # Header format: <type>(<scope>) or <type>
    if "(" in header and ")" in header:
        # There is a scope
        type_end = header.find("(")
        scope_start = type_end + 1
        scope_end = header.find(")", scope_start)
        result["type"] = header[:type_end]
        result["scope"] = header[scope_start:scope_end]
    else:
        # No scope
        result["type"] = header
        result["scope"] = None

    result["description"] = description.strip()
    return result