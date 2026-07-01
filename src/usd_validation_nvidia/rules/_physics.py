# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = [
    "ArticulationChecker",
    "ColliderChecker",
    "MassChecker",
    "PhysicsJointChecker",
    "RigidBodyChecker",
]

from collections.abc import Callable

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

import usd_validation_nvidia.capabilities as cap

from .._base_rule_checker import BaseRuleChecker
from .._categories import register_rule
from .._requirements import Requirement, register_requirements
from .._usd_validator_adapter import UsdValidatorAdapter


def _scale_is_uniform(scale: Gf.Vec3d) -> bool:
    eps = 1.0e-5
    # Find min and max scale values
    if scale[0] < scale[1]:
        lo, hi = scale[0], scale[1]
    else:
        lo, hi = scale[1], scale[0]

    if scale[2] < lo:
        lo = scale[2]
    elif scale[2] > hi:
        hi = scale[2]

    if lo * hi < 0.0:
        return False  # opposite signs

    return hi - lo <= eps * lo if hi > 0.0 else lo - hi >= eps * hi


def _get_rel(ref: Usd.Relationship) -> Sdf.Path:
    targets = ref.GetTargets()

    if not targets:
        return Sdf.Path()

    return targets[0]


def _check_joint_rel(rel_path: Sdf.Path, joint_prim: Usd.Prim) -> bool:
    if rel_path == Sdf.Path():
        return True

    rel_prim = joint_prim.GetStage().GetPrimAtPath(rel_path)
    return rel_prim.IsValid()


def register_requirements_and_add_doc(
    *requirements: Requirement,
) -> Callable[[type[BaseRuleChecker]], type[BaseRuleChecker]]:
    def _register_requirements_and_add_doc(rule_class: type[BaseRuleChecker]) -> type[BaseRuleChecker]:
        register_requirements(*requirements)(rule_class)
        rule_class.__doc__ = "Implements validation of the following requirements:\n\n"
        rule_class.__doc__ += "\n".join(f"\t* {req.code}: {req.message}" for req in requirements)
        return rule_class

    return _register_requirements_and_add_doc


class BaseRuleCheckerWCache(UsdValidatorAdapter):
    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.InitCaches()

    def InitCaches(self):
        self._xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        self._is_under_articulation_root_cache = dict()

    def ResetCaches(self):
        self._xform_cache.Clear()
        self._is_under_articulation_root_cache.clear()

    def _cache_value_to_list(self, cache: dict, value: bool, prim_paths: list[Sdf.Path]):
        for path in prim_paths:
            cache[path] = value

    def _is_under_articulation_root(self, usd_prim: Usd.Prim) -> bool:
        path = usd_prim.GetPath()
        prim_list = []
        current = usd_prim.GetParent()
        while current and current != usd_prim.GetStage().GetPseudoRoot():
            prim_list.append(path)
            path = current.GetPath()
            cached = self._is_under_articulation_root_cache.get(path)
            if cached is not None:
                self._cache_value_to_list(self._is_under_articulation_root_cache, cached, prim_list)
                return cached

            art_api = UsdPhysics.ArticulationRootAPI(current)
            if art_api:
                self._cache_value_to_list(self._is_under_articulation_root_cache, True, prim_list)
                return True

            current = current.GetParent()

        self._cache_value_to_list(self._is_under_articulation_root_cache, False, prim_list)
        return False

    def _check_non_uniform_scale(self, xformable: UsdGeom.Xformable) -> bool:
        tr = Gf.Transform(self._xform_cache.GetLocalToWorldTransform(xformable.GetPrim()))
        sc = tr.GetScale()
        return _scale_is_uniform(sc)


