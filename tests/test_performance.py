# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from common import AsyncioValidationTestCase, get_url
from nvidia_usd_validation import (
    AlmostExtremeExtentChecker,
    BaseBoundsChecker,
    BoundsLimit,
    PointsPrecisionErrorChecker,
    PointsPrecisionWarningChecker,
)
from nvidia_usd_validation.tests import IsAnError, IsAWarning
from pxr import Gf, Sdf, UsdGeom

INF = float("inf")


class AlmostExtremeExtentCheckerCheckerTest(AsyncioValidationTestCase):
    """Ensure that we identify the Prims that RTX will produce warnings for, and no others"""

    async def test_validate(self):
        # TODO: We need some more test cases
        # - Transformed parent prims
        # - Time sampled prims
        # - Prims with invalid or un-authored extent

        # Declare a list of the Paths that we expect to fail
        fail_prim_paths = [
            "/World/TranslateX/Fail",
            "/World/TranslateY/Fail",
            "/World/TranslateZ/Fail",
            "/World/ScaleX/Fail",
            "/World/ScaleY/Fail",
            "/World/ScaleZ/Fail",
        ]

        # Build a list of the warnings that we expect to be found
        warnings = []
        for path in fail_prim_paths:
            warnings.append(
                IsAWarning(
                    f"Geometry extents are approaching the size that RTX considers extreme {path}",
                    at=Sdf.Path(path),
                )
            )

        # Assert that the expected warnings are returned
        await self.assertRuleAsync(
            asset=get_url("Geometry/extremeExtent.usda"),
            rule=AlmostExtremeExtentChecker,
            asserts=warnings,
        )


class VerticalLimitChecker(BaseBoundsChecker):
    """
    This class demonstrates how a new bounds limit checker can be implemented trivially using the `BaseBoundsChecker`.

    In this case we apply a vertical limit.
    - No geometry should be below the lower limit of 0 meters, or above the upper limit of 100 meters
    - There are no horizontal limits applied.

    A value of `inf` is used for axis in which no limit should be applied.

    The up axis of the Stage is used to determine which component of point positions represent up.
    """

    BOUNDS_LIMIT: BoundsLimit = BoundsLimit(
        min_bound=Gf.Vec3d(-INF, 0.0, -INF),
        max_bound=Gf.Vec3d(INF, 100.0, INF),
        meters_per_unit=UsdGeom.LinearUnits.meters,
        message="Geometry is below the lower limit of 0m or above the upper limit of 100m",
    )


class VerticalLimitCheckerTest(AsyncioValidationTestCase):
    """Test case to ensure that the example `VerticalLimitChecker` functions as expected"""

    async def test_validate(self):
        # Declare a list of the Paths that we expect to fail
        fail_prim_paths = [
            "/World/TranslateY/Fail",
            "/World/Instance/Fail/Cube",
        ]

        # Build a list of the warnings that we expect to be found
        warnings = []
        for path in fail_prim_paths:
            warnings.append(
                IsAWarning(
                    f"Geometry is below the lower limit of 0m or above the upper limit of 100m {path}",
                    at=Sdf.Path(path),
                )
            )

        # Assert that the expected warnings are returned
        await self.assertRuleAsync(
            asset=get_url("Geometry/verticalLimits.usda"),
            rule=VerticalLimitChecker,
            asserts=warnings,
        )


class PointsPrecisionErrorCheckerTestCase(AsyncioValidationTestCase):

    MESSAGE = "Points values exceed the max value of 8388608.0 beyond which a precision of 1.0 can be expressed"

    async def test_validate(self):
        # Declare a list of the Paths that we expect to fail
        fail_prim_paths = [
            "/World/NoExtent/Error/Fail",
            "/World/Extent/Error/Fail",
        ]

        # Build a list of the asserts that we expect
        asserts = []
        for path in fail_prim_paths:
            asserts.append(IsAnError(f"{self.MESSAGE} {path}", at=Sdf.Path(path)))

        # Assert that the expected rules fail
        await self.assertRuleAsync(
            asset=get_url("Geometry/pointsPrecision.usda"),
            rule=PointsPrecisionErrorChecker,
            asserts=asserts,
        )


class PointsPrecisionWarningCheckerTestCase(AsyncioValidationTestCase):

    MESSAGE = "Points values exceed the max value of 8388.608 beyond which a precision of 0.001 can be expressed"

    async def test_validate(self):
        # Declare a list of the Paths that we expect to fail
        fail_prim_paths = [
            "/World/NoExtent/Warn/Fail",
            "/World/NoExtent/Error/Pass",
            "/World/NoExtent/Error/Fail",
            "/World/Extent/Warn/Fail",
            "/World/Extent/Error/Pass",
            "/World/Extent/Error/Fail",
        ]

        # Build a list of the asserts that we expect
        asserts = []
        for path in fail_prim_paths:
            asserts.append(IsAWarning(f"{self.MESSAGE} {path}", at=Sdf.Path(path)))

        # Assert that the expected rules fail
        await self.assertRuleAsync(
            asset=get_url("Geometry/pointsPrecision.usda"),
            rule=PointsPrecisionWarningChecker,
            asserts=asserts,
        )
