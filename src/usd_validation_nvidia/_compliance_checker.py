#
# Copyright 2018 Pixar
# Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
from __future__ import annotations

import inspect
import itertools
from asyncio import to_thread
from collections.abc import Callable, Iterator, Sequence
from functools import singledispatchmethod
from math import nextafter

from pxr import Ar, Sdf, Usd, UsdUtils

from ._asset_format import AssetFormat, AssetFormatRegistry, FormatDependency
from ._assets import AssetType
from ._base_rule_checker import BaseRuleChecker
from ._base_rule_metadata import BaseRuleCheckerMetadata
from ._compliance_runners import (
    AsyncComplianceCheckerRunner,
    ComplianceCheckerEvent,
    ComplianceCheckerEventType,
    SyncComplianceCheckerRunner,
)
from ._context_managers import AsyncCounter, DelegateContextManager, PeriodicCallback
from ._identifiers import ANON_VALIDATOR_LAYER_NAME
from ._issues import Issue, IssueSeverity
from ._parameters import ParameterMapping
from ._stats import ValidationStats
from ._url_utils import LocalUriResolver, UriResolver

__all__ = [
    "ComplianceChecker",
]


def _is_package_or_packaged_layer(layer):
    return layer.GetFileFormat().IsPackage() or Ar.IsPackageRelativePath(layer.identifier)


_MAX_PROGRESS: float = nextafter(1.0, 0.0)

_USD_2508_API: bool = Usd.GetVersion() >= (0, 25, 8)