@register_rule("Physics")
@register_requirements_and_add_doc(
    cap.Requirements.RB_005,
    cap.Requirements.RB_003,
    cap.Requirements.RB_009,
)
class RigidBodyChecker(BaseRuleCheckerWCache):
    _RIGID_BODY_ORIENTATION_SCALE_REQUIREMENT = cap.Requirements.RB_009
    _RIGID_BODY_NON_XFORMABLE_REQUIREMENT = cap.Requirements.RB_003
    _RIGID_BODY_NON_INSTANCEABLE_REQUIREMENT = cap.Requirements.RB_005

    _RIGID_BODY_NON_XFORMABLE_MESSAGE = "Rigid body API has to be applied to a xformable prim."
    _RIGID_BODY_NON_INSTANCEABLE_MESSAGE = "RigidBodyAPI on an instance proxy is not supported."
    _RIGID_BODY_ORIENTATION_SCALE_MESSAGE = "ScaleOrientation is not supported for rigid bodies."

    _REQUIREMENT_MAP = {
        "RigidBodyNonXformable": cap.Requirements.RB_003,
        "RigidBodyNonInstanceable": cap.Requirements.RB_005,
        "RigidBodyOrientationScale": cap.Requirements.RB_009,
    }

    @classmethod
    def validator_name(cls) -> str:
        return "usdPhysicsValidators:RigidBodyChecker"

    def _get_requirement(self, error) -> Requirement | None:
        return self._REQUIREMENT_MAP.get(error.GetName())

    def _CheckPrim(self, usd_prim: Usd.Prim):
        rb_api = UsdPhysics.RigidBodyAPI(usd_prim)
        if not rb_api:
            return

        # Check if rigid body is applied to xformable
        xformable = UsdGeom.Xformable(usd_prim)
        if not xformable:
            self._AddFailedCheck(
                message=self._RIGID_BODY_NON_XFORMABLE_MESSAGE,
                at=usd_prim,
                requirement=self._RIGID_BODY_NON_XFORMABLE_REQUIREMENT,
            )

        # Check instancing
        if usd_prim.IsInstanceProxy():
            report_instance_error = True

            # Check kinematic state
            kinematic = False
            kinematic = rb_api.GetKinematicEnabledAttr().Get()
            if kinematic:
                report_instance_error = False

            # Check if rigid body is enabled
            enabled = rb_api.GetRigidBodyEnabledAttr().Get()
            if not enabled:
                report_instance_error = False

            if report_instance_error:
                self._AddFailedCheck(
                    message=self._RIGID_BODY_NON_INSTANCEABLE_MESSAGE,
                    at=usd_prim,
                    requirement=self._RIGID_BODY_NON_INSTANCEABLE_REQUIREMENT,
                )

        # Check scale orientation
        if xformable:
            mat = self._xform_cache.GetLocalToWorldTransform(usd_prim)
            tr = Gf.Transform(mat)
            sc = tr.GetScale()

            if not _scale_is_uniform(sc) and tr.GetPivotOrientation().GetQuaternion() != Gf.Quaternion.GetIdentity():
                self._AddFailedCheck(
                    message=self._RIGID_BODY_ORIENTATION_SCALE_MESSAGE,
                    at=usd_prim,
                    requirement=self._RIGID_BODY_ORIENTATION_SCALE_REQUIREMENT,
                )


@register_rule("Physics")
@register_requirements_and_add_doc(
    cap.Requirements.RB_COL_004,
)
class ColliderChecker(BaseRuleCheckerWCache):
    _COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT = cap.Requirements.RB_COL_004
    _COLLIDER_NON_UNIFORM_SCALE_MESSAGE = "Non-uniform scale is not supported for {0} geometry."

    @classmethod
    def validator_name(cls) -> str:
        return "usdPhysicsValidators:ColliderChecker"

    def _CheckPrim(self, usd_prim: Usd.Prim):
        collision_api = UsdPhysics.CollisionAPI(usd_prim)
        if not collision_api:
            return

        if not usd_prim.IsA(UsdGeom.Gprim):
            return

        # Note: Removed Capsule_1 and Cylinder_1 from this check as they are not supported by older USD versions
        if (
            usd_prim.IsA(UsdGeom.Sphere)
            or usd_prim.IsA(UsdGeom.Capsule)
            or usd_prim.IsA(UsdGeom.Cylinder)
            or usd_prim.IsA(UsdGeom.Cone)
            or usd_prim.IsA(UsdGeom.Points)
        ):
            xform = UsdGeom.Xformable(usd_prim)
            if xform and not self._check_non_uniform_scale(xform):
                self._AddFailedCheck(
                    message=self._COLLIDER_NON_UNIFORM_SCALE_MESSAGE.format(usd_prim.GetTypeName()),
                    at=usd_prim,
                    requirement=self._COLLIDER_NON_UNIFORM_SCALE_REQUIREMENT,
                )


