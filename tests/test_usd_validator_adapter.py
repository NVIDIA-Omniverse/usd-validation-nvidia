# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import re
import unittest

from common import AsyncioValidationTestCase, get_url

from usd_validation_nvidia import UsdValidatorAdapter
from usd_validation_nvidia.tests import IsAFailure


class _MissingReferenceValidator(UsdValidatorAdapter):
    """Fallback description."""

    @classmethod
    def validator_name(cls) -> str:
        return "usdUtilsValidators:MissingReferenceValidator"


@unittest.skipIf(_MissingReferenceValidator.is_implemented(), "Tests disabled because validator is implemented")
class UsdValidatorAdapterCompatibilityTest(AsyncioValidationTestCase):
    async def test_description_ok(self):
        self.assertRegex(_MissingReferenceValidator.GetDescription(), r".*Fallback description\.")

    async def test_contains_nok(self):
        self.assertFalse("usdUtilsValidators:MissingReferenceValidator" in UsdValidatorAdapter)

    async def test_is_implemented_nok(self):
        self.assertFalse(_MissingReferenceValidator.is_implemented())

    async def test_validate_nok(self):
        await self.assertFailureAsync(
            asset=get_url("basicFailures.usda"),
            rule=_MissingReferenceValidator,
        )


@unittest.skipUnless(_MissingReferenceValidator.is_implemented(), "Tests disabled because validator is not implemented")
class UsdValidatorAdapterTest(AsyncioValidationTestCase):

    async def test_description_ok(self):
        self.assertRegex(
            _MissingReferenceValidator.GetDescription(), r".* should not contain any unresolvable asset dependencies .*"
        )

    async def test_contains_ok(self):
        self.assertTrue("usdUtilsValidators:MissingReferenceValidator" in UsdValidatorAdapter)

    async def test_implemented_ok(self):
        self.assertTrue(_MissingReferenceValidator.is_implemented())

    async def test_validate_nok(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=_MissingReferenceValidator,
            asserts=[
                IsAFailure(
                    message=re.compile(r".* unresolvable .*doesNotExist\.usda.*"),
                ),
            ],
        )
