"""Allow running ``python -m changelogger``.

This module simply imports the :func:`main` function from :mod:`changelogger.cli`
and invokes it.
"""

from .cli import main

if __name__ == "__main__":
    main()