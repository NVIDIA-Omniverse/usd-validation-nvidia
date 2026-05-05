# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from dataclasses import dataclass

from pxr import Gf, Usd, UsdGeom, Vt

import nvidia_usd_validation.capabilities

from ._base_rule_checker import BaseRuleChecker
from ._categories import register_rule
from ._issues import IssueSeverity
from ._requirements import register_requirements

__all__ = [
    "AlmostExtremeExtentChecker",
    "BaseBoundsChecker",
    "BoundsLimit",
    "PointsPrecisionChecker",
    "PointsPrecisionErrorChecker",
    "PointsPrecisionWarningChecker",
    "PrecisionLimit",
]

ALMOST_EXTREME: float = pow(2, 38)
STAGE_LINEAR_UNITS: float = 0.0
SUPPORTED_UP_AXIS: tuple[str] = (UsdGeom.Tokens.y, UsdGeom.Tokens.z)


@dataclass(frozen=True)
class BoundsLimit:
    """
    Describes a bounds based limit that can be enforced by the BoundsCheckerRule

    The bounds values will be adapted to match the metrics of the Stage being checked.

    Scaling will be applied based on the relative linear units (meters per unit) of the Bounds Limit and the Stage.
    A value of 0 on the Bounds Limit indicates that the linear units of the Stage should be used.

    Orientation will be applied based on the relative up axis of the Bounds Limit and the Stage.
    Only `y` and `z` up axis are supported, any other values will be ignored and an up axis of `y` assumed.

    If extent checks are enable and all corners are within the limits then the points check is skipped.

    Attributes:
        min_bound (Gf.Vec3d): Minimum value of the bound limit.
        max_bound (Gf.Vec3d): Maximum value of the bound limit.
        meters_per_unit (float): Linear units of the bounds values.
        up_axis (str): Up axis of the bounds values.
        check_extent (bool): Should extents be compared against the limits.
        check_points (bool): Should points be compared against the limits.
        message (str): The warning message to use when geometry is outside the limits.

    """

    min_bound: Gf.Vec3d
    max_bound: Gf.Vec3d
    meters_per_unit: float = STAGE_LINEAR_UNITS
    up_axis: str = UsdGeom.Tokens.y
    check_extent: bool = True
    check_points: bool = True
    message: str = "Geometry falls outside the bounds limits"


