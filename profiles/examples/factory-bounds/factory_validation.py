# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import factory_asset_profiles
from pxr import Usd, UsdGeom
from usd_validation_nvidia import (
    BaseRuleChecker,
    ParameterMapping,
    register_features,
    register_profiles,
    register_requirements,
    register_rule,
    unregister_features,
    unregister_profiles,
    unregister_requirements,
    unregister_rule,
)

FACTORY_BOUNDABLE_SIZE = factory_asset_profiles.Requirements.GEOMETRY_001


class FactoryBoundsChecker(BaseRuleChecker):
    """Validate boundable prim sizes against factory limits."""

    def __init__(self, parameters: ParameterMapping | None = None) -> None:
        super().__init__(parameters=parameters)
        self._meters_per_unit: float = 1.0
        self._bbox_cache: UsdGeom.BBoxCache | None = None

    def CheckStage(self, stage: Usd.Stage) -> None:
        self._meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
        self._bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_],
        )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if not UsdGeom.Boundable(prim):
            return

        if self._bbox_cache is None:
            self._bbox_cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                [UsdGeom.Tokens.default_],
            )

        bounds = self._bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bounds.IsEmpty():
            return

        size_meters = bounds.GetSize() * self._meters_per_unit
        limits = (
            float(self.parameters["MAX_X_METERS"].assigned_value),
            float(self.parameters["MAX_Y_METERS"].assigned_value),
            float(self.parameters["MAX_Z_METERS"].assigned_value),
        )

        if all(size_meters[axis] <= limits[axis] for axis in range(3)):
            return

        self._AddFailedCheck(
            message=f"Boundable prim {prim.GetPath()} exceeds factory bounds {limits}.",
            at=prim,
            requirement=FACTORY_BOUNDABLE_SIZE,
        )

    def ResetCaches(self) -> None:
        self._bbox_cache = None


class Plugin:
    def on_startup(self) -> None:
        register_features(factory_asset_profiles.Features)
        register_profiles(factory_asset_profiles.Profiles)
        register_requirements(FACTORY_BOUNDABLE_SIZE)(FactoryBoundsChecker)
        register_rule("Factory")(FactoryBoundsChecker)

    def on_shutdown(self) -> None:
        unregister_rule(FactoryBoundsChecker)
        unregister_requirements(FactoryBoundsChecker)
        unregister_profiles(factory_asset_profiles.Profiles)
        unregister_features(factory_asset_profiles.Features)
