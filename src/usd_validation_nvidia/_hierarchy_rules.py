# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Hierarchy validators for SimReady assets.

This module provides validators for checking hierarchy requirements in SimReady assets,
ensuring proper organization and structure of the prim hierarchy.
"""

from pxr import Usd, UsdGeom

import usd_validation_nvidia.capabilities as cap

from ._base_rule_checker import BaseRuleChecker
from ._issues import Suggestion
from ._requirements import register_requirements


@register_requirements(cap.Requirements.HI_001)
class HierarchyHasRootChecker(BaseRuleChecker):
    """
    Validates that the prim hierarchy has a single root prim.

    This validator ensures that:
    - The stage has at least one root prim (preventing scattered/disconnected hierarchies)
    """

    def CheckStage(self, usdStage: Usd.Stage) -> None:
        """
        Check that the stage has exactly one root prim.

        Args:
            usdStage: The USD stage to validate
        """
        root_children = usdStage.GetPseudoRoot().GetChildren()
        if len(root_children) == 0:
            self._AddFailedCheck(
                requirement=cap.Requirements.HI_001,
                message="Prim hierarchy must have at least one root prim. Found no root prims.",
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
