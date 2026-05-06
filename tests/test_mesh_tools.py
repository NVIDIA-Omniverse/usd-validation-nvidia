# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import random
import unittest

from pxr import Gf

from usd_validation_nvidia import RepeatedValuesSet
from usd_validation_nvidia._mesh_tools import remove_unused_values_and_remap_indices


class MeshToolsTest(unittest.TestCase):
    def test_repetitions_not_found(self):
        value = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        repetitions = RepeatedValuesSet(value)
        self.assertFalse(repetitions)
        self.assertEqual(0, len(repetitions))

    def test_repetitions_found(self):
        # 0 is repeated at 0, 5
        value = [0, 1, 2, 3, 4, 0, 6, 7, 8, 9]

        repetitions = RepeatedValuesSet(value)
        self.assertTrue(repetitions)
        self.assertEqual(2, len(repetitions))

    def test_repetitions_not_found_both(self):
        numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        words = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

        repetitions_numbers = RepeatedValuesSet(numbers)
        repetitions_words = RepeatedValuesSet(words)
        result = repetitions_numbers & repetitions_words
        self.assertFalse(result)
        self.assertEqual(0, len(result))

    def test_repetitions_found_both(self):
        # 0 is repeated at 0, 5, 9; "a" is repeated at 0, 5, 9
        numbers = [0, 1, 2, 3, 4, 0, 6, 7, 8, 0]
        words = ["a", "b", "c", "d", "e", "a", "g", "h", "i", "a"]

        repetitions_numbers = RepeatedValuesSet(numbers)
        repetitions_words = RepeatedValuesSet(words)
        result = repetitions_numbers & repetitions_words
        self.assertTrue(result)
        self.assertEqual(3, len(result))

    def test_repetitions_found_subset(self):
        # 0 is repeated at 0, 5, 9; "f" is repeated at 5, 9
        numbers = [0, 1, 2, 3, 4, 0, 6, 7, 8, 0]
        words = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "f"]

        repetitions_numbers = RepeatedValuesSet(numbers)
        repetitions_words = RepeatedValuesSet(words)
        result = repetitions_numbers & repetitions_words
        self.assertTrue(result)
        self.assertEqual(2, len(result))

    def test_remove_used_values_and_indices(self):
        vec_values = []
        for i in range(100):
            vec_values.append(Gf.Vec3d(i))

        index_values = [random.randrange(0, 100) for _ in range(50)]
        expected_to_keep_values = [vec_values[index] for index in sorted(list(set(index_values)))]
        expected_to_remove_indices = [index for index in range(100) if index not in index_values]
        expected_reference_values = [vec_values[index] for index in index_values]

        success, updated_values, updated_indices, removed_indices = remove_unused_values_and_remap_indices(
            vec_values, index_values
        )
        self.assertTrue(success)
        self.assertEqual(removed_indices, expected_to_remove_indices)
        self.assertEqual(len(updated_values), len(set(index_values)))
        self.assertEqual(expected_to_keep_values, updated_values)

        updated_reference_values = [updated_values[index] for index in updated_indices]
        self.assertEqual(updated_reference_values, expected_reference_values)

        # Generates 10 indices that are beyond value array.
        invalid_indices = [random.randrange(100, 120) for _ in range(10)]
        index_values.extend(invalid_indices)

        # Removes invalid indices also.
        success, updated_values, updated_indices, removed_indices = remove_unused_values_and_remap_indices(
            vec_values, index_values, True
        )
        self.assertTrue(success)
        self.assertEqual(removed_indices, expected_to_remove_indices)
        self.assertEqual(expected_to_keep_values, updated_values)

        updated_reference_values = [updated_values[index] for index in updated_indices]
        self.assertEqual(updated_reference_values, expected_reference_values)
