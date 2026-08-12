# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from common import AsyncioValidationTestCase
from pxr import Usd, UsdGeom, UsdLux

import usd_validation_nvidia.capabilities as cap
from usd_validation_nvidia import HierarchyHasRootChecker
from usd_validation_nvidia.tests import IsAFailure


class HierarchyHasRootCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.HI_001)

    async def test_scattered_asset_roots_fail(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/Xform1")
        UsdGeom.Xform.Define(stage, "/Xform2")
        stage.SetDefaultPrim(stage.GetPrimAtPath("/Xform1"))
        await self.assertRuleAsync(
            asset=stage,
            rule=HierarchyHasRootChecker,
            asserts=[
                IsAFailure(
                    message="Prim hierarchy must have a single root prim. Found 2 root prims: Xform1, Xform2",
                )
            ],
        )

    async def test_non_asset_roots_are_excluded(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/Asset")
        UsdLux.DomeLight.Define(stage, "/Light")
        stage.SetDefaultPrim(stage.GetPrimAtPath("/Asset"))
        await self.assertRuleAsync(asset=stage, rule=HierarchyHasRootChecker, asserts=[])

    async def test_only_non_asset_roots_reports_missing_asset_root(self):
        # Root prims exist, but none qualifies as an asset root: the message must
        # point at the content of the existing roots, not claim there are no roots.
        stage = Usd.Stage.CreateInMemory()
        UsdLux.DomeLight.Define(stage, "/Light")
        UsdGeom.Camera.Define(stage, "/Camera")
        await self.assertRuleAsync(
            asset=stage,
            rule=HierarchyHasRootChecker,
            asserts=[
                IsAFailure(
                    message=(
                        "Prim hierarchy has no asset root prim: no default prim is set and no root prim "
                        "(Light, Camera) contains asset content (Xforms, geometry, or materials)."
                    ),
                )
            ],
        )

    async def test_empty_stage_reports_no_root_prims(self):
        stage = Usd.Stage.CreateInMemory()
        await self.assertRuleAsync(
            asset=stage,
            rule=HierarchyHasRootChecker,
            asserts=[
                IsAFailure(
                    message="Prim hierarchy must have at least one root prim. Found no root prims.",
                )
            ],
        )


class RootPrimXformableCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.HI_003)
