# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia.capabilities import Requirement as RequirementDTO
from usd_validation_nvidia.tests import (
    AsyncioValidationTestCaseMixin,
    ValidationTestCaseMixin,
)


class ExamplesAssertionsTest(unittest.IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin, ValidationTestCaseMixin):
    def test_examples_without_examples_fails(self):
        requirement = RequirementDTO(code="REQ.01", version="1.0.0")

        with self.assertRaises(AssertionError):
            self.assertExamples(requirement=requirement)

    async def test_examples_async_without_examples_fails(self):
        requirement = RequirementDTO(code="REQ.01", version="1.0.0")

        with self.assertRaises(AssertionError):
            await self.assertExamplesAsync(requirement=requirement)

    async def test_examples_suggestions_async_without_examples_fails(self):
        requirement = RequirementDTO(code="REQ.01", version="1.0.0")

        with self.assertRaises(AssertionError):
            await self.assertExamplesSuggestionsAsync(requirement=requirement)
