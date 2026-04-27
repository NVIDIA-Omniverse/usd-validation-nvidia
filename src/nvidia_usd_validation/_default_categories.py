# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Sequence
from enum import Enum

from ._atomic_asset_checker import AnchoredAssetPathsChecker, SupportedFileTypesChecker
from ._base_rule_checker import BaseRuleChecker
from ._base_rules import (
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
)
from ._deprecate import deprecated
from ._geometry_checker import (
    IndexedPrimvarChecker,
    ManifoldChecker,
    NormalsExistChecker,
    NormalsValidChecker,
    NormalsWindingsChecker,
    SubdivisionSchemeChecker,
    UnusedMeshTopologyChecker,
    UnusedPrimvarChecker,
    ValidateTopologyChecker,
    WeldChecker,
    ZeroAreaFaceChecker,
)
from ._layer_checker import (
    LayerSpecChecker,
    UsdAsciiPerformanceChecker,
)
from ._layout_checker import (
    DanglingOverPrimChecker,
    DefaultPrimChecker,
)
from ._material_checker import (
    MaterialOutOfScopeChecker,
    MaterialPathChecker,
    MaterialUsdPreviewSurfaceChecker,
    ShaderImplementationSourceChecker,
    UsdDanglingMaterialBinding,
    UsdMaterialBindingApi,
)
from ._misc_checker import (
    SkelBindingAPIAppliedChecker,
    UsdGeomSubsetChecker,
    UsdLuxSchemaChecker,
)
from ._physics_checker import (
    ArticulationChecker,
    ColliderChecker,
    PhysicsJointChecker,
    RigidBodyChecker,
)

__all__ = [
    "DefaultCategoryRules",
]


@deprecated("Use CategoryRuleRegistry instead")
class DefaultCategoryRules(Enum):
    """
    The declared Categories and Rules defined in `nvidia_usd_validation` module. For additional classes use
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
