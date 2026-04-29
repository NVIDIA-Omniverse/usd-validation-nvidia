# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import pathlib
import re
from dataclasses import dataclass
from functools import singledispatchmethod

from pxr import Sdf, Usd

from .._assets import AssetType
from .._base_rule_checker import BaseRuleChecker
from .._deprecate import deprecated
from .._identifiers import Identifier
from .._issues import Issue, IssueSeverity
from .._requirements import Requirement

__all__ = [
    "Failure",
    "IsAFailure",
    "IsAWarning",
    "IsAnError",
    "IsAnInfo",
    "IsAnIssue",
]


@dataclass
class IsAnIssue:
    """
    IsAnIssue let us assert severity, message and locations of issues to match against the real issues found in
    Validation Engine. Use ``IsAFailure``, ``IsAWarning`` and ``IsAnError`` instead.

    Args:
        message: The expected message of the issue.
        at: Optional. The expected location of the issue.
        code: Optional. The expected code of the issue.
        requirement: Optional. The expected requirement of the issue.
        severity: Optional. The expected severity of the issue.
    """

    message: str | re.Pattern | None = None
    at: str | Sdf.Path | pathlib.Path | None = None
    code: str | None = None
    rule: type[BaseRuleChecker] | None = None
    requirement: Requirement | None = None
    severity: IssueSeverity = IssueSeverity.INFO

    @singledispatchmethod
    @classmethod
    def message_cmp(cls, lh, rh: str) -> bool:
        return lh == rh

    @message_cmp.register
    @classmethod
    def _(cls, lh: str, rh: str) -> bool:
        if lh != rh:
            return cls.message_cmp(re.compile(lh), rh)
        else:
            return True

    @message_cmp.register
    @classmethod
    def _(cls, lh: re.Pattern, rh: str) -> bool:
        return lh.match(rh) is not None

    @singledispatchmethod
    @classmethod
    def at_cmp(cls, lh, rh: Identifier) -> bool:
        return lh == rh

    @at_cmp.register
    @classmethod
    def _(cls, lh: str, rh: Identifier) -> bool:
        return lh == rh.as_str()

    @at_cmp.register
    @classmethod
    def _(cls, lh: Sdf.Path, rh: Identifier) -> bool:
        if hasattr(rh, "path"):
            return lh == rh.path
        else:
            return False

    @at_cmp.register
    @classmethod
    def _(cls, lh: pathlib.Path, rh: Identifier) -> bool:
        if hasattr(rh, "path") and isinstance(rh.path, str):
            return lh == pathlib.Path(rh.path)
        return False

    @classmethod
    def requirement_cmp(cls, lh: Requirement | None, rh: Requirement | None) -> bool:
        if lh is None and rh is None:
            return True
        if lh is None or rh is None:
            return False
        return (
            lh.code == rh.code
            and lh.display_name == rh.display_name
            and lh.message == rh.message
            and lh.path == rh.path
            and lh.tags == rh.tags
        )

    def __eq__(self, other: Issue) -> bool:
        return (
            self.message_cmp(self.message, other.message)
            and (self.at is None or self.at_cmp(self.at, other.at))
            and (self.code is None or self.code == other.code)
            and (self.rule is None or self.rule == other.rule)
            and (self.requirement is None or self.requirement_cmp(self.requirement, other.requirement))
            and self.severity == other.severity
        )


@dataclass(eq=False)
class IsAFailure(IsAnIssue):
    """
    IsAFailure let us assert messages and locations of failure to match against the real issue found in Validation
    Engine. This class is used in conjuntion to ValidationRuleTestCase.assertRule.

    Attributes:
        message: Regex pattern for the expected failure message.
        at: Optional. The expected location of the expected failure.
    """

    severity: IssueSeverity = IssueSeverity.FAILURE


@deprecated("Use IsAFailure instead")
class Failure(IsAFailure): ...


@dataclass(eq=False)
class IsAWarning(IsAnIssue):
    """
    IsAWarning let us assert messages and locations of warnings to match against the real issue found in Validation
    Engine. This class is used in conjuntion to ValidationRuleTestCase.assertRule.

    Attributes:
        message: Regex pattern for the expected failure message.
        at: Optional. The expected location of the expected failure.
    """

    severity: IssueSeverity = IssueSeverity.WARNING


@dataclass(eq=False)
class IsAnError(IsAnIssue):
    """
    IsAnError let us assert messages and locations of errors to match against the real issue found in Validation
    Engine. This class is used in conjuntion to ValidationRuleTestCase.assertRule.

    Attributes:
        message: Regex pattern for the expected failure message.
        at: Optional. The expected location of the expected failure.
    """

    severity: IssueSeverity = IssueSeverity.ERROR


@dataclass(eq=False)
class IsAnInfo(IsAnIssue):
    """
    IsAnInfo let us assert messages and locations of infos to match against the real info found in Validation
    Engine. This class is used in conjuntion to ValidationRuleTestCase.assertRule.

    Attributes:
        message: Regex pattern for the expected info message.
        at: Optional. The expected location of the expected info.
    """

    severity: IssueSeverity = IssueSeverity.INFO


@dataclass
class IsAnAsset:
    asset: AssetType

    @singledispatchmethod
    @classmethod
    def repr_asset(cls, asset: AssetType) -> str:
        return str(asset)

    @repr_asset.register
    @classmethod
    def _(cls, asset: Usd.Stage) -> str:
        return Usd.Describe(asset)

    @repr_asset.register
    @classmethod
    def _(cls, asset: str) -> str:
        return asset

    def __eq__(self, other: AssetType) -> bool:
        return self.repr_asset(self.asset) == self.repr_asset(other)
