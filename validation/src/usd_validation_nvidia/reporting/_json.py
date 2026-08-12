# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import enum
import json
import pathlib
from functools import singledispatchmethod
from typing import Any

from pxr import Sdf

from usd_validation_nvidia.capabilities import Requirement as _Requirement

from .._base_rule_checker import BaseRuleChecker
from .._identifiers import (
    EditTargetId,
    LayerId,
    PrimId,
    PropertyId,
    SchemaBaseId,
    SpecId,
    StageId,
)
from .._issues import Issue, IssueGroupsBy, IssueSeverity, IssuesList, Suggestion
from .._results import Results, ResultsList, to_issues_list
from .._validation_context import (
    FeatureStatus,
    ProfileStatus,
    RequirementStatus,
    ValidationContext,
)

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

    Args:
        rules: Optional list of rule classes to include in the output (even if they produced no issues).
        metadata: Optional ``ValidationContext`` to include as a structured tree in the top-level JSON output.
    """

    def __init__(
        self,
        rules: list[BaseRuleChecker] | None = None,
        metadata: ValidationContext | None = None,
        *args,
        **kwargs,
    ):
        kwargs["indent"] = 4
        super().__init__(*args, **kwargs)
        self._rules = rules if rules else []
        self._metadata = metadata

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
            if not issues:
                continue
            rule = issues.name
            rules.setdefault(rule, {"rule": rule, "status": "PASS", "issues": []})
            rules[rule]["status"] = "FAIL"
            rules[rule]["issues"] = list(issues)
        result = {
            "status": "FAIL" if o else "PASS",
        }
        if self._metadata:
            result["profiles"] = self._metadata.profiles
            result["features"] = self._metadata.features
        result["rules"] = list(rules.values())
        return result

    @default.register
    def _(self, o: ValidationContext) -> Any:
        return {"profiles": o.profiles, "features": o.features}

    @default.register
    def _(self, o: ProfileStatus) -> Any:
        return {
            "id": o.profile.id,
            "version": o.profile.version,
            "status": o.status,
            "features": o.features,
        }

    @default.register
    def _(self, o: FeatureStatus) -> Any:
        return {
            "id": o.feature.id,
            "version": o.feature.version,
            "status": o.status,
            "requirements": o.requirements,
        }

    @default.register
    def _(self, o: RequirementStatus) -> Any:
        return {
            "code": o.requirement.code,
            "version": o.requirement.version,
            "status": o.status,
        }

    @default.register
    def _(self, o: Issue) -> Any:
        result = {
            "type": Type.ISSUE,
            "message": o.message,
            "severity": o.severity,
            "rule": o.rule,
            "at": o.at,
            "suggestion": o.suggestion,
            "suggestions": list(o.suggestions),
        }
        if o.requirement is not None:
            result["requirement"] = o.requirement
        return result

    @default.register(_Requirement)
    def _(self, o: _Requirement) -> Any:
        return {"code": o.code, "version": o.version}

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
            "path": o.root_layer.identifier,
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
    json_output_path: str | pathlib.Path,
    entry: Results | ResultsList | IssuesList | Issue | Suggestion,
    metadata: ValidationContext | None = None,
) -> None:
    """
    Export validation results to a JSON file.

    Args:
        json_output_path: Path to write the JSON file.
        entry: Validation results to serialize.
        metadata: Optional :class:`ValidationContext` to include as a structured
            profile/feature/requirement tree in the top-level JSON output.
    """
    encoder = IssueJSONEncoder(metadata=metadata)
    with open(json_output_path, "w") as f:
        for chunk in encoder.iterencode(entry):
            f.write(chunk)