class BaseBoundsChecker(BaseRuleChecker):
    """Check that the world space point positions of Geometric Prims are within bounds limits"""

    BOUNDS_LIMIT: BoundsLimit = None

    @staticmethod
    def _all_points_within_bounds(bounds: Gf.Range3d, points: Vt.Vec3fArray, local_to_world: Gf.Matrix4d) -> bool:
        """Returns True if all world space points are contained within the bounds"""
        for point in points:
            world_space_point: Gf.Vec3d = local_to_world.Transform(Gf.Vec3d(point))
            if not bounds.Contains(world_space_point):
                return False
        return True

    @classmethod
    def _get_adjusted_bounds(cls, stage: Usd.Stage) -> Gf.Range3d:
        """Get the bounds used by this Checker adjusted to account for Stage metrics"""
        min_bound: Gf.Vec3d = cls.BOUNDS_LIMIT.min_bound
        max_bound: Gf.Vec3d = cls.BOUNDS_LIMIT.max_bound

        # Scale the bounds to match the stages linear units
        if cls.BOUNDS_LIMIT.meters_per_unit != 0:
            stage_unit: float = UsdGeom.GetStageMetersPerUnit(stage)
            limit_unit: float = cls.BOUNDS_LIMIT.meters_per_unit
            scaling_factor: float = limit_unit / stage_unit
            min_bound = min_bound * scaling_factor
            max_bound = max_bound * scaling_factor

        # Validate the up axis of the limit and the stage
        # For the Stage we use the fallback up axis when an invalid value is found as this is site configurable
        stage_up_axis: str = UsdGeom.GetStageUpAxis(stage)
        if stage_up_axis not in SUPPORTED_UP_AXIS:
            stage_up_axis = UsdGeom.GetFallbackUpAxis()

        # For the Bounds Limit we "y" when an invalid value is found as the BoundsLimit is not site configurable
        bounds_up_axis: str = cls.BOUNDS_LIMIT.up_axis
        if bounds_up_axis not in SUPPORTED_UP_AXIS:
            bounds_up_axis = UsdGeom.Tokens.y

        # Flip the y and z components if the up axis differ
        if bounds_up_axis != stage_up_axis:
            min_bound = Gf.Vec3d(min_bound[0], min_bound[2], min_bound[1])
            max_bound = Gf.Vec3d(max_bound[0], max_bound[2], max_bound[1])

        return Gf.Range3d(min_bound, max_bound)

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

        # Xform Cache to improve performance of local to world space calculation
        # This is cleared during CheckStage() and ResetCaches()
        self.xform_cache: UsdGeom.XformCache = UsdGeom.XformCache(Usd.TimeCode.Default())

        # The effective bounds limit to check against accounting for up axis
        # This is set during CheckStage() and cleared during ResetCaches()
        self.bounds: Gf.Range3d = None

    def _check_extent(self, min_extent: Gf.Vec3f, max_extent: Gf.Vec3f, matrix: Gf.Matrix4d) -> bool:
        """Return true if the extents of this Prim are inside of the bounds limit"""
        # Skip empty ranges that should be caught by the ExtentsChecker
        extent_range: Gf.Range3f = Gf.Range3f(min_extent, max_extent)
        if extent_range.IsEmpty():
            return True

        # Check if any of the corner points of the extent fall outside the limits
        points: Vt.Vec3fArray = [extent_range.GetCorner(x) for x in range(8)]
        return self._all_points_within_bounds(self.bounds, points, matrix)

    def _check_points(self, points: Vt.Vec3fArray, matrix: Gf.Matrix4d) -> bool:
        """Return true if the points of this Prim are inside of the bounds limit"""
        return self._all_points_within_bounds(self.bounds, points, matrix)

    def CheckStage(self, usdStage: Usd.Stage):
        # We do not perform any checks on the Stage itself, but use this as an opportunity to update Stage based data
        self.xform_cache.Clear()

        # Compute a bbox from the BoundsLimit accounting for metrics differences between the BoundsLimit and Stage
        # TODO: Store multiple bounds keyed by the Stage they were adjusted to
        self.bounds = self._get_adjusted_bounds(usdStage)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        # TODO: Support validation of world space extents for UsdGeomPointInstancer instances

        # Skip non Boundable prims
        boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)
        if not boundable:
            return

        # Skip invalid extent where we do not have a min and a max value
        # If an extent is authored with an appropriate number of values it will be used, even if the values do not match
        # the geometry. However, that case should be caught by the ExtentsChecker
        extent: Vt.Vec3fArray = boundable.ComputeExtent(Usd.TimeCode.Default())
        if extent is None or len(extent) != 2:
            return

        # Get the world matrix so that we can transform points during limits checks
        matrix: Gf.Matrix4d = self.xform_cache.GetLocalToWorldTransform(prim)

        # Check if the extents are inside the limits
        # We do not need go on to check the individual points if the extent is inside the limits
        if self.BOUNDS_LIMIT.check_extent:
            if self._check_extent(extent[0], extent[1], matrix):
                return

        # Check if the points are inside the limits
        if self.BOUNDS_LIMIT.check_points:
            point_based: UsdGeom.PointBased = UsdGeom.PointBased(prim)
            if point_based:
                points: Vt.Vec3fArray = point_based.GetPointsAttr().Get(Usd.TimeCode.Default())
                if self._check_points(points, matrix):
                    return

        self._AddWarning(message=f"{self.BOUNDS_LIMIT.message} {prim.GetPath()}", at=boundable)

    def ResetCaches(self):
        # The Xform Cache does not update on Stage changes so must be cleared when ResetCaches is called
        self.xform_cache.Clear()
        self.bounds = None


@register_rule("Performance", skip=True)
@register_requirements(nvidia_usd_validation.capabilities.Requirements.VG_RTX_001)
class AlmostExtremeExtentChecker(BaseBoundsChecker):
    """
    The world space extents of any Boundable should be within 2^40 units of the origin.
    Failure to meet this requirement will result in the offending object being discarded by the RTX renderer.

    In order to avoid reaching the RTX imposed limit an "almost extreme" check is used that looks for Boundable Prims
    that a more than 2^38 units from the origin.

    - Values are compared raw without consideration of linear units
    - Only the default time code is considered
    - The value of authored `extent` will be used for the check, even if they are incorrect
    """

    BOUNDS_LIMIT: BoundsLimit = BoundsLimit(
        min_bound=Gf.Vec3d(-ALMOST_EXTREME),
        max_bound=Gf.Vec3d(ALMOST_EXTREME),
        meters_per_unit=STAGE_LINEAR_UNITS,
        message="Geometry extents are approaching the size that RTX considers extreme",
    )


@dataclass(frozen=True)
class PrecisionLimit:
    """
    Represents a precision requirement for float values, defined by the smallest allowable increment and the unit it is
    expressed in.

    Attributes:
        min_increment (float): The smallest meaningful change that must be expressible.
        meters_per_unit (float): Linear units of the increment.

    """

    min_increment: float = 0.01
    meters_per_unit: float = STAGE_LINEAR_UNITS


