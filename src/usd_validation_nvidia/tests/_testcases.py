# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Sdf, Usd

from .._assets import AssetType
from .._base_rule_checker import BaseRuleChecker
from .._capabilities import Capability
from .._deprecate import deprecated
from .._engine import ValidationEngine
from .._examples import ExampleResult
from .._fix import FixStatus, IssueFixer
from .._issues import IssuePredicate
from .._parameters import ParameterMapping, UserParameter
from .._requirements import Requirement
from .._results import Results
from ._assertions import IsAFailure, IsAnAsset, IsAnIssue

__all__ = [
    "AsyncioValidationTestCaseMixin",
    "ValidationTestCaseMixin",
]


class ValidationTestCaseMixin:
    """
    A mixin for test cases to simplify testing of individual Validation Rules.

    Example:
        .. code-block:: python

            from unittest import TestCase
            from usd_validation_nvidia.tests import ValidationTestCaseMixin

            class ValidationTestCase(TestCase, ValidationTestCaseMixin):
                ...

            class MyTestCase(ValidationTestCase):
                def testMyRuleChecker(self):
                    self.assertRule(
                        asset='example.usd',
                        rule=MyRuleChecker,
                        asserts=[
                            IsAFailure("Prim.*has unsupported type.*"),
                        ]
                    )
    """

    def validate(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
    ) -> Results:
        """
        Validate the asset using the rule.

        Args:
            asset: The asset to validate.
            rule: The rule to use for validation.

        Returns:
            The results of the validation.
        """
        engine = ValidationEngine(init_rules=False)
        if rule:
            engine.enable_rule(rule)
        elif requirement:
            engine.enable_requirement(requirement)
        elif capability:
            engine.enable_capability(capability)
        return engine.validate(asset)

    def assertIssues(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        asserts: list[IsAnIssue],
    ) -> None:
        """Assert issues from validating one asset using either a rule, requirement or capability.

        Derived classes may use this to simplify testing of new rules with less consideration for
        the structure of `usd_validation_nvidia.Results`.

        Note there will be only one enabled rule for the validation run, so all results will have necessarily
        been produced by the provided rule or by the engine itself (eg non-existent file).

        Args:
            asset: A single asset to validate
            rule: Either a BaseRuleChecker derived class or the str class name of such a class
            asserts: A list of assertions.
        """
        result: Results = self.validate(asset=asset, rule=rule, requirement=requirement, capability=capability)
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertEqual(len(result.issues()), len(asserts), "Different number of actual and expected issues.")
        for assertion, issue in zip(asserts, result.issues()):
            self.assertEqual(assertion, issue, f"Expected {assertion} but got {issue}.")

    def assertRule(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker],
        asserts: list[IsAnIssue],
    ) -> None:
        """Assert issues from validating one asset using one rule"""
        self.assertIssues(asset=asset, rule=rule, asserts=asserts)

    def assertRequirement(
        self,
        *,
        asset: AssetType,
        requirement: Requirement,
        asserts: list[IsAnIssue],
    ) -> None:
        """Assert issues from validating one asset using one requirement"""
        self.assertIssues(asset=asset, requirement=requirement, asserts=asserts)

    def assertCapability(
        self,
        *,
        asset: AssetType,
        capability: Capability,
        asserts: list[IsAnIssue],
    ) -> None:
        """Assert issues from validating one asset using one capability"""
        self.assertIssues(asset=asset, capability=capability, asserts=asserts)

    def assertSuccess(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
    ) -> None:
        """
        Assert that the asset is validated successfully.
        """
        result: Results = self.validate(asset=asset, rule=rule, requirement=requirement, capability=capability)
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertFalse(result.issues(predicate), "There are issues found in the asset.")

    def assertFailure(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
    ) -> None:
        """
        Assert that the asset is validated with failures.
        """
        result: Results = self.validate(asset=asset, rule=rule, requirement=requirement, capability=capability)
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertTrue(result.issues(predicate), "There are no issues found in the asset.")

    @deprecated("Use assertRule instead")
    def assertRuleFailures(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker],
        expectedFailures: list[IsAFailure],
    ) -> None:
        self.assertRule(asset=asset, rule=rule, asserts=expectedFailures)

    def assertSuggestion(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
    ) -> None:
        """Assert expected failures from validating one asset using one rule will be fixed using auto fix framework.

        Derived classes may use this to simplify testing of new rules with less consideration for
        the structure of `usd_validation_nvidia.IssueFixer`.

        Note there will be only one enabled rule for the validation run, so all results will have necessarily
        been produced by the provided rule or by the engine itself (eg non-existent file).

        Args:
            asset: A single asset to validate
            rule: Either a BaseRuleChecker derived class or the str class name of such a class
            predicate: A predicate (i.e. Callable[[Issue], bool]) to filter out issues.
        """
        stage: Usd.Stage = Usd.Stage.Open(asset) if isinstance(asset, str) else asset
        session_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(session_layer.identifier)

        try:
            self.assertFailure(
                asset=stage, rule=rule, requirement=requirement, capability=capability, predicate=predicate
            )

            # Perform fixing
            result = self.validate(asset=stage, rule=rule, requirement=requirement, capability=capability)
            fixer = IssueFixer(stage)
            results = fixer.fix_at(result.issues(predicate), session_layer)
            for result in results:
                self.assertEqual(result.status, FixStatus.SUCCESS, msg=result.exception)

            self.assertSuccess(
                asset=stage, rule=rule, requirement=requirement, capability=capability, predicate=predicate
            )
        finally:
            stage.GetSessionLayer().subLayerPaths.remove(session_layer.identifier)

    def assertExamples(
        self,
        *,
        requirement: Requirement,
    ) -> None:
        """
        Assert the examples of a requirement.

        Implementation is validated against the examples of the requirement.

        Args:
            requirement: The requirement to assert the examples of.
        """
        for example in requirement.examples:
            layer: Sdf.Layer | None = None
            try:
                layer = Sdf.Layer.CreateAnonymous(f"{example.name}.usd")
                layer.ImportFromString(example.snippet.content)
            except Exception as e:
                raise ValueError(f"Error importing example: {example.name}") from e
            stage: Usd.Stage = Usd.Stage.Open(layer)
            if example.result == ExampleResult.SUCCESS:
                self.assertSuccess(asset=stage, requirement=requirement)
            else:
                self.assertFailure(asset=stage, requirement=requirement)


