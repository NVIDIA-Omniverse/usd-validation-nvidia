# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Sequence
from enum import Enum

from ._base_rule_checker import BaseRuleChecker
from .rules import (
    AnchoredAssetPathsChecker,
    ArticulationChecker,
    ByteAlignmentChecker,
    ColliderChecker,
    CompressionChecker,
    DanglingOverPrimChecker,
    DefaultPrimChecker,
    ExtentsChecker,
    IndexedPrimvarChecker,
    KindChecker,
    LayerSpecChecker,
    ManifoldChecker,
    MaterialOutOfScopeChecker,
    MaterialPathChecker,
    MaterialUsdPreviewSurfaceChecker,
    MissingReferenceChecker,
    NormalMapTextureChecker,
    NormalsExistChecker,
    NormalsValidChecker,
    NormalsWindingsChecker,
    PhysicsJointChecker,
    PrimEncapsulationChecker,
    RigidBodyChecker,
    ShaderImplementationSourceChecker,
    SkelBindingAPIAppliedChecker,
    StageMetadataChecker,
    SubdivisionSchemeChecker,
    SupportedFileTypesChecker,
    TextureChecker,
    TypeChecker,
    UnusedMeshTopologyChecker,
    UnusedPrimvarChecker,
    UsdAsciiPerformanceChecker,
    UsdDanglingMaterialBinding,
    UsdGeomSubsetChecker,
    UsdLuxSchemaChecker,
    UsdMaterialBindingApi,
    ValidateTopologyChecker,
    WeldChecker,
    ZeroAreaFaceChecker,
)
from .utils import deprecated

__all__ = [
    "DefaultCategoryRules",
]


@deprecated("Use CategoryRuleRegistry instead")
class DefaultCategoryRules(Enum):
    """
    The declared Categories and Rules defined in `usd_validation_nvidia` module. For additional classes use
    `CategoryRuleRegistry`.

    Args:
        category: The name of the category.
        rules: The sequence of rules associated to the category.
    """

    ATOMIC_ASSET = (
        "AtomicAsset",
        (
            AnchoredAssetPathsChecker,
            SupportedFileTypesChecker,
        ),
    )
    """
    AtomicAsset category is for all rules associated to Atomic Asset.

    :meta hide-value:
    """

    BASIC = (
        "Basic",
        (
            ByteAlignmentChecker,
            CompressionChecker,
            ExtentsChecker,
            KindChecker,
            MissingReferenceChecker,
            NormalMapTextureChecker,
            PrimEncapsulationChecker,
            StageMetadataChecker,
            TextureChecker,
            TypeChecker,
        ),
    )
    """
    Basic category is for all rules delivered with ComplianceChecker.

    :meta hide-value:
    """

    GEOMETRY = (
        "Geometry",
        (
            ManifoldChecker,
            NormalsExistChecker,
            NormalsValidChecker,
            NormalsWindingsChecker,
            IndexedPrimvarChecker,
            SubdivisionSchemeChecker,
            UnusedMeshTopologyChecker,
            UnusedPrimvarChecker,
            ValidateTopologyChecker,
            WeldChecker,
            ZeroAreaFaceChecker,
        ),
    )
    """
    Geometry category is for all rules for geometry and topology checks.

    :meta hide-value:
    """

    LAYER = (
        "Layer",
        (
            LayerSpecChecker,
            UsdAsciiPerformanceChecker,
        ),
    )
    """
    Layer category is for all rules running at layer level.

    :meta hide-value:
    """

    LAYOUT = (
        "Layout",
        (
            DanglingOverPrimChecker,
            DefaultPrimChecker,
        ),
    )
    """
    Layout category is for all rules concerned about best practices of prim hierarchy.

    :meta hide-value:
    """

    MATERIAL = (
        "Material",
        (
            MaterialOutOfScopeChecker,
            MaterialPathChecker,
            MaterialUsdPreviewSurfaceChecker,
            ShaderImplementationSourceChecker,
            UsdDanglingMaterialBinding,
            UsdMaterialBindingApi,
        ),
    )
    """
    Material category is for all rules about Materials.

    :meta hide-value:
    """

    PHYSICS = (
        "Physics",
        (
            ArticulationChecker,
            ColliderChecker,
            PhysicsJointChecker,
            RigidBodyChecker,
        ),
    )
    """
    Physics category is for all rules about Physics.

    :meta hide-value:
    """

    OTHER = (
        "Other",
        (
            SkelBindingAPIAppliedChecker,
            UsdGeomSubsetChecker,
            UsdLuxSchemaChecker,
        ),
    )
    """
    Category for other rules.

    :meta hide-value:
    """

    def __init__(self, category: str, rules: Sequence[type[BaseRuleChecker]]):
        self.category = category
        self.rules = rules
