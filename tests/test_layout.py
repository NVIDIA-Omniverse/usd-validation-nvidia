# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import nvidia_usd_validation.capabilities as cap
from common import AsyncioValidationTestCase, get_url
from nvidia_usd_validation import DanglingOverPrimChecker, DefaultPrimChecker, IssuePredicates
from nvidia_usd_validation.tests import IsAFailure, IsAWarning
from pxr import Sdf


class DefaultPrimCheckerTest(AsyncioValidationTestCase):

    async def test_missing_or_invalid_default_prim(self):
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=DefaultPrimChecker,
            asserts=[
                IsAFailure("Stage has missing or invalid defaultPrim.*", requirement=cap.Requirements.HI_004),
            ],
        )

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

    async def test_default_prim_is_scope(self):
        await self.assertRuleAsync(
            asset=get_url("layoutDefaultPrimScope.usda"),
            rule=DefaultPrimChecker,
            asserts=[],
        )

    async def test_fix_default_prim(self):
        await self.assertSuggestionAsync(
            asset=get_url("layoutDefaultPrimFix.usda"),
            rule=DefaultPrimChecker,
            predicate=IssuePredicates.ContainsMessage("Stage has missing or invalid defaultPrim."),
        )

    async def test_fix_activate_prim(self):
        await self.assertSuggestionAsync(
            asset=get_url("layoutFailures.usda"),
            rule=DefaultPrimChecker,
            predicate=IssuePredicates.ContainsMessage("The default prim <World> should be active."),
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