class ComplianceChecker:
    """A utility class for checking compliance of a given USD asset or a USDZ
    package.

    Since usdz files are zip files, someone could use generic zip tools to
    create an archive and just change the extension, producing a .usdz file that
    does not honor the additional constraints that usdz files require.  Even if
    someone does use our official archive creation tools, though, we
    intentionally allow creation of usdz files that can be very "permissive" in
    their contents for internal studio uses, where portability outside the
    studio is not a concern.  For content meant to be delivered over the web
    (eg. ARKit assets), however, we must be much more restrictive.

    This class provides a level of compliance checking:
    * "structural" validation that is represented by a set of base rules.

    Calling ComplianceChecker.DumpAllRules() will print an enumeration of the
    various rules in the two categories of compliance checking.
    """

    def __init__(
        self,
        *,
        skip_variants: bool = False,
        stats: ValidationStats | None = None,
        parameters: ParameterMapping | None = None,
        resolver: UriResolver | None = None,
    ):
        self._doVariants = not skip_variants
        self._issues = []
        self._stats = stats or ValidationStats()
        self._parameters = parameters or ParameterMapping()
        self._resolver: UriResolver = resolver if resolver is not None else LocalUriResolver()
        # Once a package has been checked, it goes into this set.
        self._checkedPackages = set()

        self._rule_types: set[type[BaseRuleChecker]] = set()
        self._rules: list[BaseRuleChecker] = []

    @property
    def rules(self) -> Sequence[BaseRuleChecker]:
        """
        Returns: The rules to use in this ComplianceChecker.
        """
        return tuple(self._rules)

    @staticmethod
    def _is_old_style_rule(rule_type: type[BaseRuleChecker]) -> bool:
        """
        Check if a rule type uses the old constructor signature.

        Old-style rules have exactly three parameters in this order:
        verbose, consumerLevelChecks, assetLevelChecks

        Args:
            rule_type: The rule type to check

        Returns:
            True if the rule has the old constructor signature, False otherwise
        """
        sig = inspect.signature(rule_type.__init__)
        params = list(sig.parameters.keys())[1:]

        return len(params) == 3 and params[0:3] == ["verbose", "consumerLevelChecks", "assetLevelChecks"]

    def AddRule(self, rule_type: type[BaseRuleChecker]) -> None:
        """
        Adds a rule to the ComplianceChecker.

        Args:
            rule_type (type[BaseRuleChecker]): The type of the rule to add.
        """
        if rule_type in self._rule_types:
            return
        self._rule_types.add(rule_type)
        try:
            # Instantiate rule based on constructor signature - use old OR new style, not both
            if self._is_old_style_rule(rule_type):
                # Old-style rule: pass the old boolean parameters only
                rule: BaseRuleChecker = rule_type(
                    verbose=False,
                    consumerLevelChecks=False,
                    assetLevelChecks=True,
                )
            else:
                # New-style rule: pass parameters only
                rule: BaseRuleChecker = rule_type(parameters=self._parameters)

            self._rules.append(rule)
        except Exception as error:
            self._issues.append(
                Issue(
                    severity=IssueSeverity.ERROR,
                    message=f"Failed to initialize rule {rule_type.__name__}: {error}",
                    rule=rule_type,
                )
            )

    def _AddError(self, errMsg):
        self._issues.append(Issue(severity=IssueSeverity.ERROR, message=errMsg))

    def _AddWarning(self, errMsg):
        self._issues.append(Issue(severity=IssueSeverity.WARNING, message=errMsg))

    @property
    def issues(self) -> Sequence[Issue]:
        """
        Returns all issues from all rules.
        """
        issues: list[Issue] = list(self._issues)
        for rule in self._rules:
            if rule_issues := rule.GetIssues():
                issues.extend(rule_issues)
        return tuple(issues)

    @property
    def partial_issues(self) -> Sequence[Issue]:
        """
        Returns partial issues from all rules.
        """
        issues: list[Issue] = list(self._issues)
        for rule in self._rules:
            if rule_issues := rule.GetIssues():
                issues.append(rule_issues[-1])
        return tuple(issues)

    def GetIssues(self) -> Sequence[Issue]:
        return self.issues

    def check(self, asset: str | Usd.Stage) -> None:
        """Consolidates check_compliance (for files) and check_stage_compliance (for stages)."""
        with SyncComplianceCheckerRunner(self._rules, self._stats) as runner:
            for event in self._check_compliance(asset):
                runner.append(event)

    async def check_async(self, asset: str | Usd.Stage, callback: Callable[[float], None] | None = None) -> None:
        """Asynchronous version of check.
        Args:
            asset (str, Usd.Stage): Root asset to run the validation. Can be an uri or an USD stage.
        Kwargs:
            callback (Callable(float): A callable that will be called when a batch of checkers executed.
        """
        num_events: int = 1

        asset_dependencies = None
        if self._rules_check_assets():
            # Get context from the current thread.
            if isinstance(asset, Usd.Stage):
                context: Ar.Context = asset.GetPathResolverContext()
            else:
                context: Ar.Context = Ar.GetResolver().GetCurrentContext()
            # OMPE-15461: We compute the asset dependencies and pass it to self._check_compliance to reduce the need of calling
            # UsdUtils.ComputeAllDependencies multiple times.
            asset_dependencies = await to_thread(self._check_dependencies, asset, context)

        # Setup _callback
        # Collect the total number of checker events and create a progress callback function here.
        # Note that we are not actually running any checker rules here, but
        # iterating all prims of the given asset/stage. Potential a slow process if running on a large asset?
        if callback:
            async with AsyncCounter() as counter:
                for event in self._check_compliance(asset, asset_dependencies=asset_dependencies):
                    if event.type is ComplianceCheckerEventType.FLUSH:
                        continue
                    await counter.count(len(self._rules))
                num_events = counter.counter

        # OMPE-11167: Clean up - make sure we don't have cached data.
        self._checkedPackages = set()
        # Run checkers
        runner = self._create_async_runner(self._rules, self._stats)

        def progress_callback() -> None:
            callback(round(min(runner.counter / num_events, _MAX_PROGRESS), 2))

        async with PeriodicCallback(progress_callback if callback else None):
            async with runner:
                for event in self._check_compliance(asset, asset_dependencies=asset_dependencies):
                    await runner.append(event)

    @classmethod
    def _create_async_runner(cls, rules: list[BaseRuleChecker], stats: ValidationStats) -> AsyncComplianceCheckerRunner:
        return AsyncComplianceCheckerRunner(rules, stats)

    def _rules_check_assets(self) -> bool:
        """Checks if any of the rules has implemented Asset checks."""
        return any(BaseRuleCheckerMetadata(type(rule)).is_asset_implemented() for rule in self._rules)

    def _rules_check_prims(self) -> bool:
        """Checks if any of the rules has implemented CheckPrim."""
        return any(BaseRuleCheckerMetadata(type(rule)).is_prim_implemented() for rule in self._rules)

    @singledispatchmethod
    @classmethod
    def _create_stage(cls, asset: AssetType) -> Usd.Stage:
        """
        Creates a stage from asset. If asset is string, it creates a new stage. If asset is an existing stage,
        it creates a copy to avoid possible data interfering.

        Args:
            asset (AssetType): Either str or existing stage.

        Returns:
            A new stage.
        """
        raise ValueError(f"Unknown asset of type {type(asset)}")

    @_create_stage.register
    @classmethod
    def _(cls, asset: str) -> Usd.Stage:
        compliance_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous(ANON_VALIDATOR_LAYER_NAME)
        stage: Usd.Stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(asset), compliance_layer)
        stage.SetEditTarget(stage.GetEditTargetForLocalLayer(compliance_layer))
        return stage

    @_create_stage.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> Usd.Stage:
        compliance_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous(ANON_VALIDATOR_LAYER_NAME)
        compliance_layer.TransferContent(asset.GetSessionLayer())
        stage: Usd.Stage = Usd.Stage.Open(asset.GetRootLayer(), compliance_layer)
        mask: Usd.StagePopulationMask = asset.GetPopulationMask()
        if not mask.IsEmpty():
            stage.SetPopulationMask(mask)
        stage.SetEditTarget(stage.GetEditTargetForLocalLayer(compliance_layer))
        return stage

    @classmethod
    def _create_prims_it(cls, stage: Usd.Stage):
        return iter(Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()))

    def _check_compliance(
        self, asset: str | Usd.Stage, asset_dependencies: tuple[Sdf.Layer, str, str] | None = None
    ) -> Iterator[ComplianceCheckerEvent]:
        """Yield ComplianceCheckerEvents for the given asset.
        Args:
            asset (str, Usd.Stage): Stage identifier or stage to validate.

        Kwargs:
            asset_dependencies (tuple): Tuple of asset's dependencies = all_layers, all_assets, unresolved_paths.
                If this argument is given, this method uses the given asset dependencies instead of calling
                `UsdUtils.ComputeAllDependencies` on the given asset in order to speed up the process.
        """
        if isinstance(asset, str) and not Usd.Stage.IsSupportedFile(asset):
            yield from self._check_asset_format(asset)
            return

        with DelegateContextManager() as ctx:
            usd_stage = self._create_stage(asset)
            stage_open_diagnostics = ctx.delegate.TakeUncoalescedDiagnostics()
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.FLUSH, None)  # Pause

        yield ComplianceCheckerEvent(ComplianceCheckerEventType.STAGE, usd_stage)
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.DIAGNOSTICS, stage_open_diagnostics)
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.FLUSH, None)  # Pause

        with Ar.ResolverContextBinder(usd_stage.GetPathResolverContext()):
            if self._rules_check_assets():
                all_layers, all_assets, unresolved_paths = asset_dependencies or self._check_dependencies(
                    asset, usd_stage.GetPathResolverContext()
                )

                # Compute dependencies can be expensive, pause quickly.
                yield ComplianceCheckerEvent(ComplianceCheckerEventType.FLUSH, None)
                yield ComplianceCheckerEvent(ComplianceCheckerEventType.UNRESOLVED_PATHS, unresolved_paths)
                yield ComplianceCheckerEvent(
                    ComplianceCheckerEventType.DEPENDENCIES, (usd_stage, all_layers, all_assets)
                )

            if self._rules_check_assets():
                # Process every package just once by storing them all in a set.
                packages = set()
                for layer in all_layers:
                    if _is_package_or_packaged_layer(layer):
                        package_path = Ar.SplitPackageRelativePathInner(layer.identifier)[0]
                        packages.add(package_path)
                    yield ComplianceCheckerEvent(ComplianceCheckerEventType.LAYER, layer)
                for package in packages:
                    yield from self._check_package(package)

            if self._rules_check_prims():
                all_prims_iterator = self._create_prims_it(usd_stage)
                yield from self._traverse_range(all_prims_iterator, isStageRoot=True)

    @classmethod
    def _check_dependencies(cls, asset: str | Usd.Stage, context: Ar.Context) -> tuple[Sdf.Layer, list[str], list[str]]:
        """
        Computes the asset dependencies for the given asset.

        Args:
            asset (str | Usd.Stage): The asset to compute the dependencies for.
            context (Ar.Context): The context to use for the resolver.

        Returns:
            A tuple of (all_layers, all_assets, unresolved_paths).
        """
        with Ar.ResolverContextBinder(context):
            with Ar.ResolverScopedCache():
                identifier: str = asset if isinstance(asset, str) else asset.GetRootLayer().identifier
                with DelegateContextManager():
                    asset_dependencies = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(identifier))
                    return asset_dependencies

    def _check_asset_format(self, asset_path: str) -> Iterator[ComplianceCheckerEvent]:
        """Yield events for each path returned by the matching AssetFormat handler.

        USD paths are routed through the normal compliance workflow (CheckStage, CheckLayer, etc.).
        Non-USD paths yield FORMAT_DEPENDENCY events for rules to inspect.
        If no handler is registered for *asset_path*, records an error and yields nothing.
        """
        asset_format: AssetFormat | None = AssetFormatRegistry().find(asset_path)
        if asset_format is None:
            self._AddError(f"Cannot open file '{asset_path}': no registered format handler.")
            return
        for dependency_path in asset_format.get_dependencies(asset_path, self._resolver):
            if Usd.Stage.IsSupportedFile(dependency_path):
                yield from self._check_compliance(dependency_path)
            else:
                format_dependency = FormatDependency(
                    path=dependency_path,
                    uri_resolver=self._resolver,
                    root_asset_path=asset_path,
                )
                yield ComplianceCheckerEvent(ComplianceCheckerEventType.FORMAT_DEPENDENCY, format_dependency)
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.FLUSH, None)

    def _check_package(self, package_path) -> Iterator[ComplianceCheckerEvent]:

        # XXX: Should we open the package on a stage to ensure that it is valid
        # and entirely self-contained.
        pkg_ext = Ar.GetResolver().GetExtension(package_path)
        if pkg_ext != "usdz":
            self._AddError(f"Package at path {package_path} has an invalid extension.")
            return

        # Check the parent package first.
        if Ar.IsPackageRelativePath(package_path):
            parent_package_path = Ar.SplitPackageRelativePathInner(package_path)[0]
            yield from self._check_package(parent_package_path)

        # Avoid checking the same parent package multiple times.
        if package_path in self._checkedPackages:
            return
        self._checkedPackages.add(package_path)

        resolved_path = Ar.GetResolver().Resolve(package_path)
        if not resolved_path:
            self._AddError(f"Failed to resolve package path '{package_path}'.")
            return

        if _USD_2508_API:
            zip_file = Sdf.ZipFile.Open(resolved_path)
        else:
            zip_file = Usd.ZipFile.Open(resolved_path)
        if not zip_file:
            self._AddError(f"Could not open package at path '{resolved_path}'.")
            return
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.ZIP_FILE, (zip_file, package_path))

    def _traverse_range(self, primRangeIt, isStageRoot) -> Iterator[ComplianceCheckerEvent]:
        prims_with_variants = []
        root_prim = primRangeIt.GetCurrentPrim()
        for prim in primRangeIt:
            # Skip variant set check on the root prim if it is the stage'.
            if not self._doVariants or (not isStageRoot and prim == root_prim):
                yield ComplianceCheckerEvent(ComplianceCheckerEventType.PRIM, prim)
                continue

            variant_sets = prim.GetVariantSets()
            variant_sets_names = variant_sets.GetNames()
            if len(variant_sets_names) == 0:
                yield ComplianceCheckerEvent(ComplianceCheckerEventType.PRIM, prim)
            else:
                prims_with_variants.append(prim)
                primRangeIt.PruneChildren()

        # Process prims before prims_with_variants
        yield ComplianceCheckerEvent(ComplianceCheckerEventType.FLUSH, None)
        for prim in prims_with_variants:
            yield from self._traverse_variants(prim)

    def _traverse_variants(self, prim) -> Iterator[ComplianceCheckerEvent]:
        if prim.IsInstanceProxy():
            return
        variant_sets = prim.GetVariantSets()
        variant_sets_names = variant_sets.GetNames()
        all_variant_names = []
        for vset_name in variant_sets_names:
            variant_set = variant_sets.GetVariantSet(vset_name)
            variant_names = variant_set.GetVariantNames()
            all_variant_names.append(variant_names)

        all_variations = itertools.product(*all_variant_names)

        for variation in all_variations:
            for idx, sel in enumerate(variation):
                variant_sets.SetSelection(variant_sets_names[idx], sel)
            yield ComplianceCheckerEvent(ComplianceCheckerEventType.RESET_CACHE, None)
            prim_range_iterator = iter(Usd.PrimRange(prim, Usd.TraverseInstanceProxies()))
            yield from self._traverse_range(prim_range_iterator, isStageRoot=False)
