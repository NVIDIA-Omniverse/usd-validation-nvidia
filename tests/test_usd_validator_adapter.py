# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import re
import unittest
from unittest import mock

from common import AsyncioValidationTestCase, get_url
from pxr import Usd

from usd_validation_nvidia import PrimId, UsdValidatorAdapter
from usd_validation_nvidia.tests import IsAFailure


class _MissingReferenceValidator(UsdValidatorAdapter):
    """Fallback description."""

    @classmethod
    def validator_name(cls) -> str:
        return "usdUtilsValidators:MissingReferenceValidator"


class _FallbackPrimValidator(UsdValidatorAdapter):
    @classmethod
    def validator_name(cls) -> str:
        return "test:FallbackPrimValidator"

    def _CheckPrim(self, prim):
        self.checked_prim = prim


class _NoFallbackValidator(UsdValidatorAdapter):
    @classmethod
    def validator_name(cls) -> str:
        return "test:NoFallbackValidator"


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


class UsdValidatorAdapterHelperTest(unittest.TestCase):
    def test_check_prim_uses_fallback_when_native_validator_is_unavailable(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/Prim")
        checker = _FallbackPrimValidator(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)

        with mock.patch.object(_FallbackPrimValidator, "is_implemented", return_value=False):
            checker.CheckPrim(prim)

        self.assertEqual(checker.checked_prim, prim)

    def test_check_prim_raises_when_no_native_validator_or_fallback_exists(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/Prim")
        checker = _NoFallbackValidator(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)

        with (
            mock.patch.object(_NoFallbackValidator, "is_implemented", return_value=False),
            self.assertRaisesRegex(ValueError, "not implemented"),
        ):
            checker.CheckPrim(prim)

    def test_transform_uses_validator_error_sites(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/Prim")
        checker = _NoFallbackValidator(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        site = mock.Mock()
        site.GetPrim.return_value = prim
        site.GetProperty.return_value = None
        site.GetPrimSpec.return_value = None
        site.GetPropertySpec.return_value = None
        site.GetLayer.return_value = None
        site.GetStage.return_value = None
        error = mock.Mock()
        error.GetMessage.return_value = "message"
        error.GetSites.return_value = [site]

        issues = checker._transform(error)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].message, "message")
        self.assertEqual(issues[0].at, PrimId.from_(prim))

    def test_transform_returns_site_less_issue_when_error_has_no_sites(self):
        checker = _NoFallbackValidator(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        error = mock.Mock()
        error.GetMessage.return_value = "message"
        error.GetSites.return_value = []

        issues = checker._transform(error)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].message, "message")
        self.assertIsNone(issues[0].at)
