# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Usd, UsdGeom

import usd_validation_nvidia.capabilities as cap

from ._base_rule_checker import BaseRuleChecker
from ._requirements import register_requirements


@register_requirements(cap.Requirements.UN_006)
class UpAxisZChecker(BaseRuleChecker):
    """
    Validates that stage upAxis is 'Z'.

    This validator checks that the stage has an upAxis specified and that it is set to 'Z'.
    This is a requirement for certain simulation environments that expect Z-up coordinate systems.
    """

    def CheckStage(self, stage: Usd.Stage) -> None:
        # Get the stage upAxis
        up_axis = UsdGeom.GetStageUpAxis(stage)

        if not up_axis:
            self._AddFailedCheck(
                requirement=cap.Requirements.UN_006, message="Stage has no upAxis specified.", at=stage
            )
        elif up_axis != UsdGeom.Tokens.z:
            self._AddFailedCheck(
                requirement=cap.Requirements.UN_006, message=f"Stage has upAxis of '{up_axis}', not 'Z'.", at=stage
            )


@register_requirements(cap.Requirements.UN_007)
class UnitsInMetersChecker(BaseRuleChecker):
    """
    Validates that stage metersPerUnit is exactly 1.0.

    This validator checks that:
    - The stage has metersPerUnit specified
    - The metersPerUnit value is exactly 1.0

    This ensures the stage uses real-world scale (1 unit = 1 meter).
    """

    def CheckStage(self, stage: Usd.Stage) -> None:
        # Get the stage metersPerUnit
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)

        if meters_per_unit is None:
            self._AddFailedCheck(
                requirement=cap.Requirements.UN_007, message="Stage has no metersPerUnit specified.", at=stage
            )
        elif meters_per_unit != 1.0:
            self._AddFailedCheck(
                requirement=cap.Requirements.UN_007,
                message=f"Stage has metersPerUnit of {meters_per_unit}, not 1.0.",
                at=stage,
            )
