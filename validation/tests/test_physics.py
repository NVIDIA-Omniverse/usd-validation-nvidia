# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import usd_validation_nvidia.capabilities as cap
from common import AsyncioValidationTestCase
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics
from usd_validation_nvidia import (
    ArticulationChecker,
    ColliderChecker,
)
from usd_validation_nvidia.tests import IsAFailure


class UsdPhysicsCheckerTestCase(AsyncioValidationTestCase):

    maxDiff = None

    async def test_rigid_body_examples(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.RB_003)
        await self.assertExamplesAsync(requirement=cap.Requirements.RB_005)
        await self.assertExamplesAsync(requirement=cap.Requirements.RB_009)

    async def test_collider_non_uniform_scale(self):
        stage = Usd.Stage.CreateInMemory()

        # Note: Removed Capsule_1 and Cylinder_1 from this check as they are not supported by older USD versions
        shapes = [UsdGeom.Sphere, UsdGeom.Capsule, UsdGeom.Cone, UsdGeom.Cylinder, UsdGeom.Points]
        parent = UsdGeom.Xform.Define(stage, "/parent")

        for shape_type in shapes:
            shape = shape_type.Define(stage, "/parent/shape")
            UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
            if shape_type == UsdGeom.Points:
                points = UsdGeom.Points(shape.GetPrim())
                points.GetPointsAttr().Set([Gf.Vec3f(0, 0, 0)])
                points.GetWidthsAttr().Set([1.0])
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[])

            # Clearly non-uniform scale on shape
            shape.AddScaleOp().Set(Gf.Vec3d(1, 2, 1))
            expected_failure = IsAFailure(
                message=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(shape.GetPrim().GetTypeName()),
                at="Prim </parent/shape>",
                requirement=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
            )
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[expected_failure])
            shape.ClearXformOpOrder()

            # Nearly uniform scale but still outside epsilon on shape
            shape.AddScaleOp().Set(Gf.Vec3d(1, 1.00006, 1))
            expected_failure = IsAFailure(
                message=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(shape.GetPrim().GetTypeName()),
                at=Sdf.Path("/parent/shape"),
                requirement=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
            )
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[expected_failure])
            shape.ClearXformOpOrder()

            # Nearly uniform scale within epsilon on shape (should pass)
            shape.AddScaleOp().Set(Gf.Vec3d(1, 1.000001, 1))
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[])

            # Non-uniform scale on parent
            shape.ClearXformOpOrder()
            parent.ClearXformOpOrder()
            parent.AddScaleOp().Set(Gf.Vec3d(1, 2, 1))
            expected_failure = IsAFailure(
                message=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(shape.GetPrim().GetTypeName()),
                at=Sdf.Path("/parent/shape"),
                requirement=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
            )
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[expected_failure])

            # Nearly non-uniform scale on parent but outside epsilon
            parent.ClearXformOpOrder()
            parent.AddScaleOp().Set(Gf.Vec3d(1, 1.00006, 1))
            expected_failure = IsAFailure(
                message=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(shape.GetPrim().GetTypeName()),
                at=Sdf.Path("/parent/shape"),
                requirement=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
            )
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[expected_failure])

            # Combined parent and shape scale that results in non-uniform scale
            parent.ClearXformOpOrder()
            parent.AddScaleOp().Set(Gf.Vec3d(1, 1.000025, 1))
            shape.AddScaleOp().Set(Gf.Vec3d(1, 1.000035, 1))
            expected_failure = IsAFailure(
                message=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(shape.GetPrim().GetTypeName()),
                at=Sdf.Path("/parent/shape"),
                requirement=ColliderChecker._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
            )
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[expected_failure])

            # Combined parent and shape scale that results in uniform scale within epsilon
            parent.ClearXformOpOrder()
            parent.AddScaleOp().Set(Gf.Vec3d(1, 1.000002, 1))
            shape.ClearXformOpOrder()
            shape.AddScaleOp().Set(Gf.Vec3d(1, 0.999999, 1))
            await self.assertRuleAsync(asset=stage, rule=ColliderChecker, asserts=[])

            # Clean up
            parent.ClearXformOpOrder()
            stage.RemovePrim(shape.GetPrim().GetPath())

    async def test_articulation_examples(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.JT_ART_002)
        await self.assertExamplesAsync(requirement=cap.Requirements.JT_ART_004)

    async def test_articulation_nesting_cache(self):
        stage = Usd.Stage.CreateInMemory()
        checker = ArticulationChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)

        articulation0 = UsdGeom.Xform.Define(stage, "/articulation0")
        articulation1 = UsdGeom.Xform.Define(stage, "/articulation0/articulation1")
        xform0 = UsdGeom.Xform.Define(stage, "/articulation0/articulation1/xform")
        articulation2 = UsdGeom.Xform.Define(stage, "/articulation0/articulation2")
        articulation3 = UsdGeom.Xform.Define(stage, "/articulation0/articulation1/xform/articulation3")

        UsdPhysics.ArticulationRootAPI.Apply(articulation0.GetPrim())
        UsdPhysics.ArticulationRootAPI.Apply(articulation1.GetPrim())
        UsdPhysics.ArticulationRootAPI.Apply(articulation2.GetPrim())
        UsdPhysics.ArticulationRootAPI.Apply(articulation3.GetPrim())

        checker._is_under_articulation_root(articulation3.GetPrim())
        expected_cache = {
            articulation3.GetPath(): True,
            xform0.GetPath(): True,
        }
        self.assertEqual(checker._is_under_articulation_root_cache, expected_cache)

        checker._is_under_articulation_root(articulation2.GetPrim())
        expected_cache = {
            articulation3.GetPath(): True,
            xform0.GetPath(): True,
            articulation2.GetPath(): True,
        }
        self.assertEqual(checker._is_under_articulation_root_cache, expected_cache)

    async def test_physics_joint_examples(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.JT_002)
        await self.assertExamplesAsync(requirement=cap.Requirements.JT_003)

    async def test_mass_examples(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.RB_007)
