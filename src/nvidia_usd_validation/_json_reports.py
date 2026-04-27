# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import enum
import json
import pathlib
from functools import singledispatchmethod
from typing import Any

from pxr import Sdf

from ._base_rule_checker import BaseRuleChecker
from ._identifiers import EditTargetId, LayerId, PrimId, PropertyId, SchemaBaseId, SpecId, StageId
from ._issues import Issue, IssueGroupsBy, IssueSeverity, IssuesList, Suggestion
from ._results import Results, ResultsList, to_issues_list

__all__ = [
    "IssueJSONEncoder",
    "export_json_file",
]


class Type(enum.Enum):
    PRIM = 0
    PROPERTY = 1
    SUGGESTION = 2
    RULE = 3
    ISSUE = 4
    LAYER = 5
    STAGE = 6
    SPEC = 7
    SCHEMA = 8


class IssueJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for serializing various issue-related objects into a structured JSON format.

    This encoder handles serializing `Results`, `ResultsList`, `IssuesList`, `Issue`, `Suggestion`, `Identifier`
    and list of Issues.
    """

    def __init__(self, rules: list[BaseRuleChecker] | None = None, *args, **kwargs):
        kwargs["indent"] = 4
        super().__init__(*args, **kwargs)
        self._rules = rules if rules else []

    @classmethod
    def _is_rule(cls, o: Any) -> bool:
        try:
            return issubclass(o, BaseRuleChecker)
        except TypeError:
            return False

    @singledispatchmethod
    def default(self, o: Any) -> Any:
        return super().default(o)

    @default.register
    def _(self, o: Results) -> Any:
        return o.issues

    @default.register
    def _(self, o: ResultsList) -> Any:
        return o.issues()

    @default.register(IssuesList)
    @default.register(list)
    def _(self, o: IssuesList | list[Issue]) -> Any:
        o = to_issues_list(o)
        # Set all rules
        rules: dict = {}
        for rule in self._rules:
            rules[rule] = {"rule": rule, "status": "PASS", "issues": []}
        # Add issues to failing rules
        for issues in o.group_by(IssueGroupsBy.rule()):
            rule = issues.name
            if rule is not None:
                rules.setdefault(rule, {"rule": rule, "status": "PASS", "issues": []})
                rules[rule]["status"] = "FAIL"
                rules[rule]["issues"] = list(issues)
        # Return global one
        return {
            "status": "FAIL" if o else "PASS",
            "rules": list(rules.values()),
        }

    @default.register
    def _(self, o: Issue) -> Any:
        return {
            "type": Type.ISSUE,
            "message": o.message,
            "severity": o.severity,
            "rule": o.rule,
            "at": o.at,
            "suggestion": o.suggestion,
            "suggestions": list(o.suggestions),
        }

    @default.register
    def _(self, o: Suggestion) -> Any:
        return {
            "type": Type.SUGGESTION,
            "message": o.message,
        }

    @default.register
    def _(self, o: PrimId) -> Any:
        return {
            "type": Type.PRIM,
            "path": o.path,
        }

    @default.register
    def _(self, o: PropertyId) -> Any:
        return {
            "type": Type.PROPERTY,
            "path": o.prim_id.path,
            "name": o.name,
        }

    @default.register
    def _(self, o: LayerId) -> Any:
        return {
            "type": Type.LAYER,
            "path": o.identifier,
        }

    @default.register
    def _(self, o: StageId) -> Any:
        return {
            "type": Type.STAGE,
            "path": o.identifier,
        }

    @default.register
    def _(self, o: EditTargetId) -> Any:
        return {
            "type": Type.SPEC,
            "path": o.path,
        }

    @default.register
    def _(self, o: SpecId) -> Any:
        return {
            "type": Type.SPEC,
            "path": o.path,
        }

    @default.register
    def _(self, o: SchemaBaseId) -> Any:
        return {"type": Type.SCHEMA, "path": o.prim_id.path, "schema_class": o.schema_class.__name__}

    @default.register
    def _(self, o: IssueSeverity) -> Any:
        return o.name

    @default.register
    def _(self, o: Type) -> Any:
        return o.name

    @default.register
    def _(self, o: Sdf.Path) -> Any:
        return str(o)

    @default.register(type(BaseRuleChecker))
    def _(self, o: type[BaseRuleChecker]) -> Any:
        return {
            "type": Type.RULE,
            "name": o.__name__,
        }


def export_json_file(
    json_output_path: str | pathlib.Path, entry: Results | ResultsList | IssuesList | Issue | Suggestion
) -> None:
    with open(json_output_path, "w") as f:
        json.dump(entry, f, cls=IssueJSONEncoder)
