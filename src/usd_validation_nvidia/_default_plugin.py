# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
Default plugin for the Omniverse Asset Validator.

Registers all built-in validation rules via the entrypoint plugin system.
"""
from __future__ import annotations

__all__ = [
    "DefaultPlugin",
]

import logging

from pxr import Usd

from usd_validation_nvidia.capabilities import Capabilities, Features, Profiles

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
    UsdzPackageValidator,
)
from ._capabilities import register_capabilities, unregister_capabilities
from ._categories import CategoryRuleRegistry, register_rule
from ._features import register_features, unregister_features
from ._gaussian_splat_checker import GaussianSplatSchemaChecker
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
from ._layer_checker import LayerSpecChecker, UsdAsciiPerformanceChecker
from ._layout_checker import DanglingOverPrimChecker, DefaultPrimChecker
from ._material_checker import (
    MaterialOldMdlSchemaChecker,
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
    MassChecker,
    PhysicsJointChecker,
    RigidBodyChecker,
)
from ._profiles import register_profiles, unregister_profiles
from ._utf8_checker import UnicodeNameChecker

logger = logging.getLogger(__name__)


class DefaultPlugin:
    """
    Default plugin that registers all built-in validation rules.

    This plugin is loaded by default through the entrypoint plugin system.
    Its ``on_startup()`` method explicitly registers all built-in rules.
    """

    def __init__(self):
        self._registered_rules: list[type[BaseRuleChecker]] = []

    def on_startup(self) -> None:
        """Register all built-in validation rules, capabilities, features and profiles."""
        register_capabilities(Capabilities)
        register_features(Features)
        register_profiles(Profiles)

        def _register(category, rule, **kwargs):
            register_rule(category, **kwargs)(rule)
            self._registered_rules.append(rule)

        # Basic rules
        _register("Basic", ByteAlignmentChecker, skip=UsdzPackageValidator.is_implemented())
        _register("Basic", CompressionChecker, skip=UsdzPackageValidator.is_implemented())
        _register("Basic", UsdzPackageValidator, skip=not UsdzPackageValidator.is_implemented())
        _register("Basic", MissingReferenceChecker)
        _register("Basic", StageMetadataChecker)
        _register("Basic", TextureChecker)
        _register("Basic", PrimEncapsulationChecker)
        _register("Basic", NormalMapTextureChecker)
        _register("Basic", KindChecker)
        _register("Basic", ExtentsChecker)
        _register("Basic", TypeChecker)

        # Layer rules
        _register("Layer", LayerSpecChecker)
        _register("Layer", UsdAsciiPerformanceChecker)

        # Other rules
        _register("Other", UnicodeNameChecker, skip=Usd.GetVersion() < (0, 24, 3))
        _register("Other", UsdGeomSubsetChecker)
        _register("Other", UsdLuxSchemaChecker)
        _register("Other", SkelBindingAPIAppliedChecker)

        # Geometry rules
        _register("Geometry", IndexedPrimvarChecker)
        _register("Geometry", ManifoldChecker)
        _register("Geometry", NormalsExistChecker)
        _register("Geometry", NormalsValidChecker)
        _register("Geometry", NormalsWindingsChecker)
        _register("Geometry", GaussianSplatSchemaChecker, skip=True)
        _register("Geometry", SubdivisionSchemeChecker)
        _register("Geometry", UnusedMeshTopologyChecker)
        _register("Geometry", UnusedPrimvarChecker)
        _register("Geometry", ValidateTopologyChecker)
        _register("Geometry", WeldChecker)
        _register("Geometry", ZeroAreaFaceChecker)

        # Material rules
        _register("Material", MaterialPathChecker)
        _register("Material", MaterialOutOfScopeChecker)
        _register("Material", UsdDanglingMaterialBinding)
        _register("Material", UsdMaterialBindingApi)
        _register("Material", MaterialUsdPreviewSurfaceChecker)
        _register("Material", ShaderImplementationSourceChecker)
        _register("Material", MaterialOldMdlSchemaChecker)

        # Layout rules
        _register("Layout", DefaultPrimChecker)
        _register("Layout", DanglingOverPrimChecker)

        # Physics rules
        _register("Physics", RigidBodyChecker)
        _register("Physics", ColliderChecker)
        _register("Physics", PhysicsJointChecker)
        _register("Physics", ArticulationChecker)
        _register("Physics", MassChecker)

    def on_shutdown(self) -> None:
        """Unregister all rules, capabilities, features and profiles registered by this plugin."""
        registry = CategoryRuleRegistry()
        for rule in self._registered_rules:
            registry.remove(rule)
        self._registered_rules.clear()
        unregister_profiles(Profiles)
        unregister_features(Features)
        unregister_capabilities(Capabilities)
