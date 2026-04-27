# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from inspect import iscoroutinefunction

from ._base_rule_checker import BaseRuleChecker

__all__ = [
    "BaseRuleCheckerMetadata",
]


@cache
@dataclass(frozen=True, slots=True)
class BaseRuleCheckerMetadata:
    """Metadata for a compliance checker rule."""

    rule_type: type[BaseRuleChecker]

    def is_stage_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckStage.
        """
        return self.rule_type.CheckStage is not BaseRuleChecker.CheckStage

    def is_diagnostics_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckDiagnostics.
        """
        return self.rule_type.CheckDiagnostics is not BaseRuleChecker.CheckDiagnostics

    def is_unresolved_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckUnresolvedPaths.
        """
        return self.rule_type.CheckUnresolvedPaths is not BaseRuleChecker.CheckUnresolvedPaths

    def is_dependencies_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckDependencies.
        """
        return self.rule_type.CheckDependencies is not BaseRuleChecker.CheckDependencies

    def is_layer_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckLayer.
        """
        return self.rule_type.CheckLayer is not BaseRuleChecker.CheckLayer

    def is_zip_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckZipFile.
        """
        return self.rule_type.CheckZipFile is not BaseRuleChecker.CheckZipFile

    def is_format_dependency_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckFormatDependency.
        """
        return self.rule_type.CheckFormatDependency is not BaseRuleChecker.CheckFormatDependency

    def is_prim_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckPrim.
        """
        return self.rule_type.CheckPrim is not BaseRuleChecker.CheckPrim

    @cache
    def is_asset_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented any asset checks (layer, zip file, dependencies and unresolved paths).
        """
        return (
            self.is_layer_implemented()
            or self.is_zip_implemented()
            or self.is_dependencies_implemented()
            or self.is_unresolved_implemented()
        )

    @cache
    def is_only_stage_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckStage and no other methods.
        """
        return (
            self.is_stage_implemented()
            and not self.is_diagnostics_implemented()
            and not self.is_unresolved_implemented()
            and not self.is_dependencies_implemented()
            and not self.is_layer_implemented()
            and not self.is_zip_implemented()
            and not self.is_prim_implemented()
            and not self.is_format_dependency_implemented()
        )

    @cache
    def is_only_layer_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckLayer and no other methods.
        """
        return (
            self.is_layer_implemented()
            and not self.is_stage_implemented()
            and not self.is_diagnostics_implemented()
            and not self.is_unresolved_implemented()
            and not self.is_dependencies_implemented()
            and not self.is_zip_implemented()
            and not self.is_prim_implemented()
            and not self.is_format_dependency_implemented()
        )

    @cache
    def is_only_zip_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckZipFile and no other methods.
        """
        return (
            self.is_zip_implemented()
            and not self.is_stage_implemented()
            and not self.is_diagnostics_implemented()
            and not self.is_unresolved_implemented()
            and not self.is_dependencies_implemented()
            and not self.is_layer_implemented()
            and not self.is_prim_implemented()
            and not self.is_format_dependency_implemented()
        )

    @cache
    def is_only_format_dependency_implemented(self) -> bool:
        """
        Returns
            True if the rule has implemented CheckFormatDependency and no other methods.
        """
        return (
            self.is_format_dependency_implemented()
            and not self.is_stage_implemented()
            and not self.is_diagnostics_implemented()
            and not self.is_unresolved_implemented()
            and not self.is_dependencies_implemented()
            and not self.is_layer_implemented()
            and not self.is_zip_implemented()
            and not self.is_prim_implemented()
        )

    @cache
    def has_async_implementations(self) -> bool:
        """
        Returns
            True if the rule has implemented any asynchronous methods.
        """
        return (
            (self.is_stage_implemented() and iscoroutinefunction(self.rule_type.CheckStage))
            or (self.is_layer_implemented() and iscoroutinefunction(self.rule_type.CheckLayer))
            or (self.is_zip_implemented() and iscoroutinefunction(self.rule_type.CheckZipFile))
            or (self.is_prim_implemented() and iscoroutinefunction(self.rule_type.CheckPrim))
            or (self.is_diagnostics_implemented() and iscoroutinefunction(self.rule_type.CheckDiagnostics))
            or (self.is_unresolved_implemented() and iscoroutinefunction(self.rule_type.CheckUnresolvedPaths))
            or (self.is_dependencies_implemented() and iscoroutinefunction(self.rule_type.CheckDependencies))
            or (self.is_format_dependency_implemented() and iscoroutinefunction(self.rule_type.CheckFormatDependency))
        )
