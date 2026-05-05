# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import asyncio
import contextlib
import dataclasses
import logging
import traceback
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from functools import cached_property, lru_cache, singledispatchmethod
from typing import TypeVar
from urllib.parse import ParseResult, urlparse

from pxr import Sdf, Usd

from ._asset_format import AssetFormatRegistry
from ._assets import (
    AssetLocatedCallback,
    AssetProgress,
    AssetProgressCallback,
    AssetType,
    AssetValidatedCallback,
)
from ._base_rule_checker import BaseRuleChecker
from ._capabilities import Capability
from ._categories import CategoryRuleRegistry
from ._compliance_checker import ComplianceChecker
from ._deprecate import deprecated
from ._features import Feature
from ._issues import Issue, IssuePredicate, IssueSeverity
from ._parameters import Parameter, ParameterMapping
from ._plugins import PluginManager
from ._profiles import Profile, ProfileRegistry
from ._requirements import Requirement, RequirementsRegistry
from ._results import Results, ResultsList
from ._stats import ValidationStats
from ._url_utils import LocalUriResolver, UriResolver
from ._validation_context import ValidationContext
from ._version import __version__

__all__ = [
    "ValidationEngine",
]

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationEngine:
    """An engine for running rule-checkers on a given OpenUSD Asset.

    Rules are :py:class:`BaseRuleChecker` derived classes which perform specific validation checks over various aspects
    of a USD layer/stage. Rules must be added through enable_rule. removed through disable_rule.

    Validation can be performed asynchronously (using either :py:meth:`validate_async` or :py:meth:`validate_with_callbacks`)
    or blocking (via :py:meth:`validate`).

    Example:
        Construct an engine and validate several assets using the default-enabled rules:

        .. code-block:: python

            import nvidia_usd_validation

            engine = nvidia_usd_validation.ValidationEngine()
            engine.enable_rule(MyRule)

            # Validate a single OpenUSD file
            print( engine.validate('foo.usd') )

            # Search a folder and recursively validate all OpenUSD files asynchronously
            # note a running asyncio EvenLoop is required
            task = engine.validate_with_callbacks(
                'bar/',
                asset_located_fn = lambda url: print(f'Validating "{url}"'),
                asset_validated_fn = lambda result: print(result),
            )
            task.add_done_callback(lambda task: print('validate_with_callbacks complete'))

            # Perform the same search & validate but await the results
            import asyncio
            async def test(url):
                results = await engine.validate_async(url)
                for result in results:
                    print(result)
            asyncio.ensure_future(test('bar/'))

            # Load a layer onto a stage and validate it in-memory, including any unsaved edits
            from pxr import Usd, Kind
            stage = Usd.Stage.Open('foo.usd')
            prim = stage.DefinePrim(f'{stage.GetDefaultPrim().GetPath()}/MyCube', 'cube')
            Usd.ModelAPI(prim).SetKind(Kind.Tokens.component)
            print( engine.validate(stage) )
    """

    def __init__(self, *, init_rules: bool = True, variants: bool = True) -> None:
        """
        Args:
            init_rules (bool): Whether to initialize rules from :func:`CategoryRuleRegistry`.
            variants (bool): Whether to process all variants.
        """
        self._variants = variants
        self._init_rules = init_rules
        self._enabled_rules: list[type[BaseRuleChecker]] = []
        self._disabled_rules: list[type[BaseRuleChecker]] = []
        self._enabled_requirements: list[Requirement] = []
        self._disabled_requirements: list[Requirement] = []
        self._enabled_capabilities: list[Capability] = []
        self._disabled_capabilities: list[Capability] = []
        self._enabled_features: list[Feature] = []
        self._disabled_features: list[Feature] = []
        self._enabled_profiles: list[Profile] = []
        self._disabled_profiles: list[Profile] = []
        self._tasks = set()
        self._stats = ValidationStats()
        self._parameters = []

    @cached_property
    def _resolver(self) -> UriResolver:
        return LocalUriResolver()

    @property
    def init_rules(self) -> bool:
        """
        Returns:
            Whether to initialize rules from :func:`CategoryRuleRegistry`.
        """
        return self._init_rules

    @property
    def initialized_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            A list of rules that have been initialized.
        """
        return CategoryRuleRegistry().rules

    @property
    def variants(self) -> bool:
        """
        Returns:
            Whether to process all variants.
        """
        return self._variants

    def add_parameter(self, parameter: Parameter) -> None:
        """
        Adds a custom parameter to the engine.
        """
        self._parameters.append(parameter)

    @property
    def parameters(self) -> ParameterMapping:
        """
        Returns:
            A mapping of all parameters from enabled requirements and custom parameters.
        """
        parameters: ParameterMapping = ParameterMapping()
        for requirement in self.requirements:
            for parameter in requirement.parameters:
                parameters.add(parameter)
        for parameter in self._parameters:
            parameters.add(parameter)
        return parameters

    @singledispatchmethod
    @classmethod
    def is_asset_supported(cls, asset: AssetType) -> bool:
        """
        Determines if the provided asset can be validated by the engine.

        Args:
            asset (AssetType): A single Asset pointing to a file URI, folder/container URI, or a live `Usd.Stage`.

        Returns:
            Whether the provided asset can be validated by the engine.
        """
        raise NotImplementedError(f"Unknown type {type(asset)}")

    @is_asset_supported.register(type(None))
    @classmethod
    def _(cls, asset: None) -> bool:
        return False

    @is_asset_supported.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> bool:
        return True

    @is_asset_supported.register
    @classmethod
    def _(cls, asset: str) -> bool:
        parse_result: ParseResult = urlparse(asset)
        return Usd.Stage.IsSupportedFile(parse_result.path) or AssetFormatRegistry().find(asset) is not None

    @singledispatchmethod
    @classmethod
    def describe(cls, asset: AssetType) -> str:
        """Provides a description of an Asset.

        Args:
            asset (AssetType): A single Asset pointing to a file URI, folder/container URI, or a live `Usd.Stage`.

        Returns:
            The `str` description of the asset that was validated.
        """
        raise NotImplementedError(f"Unknown type {type(asset)}")

    @describe.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> str:
        return Usd.Describe(asset)

    @describe.register
    @classmethod
    def _(cls, asset: str) -> str:
        return asset

    def enable_rule(self, rule: type[BaseRuleChecker]) -> None:
        """
        Enable a given rule on this engine.

        Args:
            rule (Type[BaseRuleChecker]): A `BaseRuleChecker` derived class to be enabled
        """
        self._enabled_rules.append(rule)
        with contextlib.suppress(ValueError):
            self._disabled_rules.remove(rule)

    def disable_rule(self, rule: type[BaseRuleChecker]) -> None:
        """
        Disable a given rule on this engine.

        Args:
            rule (type[BaseRuleChecker]): A `BaseRuleChecker` derived class to be enabled
        """
        self._disabled_rules.append(rule)
        with contextlib.suppress(ValueError):
            self._enabled_rules.remove(rule)

    @property
    def enabled_rules(self) -> list[type[BaseRuleChecker]]:
        return self._enabled_rules

    @property
    def disabled_rules(self) -> list[type[BaseRuleChecker]]:
        return self._disabled_rules

    def enable_requirement(self, requirement: Requirement) -> None:
        """
        Enable a given requirement on this engine.

        Args:
            requirement (Requirement): A `Requirement` to be enabled
        """
        rule: type[BaseRuleChecker] | None = RequirementsRegistry().get_validator(requirement)
        if rule is None:
            logging.warning(f"No rule registered for requirement {requirement.code}@{requirement.version}")
        self._enabled_requirements.append(requirement)
        with contextlib.suppress(ValueError):
            self._disabled_requirements.remove(requirement)

    def disable_requirement(self, requirement: Requirement) -> None:
        self._disabled_requirements.append(requirement)
        with contextlib.suppress(ValueError):
            self._enabled_requirements.remove(requirement)

    @property
    def enabled_requirements(self) -> list[Requirement]:
        return self._enabled_requirements

    @property
    def disabled_requirements(self) -> list[Requirement]:
        return self._disabled_requirements

    def enable_capability(self, capability: Capability) -> None:
        """
        Enable a given capability on this engine.

        Args:
            capability (Capability): A `Capability` to be enabled
        """
        self._enabled_capabilities.append(capability)
        with contextlib.suppress(ValueError):
            self._disabled_capabilities.remove(capability)

    def disable_capability(self, capability: Capability) -> None:
        """
        Disable a given capability on this engine.

        Args:
            capability (Capability): A `Capability` to be disabled
        """
        self._disabled_capabilities.append(capability)
        with contextlib.suppress(ValueError):
            self._enabled_capabilities.remove(capability)

    @property
    def enabled_capabilities(self) -> list[Capability]:
        return self._enabled_capabilities

    @property
    def disabled_capabilities(self) -> list[Capability]:
        return self._disabled_capabilities

    def enable_feature(self, feature: Feature) -> None:
        """
        Enable a given feature on this engine.

        Args:
            feature (Feature): A `Feature` to be enabled
        """
        self._enabled_features.append(feature)
        with contextlib.suppress(ValueError):
            self._disabled_features.remove(feature)

    def disable_feature(self, feature: Feature) -> None:
        """
        Disable a given feature on this engine.

        Args:
            feature (Feature): A `Feature` to be disabled
        """
        self._disabled_features.append(feature)
        with contextlib.suppress(ValueError):
            self._enabled_features.remove(feature)

    @property
    def enabled_features(self) -> list[Feature]:
        return self._enabled_features

    @property
    def disabled_features(self) -> list[Feature]:
        return self._disabled_features

    def enable_profile(self, profile: Profile) -> None:
        """
        Enable a given profile on this engine.

        Args:
            profile (Profile): A `Profile` to be enabled
        """
        self._enabled_profiles.append(profile)
        with contextlib.suppress(ValueError):
            self._disabled_profiles.remove(profile)

    def enable_profile_detection(self) -> None:
        """Enable all registered profiles for compliance evaluation.

        After calling this, a normal ``validate()`` call will populate
        ``result.context.profiles`` with a :py:class:`ProfileStatus`
        (PASS/FAIL) for every registered profile.
        """
        for profile in ProfileRegistry().latest_values():
            self.enable_profile(profile)

    def disable_profile(self, profile: Profile) -> None:
        """
        Disable a given profile on this engine.

        Args:
            profile (Profile): A `Profile` to be disabled
        """
        self._disabled_profiles.append(profile)
        with contextlib.suppress(ValueError):
            self._enabled_profiles.remove(profile)

    @property
    def enabled_profiles(self) -> list[Profile]:
        return self._enabled_profiles

    @property
    def disabled_profiles(self) -> list[Profile]:
        return self._disabled_profiles

    @property
    def _direct_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            A list of rules that are enabled directly on this engine.
        """
        rules: set[type[BaseRuleChecker]] = set()
        rules |= set(self.initialized_rules) if self.init_rules else set()
        rules |= set(self.enabled_rules)
        rules -= set(self.disabled_rules)
        return list(rules)

    @property
    def _direct_requirements(self) -> list[Requirement]:
        """
        Returns:
            A list of requirements that are enabled directly on this engine.
        """
        requirements: dict[tuple[str, str], Requirement] = {}

        for req in self.enabled_requirements:
            requirements[(req.code, req.version)] = req
        for capability in self.enabled_capabilities:
            for req in capability.requirements:
                requirements[(req.code, req.version)] = req
        for feature in self.enabled_features:
            for req in feature.requirements:
                requirements[(req.code, req.version)] = req
        for profile in self.enabled_profiles:
            for capability in profile.capabilities:
                for req in capability.requirements:
                    requirements[(req.code, req.version)] = req

        for req in self.disabled_requirements:
            requirements.pop((req.code, req.version), None)
        for capability in self.disabled_capabilities:
            for req in capability.requirements:
                requirements.pop((req.code, req.version), None)
        for feature in self.disabled_features:
            for req in feature.requirements:
                requirements.pop((req.code, req.version), None)
        for profile in self.disabled_profiles:
            for capability in profile.capabilities:
                for req in capability.requirements:
                    requirements.pop((req.code, req.version), None)
        return list(requirements.values())

    @property
    def rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            A list of rules that are enabled on this engine.
        """
        rules: set[type[BaseRuleChecker]] = set(self._direct_rules)
        rules |= set(RequirementsRegistry().get_validators(self._direct_requirements))
        return list(rules)

    @property
    def requirements(self) -> list[Requirement]:
        """
        Returns:
            A list of requirements that are enabled on this engine.
        """
        requirements: dict[tuple[str, str], Requirement] = {
            (req.code, req.version): req for req in self._direct_requirements
        }
        registry: RequirementsRegistry = RequirementsRegistry()
        for rule in self._direct_rules:
            for req in registry.get_requirements(rule):
                requirements[(req.code, req.version)] = req
        return list(requirements.values())

    @property
    def predicate(self) -> IssuePredicate:
        """
        Returns:
            A predicate that filters issues by enabled requirements and rules.
        """
        rules: set[type[BaseRuleChecker]] = set(self._direct_rules)
        requirements: set[tuple[str, str | None]] = set((req.code, req.version) for req in self._direct_requirements)

        def predicate(issue: Issue) -> bool:
            if issue.severity is IssueSeverity.ERROR:
                return True
            if issue.rule is not None:
                if issue.rule in rules:
                    return True
                elif issue.requirement is not None:
                    return (issue.requirement.code, issue.requirement.version) in requirements
                else:
                    return False
            return True

        return predicate

    def validate(self, asset: AssetType) -> Results:
        """
        Run the enabled rules on the given asset. **(Blocking version)**

        .. note::
            Validation of folders/container URIs is not supported in the blocking version. Use
            :py:meth:`validate_async` or :py:meth:`validate_with_callbacks` to recursively validate a folder.

        Args:
            asset (AssetType): A single Asset pointing to a file URI or a live `Usd.Stage`.

        Returns:
            All issues reported by the enabled rules.
        """
        desc: str = self.describe(asset)

        if isinstance(asset, Usd.Stage):
            return self._validate(asset)

        if not self._resolver.is_uri_found(asset):
            return self._access_failure(asset)

        if self._resolver.is_uri_prefix(asset):
            raise RuntimeError(
                "ValidationEngine: Synchronous validation of folders/containers is not available. "
                "Use `validate_async` or `validate_with_callbacks`"
            )

        if not self.is_asset_supported(asset):
            return Results(
                asset=desc,
                issues=[
                    Issue(
                        severity=IssueSeverity.ERROR,
                        message=f'"{desc}" is not a readable USD file and has no registered format handler.',
                    )
                ],
            )

        return self._validate(asset)

    async def validate_async(self, asset: AssetType) -> ResultsList:
        """
        Asynchronously run the enabled rules on the given asset. **(Concurrent Version)**

        If the asset is a folder/container URI it will be recursively searched for individual asset files and each
        applicable URI will be validated, with all results accumulated and indexed alongside the respective asset.

        .. note::
            Even a single asset will return a list of :py:class:`Results`, so it must be indexed via
            `results[0].asset`, `results[0].failures`, etc

        Args:
            asset (AssetType): A single Asset. Note this can be a file URI, folder/container URI,
            or a live `Usd.Stage`.

        Returns:
            All issues reported by the enabled rules, index aligned with their respective asset.
        """
        if isinstance(asset, Usd.Stage):
            result: Results = await self._validate_async(asset=asset, asset_progress_fn=None)
            results_list = ResultsList(results=[result])
            return dataclasses.replace(results_list, context=self.build_context(results_list))

        if not self._resolver.is_uri_found(asset):
            result: Results = self._access_failure(asset)
            return ResultsList(results=[result])

        all_assets = await self._check_entry(asset)
        return await self._validate_all_async(all_assets=all_assets, asset_validated_fn=None, asset_progress_fn=None)

    def validate_with_callbacks(
        self,
        asset: AssetType,
        asset_located_fn: AssetLocatedCallback | None = None,
        asset_validated_fn: AssetValidatedCallback | None = None,
        asset_progress_fn: AssetProgressCallback | None = None,
    ) -> asyncio.Task:
        """
        Asynchronously run the enabled rules on the given asset. **(Callbacks Version)**

        If the asset is validate-able (e.g. a USD layer file), `asset_located_fn` will be invoked before validation
        begins. When validation completes, `asset_validated_fn` will be invoked with the results.

        If the asset is a folder/container URI it will be recursively searched for individual asset files and each
        applicable URL will be validated, with `asset_located_fn` and `asset_validated_fn` being invoked once per
        validate-able asset.

        Args:
            asset: A single Asset. Note this can be a file URI, folder/container URI, or a live `Usd.Stage`.
            asset_located_fn: A callable to be invoked upon locating an individual asset. If `asset` is a single
                validate-able asset (e.g. a USD layer file) `asset_located_fn` will be called once. If `asset` is a
                folder/container URI `asset_located_fn` will be called once per validate-able asset within the container
                (e.g. once per USD layer file). Signature must be `cb(AssetType)` where str is the url of the located asset.
            asset_validated_fn: A callable to be invoked when validation of an individual asset has completed. If `asset`
                is itself a single validate-able asset (e.g. a USD layer file) `asset_validated_fn` will be called once.
                If `asset` is a folder/container `asset_validated_fn` will be called once per validate-able asset within
                the container (e.g. once per USD layer file). Signature must be `cb(results)`.
            asset_progress_fn: A callable to be invoked when validation of an individual asset is running.

        Returns:
            A task to control execution.
        """
        return self._run_in_background(
            coroutine=self._validate_with_callbacks_async(
                asset=asset,
                asset_located_fn=asset_located_fn,
                asset_progress_fn=asset_progress_fn,
                asset_validated_fn=asset_validated_fn,
            )
        )

    def _validate(self, asset: AssetType) -> Results:
        checker: ComplianceChecker = self._create_compliance_checker()
        if not checker.rules:
            return Results.create(
                asset=asset,
                issues=[
                    *checker.GetIssues(),
                    Issue(severity=IssueSeverity.ERROR, message="No rules or requirements have been enabled."),
                ],
            )
        desc: str = self.describe(asset)
        try:
            checker.check(asset)
        except Exception:
            return Results.create(
                asset=asset,
                issues=[
                    *checker.GetIssues(),
                    Issue(
                        severity=IssueSeverity.ERROR,
                        message=f'Failed to Open "{desc}". See traceback for details.\n{traceback.format_exc()}',
                    ),
                ],
            )
        else:
            result = Results.create(
                asset=asset,
                issues=checker.GetIssues(),
            ).filter_by(self.predicate)
            return dataclasses.replace(result, context=self.build_context(result))

    @singledispatchmethod
    def build_context(self, results) -> ValidationContext | None:
        """Build a typed validation context summarising pass/fail for every enabled
        profile, feature, and requirement.

        Returns ``None`` when no profile/feature/capability scope is active so that
        callers can skip structured output entirely for plain rule-based validation.

        Args:
            results: Validation results to evaluate against enabled profiles/features.
        """
        raise NotImplementedError(f"Unknown type {type(results)}")

    @build_context.register
    def _(self, results: Results) -> ValidationContext | None:
        """Build context for a single asset, collecting failed requirements from its issues."""
        failed_requirements: dict[tuple[str, str | None], Requirement] = {}
        for issue in results.issues:
            if issue.severity not in (IssueSeverity.FAILURE, IssueSeverity.ERROR):
                continue
            if requirement := issue.requirement:
                failed_requirements[(requirement.code, requirement.version)] = requirement
        return ValidationContext.build(
            enabled_profiles=self.enabled_profiles,
            enabled_features=self.enabled_features,
            enabled_capabilities=self.enabled_capabilities,
            failed_requirements=failed_requirements.values(),
        )

    @build_context.register
    def _(self, results: ResultsList) -> ValidationContext | None:
        """Build aggregate context for a batch, unioning failed requirements across all assets."""
        failed_requirements: dict[tuple[str, str | None], Requirement] = {}
        for result in results:
            per_context = self.build_context(result)
            if per_context is None:
                continue
            for req in per_context.failed_requirements:
                failed_requirements[(req.code, req.version)] = req
        return ValidationContext.build(
            enabled_profiles=self.enabled_profiles,
            enabled_features=self.enabled_features,
            enabled_capabilities=self.enabled_capabilities,
            failed_requirements=failed_requirements.values(),
        )

    def stamp_asset(self, asset: AssetType, results: Results, *, key: str = "asset_validator") -> Sdf.Layer | None:
        """Stamp the USD asset's customLayerData with validation profile metadata.

        Only stamps when profiles are enabled and validation produced no
        FAILURE or ERROR issues. Skips silently otherwise.

        Args:
            asset: The asset to stamp (Usd.Stage or file path).
            results: Validation results to check for pass/fail.
            key: The top-level key in customLayerData to write under.
                Configurable to allow different consumers (e.g. "SimReady_Metadata").

        Returns:
            The :class:`Sdf.Layer` that was stamped, or ``None`` if stamping was
            skipped (no profiles enabled, validation failures, or unresolvable asset).
            Callers are responsible for saving the layer if persistence is required.
        """
        if not self.enabled_profiles:
            return None

        has_failures = any(issue.severity in (IssueSeverity.FAILURE, IssueSeverity.ERROR) for issue in results.issues)
        if has_failures:
            logger.info("Skipping stamp: validation has failures.")
            return None

        if isinstance(asset, Usd.Stage):
            layer = asset.GetRootLayer()
        elif isinstance(asset, str):
            layer = Sdf.Layer.FindOrOpen(asset)
        else:
            layer = None

        if layer is None:
            logger.warning(f"Skipping stamp: could not resolve layer for '{asset}'.")
            return None

        profiles_data = {p.id: {"profile_version": str(p.version)} for p in self.enabled_profiles}

        plugin_versions = {p.distribution_name: p.version for p in PluginManager().loaded_plugins}

        custom_data = layer.customLayerData
        custom_data[key] = {
            "validation": {
                "profiles": profiles_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "validator_version": __version__,
                "plugins": plugin_versions,
            }
        }
        layer.customLayerData = custom_data
        profile_ids = list(profiles_data.keys())
        logger.info(f"Stamped asset with profiles {profile_ids}")
        return layer

    async def _validate_async(self, asset: AssetType, asset_progress_fn: AssetProgressCallback | None) -> Results:
        asset_describe: str = self.describe(asset)
        checker: ComplianceChecker = self._create_compliance_checker()

        @lru_cache(maxsize=1)
        def report_progress(value: float) -> None:
            if asset_progress_fn is not None:
                results: Results = Results.create(asset=asset, issues=checker.partial_issues)
                asset_progress_fn(
                    AssetProgress(
                        asset=asset_describe,
                        progress=value,
                        results=results.filter_by(self.predicate),
                    )
                )

        try:
            if not checker.rules:
                message: str = "No rules or requirements have been enabled."
                return Results.create(
                    asset=asset,
                    issues=[*checker.GetIssues(), Issue(severity=IssueSeverity.ERROR, message=message)],
                )
            await checker.check_async(asset, callback=report_progress if asset_progress_fn else None)
        except Exception:
            message: str = f'Failed to Open "{asset_describe}". See traceback for details.\n{traceback.format_exc()}'
            return Results.create(
                asset=asset,
                issues=[*checker.GetIssues(), Issue(severity=IssueSeverity.ERROR, message=message)],
            )
        else:
            result: Results = Results.create(asset=asset, issues=checker.GetIssues()).filter_by(self.predicate)
            return dataclasses.replace(result, context=self.build_context(result))
        finally:
            report_progress(1.0)

    def _run_in_background(self, coroutine: Coroutine) -> asyncio.Task:
        # Enqueue a coroutine. Save reference, to avoid a task disappearing mid-execution.
        task: asyncio.Task = asyncio.ensure_future(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _call_async(self, callback: Callable[[T], None] | None, arg: T) -> None:
        # run_in_executor to avoid blocking.
        if not callback:
            return
        await asyncio.to_thread(callback, arg)

    async def _validate_all_async(
        self,
        all_assets: list[AssetType],
        asset_progress_fn: AssetProgressCallback | None,
        asset_validated_fn: AssetValidatedCallback | None,
    ) -> ResultsList:
        results: list[Results] = []
        for asset in all_assets:
            result: Results = await self._validate_async(asset=asset, asset_progress_fn=asset_progress_fn)
            await self._call_async(asset_validated_fn, result)
            results.append(result)
        results_list = ResultsList(results=results)
        results_list = dataclasses.replace(results_list, context=self.build_context(results_list))
        return results_list

    async def _validate_with_callbacks_async(
        self,
        asset: AssetType,
        asset_located_fn: AssetLocatedCallback | None,
        asset_progress_fn: AssetProgressCallback | None,
        asset_validated_fn: AssetValidatedCallback | None,
    ) -> ResultsList:
        if isinstance(asset, Usd.Stage):
            await self._call_async(asset_located_fn, asset)
            result: Results = await self._validate_async(asset=asset, asset_progress_fn=asset_progress_fn)
            await self._call_async(asset_validated_fn, result)
            results_list = ResultsList(results=[result])
            results_list = dataclasses.replace(results_list, context=self.build_context(results_list))
            return results_list
        else:
            result: ResultsList | None = await self._access_failure_with_callbacks(
                asset, asset_located_fn, asset_progress_fn, asset_validated_fn
            )
            if result is not None:
                return result
            all_assets = await self._check_entry(asset, asset_located_fn=asset_located_fn)
            return await self._validate_all_async(all_assets, asset_progress_fn, asset_validated_fn)

    async def _access_failure_with_callbacks(
        self,
        url: str,
        asset_located_fn: AssetLocatedCallback | None,
        asset_progress_fn: AssetProgressCallback | None,
        asset_validated_fn: AssetValidatedCallback | None,
    ) -> ResultsList | None:
        if not self._resolver.is_uri_found(url):
            result: Results = self._access_failure(url)
            await self._call_async(asset_located_fn, url)
            await self._call_async(asset_progress_fn, AssetProgress(asset=url, progress=1.0))
            await self._call_async(asset_validated_fn, result)
            return ResultsList(results=[result])
        return None

    async def _check_entry(self, url: str, asset_located_fn: AssetLocatedCallback | None = None) -> list[str]:
        if self._resolver.is_uri_found(url):
            if self.is_asset_supported(url):
                await self._call_async(asset_located_fn, url)
                return [url]
            elif self._resolver.is_uri_prefix(url):
                return await self._check_children(url, asset_located_fn)
            else:
                return []
        else:
            return []

    async def _check_children(self, url: str, asset_located_fn: AssetLocatedCallback | None) -> list[str]:
        all_assets: list[str] = []
        for entry_url in self._resolver.list_uris(url):
            assets: list[str] = await self._check_entry(entry_url, asset_located_fn)
            all_assets.extend(assets)
        return all_assets

    @classmethod
    def _access_failure(cls, url: str) -> Results:
        return Results.create(
            asset=url, issues=[Issue(severity=IssueSeverity.ERROR, message=f'Accessing "{url}" failed')]
        )

    def _create_compliance_checker(self) -> ComplianceChecker:
        checker = ComplianceChecker(
            stats=self.stats,
            skip_variants=not self.variants,
            parameters=self.parameters,
            resolver=self._resolver,
        )
        for rule in self.rules:
            checker.AddRule(rule)
        return checker

    @property
    def stats(self) -> ValidationStats:
        """
        Returns
            Statistics about each validation run.
        """
        return self._stats

    @deprecated("Use ValidationEngine.enable_rule instead")
    def enableRule(self, rule: type[BaseRuleChecker]) -> None:
        self.enable_rule(rule)

    @deprecated("Use ValidationEngine.disable_rule instead")
    def disableRule(self, rule: type[BaseRuleChecker]) -> None:
        self.disable_rule(rule)

    @classmethod
    @deprecated("Use ValidationEngine.is_asset_supported instead")
    def isAssetSupported(cls, asset: AssetType) -> bool:
        return cls.is_asset_supported(asset)
