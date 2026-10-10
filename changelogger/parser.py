def parse_commit(message: str) -> dict:
    """Parse a conventional commit message into components.

    Args:
        message: The commit message string.

    Returns:
        A dictionary with keys ``type``, ``scope``, ``description`` and ``breaking``.
        ``breaking`` is ``True`` when the commit header contains a ``!`` after the type
        (or after the optional scope) as defined by the Conventional Commits spec.
        Missing parts are set to ``None`` (or ``False`` for ``breaking``).
    """
    # Initialize result with default values
    result = {"type": None, "scope": None, "description": None, "breaking": False}

    # Split by ': ' to separate header and description
    if ": " not in message:
        header = message
        description = ""
    else:
        header, description = message.split(": ", 1)

    # Detect breaking change indicator '!' in header
    # It can appear directly after the type (e.g., "feat!:") or after the closing
    # parenthesis of the scope (e.g., "feat(core)!:").
    if header.endswith("!"):
        result["breaking"] = True
        header = header[:-1]  # remove the trailing '!'

    # Now parse header for type and optional scope
    if "(" in header and ")" in header:
        type_end = header.find("(")
        scope_start = type_end + 1
        scope_end = header.find(")", scope_start)
        result["type"] = header[:type_end]
        result["scope"] = header[scope_start:scope_end]
    else:
        result["type"] = header
        result["scope"] = None

    result["description"] = description.strip()

    # Detect breaking change footer
    # If any line starts with 'BREAKING CHANGE:' set breaking True
    if "BREAKING CHANGE:" in message:
        result["breaking"] = True

    return result