class AsyncioValidationTestCaseMixin:
    """
    A mixin for asyncio test cases to simplify testing of individual Validation Rules.

    Example:
        .. code-block:: python

            from unittest import IsolatedAsyncioTestCase
            from usd_validation_nvidia.tests import AsyncioValidationTestCaseMixin

            class AsyncioValidationTestCase(IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin):
                ...

            class MyTestCase(AsyncioValidationTestCase):
                async def testMyRuleChecker(self):
                    await self.assertRuleAsync(
                        asset='example.usd',
                        rule=MyRuleChecker,
                        asserts=[
                            IsAFailure("Prim.*has unsupported type.*"),
                        ]
                    )
    """

    async def validateAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        parameters: dict[str, int | float | bool | str] | None = None,
    ) -> Results:
        """
        Validate the asset using the rule.
        """
        engine = ValidationEngine(init_rules=False)
        if rule:
            engine.enable_rule(rule)
        if requirement:
            engine.enable_requirement(requirement)
        if capability:
            engine.enable_capability(capability)
        if parameters:
            engine_parameters: ParameterMapping = engine.parameters
            for name, value in parameters.items():
                engine.add_parameter(UserParameter(parameter=engine_parameters[name], assigned_value=value))

        results: list[Results] = await engine.validate_async(asset)
        return results[0]

    async def assertIssuesAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        asserts: list[IsAnIssue],
    ) -> None:
        """
        Same as assertIssues, but for async tests.
        """
        result: Results = await self.validateAsync(
            asset=asset, rule=rule, requirement=requirement, capability=capability
        )
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertEqual(len(result.issues()), len(asserts), "Different number of actual and expected issues.")
        for assertion, issue in zip(asserts, result.issues()):
            self.assertEqual(assertion, issue, f"Expected {assertion} but got {issue}.")

    async def assertRuleAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker],
        asserts: list[IsAnIssue],
    ) -> None:
        """
        Same as assertRule, but for async tests.
        """
        await self.assertIssuesAsync(asset=asset, rule=rule, asserts=asserts)

    async def assertRequirementAsync(
        self,
        *,
        asset: AssetType,
        requirement: Requirement,
        asserts: list[IsAnIssue],
    ) -> None:
        """Same as assertRequirement, but for async tests."""
        await self.assertIssuesAsync(asset=asset, requirement=requirement, asserts=asserts)

    async def assertCapabilityAsync(
        self,
        *,
        asset: AssetType,
        capability: Capability,
        asserts: list[IsAnIssue],
    ) -> None:
        """Same as assertCapability, but for async tests."""
        await self.assertIssuesAsync(asset=asset, capability=capability, asserts=asserts)

    async def assertSuccessAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
        parameters: dict[str, int | float | bool | str] | None = None,
    ) -> None:
        """
        Same as assertSuccess, but for async tests.
        """
        result: Results = await self.validateAsync(
            asset=asset, rule=rule, requirement=requirement, capability=capability, parameters=parameters
        )
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertFalse(result.issues(predicate), "There are issues found in the asset.")

    async def assertFailureAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
    ) -> None:
        """
        Same as assertFailure, but for async tests.
        """
        result: Results = await self.validateAsync(
            asset=asset, rule=rule, requirement=requirement, capability=capability
        )
        self.assertEqual(IsAnAsset(asset), result.asset)
        self.assertTrue(result.issues(predicate), "There are no issues found in the asset.")

    async def assertSuggestionAsync(
        self,
        *,
        asset: AssetType,
        rule: type[BaseRuleChecker] | None = None,
        requirement: Requirement | None = None,
        capability: Capability | None = None,
        predicate: IssuePredicate | None = None,
    ) -> None:
        """
        Same as assertSuggestion, but for async tests.
        """
        stage: Usd.Stage = Usd.Stage.Open(asset) if isinstance(asset, str) else asset
        session_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(session_layer.identifier)

        try:
            await self.assertFailureAsync(
                asset=stage, rule=rule, requirement=requirement, capability=capability, predicate=predicate
            )

            # Perform fixing
            result: Results = await self.validateAsync(
                asset=stage, rule=rule, requirement=requirement, capability=capability
            )
            fixer = IssueFixer(stage)
            fix_results = fixer.fix_at(result.issues(predicate), session_layer)
            for fix_result in fix_results:
                self.assertEqual(fix_result.status, FixStatus.SUCCESS, msg=fix_result.exception)

            await self.assertSuccessAsync(
                asset=stage, rule=rule, requirement=requirement, capability=capability, predicate=predicate
            )
        finally:
            stage.GetSessionLayer().subLayerPaths.remove(session_layer.identifier)

    async def assertExamplesAsync(
        self,
        *,
        requirement: Requirement,
    ) -> None:
        """
        Same as assertExamples, but for async tests.
        """
        for example in requirement.examples:
            layer: Sdf.Layer | None = None
            try:
                layer = Sdf.Layer.CreateAnonymous(f"{example.name}.usd")
                layer.ImportFromString(example.snippet.content)
            except Exception as e:
                raise ValueError(f"Error importing example: {example.name}") from e
            stage: Usd.Stage = Usd.Stage.Open(layer)
            if example.result == ExampleResult.SUCCESS:
                await self.assertSuccessAsync(asset=stage, requirement=requirement)
            else:
                await self.assertFailureAsync(asset=stage, requirement=requirement)

    async def assertExamplesSuggestionsAsync(
        self,
        *,
        requirement: Requirement,
    ) -> None:
        """
        Same as assertExamplesAsync, but failure examples are asserted via assertSuggestionAsync
        (i.e. failures must have a working fix that yields success).
        """
        for example in requirement.examples:
            layer: Sdf.Layer | None = None
            try:
                layer = Sdf.Layer.CreateAnonymous(f"{example.name}.usd")
                layer.ImportFromString(example.snippet.content)
            except Exception as e:
                raise ValueError(f"Error importing example: {example.name}") from e
            stage: Usd.Stage = Usd.Stage.Open(layer)
            if example.result == ExampleResult.SUCCESS:
                await self.assertSuccessAsync(asset=stage, requirement=requirement)
            else:
                await self.assertSuggestionAsync(asset=stage, requirement=requirement)
