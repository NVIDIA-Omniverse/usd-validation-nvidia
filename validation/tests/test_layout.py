# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import usd_validation_nvidia.capabilities as cap
from common import AsyncioValidationTestCase, get_url
from pxr import Sdf
from usd_validation_nvidia import (
    DanglingOverPrimChecker,
    DefaultPrimChecker,
)
from usd_validation_nvidia.tests import IsAFailure, IsAWarning


class DefaultPrimCheckerTest(AsyncioValidationTestCase):

    async def test_examples(self):
        await self.assertExamplesSuggestionsAsync(requirement=cap.Requirements.HI_004)

    async def test_invalid_default_prims(self):
        await self.assertRuleAsync(
            asset=get_url("layoutFailures.usda"),
            rule=DefaultPrimChecker,
            asserts=[
                IsAFailure("The default prim.*not Xformable", at=Sdf.Path("/World")),
                IsAFailure(
                    "The default prim.*should be active",
                    at=Sdf.Path("/World"),
                    requirement=cap.Requirements.HI_004,
                ),
                IsAWarning("The prim.*is a sibling of the default prim.*", at=Sdf.Path("/Root")),
                IsAWarning(
                    "The prim.*is a sibling of the default prim.*",
                    at=Sdf.Path("/ScopeIsConsideredDefaultPrimCandidate"),
                ),
            ],
        )


class DanglingOverPrimCheckerTest(AsyncioValidationTestCase):

    async def testDanglingOverPrimChecker(self):
        await self.assertRuleAsync(
            asset=get_url("layoutFailures.usda"),
            rule=DanglingOverPrimChecker,
            asserts=[
                IsAFailure("Prim has an dangling over.*", at=Sdf.Path("/Root/Orphan")),
            ],
        )

        await self.assertRuleAsync(
            asset=get_url("validOrphanedOver.usda"),
            rule=DanglingOverPrimChecker,
            asserts=[],
        )
