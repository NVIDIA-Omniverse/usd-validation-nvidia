# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from ._asset_formats import (
    AssetFormat,
    AssetFormatRegistry,
    FormatDependency,
    add_registry_asset_format_callback,
    register_format,
    unregister_format,
)
from ._capabilities import (
    Capability,
    CapabilityRegistry,
    add_registry_capability_callback,
    register_capabilities,
    register_capability,
    unregister_capabilities,
    unregister_capability,
)
from ._categories import (
    CategoryRuleRegistry,
    add_registry_rule_callback,
    get_category_rules_registry,
    register_rule,
    unregister_rule,
)
from ._content import register_content, unregister_content
from ._features import (
    Feature,
    FeatureRegistry,
    add_registry_feature_callback,
    register_feature,
    register_features,
    unregister_feature,
    unregister_features,
)
from ._profiles import (
    Profile,
    ProfileRegistry,
    add_registry_profile_callback,
    register_profile,
    register_profiles,
    unregister_profile,
    unregister_profiles,
)
from ._registry import IdVersion, Registry, VersionedRegistry
from ._requirements import (
    Requirement,
    RequirementsRegistry,
    add_registry_requirement_callback,
    register_requirements,
    unregister_requirements,
)

__all__ = [
    "AssetFormat",
    "AssetFormatRegistry",
    "Capability",
    "CapabilityRegistry",
    "CategoryRuleRegistry",
    "Feature",
    "FeatureRegistry",
    "FormatDependency",
    "IdVersion",
    "Profile",
    "ProfileRegistry",
    "Registry",
    "Requirement",
    "RequirementsRegistry",
    "VersionedRegistry",
    "add_registry_asset_format_callback",
    "add_registry_capability_callback",
    "add_registry_feature_callback",
    "add_registry_profile_callback",
    "add_registry_requirement_callback",
    "add_registry_rule_callback",
    "get_category_rules_registry",
    "register_capabilities",
    "register_capability",
    "register_content",
    "register_feature",
    "register_features",
    "register_format",
    "register_profile",
    "register_profiles",
    "register_requirements",
    "register_rule",
    "unregister_capabilities",
    "unregister_capability",
    "unregister_content",
    "unregister_feature",
    "unregister_features",
    "unregister_format",
    "unregister_profile",
    "unregister_profiles",
    "unregister_requirements",
    "unregister_rule",
]
