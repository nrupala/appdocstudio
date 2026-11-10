"""Greeter service used as a parser fixture.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

DEFAULT_LOCALE = "en"


class Greeter:
    """Greets people in a configurable locale."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        """Create a greeter for a locale."""
        self.locale = locale

    def greet(self, name: str, *, punctuate: bool = True) -> str:
        """Return a greeting for ``name``.

        The greeting uses the greeter's locale.
        """
        suffix = "!" if punctuate else ""
        return f"Hello, {name}{suffix}"

    async def greet_many(self, names: list[str]) -> list[str]:
        """Greet many people at once."""
        return [self.greet(n) for n in names]


def make_greeter(locale: str = "en") -> Greeter:
    """Build a Greeter for the given locale."""
    return Greeter(locale)