@register_rule("Physics")
@register_requirements_and_add_doc(
    cap.Requirements.JT_002,
    cap.Requirements.JT_003,
)
class PhysicsJointChecker(UsdValidatorAdapter):
    _JOINT_INVALID_PRIM_REL_REQUIREMENT = cap.Requirements.JT_002
    _JOINT_MULTIPLE_PRIMS_REL_REQUIREMENT = cap.Requirements.JT_003

    _JOINT_INVALID_PRIM_REL_MESSAGE = (
        "Joint ({0}) body relationship points to a non existent prim, joint will not be parsed."
    )
    _JOINT_MULTIPLE_PRIMS_REL_MESSAGE = (
        "Joint prim does have relationship to multiple bodies this is not supported, jointPrim {0}"
    )

    _REQUIREMENT_MAP = {
        "JointInvalidPrimRel": cap.Requirements.JT_002,
        "JointMultiplePrimsRel": cap.Requirements.JT_003,
    }

    @classmethod
    def validator_name(cls) -> str:
        return "usdPhysicsValidators:PhysicsJointChecker"

    def _get_requirement(self, error) -> Requirement | None:
        return self._REQUIREMENT_MAP.get(error.GetName())

    def _CheckPrim(self, usd_prim: Usd.Prim):
        physics_joint = UsdPhysics.Joint(usd_prim)

        if not physics_joint:
            return

        # Check valid relationship prims
        rel0path = _get_rel(physics_joint.GetBody0Rel())
        rel1path = _get_rel(physics_joint.GetBody1Rel())

        # Check relationship validity
        if not _check_joint_rel(rel0path, usd_prim):
            self._AddFailedCheck(
                message=self._JOINT_INVALID_PRIM_REL_MESSAGE.format(usd_prim.GetPrimPath()),
                at=usd_prim,
                requirement=self._JOINT_INVALID_PRIM_REL_REQUIREMENT,
            )

        if not _check_joint_rel(rel1path, usd_prim):
            self._AddFailedCheck(
                message=self._JOINT_INVALID_PRIM_REL_MESSAGE.format(usd_prim.GetPrimPath()),
                at=usd_prim,
                requirement=self._JOINT_INVALID_PRIM_REL_REQUIREMENT,
            )

        # Check multiple relationship prims
        targets0 = physics_joint.GetBody0Rel().GetTargets()
        targets1 = physics_joint.GetBody1Rel().GetTargets()

        if len(targets0) > 1:
            self._AddFailedCheck(
                message=self._JOINT_MULTIPLE_PRIMS_REL_MESSAGE.format(usd_prim.GetPrimPath()),
                at=usd_prim,
                requirement=self._JOINT_MULTIPLE_PRIMS_REL_REQUIREMENT,
            )

        if len(targets1) > 1:
            self._AddFailedCheck(
                message=self._JOINT_MULTIPLE_PRIMS_REL_MESSAGE.format(usd_prim.GetPrimPath()),
                at=usd_prim,
                requirement=self._JOINT_MULTIPLE_PRIMS_REL_REQUIREMENT,
            )


@register_rule("Physics")
@register_requirements_and_add_doc(
    cap.Requirements.JT_ART_002,
    cap.Requirements.JT_ART_004,
)
class ArticulationChecker(BaseRuleCheckerWCache):
    _NESTED_ARTICULATION_REQUIREMENT = cap.Requirements.JT_ART_002
    _ARTICULATION_ON_STATIC_BODY_REQUIREMENT = cap.Requirements.JT_ART_004

    _NESTED_ARTICULATION_MESSAGE = "Nested ArticulationRootAPI not supported."
    _ARTICULATION_ON_STATIC_BODY_MESSAGE = "ArticulationRootAPI definition on a static rigid body is not allowed."

    _REQUIREMENT_MAP = {
        "NestedArticulation": cap.Requirements.JT_ART_002,
        "ArticulationOnStaticBody": cap.Requirements.JT_ART_004,
    }

    @classmethod
    def validator_name(cls) -> str:
        return "usdPhysicsValidators:ArticulationChecker"

    def _get_requirement(self, error) -> Requirement | None:
        return self._REQUIREMENT_MAP.get(error.GetName())

    def _CheckPrim(self, usd_prim: Usd.Prim):
        art_api = UsdPhysics.ArticulationRootAPI(usd_prim)

        if not art_api:
            return

        # Check for nested articulation roots
        if self._is_under_articulation_root(usd_prim):
            self._AddFailedCheck(
                message=self._NESTED_ARTICULATION_MESSAGE,
                at=usd_prim,
                requirement=self._NESTED_ARTICULATION_REQUIREMENT,
            )

        # Check rigid body static errors
        rbo_api = UsdPhysics.RigidBodyAPI(usd_prim)
        if rbo_api:
            # Check if rigid body is enabled
            body_enabled = rbo_api.GetRigidBodyEnabledAttr().Get()
            if not body_enabled:
                self._AddFailedCheck(
                    message=self._ARTICULATION_ON_STATIC_BODY_MESSAGE,
                    at=usd_prim,
                    requirement=self._ARTICULATION_ON_STATIC_BODY_REQUIREMENT,
                )


