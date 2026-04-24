# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import singledispatch

from pxr import Usd

from ._issues import Issue, IssuePredicate, IssuesList

__all__ = [
    "Results",
    "ResultsList",
]


@singledispatch
def to_issues_list(value: IssuesList | list[Issue]) -> IssuesList:
    raise NotImplementedError(f"Unknown type {type(value)}")


@dataclass
class Results(Sequence[Issue]):
    """A collection of :py:class:`Issue`.

    Provides convenience mechanisms to filter :py:class:`Issue` by :py:class:`IssuePredicates`.

    Attributes:
        asset (str): The asset.
        issues (list[Issue] | IssuesList): The issues.
    """

    asset: str
    issues: list[Issue] | IssuesList = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(self, "issues", to_issues_list(self.issues))

    @classmethod
    def create(cls, asset: Usd.Stage | str, issues: Sequence[Issue]) -> Results:
        """
        Convenience method. The only difference with constructor is that it will link the issues with the asset.

        Args:
            asset (Usd.Stage | str): The asset.
            issues (List[Issue]): A list of issues to associate with asset.

        Returns:
            A new Results object.
        """
        return Results(
            asset=Usd.Describe(asset) if isinstance(asset, Usd.Stage) else asset,
            issues=IssuesList(
                # suggestion=None avoids passing both suggestion and suggestions to Issue(),
                # which raises ValueError. After normalization, suggestions is the canonical
                # field, so clearing suggestion lets __post_init__ derive it from suggestions.
                issues=[dataclasses.replace(issue, suggestion=None, asset=asset) for issue in issues],
                success=[] if issues else [dataclasses.replace(Issue.none(), suggestion=None, asset=asset)],
            ),
        )

    def filter_by(self, predicate: IssuePredicate) -> Results:
        """
        Filter the issues by the given predicate.
        """
        return Results(
            asset=self.asset,
            issues=self.issues.filter_by(predicate),
        )

    def __len__(self) -> int:
        return len(self.issues)

    def __getitem__(self, item: int) -> Issue:
        return self.issues[item]

    def __str__(self):
        tokens = []
        issues = sorted(self.issues(), key=lambda issue: (issue.message, issue.rule.__name__ if issue.rule else None))
        for issue in issues:
            tokens.append(
                f"""
                    Issue(
                        message="{issue.message}",
                        severity={issue.severity},
                        rule={issue.rule.__name__ if issue.rule else None},
                        at={issue.at},
                        suggestion={issue.suggestion if issue.suggestion else None}
                    )"""
            )
        text = ",".join(tokens)
        return inspect.cleandoc(
            f"""
            Results(
                asset="{self.asset}",
                issues=[
                    {text.lstrip()}
                ]
            )"""
        )


@dataclass(frozen=True)
class ResultsList(Sequence[Results]):
    results: list[Results] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, item: int) -> Results:
        return self.results[item]

    def issues(self) -> IssuesList:
        """
        Returns: A list with all the issues.
        """
        ret: IssuesList = IssuesList(issues=[])
        for result in self.results:
            ret = ret.merge(result.issues())
        return ret


@to_issues_list.register(IssuesList)
def _(value: IssuesList) -> IssuesList:
    return value


@to_issues_list.register(list)
def _(value: list[Issue]) -> IssuesList:
    return IssuesList(issues=value)


@to_issues_list.register(Issue)
def _(value: Issue) -> IssuesList:
    return IssuesList(issues=[value])


@to_issues_list.register(Results)
def _(value: Results) -> IssuesList:
    return value.issues


@to_issues_list.register(ResultsList)
def _(value: ResultsList) -> IssuesList:
    return value.issues()
