# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import nvidia_usd_validation.capabilities as cap
from pxr import Tf, Usd, UsdGeom

from ._base_rule_checker import BaseRuleChecker
from ._requirements import register_requirements

__all__ = [
    "GaussianSplatSchemaChecker",
]

_PRIM_TYPE = "ParticleField3DGaussianSplat"

# Tf type names that appear when UsdVol registers ParticleField3DGaussianSplat (varies by USD build / fork).
_TF_SCHEMA_TYPE_CANDIDATES = (
    _PRIM_TYPE,
    "UsdVolParticleField3DGaussianSplat",
)

_REQUIRED_ATTRS = (
    "positions",
    "scales",
    "orientations",
    "opacities",
    "radiance:sphericalHarmonicsDegree",
    "radiance:sphericalHarmonicsCoefficients",
)

_SH_DEGREE_TO_ELEMENT_SIZE = {0: 1, 1: 4, 2: 9, 3: 16}

_QUAT_NORM_TOL = 1e-3

# Stock OpenUSD first shipped this schema in 26.03; 25.11 also includes it. Omniverse/Kit may backport the
# schema while ``Usd.GetVersion()`` still reports an older tuple, so prefer runtime type registration checks.
_SCHEMA_MIN_USD_VERSION = (0, 25, 11)


def _tf_schema_registered(type_name: str) -> bool:
    t = Tf.Type.FindByName(type_name)
    return bool(t) and not t.IsUnknown()


def _particle_field_gaussian_splat_schema_available() -> bool:
    if any(_tf_schema_registered(name) for name in _TF_SCHEMA_TYPE_CANDIDATES):
        return True
    return Usd.GetVersion() >= _SCHEMA_MIN_USD_VERSION


@register_requirements(cap.Requirements.VG_035)
class GaussianSplatSchemaChecker(BaseRuleChecker):
    """VG.035 / usdgeom-particle-field-gaussian-splat — validate ``ParticleField3DGaussianSplat`` prim data."""

    @staticmethod
    def is_implemented() -> bool:
        """True when this USD build exposes the ``ParticleField3DGaussianSplat`` schema (typed Tf or version)."""
        return _particle_field_gaussian_splat_schema_available()

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if prim.GetTypeName() != _PRIM_TYPE:
            return

        self._check_required_attrs(prim)
        vertex_count = self._check_vertex_count_consistency(prim)
        if vertex_count is None or vertex_count == 0:
            return
        self._check_opacity_range(prim)
        self._check_scales_positive(prim)
        self._check_orientations_unit(prim)
        self._check_sh_degree(prim)
        self._check_sh_coefficients(prim, vertex_count)

    def _check_required_attrs(self, prim: Usd.Prim) -> None:
        for attr_name in _REQUIRED_ATTRS:
            attr = prim.GetAttribute(attr_name)
            if not attr or not attr.HasValue():
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_035,
                    message=f"Required attribute '{attr_name}' is missing or has no value.",
                    at=prim,
                )

        extent_attr = UsdGeom.Boundable(prim).GetExtentAttr()
        if not extent_attr or not extent_attr.HasValue():
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message="Required attribute 'extent' is missing or has no value.",
                at=prim,
            )

    def _check_vertex_count_consistency(self, prim: Usd.Prim) -> int | None:
        positions_attr = prim.GetAttribute("positions")
        if not positions_attr or not positions_attr.HasValue():
            return None

        position_count = len(positions_attr.Get())
        if position_count == 0:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message="positions array is empty.",
                at=prim,
            )
            return 0

        for name in ("scales", "orientations", "opacities"):
            attr = prim.GetAttribute(name)
            if attr and attr.HasValue():
                count = len(attr.Get())
                if count != position_count:
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VG_035,
                        message=f"'{name}' has {count} elements, expected {position_count} (positions count).",
                        at=prim,
                    )
        return position_count

    def _check_opacity_range(self, prim: Usd.Prim) -> None:
        attr = prim.GetAttribute("opacities")
        if not attr or not attr.HasValue():
            return
        for index, opacity in enumerate(attr.Get()):
            if opacity < 0.0 or opacity > 1.0:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_035,
                    message=f"Opacity at index {index} is {opacity}, expected range [0, 1].",
                    at=prim,
                )
                break

    def _check_scales_positive(self, prim: Usd.Prim) -> None:
        attr = prim.GetAttribute("scales")
        if not attr or not attr.HasValue():
            return
        for index, scale in enumerate(attr.Get()):
            if scale[0] <= 0 or scale[1] <= 0 or scale[2] <= 0:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_035,
                    message=(
                        f"Scale at index {index} has non-positive component: " f"({scale[0]}, {scale[1]}, {scale[2]})."
                    ),
                    at=prim,
                )
                break

    def _check_orientations_unit(self, prim: Usd.Prim) -> None:
        attr = prim.GetAttribute("orientations")
        if not attr or not attr.HasValue():
            return
        for index, orientation in enumerate(attr.Get()):
            norm = orientation.GetLength()
            if abs(norm - 1.0) > _QUAT_NORM_TOL:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_035,
                    message=(f"Orientation at index {index} is not a unit quaternion (norm={norm:.6f})."),
                    at=prim,
                )
                break

    def _check_sh_degree(self, prim: Usd.Prim) -> None:
        attr = prim.GetAttribute("radiance:sphericalHarmonicsDegree")
        if not attr or not attr.HasValue():
            return
        degree = attr.Get()
        if degree not in _SH_DEGREE_TO_ELEMENT_SIZE:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message=f"SH degree is {degree}, expected one of {{0, 1, 2, 3}}.",
                at=prim,
            )

    def _check_sh_coefficients(self, prim: Usd.Prim, vertex_count: int) -> None:
        attr = prim.GetAttribute("radiance:sphericalHarmonicsCoefficients")
        if not attr or not attr.HasValue():
            return

        sh_primvar = UsdGeom.Primvar(attr)

        interpolation = sh_primvar.GetInterpolation()
        if interpolation != UsdGeom.Tokens.vertex:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message=f"SH coefficients primvar interpolation is '{interpolation}', expected 'vertex'.",
                at=prim,
            )

        element_size = sh_primvar.GetElementSize()
        if element_size <= 0:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message="SH coefficients primvar elementSize is not set.",
                at=prim,
            )
            return

        sh_degree_attr = prim.GetAttribute("radiance:sphericalHarmonicsDegree")
        if sh_degree_attr and sh_degree_attr.HasValue():
            degree = sh_degree_attr.Get()
            if degree in _SH_DEGREE_TO_ELEMENT_SIZE:
                expected = _SH_DEGREE_TO_ELEMENT_SIZE[degree]
                if element_size != expected:
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VG_035,
                        message=f"SH elementSize is {element_size} but degree {degree} expects {expected}.",
                        at=prim,
                    )

        total = len(attr.Get())
        expected_total = vertex_count * element_size
        if total != expected_total:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_035,
                message=(
                    "SH coefficients array has "
                    f"{total} elements, expected {vertex_count} x {element_size} = {expected_total}."
                ),
                at=prim,
            )
