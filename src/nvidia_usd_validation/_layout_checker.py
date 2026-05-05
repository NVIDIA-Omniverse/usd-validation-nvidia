# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Generator

from pxr import Usd, UsdGeom

import nvidia_usd_validation.capabilities as cap

from ._base_rule_checker import BaseRuleChecker
from ._categories import register_rule
from ._issues import Suggestion
from ._requirements import register_requirements

__all__ = [
    "DanglingOverPrimChecker",
    "DefaultPrimChecker",
]


@register_rule("Layout")
@register_requirements(cap.Requirements.HI_004)
class DefaultPrimChecker(BaseRuleChecker):
    """
    When working with layers that represent assets, it is often useful to have a single, active,
    Xformable or Scope type root prim as the layers default prim.
    """

    # Keep this docstring in sync derived class' docstring

    @classmethod
    def activate_prim(cls, _: Usd.Stage, prim: Usd.Prim) -> None:
        prim.SetActive(True)

    @classmethod
    def _get_all_default_prim_candidates(cls, stage: Usd.Stage) -> Generator[Usd.Prim, None, None]:
        """
        Returns:
            All prims that can be default prims.
        """
        for prim in stage.GetPseudoRoot().GetChildren():
            # Must be Xformable or a Scope type
            if not prim.IsA(UsdGeom.Xformable) and not prim.IsA(UsdGeom.Scope):
                continue
            # Must be active
            if not prim.IsActive():
                continue
            # Cannot be abstract
            if prim.IsAbstract():
                continue
            # Cannot be prototyped
            if cls.__IsPrototype(prim):
                continue
            yield prim

    @classmethod
    def _get_default_prim_candidate(cls, stage: Usd.Stage) -> Usd.Prim:
        """Returns the most likely default prim or raise exception."""
        candidates = list(cls._get_all_default_prim_candidates(stage))
        if not candidates:
            raise ValueError("Can not set default prim (no prims under pseudo root).")
        if len(candidates) > 1:
            raise ValueError("Can not set default prim (potentially many candidates).")
        return candidates[0]

    @classmethod
    def update_default_prim(cls, stage: Usd.Stage, _) -> None:
        candidate = cls._get_default_prim_candidate(stage)
        stage.SetDefaultPrim(candidate)

    @classmethod
    def _get_default_prim_suggestion(cls, stage: Usd.Stage) -> Suggestion | None:
        try:
            cls._get_default_prim_candidate(stage)
        except ValueError:
            return None
        else:
            return Suggestion(cls.update_default_prim, "Updates the default prim")

    def CheckStage(self, usdStage):
        default_prim = usdStage.GetDefaultPrim()
        if not default_prim:
            self._AddFailedCheck(
                "Stage has missing or invalid defaultPrim.",
                at=usdStage,
                suggestion=self._get_default_prim_suggestion(usdStage),
                requirement=cap.Requirements.HI_004,
            )
            return

        if not default_prim.GetParent().IsPseudoRoot():
            self._AddFailedCheck(
                "The default prim must be a root prim.",
                at=default_prim,
            )

        # A Scope prim as the default prim is valid.
        if not default_prim.IsA(UsdGeom.Xformable) and not default_prim.IsA(UsdGeom.Scope):
            self._AddFailedCheck(
                f'The default prim <{default_prim.GetName()}> of type "{default_prim.GetTypeName()}" '
                "is not Xformable nor a Scope type.",
                at=default_prim,
            )

        if not default_prim.IsActive():
            self._AddFailedCheck(
                f"The default prim <{default_prim.GetName()}> should be active.",
                at=default_prim,
                suggestion=Suggestion(self.activate_prim, f"Activates Prim {default_prim.GetPath()}."),
                requirement=cap.Requirements.HI_004,
            )

        if default_prim.IsAbstract():
            self._AddFailedCheck(
                f"The default prim <{default_prim.GetName()}> should not be abstract.",
                at=default_prim,
                requirement=cap.Requirements.HI_004,
            )

        for prim in self._get_all_default_prim_candidates(usdStage):
            if prim != default_prim:
                self._AddWarning(
                    f"The prim <{prim.GetName()}> ({prim.GetPath()}) is a sibling of the default prim "
                    f"<{default_prim.GetName()}>.",
                    at=prim,
                    requirement=cap.Requirements.HI_004,
                )

    @staticmethod
    def __IsPrototype(prim):
        if hasattr(prim, "IsPrototype"):
            return prim.IsPrototype()
        return prim.IsMaster()


@register_rule("Layout")
class DanglingOverPrimChecker(BaseRuleChecker):
    """
    Prims usually need a ``def`` or ``class`` specifier, not just ``over`` specifiers.
    However, such overs may be used to hold relationship targets, attribute connections,
    or speculative opinions.
    """

    # Keep this docstring in sync with derived class' docstring

    def CheckStage(self, usdStage):
        excluded = self._GetValidOrphanOvers(usdStage)

        for prim in usdStage.TraverseAll():
            if not prim.HasDefiningSpecifier() and not prim in excluded:
                self._AddFailedCheck(
                    "Prim has an dangling over and does not contain the target prim/property of a relationship or "
                    "connection attribute. Ignore this message if the over was meant to specify speculative opinions.",
                    at=prim,
                )

    def _GetValidOrphanOvers(self, usdStage):
        # Get all relationships and attribute connections
        targeted_prims = set()
        for prim in usdStage.TraverseAll():
            for rel in prim.GetRelationships():
                for target in rel.GetTargets():
                    targeted_prims.add(usdStage.GetPrimAtPath(target.GetPrimPath()))

            for attribute in prim.GetAttributes():
                for connection in attribute.GetConnections():
                    targeted_prims.add(usdStage.GetPrimAtPath(connection.GetPrimPath()))

        # Check ancestors for valid orphan overs
        excluded = set()
        for prim in targeted_prims:
            while prim:
                if not prim.HasDefiningSpecifier():
                    excluded.add(prim)
                prim = prim.GetParent()
        return excluded
