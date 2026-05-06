# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import difflib
import itertools
import re
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from re import Pattern

__all__ = [
    "_PatternTree",
    "_common_pattern",
]

WILDCARD: str = r".*"
"""
A constant defining regex for match all.
"""


def tokenize(value: str) -> list[str]:
    """
    If `value` does not contain any regex symbols, then "".join(tokenize(value)) == value. If `value` does contain
    Wildcards, the wildcards should be preserved. Notice wildcards could happen as substrings. Tokenize should also
    preserve any white space, tabs and line breaks.

    Args:
        value: The string to tokenize.

    Returns:
        The value broken into tokens.
    """
    tokens: list[str] = []
    for token in re.split(r"(\s+|\.\*)", value):
        if token.isspace():
            tokens.append(token)
        elif token == WILDCARD:
            tokens.append(WILDCARD)
        elif token:
            tokens.append(re.escape(token))
    return tokens


def normalize_regex(tokens: list[str]) -> str:
    """
    Attempts to normalize a regex. We generate only wildcards, as such, things like: `This is an .*.* example` should
    be written as `This is an .* example` instead.

    Args:
        tokens: The list of tokens.

    Returns:
        The normalized pattern as string.
    """
    flag: bool = True
    while flag:
        flag = False
        reduced_tokens: list[str] = []
        # Remove consecutive wildcards
        for key, group in itertools.groupby(tokens):
            if key == WILDCARD:
                reduced_tokens.append(key)
            else:
                reduced_tokens.extend(group)
        # Introduce more wildcards
        tokens = reduced_tokens
        for i in range(len(tokens) - 2):
            if tokens[i] == WILDCARD and tokens[i + 1].isspace() and tokens[i + 2] == WILDCARD:
                tokens[i + 1] = WILDCARD
                flag = True
    return "".join(tokens)


def _common_pattern(this: str, other: str, max_diff: int | None = None) -> Pattern | None:
    """
    Creates a common expression between `self` and `other`. A common expression should satisfy:
    - common.matches(self) -> True
    - common.matches(other) -> True

    Args:
        this: A string value.
        other: A string value.
        max_diff: Optional. The maximum number of editions (i.e. insertions and deletions).

    Returns:
        A common expression that matches both `self` and `other`. if `max_diff` was provided and a common pattern
        that has fewer edits than `max_diff` is not found, returns None.
    """
    if this == WILDCARD:
        return other
    elif other == WILDCARD:
        return this

    lh_tokens: list[str] = tokenize(this)
    rh_tokens: list[str] = tokenize(other)
    matcher = difflib.SequenceMatcher(None, lh_tokens, rh_tokens)

    if max_diff is not None:
        num_matches: int = sum(block.size for block in matcher.get_matching_blocks())
        num_diffs: int = (len(lh_tokens) - num_matches) + (len(rh_tokens) - num_matches)
        if num_diffs > max_diff:
            return None

    tokens: list[str] = []
    for tag, start, end, _, _ in matcher.get_opcodes():
        if tag == "equal":
            tokens.extend(lh_tokens[start:end])
        else:
            tokens.append(WILDCARD)
    return re.compile(normalize_regex(tokens), flags=re.DOTALL)


def edit_distance(this: str, other: str) -> int:
    """
    Computes the edit distance between `this` and `other`, i.e. the smallest number of additions and deletions to
    convert `this` into `other`.

    Args:
        this: A string value.
        other: A string value

    Returns:
        The edit distance between `this` and `other`.
    """
    if this == WILDCARD or other == WILDCARD:
        return len(this) + len(other)

    lh_tokens: list[str] = tokenize(this)
    rh_tokens: list[str] = tokenize(other)

    matcher = difflib.SequenceMatcher(None, lh_tokens, rh_tokens)
    num_matches: int = sum(block.size for block in matcher.get_matching_blocks())
    return (len(lh_tokens) - num_matches) + (len(rh_tokens) - num_matches)


@dataclass
class PatternNode:
    value: Pattern | str = field()
    children: list[PatternNode] = field(default_factory=list)

    @property
    def literal(self) -> str:
        """Returns the string value of this node."""
        if isinstance(self.value, Pattern):
            return self.value.pattern
        else:
            return self.value

    @property
    def lower(self):
        """A lower node is one that is close to the leaves rather than the root."""
        wildcards, words = 0, 0
        for token in tokenize(self.literal):
            if token == WILDCARD:
                wildcards += 1
            elif not token.isspace():
                words += 1
        return wildcards + 1 < words

    def leaves(self) -> Iterator[PatternNode]:
        """Return the leave nodes under this node."""
        q: deque[PatternNode] = deque()
        q.append(self)
        while q:
            node: PatternNode = q.pop()
            if not node.children:
                yield node
            else:
                for child in node.children:
                    q.append(child)

    def match(self, literal: str) -> bool:
        if isinstance(self.value, Pattern):
            return self.value.fullmatch(literal)
        else:
            return self.value == literal

    def insert(self, literal: str) -> bool:
        """
        Args:
            literal: Another pattern.

        Returns:
            Returns true if it can insert the pattern as a child node. False otherwise.
        """
        if not self.match(literal):
            return False
        if self.literal == literal:
            return True
        # Find specific pattern first.
        for child in self.children:
            if child.insert(literal):
                return True

        # Append as a child or as a grandchild.
        min_dist: int = edit_distance(self.literal, literal)
        min_index: int | None = None
        min_common: Pattern | None = None
        for index, child in enumerate(self.children):
            common: Pattern | None = _common_pattern(child.literal, literal, min_dist)
            if common is None:
                # i.e. common pattern would require edits > min_dist
                continue
            if self.literal == common.pattern:
                # i.e. common pattern is self
                continue
            dist: int = max(
                edit_distance(common.pattern, child.literal),
                edit_distance(common.pattern, literal),
            )
            if dist < min_dist:
                min_dist, min_index, min_common = dist, index, common

        if min_index is None:
            self.children.append(
                PatternNode(value=literal),
            )
        else:
            self.children[min_index] = PatternNode(
                value=min_common,
                children=[
                    self.children[min_index],
                    PatternNode(value=literal),
                ],
            )
        return True


@dataclass
class _PatternTree:
    """
    A tree of patterns. The root of a pattern tree is a Wildcard (i.e. `.*`), the leaves are Literal expressions (
    i.e. do not contain Wildcards). The further down in the tree the more specific the patterns are.
    """

    root: PatternNode = field(default_factory=lambda: PatternNode(value=re.compile(WILDCARD, flags=re.DOTALL)))

    def insert(self, message: str) -> None:
        """
        Args:
            message: The message to insert into the pattern tree.
        """
        self.root.insert(message)

    def as_dict(self) -> dict[str, list[str]]:
        """
        Returns:
            Internal method to return this tree as a python dict.
        """
        patterns: list[PatternNode] = []

        q: deque[PatternNode] = deque()
        q.append(self.root)
        while q:
            node: PatternNode = q.pop()
            if node.lower:
                patterns.append(node)
            else:
                for child in reversed(node.children):
                    q.append(child)

        result = {}
        for node in patterns:
            expressions: list[str] = []
            for leaf in node.leaves():
                expressions.append(leaf.literal)
            result[node.literal] = expressions
        return result

    def __iter__(self) -> Iterator[tuple[int, Pattern]]:
        q: deque[PatternNode] = deque()
        q.append((self.root, 0))
        while q:
            node, height = q.pop()
            yield height, node.literal
            for child in reversed(node.children):
                q.append((child, height + 1))
