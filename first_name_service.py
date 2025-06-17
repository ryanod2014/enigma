"""first_name_service.py
Simple service wrapper around FirstNameIndex so the rest of the backend can
interact with first-name data via a stable interface (mirrors noun & place
services).
"""
from __future__ import annotations

from typing import List

from first_name_index import FirstNameIndex


class FirstNameService:
    """Public service exposing convenient query helpers for first names."""

    _index = FirstNameIndex()

    # ------------------------------------------------------------------ #
    @classmethod
    def exact(
        cls,
        length: int,
        first_letter: str,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        *,
        gender: str | None = None,
        origin: str | None = None,
        common: bool | None = None,
        nickname: str | None = None,
    ) -> List[str]:
        """Exact-letter query – thin pass-through to FirstNameIndex.query."""
        return cls._index.query(
            length,
            first_letter,
            first_vowel_pos,
            second_vowel_pos,
            gender=gender,
            origin=origin,
            common=common,
            nickname=nickname,
        )

    # ------------------------------------------------------------------ #
    @classmethod
    def category(
        cls,
        length: int,
        category: int,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        *,
        random_constraint: str | None = None,
        more_vowels: bool | None = None,
        gender: str | None = None,
        origin: str | None = None,
        common: bool | None = None,
        nickname: str | None = None,
    ) -> List[str]:
        """Category query – mirrors PlaceService.category semantics."""
        return cls._index.query_category(
            length,
            category,
            first_vowel_pos,
            second_vowel_pos,
            random_constraint=random_constraint,
            more_vowels=more_vowels,
            gender=gender,
            origin=origin,
            common=common,
            nickname=nickname,
        ) 