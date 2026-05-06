# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import inspect
import unittest
from itertools import permutations
from re import Pattern

from usd_validation_nvidia import _common_pattern, _PatternTree


class ExpressionTests(unittest.TestCase):
    def test_expression_common(self):
        a: str = "This is a nice sentence"

        self.assertEqual(_common_pattern(a, "This is a cool sentence").pattern, "This is a .* sentence")
        self.assertEqual(_common_pattern(a, "This is a very cool sentence").pattern, "This is a .* sentence")
        self.assertEqual(_common_pattern(a, "This is a sentence complete").pattern, "This is a .*")
        self.assertEqual(_common_pattern(a, "Completely unrelated").pattern, ".*")

    def test_expression_common_matches(self):
        expressions: list[str] = [
            "This is a nice sentence",
            "This is a cool sentence",
            "This is a very cool sentence",
            "This is a sentence complete",
            "Unrelated stuff!",
        ]
        for permutation in permutations(expressions, 2):
            common: Pattern | None = _common_pattern(permutation[0], permutation[1])
            self.assertIsNotNone(common)
            self.assertTrue(common.fullmatch(permutation[0]))
            self.assertTrue(common.fullmatch(permutation[1]))

    @classmethod
    def print_tree(cls, tree) -> str:
        lines: list[str] = []
        for height, expression in tree:
            space: str = "    " * height
            lines.append(f"{space}{expression}")
        return "\n".join(lines)

    def test_expression_tree_init(self):
        tree = _PatternTree()
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
            """
            ),
        )

    def test_expression_tree(self):
        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a nice sentence
            """
            ),
        )

        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a cool sentence")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a .* sentence
                    This is a nice sentence
                    This is a cool sentence
            """
            ),
        )

        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a cool sentence")
        tree.insert("This is a very cool sentence")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a .* sentence
                    This is a nice sentence
                    This is a .*cool sentence
                        This is a cool sentence
                        This is a very cool sentence
            """
            ),
        )

        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a cool sentence")
        tree.insert("This is a very cool sentence")
        tree.insert("This is a sentence complete")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a .*
                    This is a .* sentence
                        This is a nice sentence
                        This is a .*cool sentence
                            This is a cool sentence
                            This is a very cool sentence
                    This is a sentence complete
            """
            ),
        )

        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a cool sentence")
        tree.insert("This is a very cool sentence")
        tree.insert("This is a sentence complete")
        tree.insert("Unrelated stuff!")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a .*
                    This is a .* sentence
                        This is a nice sentence
                        This is a .*cool sentence
                            This is a cool sentence
                            This is a very cool sentence
                    This is a sentence complete
                Unrelated stuff!
            """
            ),
        )

        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a very cool sentence")
        tree.insert("This is a cool sentence")
        tree.insert("This is a sentence complete")
        tree.insert("Unrelated stuff!")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a .*
                    This is a .* sentence
                        This is a nice sentence
                        This is a very cool sentence
                        This is a cool sentence
                    This is a sentence complete
                Unrelated stuff!
            """
            ),
        )

    def test_expression_tree_repeated(self):
        tree = _PatternTree()
        tree.insert("This is a nice sentence")
        tree.insert("This is a nice sentence")
        self.assertEqual(
            self.print_tree(tree),
            inspect.cleandoc(
                """
            .*
                This is a nice sentence
            """
            ),
        )
