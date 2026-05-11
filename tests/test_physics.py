# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock

from common import AsyncioValidationTestCase
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from usd_validation_nvidia import (
    ArticulationChecker,
    ColliderChecker,
    MassChecker,
    PhysicsJointChecker,
    RigidBodyChecker,
)
from usd_validation_nvidia.tests import IsAFailure
from usd_validation_nvidia._physics_checker import _scale_is_uniform


class UsdPhysicsCheckerTestCase(AsyncioValidationTestCase):

    maxDiff = None

    def test_scale_is_uniform_ok(self):
        self.assertTrue(_scale_is_uniform(Gf.Vec3d(1.0, 1.0, 1.0)))
        self.assertTrue(_scale_is_uniform(Gf.Vec3d(0.0, 0.0, 0.0)))
        self.assertFalse(_scale_is_uniform(Gf.Vec3d(1.0, 1.0001, 1.0)))
        self.assertFalse(_scale_is_uniform(Gf.Vec3d(-1.0, 1.0, 1.0)))

    def test_rigid_body_fallback_ok(self):
        checker = RigidBodyChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        stage = Usd.Stage.CreateInMemory()

        no_api = UsdGeom.Xform.Define(stage, "/noApi")
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(no_api.GetPrim())
            add_failed.assert_not_called()

        non_xformable = UsdGeom.Scope.Define(stage, "/nonXformable")
        UsdPhysics.RigidBodyAPI.Apply(non_xformable.GetPrim())
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(non_xformable.GetPrim())
            add_failed.assert_called_once()

        UsdGeom.Xform.Define(stage, "/source")
        rigid_body = UsdGeom.Cube.Define(stage, "/source/rigidBody")
        rb_api = UsdPhysics.RigidBodyAPI.Apply(rigid_body.GetPrim())
        instance = UsdGeom.Xform.Define(stage, "/instance")
        instance.GetPrim().GetReferences().AddInternalReference("/source")
        instance.GetPrim().SetInstanceable(True)
        instance_body = stage.GetPrimAtPath("/instance/rigidBody")

        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(instance_body)
            add_failed.assert_called_once()

        rb_api.GetKinematicEnabledAttr().Set(True)
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(instance_body)
            add_failed.assert_not_called()

        rb_api.GetKinematicEnabledAttr().Set(False)
        rb_api.GetRigidBodyEnabledAttr().Set(False)
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(instance_body)
            add_failed.assert_not_called()

    def test_collider_fallback_ok(self):
        checker = ColliderChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        stage = Usd.Stage.CreateInMemory()

        no_api = UsdGeom.Xform.Define(stage, "/noApi")
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(no_api.GetPrim())
            add_failed.assert_not_called()

        non_gprim = UsdGeom.Scope.Define(stage, "/nonGprim")
        UsdPhysics.CollisionAPI.Apply(non_gprim.GetPrim())
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(non_gprim.GetPrim())
            add_failed.assert_not_called()

        sphere = UsdGeom.Sphere.Define(stage, "/sphere")
        sphere.AddScaleOp().Set(Gf.Vec3d(1.0, 2.0, 1.0))
        UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(sphere.GetPrim())
            add_failed.assert_called_once()

    def test_physics_joint_fallback_ok(self):
        checker = PhysicsJointChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        stage = Usd.Stage.CreateInMemory()

        no_joint = UsdGeom.Xform.Define(stage, "/noJoint")
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(no_joint.GetPrim())
            add_failed.assert_not_called()

        joint = UsdPhysics.Joint.Define(stage, "/joint")
        joint.GetBody0Rel().AddTarget("/missing0")
        joint.GetBody0Rel().AddTarget("/missing1")
        joint.GetBody1Rel().AddTarget("/missing2")
        joint.GetBody1Rel().AddTarget("/missing3")
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(joint.GetPrim())
            self.assertEqual(add_failed.call_count, 4)

    def test_articulation_fallback_ok(self):
        checker = ArticulationChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)
        stage = Usd.Stage.CreateInMemory()

        no_api = UsdGeom.Xform.Define(stage, "/noApi")
        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(no_api.GetPrim())
            add_failed.assert_not_called()

        parent = UsdGeom.Xform.Define(stage, "/parent")
        child = UsdGeom.Xform.Define(stage, "/parent/child")
        UsdPhysics.ArticulationRootAPI.Apply(parent.GetPrim())
        UsdPhysics.ArticulationRootAPI.Apply(child.GetPrim())
        rb_api = UsdPhysics.RigidBodyAPI.Apply(child.GetPrim())
        rb_api.GetRigidBodyEnabledAttr().Set(False)

        with mock.patch.object(checker, "_AddFailedCheck") as add_failed:
            checker._CheckPrim(child.GetPrim())
            self.assertEqual(add_failed.call_count, 2)

    async def test_rigid_body_xformable(self):
        stage = Usd.Stage.CreateInMemory()

        rigidbody = UsdGeom.Scope.Define(stage, "/rigidBody")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())

        expected_failure = IsAFailure(
            RigidBodyChecker._RIGID_BODY_NON_XFORMABLE_MESSAGE,
            at=Sdf.Path("/rigidBody"),
            requirement=RigidBodyChecker._RIGID_BODY_NON_XFORMABLE_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[expected_failure])

    async def test_rigid_body_orientation_scale(self):
        stage = Usd.Stage.CreateInMemory()

        rigidbody = UsdGeom.Xform.Define(stage, "/rigidBody")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())

        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[])

        pivot_orientation = Gf.Rotation(Gf.Vec3d(1, 2, 3), 20.3)
        transform = Gf.Transform(scale=Gf.Vec3d(7, 8, 9), pivotOrientation=pivot_orientation)
        rigidbody.AddTransformOp().Set(transform.GetMatrix())

        expected_failure = IsAFailure(
            RigidBodyChecker._RIGID_BODY_ORIENTATION_SCALE_MESSAGE,
            at=Sdf.Path("/rigidBody"),
            requirement=RigidBodyChecker._RIGID_BODY_ORIENTATION_SCALE_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[expected_failure])

        transform = Gf.Transform(Gf.Vec3d(1, 1, 1), pivotOrientation=pivot_orientation)
        rigidbody.ClearXformOpOrder()
        rigidbody.AddTransformOp().Set(transform.GetMatrix())

        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[])

    async def test_rigid_body_instancing(self):
        stage = Usd.Stage.CreateInMemory()

        xform = UsdGeom.Xform.Define(stage, "/xform")
        UsdGeom.Xform.Define(stage, "/xform")
        cube = UsdGeom.Cube.Define(stage, "/xform/rigidBody")
        rb_api = UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())

        self.assertIsNotNone(cube)
        self.assertIsNotNone(rb_api)
        self.assertFalse(cube.GetPrim().IsInstanceProxy())
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[])

        xform = UsdGeom.Xform.Define(stage, "/xformInstance")
        xform.GetPrim().GetReferences().AddInternalReference("/xform")
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[])
        xform.GetPrim().SetInstanceable(True)

        instance_rigid_body = stage.GetPrimAtPath("/xformInstance/rigidBody")
        self.assertTrue(instance_rigid_body.IsInstanceProxy())

        expected_failure = IsAFailure(
            message=RigidBodyChecker._RIGID_BODY_NON_INSTANCEABLE_MESSAGE,
            at=Sdf.Path("/xformInstance/rigidBody"),
            requirement=RigidBodyChecker._RIGID_BODY_NON_INSTANCEABLE_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[expected_failure])

        # Rigid body API with kinematic enabled can be applied on an instance proxy
        rb_api.GetKinematicEnabledAttr().Set(True)
        await self.assertRuleAsync(asset=stage, rule=RigidBodyChecker, asserts=[])

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

    async def test_articulation_nesting(self):
        stage = Usd.Stage.CreateInMemory()

        # Base
        articulation0 = UsdGeom.Xform.Define(stage, "/articulation0")
        UsdPhysics.ArticulationRootAPI.Apply(articulation0.GetPrim())
        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[])

        # Nested articulation - direct
        articulation1 = UsdGeom.Xform.Define(stage, "/articulation0/articulation1")
        UsdPhysics.ArticulationRootAPI.Apply(articulation1.GetPrim())
        expected_failure = IsAFailure(
            message=ArticulationChecker._NESTED_ARTICULATION_MESSAGE,
            at="Prim </articulation0/articulation1>",
            requirement=ArticulationChecker._NESTED_ARTICULATION_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[expected_failure])

        # Remove the nested one
        stage.RemovePrim(articulation1.GetPrim().GetPath())

        # Nested by one
        UsdGeom.Xform.Define(stage, "/articulation0/xform")
        articulation2 = UsdGeom.Xform.Define(stage, "/articulation0/xform/articulation2")
        UsdPhysics.ArticulationRootAPI.Apply(articulation2.GetPrim())
        expected_failure = IsAFailure(
            message=ArticulationChecker._NESTED_ARTICULATION_MESSAGE,
            at="Prim </articulation0/xform/articulation2>",
            requirement=ArticulationChecker._NESTED_ARTICULATION_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[expected_failure])

        # Remove the top root, should pass
        articulation0.GetPrim().RemoveAPI(UsdPhysics.ArticulationRootAPI)
        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[])

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

    async def test_articulation_body(self):
        stage = Usd.Stage.CreateInMemory()

        articulation = UsdGeom.Xform.Define(stage, "/articulation")
        UsdPhysics.ArticulationRootAPI.Apply(articulation.GetPrim())

        rigid_body = UsdPhysics.RigidBodyAPI.Apply(articulation.GetPrim())

        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[])

        rigid_body.GetRigidBodyEnabledAttr().Set(False)

        expected_failure = IsAFailure(
            message=ArticulationChecker._ARTICULATION_ON_STATIC_BODY_MESSAGE,
            at="Prim </articulation>",
            requirement=ArticulationChecker._ARTICULATION_ON_STATIC_BODY_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=ArticulationChecker, asserts=[expected_failure])

    async def test_physics_joint_invalid_rel(self):
        stage = Usd.Stage.CreateInMemory()

        physics_joint = UsdPhysics.Joint.Define(stage, "/joint")

        await self.assertRuleAsync(asset=stage, rule=PhysicsJointChecker, asserts=[])

        physics_joint.GetBody1Rel().AddTarget("/invalidPrim")

        expected_failure = IsAFailure(
            message=PhysicsJointChecker._JOINT_INVALID_PRIM_REL_MESSAGE.format("/joint"),
            at="Prim </joint>",
            requirement=PhysicsJointChecker._JOINT_INVALID_PRIM_REL_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=PhysicsJointChecker, asserts=[expected_failure])

    async def test_physics_joint_multiple_rels(self):
        stage = Usd.Stage.CreateInMemory()

        UsdGeom.Xform.Define(stage, "/xform0")
        UsdGeom.Xform.Define(stage, "/xform1")

        physics_joint = UsdPhysics.Joint.Define(stage, "/joint")
        physics_joint.GetBody1Rel().AddTarget("/xform0")

        await self.assertRuleAsync(asset=stage, rule=PhysicsJointChecker, asserts=[])

        physics_joint.GetBody1Rel().AddTarget("/xform1")

        expected_failure = IsAFailure(
            message=PhysicsJointChecker._JOINT_MULTIPLE_PRIMS_REL_MESSAGE.format("/joint"),
            at="Prim </joint>",
            requirement=PhysicsJointChecker._JOINT_MULTIPLE_PRIMS_REL_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=PhysicsJointChecker, asserts=[expected_failure])

    async def test_mass_on_non_physics_prim(self):
        # MassAPI on non-rigid body/collision prim should fail
        stage = Usd.Stage.CreateInMemory()
        xform = UsdGeom.Xform.Define(stage, "/xform")
        UsdPhysics.MassAPI.Apply(xform.GetPrim())
        expected_failure = IsAFailure(
            message="MassAPI can only be applied to a rigid body or collision prim.",
            at=Sdf.Path("/xform"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_on_collision_prim(self):
        # MassAPI on collision prim should pass
        stage = Usd.Stage.CreateInMemory()
        cube = UsdGeom.Cube.Define(stage, "/cube")
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        UsdPhysics.MassAPI.Apply(cube.GetPrim())
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[])

    async def test_mass_negative_value(self):
        # negative mass should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody1")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetMassAttr().Set(-5.0)
        expected_failure = IsAFailure(
            message=MassChecker._MASS_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody1"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_negative_density(self):
        # negative density should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody2")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetDensityAttr().Set(-10.0)

        expected_failure = IsAFailure(
            message=MassChecker._DENSITY_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody2"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_unauthored_inertia(self):
        # neither principalAxes nor diagonalInertia authored on rigid body - should pass
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody3")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[])

    async def test_mass_missing_diagonal_inertia(self):
        # only principalAxes authored with non-fallback value - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody4")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody4"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_missing_principal_axes(self):
        # only diagonalInertia authored with non-fallback value - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody5")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(1.0, 2.0, 3.0))
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody5"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_valid_inertia(self):
        # both authored with valid values - should pass
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody6")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))  # Valid unit quaternion
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(1.0, 2.0, 3.0))  # Valid positive values
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[])

    async def test_mass_valid_fallback_inertia(self):
        # both authored with fallback values - should pass
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody7")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(0.0, 0.0, 0.0, 0.0))  # Fallback value
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(0.0, 0.0, 0.0))  # Fallback value
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[])

    async def test_mass_mismatched_fallback_inertia(self):
        # principalAxes fallback but diagonalInertia non-fallback - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody8")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(0.0, 0.0, 0.0, 0.0))  # Fallback value
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(1.0, 2.0, 3.0))  # Non-fallback value
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody8"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_mismatched_fallback_inertia_2(self):
        # principalAxes non-fallback but diagonalInertia fallback - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody9")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))  # Non-fallback value
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(0.0, 0.0, 0.0))  # Fallback value
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody9"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_non_unit_principal_axes(self):
        # principalAxes is non-unit quaternion - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody10")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(2.0, 0.0, 0.0, 0.0))  # Non-unit quaternion
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(1.0, 2.0, 3.0))
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody10"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_negative_diagonal_inertia(self):
        # diagonalInertia has negative values - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody11")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(-1.0, 2.0, 3.0))  # Negative value
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody11"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_zero_diagonal_inertia(self):
        # diagonalInertia has zero values - should fail
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody12")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(0.0, 2.0, 3.0))  # Zero value
        expected_failure = IsAFailure(
            message=MassChecker._INERTIA_INVALID_VALUES_MESSAGE,
            at=Sdf.Path("/rigidbody12"),
            requirement=MassChecker._MASS_API_INVALID_VALUES_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[expected_failure])

    async def test_mass_valid_explicit_inertia(self):
        # valid normalized quaternion on rigid body - should pass
        stage = Usd.Stage.CreateInMemory()
        rigidbody = UsdGeom.Xform.Define(stage, "/rigidbody13")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody.GetPrim())
        mass_api = UsdPhysics.MassAPI.Apply(rigidbody.GetPrim())
        # Quaternion representing 45 degree rotation around Y axis
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(0.9238795, 0.0, 0.3826834, 0.0))
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(1.0, 2.0, 3.0))
        await self.assertRuleAsync(asset=stage, rule=MassChecker, asserts=[])
