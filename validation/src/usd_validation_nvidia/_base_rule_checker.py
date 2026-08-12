#
# Copyright 2018 Pixar
# Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import inspect
from collections.abc import Sequence

from ._asset_format import FormatDependency
from ._identifiers import AtType
from ._issues import Issue, IssueSeverity, Suggestion
from ._parameters import ParameterMapping
from ._requirements import Requirement
from .capabilities import RequirementRefProtocol

__all__ = [
    "BaseRuleChecker",
]


class BaseRuleChecker:
    """This is Base class for all the rule-checkers.

    Args:
        verbose: Deprecated parameter, kept for backward compatibility. Not used in new rules.
        consumerLevelChecks: Deprecated parameter, kept for backward compatibility. Not used in new rules.
        assetLevelChecks: Deprecated parameter, kept for backward compatibility. Not used in new rules.
        parameters: Optional ParameterMapping instance containing rule checker configuration.
    """

    def __init__(
        self,
        verbose: bool = False,
        consumerLevelChecks: bool = False,
        assetLevelChecks: bool = True,
        *args,
        parameters: ParameterMapping | None = None,
        **kwargs,
    ):
        """
        Args:
            verbose: Deprecated parameter, kept for backward compatibility with existing rules.
            consumerLevelChecks: Deprecated parameter, kept for backward compatibility with existing rules.
            assetLevelChecks: Deprecated parameter, kept for backward compatibility with existing rules.
            parameters: Optional ParameterMapping instance containing rule checker configuration.
        """
        self._verbose = verbose
        self._consumerLevelChecks = consumerLevelChecks
        self._assetLevelChecks = assetLevelChecks
        self._parameters = parameters or ParameterMapping()

        # Initialize issues list
        self._issues = []

    def _AddIssue(self, issue: Issue) -> None:
        self._issues.append(issue)

    def _AddFailedCheck(
        self,
        message: str | None = None,
        at: AtType | list[AtType] | None = None,
        suggestion: Suggestion | None = None,
        code: str | None = None,
        requirement: Requirement | RequirementRefProtocol | None = None,
        suggestions: list[Suggestion] | None = None,
    ) -> None:
        self._AddIssue(
            Issue(
                message=message,
                severity=IssueSeverity.FAILURE,
                rule=self.__class__,
                at=at,
                suggestion=suggestion,
                suggestions=suggestions,
                code=code,
                requirement=requirement,
            )
        )

    def _AddError(
        self,
        message: str | None = None,
        at: AtType | list[AtType] | None = None,
        suggestion: Suggestion | None = None,
        code: str | None = None,
        requirement: Requirement | RequirementRefProtocol | None = None,
        suggestions: list[Suggestion] | None = None,
    ) -> None:
        self._AddIssue(
            Issue(
                message=message,
                severity=IssueSeverity.ERROR,
                rule=self.__class__,
                at=at,
                suggestion=suggestion,
                suggestions=suggestions,
                code=code,
                requirement=requirement,
            )
        )

    def _AddWarning(
        self,
        message: str | None = None,
        at: AtType | list[AtType] | None = None,
        suggestion: Suggestion | None = None,
        code: str | None = None,
        requirement: Requirement | RequirementRefProtocol | None = None,
        suggestions: list[Suggestion] | None = None,
    ) -> None:
        self._AddIssue(
            Issue(
                message=message,
                severity=IssueSeverity.WARNING,
                rule=self.__class__,
                at=at,
                suggestion=suggestion,
                suggestions=suggestions,
                code=code,
                requirement=requirement,
            )
        )

    def _AddInfo(
        self,
        message: str | None = None,
        at: AtType | list[AtType] | None = None,
        code: str | None = None,
        requirement: Requirement | RequirementRefProtocol | None = None,
    ) -> None:
        self._AddIssue(
            Issue(
                message=message,
                severity=IssueSeverity.INFO,
                rule=self.__class__,
                at=at,
                code=code,
                requirement=requirement,
            )
        )

    def GetIssues(self) -> Sequence[Issue]:
        return self._issues

    @property
    def parameters(self) -> ParameterMapping:
        """Access the ParameterMapping instance containing rule checker configuration.

        Returns:
            The ParameterMapping instance (never None; defaults to empty ParameterMapping if not provided).
        """
        return self._parameters

    @classmethod
    def GetDescription(cls):
        """Returns the docstring describing the rule."""
        if not cls.__doc__:
            return f"Docstring not found for rule class {cls.__name__}."
        return inspect.cleandoc(cls.__doc__)

    # -------------------------------------------------------------------------
    # Virtual methods that any derived rule-checker may want to override.
    # Default implementations do nothing.
    #
    # A rule-checker may choose to override one or more of the virtual methods.
    # The callbacks are invoked in the order they are defined here (i.e.
    # CheckStage is invoked first, followed by CheckDiagnostics, followed by
    # CheckUnresolvedPaths and so on until CheckPrim). Some of the callbacks may
    # be invoked multiple times per-rule with different parameters, for example,
    # CheckLayer, CheckPrim and CheckZipFile.

    def CheckStage(self, usdStage):
        """Check the given usdStage."""
        pass

    def CheckDiagnostics(self, diagnostics):
        """Check the diagnostic messages that were generated when opening the
        USD stage. The diagnostic messages are collected using a
        UsdUtilsCoalescingDiagnosticDelegate.
        """
        pass

    def CheckUnresolvedPaths(self, unresolvedPaths):
        """Check or process any unresolved asset paths that were found when
        analysing the dependencies.
        """
        pass

    def CheckDependencies(self, usdStage, layerDeps, assetDeps):
        """Check usdStage's layer and asset dependencies that were gathered
        using UsdUtils.ComputeAllDependencies().
        """
        pass

    def CheckLayer(self, layer):
        """Check the given SdfLayer."""
        pass

    def CheckZipFile(self, zipFile, packagePath):
        """Check the zipFile object created by opening the package at path
        packagePath.
        """
        pass

    def CheckFormatDependency(self, dependency: FormatDependency):
        """Check a single dependency returned by an :py:class:`~usd_validation_nvidia.AssetFormat` handler.

        Called once per path in the flat list produced by :py:meth:`~usd_validation_nvidia.AssetFormat.get_dependencies`.
        """
        pass

    def CheckPrim(self, prim):
        """Check the given prim, which may only exist is a specific combination
        of variant selections on the UsdStage.
        """
        pass

    def ResetCaches(self):
        """Reset any caches the rule owns.  Called whenever stage authoring
        occurs, such as when we iterate through VariantSet combinations.
        """
        pass