@register_rule("Other", skip=True)
@register_requirements(nvidia_usd_validation.capabilities.Requirements.VG_020)
class PointsPrecisionChecker(BaseRuleChecker):
    """
    Points values must not exceed the range at which a given precision, represented as the smallest possible increment,
    can be reliably expressed using float precision.

    Failure to meet this requirement will result in loss of precision, where small changes are rounded away.
    This can cause visible artifacts in geometry, and unpredictable behavior in simulation or rendering pipelines.

    """

    PRECISION_LIMIT: PrecisionLimit = PrecisionLimit(min_increment=0.01, meters_per_unit=STAGE_LINEAR_UNITS)
    SEVERITY: IssueSeverity = IssueSeverity.WARNING

    @staticmethod
    def _all_points_are_safe(max_value: float, points: Vt.Vec3fArray) -> bool:
        """Returns True if the components of all points are below the max value"""
        for point in points:
            for index in range(3):
                if abs(point[index]) > max_value:
                    return False
        return True

    @classmethod
    def _get_adjusted_max_safe_float_value(cls, stage: Usd.Stage) -> float:
        """
        Returns the maximum float value that can safely express the precision limit used by this Checker.
        The value is adjusted to account the linear units of the Precision Limit vs the Stage metrics.
        """
        min_increment: float = cls.PRECISION_LIMIT.min_increment

        # Scale the min increment to match the stages linear units
        if cls.PRECISION_LIMIT.meters_per_unit != STAGE_LINEAR_UNITS:
            stage_unit: float = UsdGeom.GetStageMetersPerUnit(stage)
            limit_unit: float = cls.PRECISION_LIMIT.meters_per_unit
            scaling_factor: float = limit_unit / stage_unit
            min_increment = min_increment * scaling_factor

        max_value: float = min_increment * pow(2, 23)
        return max_value

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

        # The effective max value to check against accounting for stage linear units
        # This is set during CheckStage() and cleared during ResetCaches()
        self.max_value: float = None

    def _check_extent(self, min_extent: Gf.Vec3f, max_extent: Gf.Vec3f) -> bool:
        """Return true if the extents of this Prim are inside of the precision limit"""
        # Skip empty ranges that should be caught by the ExtentsChecker
        extent_range: Gf.Range3f = Gf.Range3f(min_extent, max_extent)
        if extent_range.IsEmpty():
            return True

        # Check the corner points of the extent
        points: Vt.Vec3fArray = [extent_range.GetCorner(x) for x in range(8)]
        return self._all_points_are_safe(self.max_value, points)

    def CheckStage(self, usdStage: Usd.Stage):
        # Compute the maximum float value accounting for the linear units of this Stage
        self.max_value = self._get_adjusted_max_safe_float_value(usdStage)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        # Skip non Point Based prims
        point_based: UsdGeom.PointBased = UsdGeom.PointBased(prim)
        if not point_based:
            return

        # Skip invalid extent where we do not have a min and a max value
        # If an extent is authored with an appropriate number of values it will be used, even if the values do not match
        # the geometry. However, that case should be caught by the ExtentsChecker
        boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)
        extent: Vt.Vec3fArray = boundable.ComputeExtent(Usd.TimeCode.Default())
        if extent is None or len(extent) != 2:
            return

        # Check if the extents are inside the limits
        # We do not need to check the actual points because the extent describes the max values
        if self._check_extent(extent[0], extent[1]):
            return

        # Add an issue regarding values exceeding the precision limit
        message = f"Points values exceed the max value of {self.max_value} beyond which a precision of {self.PRECISION_LIMIT.min_increment} can be expressed"
        match self.SEVERITY:
            case IssueSeverity.ERROR:
                self._AddError(message=f"{message} {prim.GetPath()}", at=boundable)
            case IssueSeverity.WARNING:
                self._AddWarning(message=f"{message} {prim.GetPath()}", at=boundable)
            case IssueSeverity.INFO:
                self._AddInfo(message=f"{message} {prim.GetPath()}", at=boundable)

    def ResetCaches(self):
        self.max_value = None


@register_rule("Other", skip=True)
class PointsPrecisionErrorChecker(PointsPrecisionChecker):
    """
    Points must be defined such that the smallest meaningful increment between values is less than 1.0 linear units.

    Value greater than this limit have insufficient precision to represent small adjustments, leading to severe
    rounding, loss of detail, and major rendering or simulation artifacts.
    """

    PRECISION_LIMIT: PrecisionLimit = PrecisionLimit(min_increment=1.0, meters_per_unit=STAGE_LINEAR_UNITS)
    SEVERITY: IssueSeverity = IssueSeverity.ERROR


@register_rule("Other", skip=True)
class PointsPrecisionWarningChecker(PointsPrecisionChecker):
    """
    Points should be defined such that the smallest meaningful increment between values is less than 0.01 linear units.

    Value greater than this limit have insufficient precision to represent fine grained adjustments, leading to severe
    rounding, loss of detail, and major rendering or simulation artifacts.
    """

    PRECISION_LIMIT: PrecisionLimit = PrecisionLimit(min_increment=0.001, meters_per_unit=STAGE_LINEAR_UNITS)
    SEVERITY: IssueSeverity = IssueSeverity.WARNING
