# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Hierarchy validators for SimReady assets.

This module provides validators for checking hierarchy requirements in SimReady assets,
ensuring proper organization and structure of the prim hierarchy.
"""

from pxr import Usd, UsdGeom, UsdShade

import usd_validation_nvidia.capabilities as cap

from .._base_rule_checker import BaseRuleChecker
from .._issues import Suggestion
from .._requirements import register_requirements


@register_requirements(cap.Requirements.HI_001)
class HierarchyHasRootChecker(BaseRuleChecker):
    """
    Validates that all asset content lives under a single root prim.

    This validator ensures that:
    - The stage has exactly one asset root prim (preventing scattered/disconnected hierarchies)

    Root prims that are not part of the referenceable asset (review light rigs,
    cameras, or render-settings scopes such as the Omniverse-generated /Render prim)
    are excluded from the single-root count.
    """

    @staticmethod
    def _contains_asset_content(prim: Usd.Prim) -> bool:
        """Return True when the prim or any descendant is asset content (Xform, geometry, or material)."""
        for child in Usd.PrimRange(prim):
            if child.IsA(UsdGeom.Xform) or child.IsA(UsdGeom.Gprim) or child.IsA(UsdShade.Material):
                return True
        return False

    @classmethod
    def _is_asset_root(cls, prim: Usd.Prim) -> bool:
        """
        Return True when a root prim counts towards the single-root rule.

        The default prim always counts. Other root prims count only when they contain
        asset content (Xforms, geometry, or materials). Prims that are not part of the
        referenceable asset — review light rigs, cameras, or render-settings scopes such
        as the Omniverse-generated /Render prim — are permitted outside the hierarchy.
        """
        if prim == prim.GetStage().GetDefaultPrim():
            return True
        return cls._contains_asset_content(prim)

    def CheckStage(self, usdStage: Usd.Stage) -> None:
        """
        Check that the stage has exactly one asset root prim.

        Args:
            usdStage: The USD stage to validate
        """
        all_roots = usdStage.GetPseudoRoot().GetChildren()
        root_children = [prim for prim in all_roots if self._is_asset_root(prim)]

        if len(root_children) == 0:
            if all_roots:
                root_prim_names = [prim.GetName() for prim in all_roots]
                message = (
                    f"Prim hierarchy has no asset root prim: no default prim is set and no root prim "
                    f"({', '.join(root_prim_names)}) contains asset content (Xforms, geometry, or materials)."
                )
            else:
                message = "Prim hierarchy must have at least one root prim. Found no root prims."
            self._AddFailedCheck(
                requirement=cap.Requirements.HI_001,
                message=message,
                at=usdStage,
            )
            return

        if len(root_children) > 1:
            # List the scattered root prims to help users identify the issue
            root_prim_names = [prim.GetName() for prim in root_children]
            self._AddFailedCheck(
                requirement=cap.Requirements.HI_001,
                message=f"Prim hierarchy must have a single root prim. Found {len(root_children)} root prims: {', '.join(root_prim_names)}",
                at=usdStage,
            )


@register_requirements(cap.Requirements.HI_003)
class RootPrimXformableChecker(BaseRuleChecker):
    """
    Validates that the root prim of a placeable asset is strictly an Xformable prim.

    This is a stricter version of DefaultPrimChecker that enforces HI.003 requirement:
    The root prim must inherit UsdGeomXformable (such as Xform) and NOT be a Scope.

    This ensures:
    - The entire asset can be transformed as a single unit
    - Easy positioning and orientation when referencing into scenes
    - Consistent behavior for asset manipulation tools
    - Facilitated automated scene composition and layout workflows
    """

    @classmethod
    def _set_root_prim_to_xformable(cls, stage: Usd.Stage, _: Usd.Prim) -> None:
        for prim in stage.GetPseudoRoot().GetChildren():
            if UsdGeom.Xformable(prim):
                stage.SetDefaultPrim(prim)
                return
        raise ValueError("No xformable root prim found")

    @classmethod
    def _has_xformable_root(cls, stage: Usd.Stage) -> bool:
        for prim in stage.GetPseudoRoot().GetChildren():
            if UsdGeom.Xformable(prim):
                return True
        return False

    def CheckStage(self, stage: Usd.Stage) -> None:
        default_prim = stage.GetDefaultPrim()
        if not default_prim:
            return
        if not default_prim.GetParent().IsPseudoRoot():
            return
        xformable = UsdGeom.Xformable(default_prim)
        if not xformable:
            suggestion: Suggestion | None = None
            if self._has_xformable_root(stage):
                suggestion = Suggestion(
                    message="Set the root prim to an Xformable",
                    callable=self._set_root_prim_to_xformable,
                )
            self._AddFailedCheck(
                requirement=cap.Requirements.HI_003,
                message=f'Root prim <{default_prim.GetName()}> must be Xformable (e.g. Xform); got "{default_prim.GetTypeName()}".',
                at=default_prim,
                suggestion=suggestion,
            )