@register_rule("Physics")
@register_requirements_and_add_doc(
    cap.Requirements.RB_007,
)
class MassChecker(BaseRuleChecker):
    _MASS_API_INVALID_VALUES_REQUIREMENT = cap.Requirements.RB_007

    _MASS_INVALID_VALUES_MESSAGE = "Mass must be a positive value or 0.0."
    _DENSITY_INVALID_VALUES_MESSAGE = "Density must be a positive value or 0.0."
    _INERTIA_INVALID_VALUES_MESSAGE = (
        "If principalAxes or diagonalInertia is authored on rigid body, both must be authored. "
        "principalAxes must be a unit length quaternion. diagonalInertia must have positive values."
    )

    def CheckPrim(self, usd_prim: Usd.Prim):
        # Check if prim has MassAPI applied
        mass_api = UsdPhysics.MassAPI(usd_prim)
        if not mass_api:
            return

        rbd_api = UsdPhysics.RigidBodyAPI(usd_prim)
        collision_api = UsdPhysics.CollisionAPI(usd_prim)
        if not (rbd_api or collision_api):
            self._AddFailedCheck(
                message="MassAPI can only be applied to a rigid body or collision prim.",
                at=usd_prim,
                requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
            )

        # Check mass value
        mass_attr = mass_api.GetMassAttr()
        if mass_attr.IsAuthored():
            mass = mass_attr.Get()
            if mass is not None and mass < 0.0:
                self._AddFailedCheck(
                    message=self._MASS_INVALID_VALUES_MESSAGE,
                    at=usd_prim,
                    requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                )

        # Check density value
        density_attr = mass_api.GetDensityAttr()
        if density_attr.IsAuthored():
            density = density_attr.Get()
            if density is not None and density < 0.0:
                self._AddFailedCheck(
                    message=self._DENSITY_INVALID_VALUES_MESSAGE,
                    at=usd_prim,
                    requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                )

        # Check inertia values
        principal_axes_attr = mass_api.GetPrincipalAxesAttr()
        diagonal_inertia_attr = mass_api.GetDiagonalInertiaAttr()

        principal_axes_authored = principal_axes_attr.IsAuthored()
        diagonal_inertia_authored = diagonal_inertia_attr.IsAuthored()

        if principal_axes_authored or diagonal_inertia_authored:
            # Both must be authored if either is authored
            if not (principal_axes_authored and diagonal_inertia_authored):
                self._AddFailedCheck(
                    message=self._INERTIA_INVALID_VALUES_MESSAGE,
                    at=usd_prim,
                    requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                )
                return

            # Get the values
            principal_axes = principal_axes_attr.Get()
            diagonal_inertia = diagonal_inertia_attr.Get()

            if principal_axes is None or diagonal_inertia is None:
                return

            # Check if both are fallback values (all zeros)
            fallback_quat = Gf.Quatf(0.0, 0.0, 0.0, 0.0)
            fallback_vec = Gf.Vec3f(0.0, 0.0, 0.0)

            is_principal_fallback = principal_axes == fallback_quat
            is_diagonal_fallback = diagonal_inertia == fallback_vec

            # If both are fallback, that's valid
            if is_principal_fallback and is_diagonal_fallback:
                return

            # If only one is fallback, that's invalid
            if is_principal_fallback != is_diagonal_fallback:
                self._AddFailedCheck(
                    message=self._INERTIA_INVALID_VALUES_MESSAGE,
                    at=usd_prim,
                    requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                )
                return

            # Check if principalAxes is a unit quaternion (but not the fallback)
            if not is_principal_fallback:
                # Convert to quaternion for length check
                quat_length = principal_axes.GetLength()
                if abs(quat_length - 1.0) > 1e-5:  # Allow small epsilon for floating point
                    self._AddFailedCheck(
                        message=self._INERTIA_INVALID_VALUES_MESSAGE,
                        at=usd_prim,
                        requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                    )
                    return

            # Check if diagonalInertia has positive values (but not the fallback)
            if not is_diagonal_fallback:
                if diagonal_inertia[0] <= 0.0 or diagonal_inertia[1] <= 0.0 or diagonal_inertia[2] <= 0.0:
                    self._AddFailedCheck(
                        message=self._INERTIA_INVALID_VALUES_MESSAGE,
                        at=usd_prim,
                        requirement=self._MASS_API_INVALID_VALUES_REQUIREMENT,
                    )
