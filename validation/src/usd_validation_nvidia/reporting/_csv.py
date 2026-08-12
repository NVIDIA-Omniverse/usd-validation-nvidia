# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import csv
import io
import pathlib
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from .._identifiers import Identifier, StageId
from .._issues import Issue, IssueSeverity, IssuesList, Suggestion
from .._results import Results, ResultsList, to_issues_list
from .._validation_context import ValidationContext

__all__ = [
    "ColumnCSVTable",
    "IssueCSVData",
    "RowCSVTable",
    "export_csv_file",
]


@dataclass
class BaseCSVTable(ABC):

    class _Headers(str, Enum):
        ASSET: str = "Asset"
        RULE: str = "Rule"
        MESSAGE: str = "Message"
        SEVERITY: str = "Severity"
        SUGGESTION: str = "Suggestion"
        LOCATION: str = "Location"

    _SEVERITY_LABELS: ClassVar[dict[IssueSeverity, str]] = {
        IssueSeverity.ERROR: "Error",
        IssueSeverity.FAILURE: "Failure",
        IssueSeverity.WARNING: "Warning",
        IssueSeverity.INFO: "Info",
        IssueSeverity.NONE: "None",
    }

    @classmethod
    def _get_asset_str(cls, asset) -> str:
        if asset is None:
            return "Unknown asset"
        elif isinstance(asset, StageId):
            return asset.root_layer.identifier
        elif isinstance(asset, Identifier):
            return asset.as_str()
        else:
            return str(asset)

    @classmethod
    def _get_severity_str(cls, severity: IssueSeverity) -> str:
        try:
            return cls._SEVERITY_LABELS[severity]
        except KeyError:
            return str(severity)

    @classmethod
    def _get_rule_name(cls, issue: Issue) -> str:
        try:
            return issue.rule.__name__
        except AttributeError:
            return "None"

    @classmethod
    def _get_suggestion_str(cls, suggestion) -> str:
        if suggestion is None:
            return "None"
        elif isinstance(suggestion, str):
            return suggestion
        elif isinstance(suggestion, Suggestion):
            return suggestion.message
        raise TypeError(f"Unsupported type {type(suggestion)} of {suggestion}")

    @classmethod
    def _get_location_str(cls, at) -> str:
        if at is None:
            return "None"
        elif isinstance(at, tuple):
            return ", ".join(loc.as_str() for loc in at)
        elif isinstance(at, Identifier):
            return at.as_str()
        else:
            return str(at)

    @classmethod
    def _get_requirement_str(cls, issue: Issue) -> str:
        if issue.requirement is not None:
            return f"{issue.requirement.code}@{issue.requirement.version}"
        return ""

    @classmethod
    def _get_issue_row(cls, issue: Issue, asset=None) -> dict[str, str]:
        return {
            cls._Headers.ASSET: cls._get_asset_str(issue.asset or asset),
            cls._Headers.RULE: cls._get_rule_name(issue),
            cls._Headers.MESSAGE: issue.message or "None",
            cls._Headers.SEVERITY: cls._get_severity_str(issue.severity),
            cls._Headers.SUGGESTION: cls._get_suggestion_str(issue.suggestion),
            cls._Headers.LOCATION: cls._get_location_str(issue.at),
        }

    @abstractmethod
    def __len__(self) -> int:
        """The number of rows, i.e. the maximum between number of issues or appended values."""

    @abstractmethod
    def __iter__(self) -> Iterator[dict[str, str]]:
        """Iterate all rows as dictionaries."""

    def _get_data_dict(self, headers: list[str] | None = None) -> dict[str, list[str]]:
        """Returns a dictionary mapping headers to their respective column data."""
        headers = headers if headers else self.headers
        data_dict = {header: [] for header in headers}
        for row in self:
            for header in headers:
                data_dict[header].append(row.get(header, ""))
        return data_dict

    def get_csv_as_str(self, headers: list[str] | None = None, delimiter: str = ",") -> str:
        """
        Returns a string containing the data in CSV format.
        The result can be written to a file using regular file operations,
        or copied to the clipboard.
        Args:
            headers: list[str] | None - An optional list of headers to include in the CSV.
            delimiter: str - The delimiter to use in the CSV.
        Returns:
            A string containing the data in CSV format.
        """
        headers = headers if headers else self.headers
        with io.StringIO() as csv_output:
            csv_writer = csv.DictWriter(
                csv_output,
                fieldnames=headers,
                delimiter=delimiter,
                restval="",
                extrasaction="ignore",
            )
            csv_writer.writeheader()
            csv_writer.writerows(self)
            return csv_output.getvalue()

    def export_csv(self, file_url: str | pathlib.Path, headers: list[str] | None = None, delimiter: str = ","):
        """
        Exports the issue data to a CSV file at the given file path.
        """
        headers = headers if headers else self.headers
        with open(file_url, "w", newline="") as csv_file:
            csv_writer = csv.DictWriter(
                csv_file,
                fieldnames=headers,
                delimiter=delimiter,
                restval="",
                extrasaction="ignore",
            )
            csv_writer.writeheader()
            csv_writer.writerows(self)


@dataclass
class ColumnCSVTable(BaseCSVTable):
    """
    A column-backed table for organizing and exporting issue data into CSV format.

    Args:
        headers (list[str]): The headers for the CSV columns. By default, it includes "Asset", "Rule", "Message", "Suggestion", and "Location".
        assets (list[str]): The list of assets associated with the issues.
        rules (list[str]): The list of rules corresponding to each issue.
        messages (list[str]): Detailed messages for each issue.
        suggestions (list[str]): Suggestions for each issue.
        ats (list[str]): Locations of the issues.
        additional_column (dict[str, list[str]]): Additional custom columns that can be appended dynamically.
    """

    headers: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    severities: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    ats: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    additional_column: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_(
        cls,
        value: Issue | list[Issue] | IssuesList | Results | ResultsList,
    ):
        """Creates an instance of ColumnCSVTable from given input."""
        issue_list = to_issues_list(value)
        asset = value.asset if isinstance(value, Results) else None
        rows = [cls._get_issue_row(issue, asset) for issue in issue_list]
        return cls(
            list(cls._Headers),
            [row.get(cls._Headers.ASSET, "") for row in rows],
            [row.get(cls._Headers.RULE, "") for row in rows],
            [row.get(cls._Headers.MESSAGE, "") for row in rows],
            [row.get(cls._Headers.SEVERITY, "") for row in rows],
            [row.get(cls._Headers.SUGGESTION, "") for row in rows],
            [row.get(cls._Headers.LOCATION, "") for row in rows],
            [cls._get_requirement_str(issue) for issue in issue_list],
        )

    def append_column(self, header: str, values: Sequence[str]):
        """Appends a custom column to the table with the given header and corresponding values."""
        self.headers.append(header)
        self.additional_column[header] = values

    def __len__(self) -> int:
        return max(
            len(self.assets),
            max((len(values) for values in self.additional_column.values()), default=0),
        )

    def __iter__(self) -> Iterator[dict[str, str]]:
        """
        Returns dictionaries representing the CSV data rows.
        Yields:
            A dictionary mapping CSV headers to row values.
        """
        data_map = {
            self._Headers.ASSET: self.assets,
            self._Headers.RULE: self.rules,
            self._Headers.MESSAGE: self.messages,
            self._Headers.SEVERITY: self.severities,
            self._Headers.SUGGESTION: self.suggestions,
            self._Headers.LOCATION: self.ats,
            **self.additional_column,
        }
        for i in range(len(self)):
            yield {header: values[i] if i < len(values) else "" for header, values in data_map.items()}


IssueCSVData = ColumnCSVTable


@dataclass
class RowCSVTable(BaseCSVTable):
    """
    A row-backed table for generating issue CSV rows on iteration.

    It exposes the same CSV-oriented public API as :class:`ColumnCSVTable`, but stores issue objects and generates
    row dictionaries as needed.
    """

    issues: IssuesList
    asset: str | Identifier | None = None
    headers: list[str] = field(default_factory=lambda: list(BaseCSVTable._Headers))
    additional_column: dict[str, Sequence[str]] = field(default_factory=dict)

    @classmethod
    def from_(
        cls,
        value: Issue | list[Issue] | IssuesList | Results | ResultsList,
    ):
        """Creates an instance of RowCSVTable from given input."""
        return cls(issues=to_issues_list(value), asset=value.asset if isinstance(value, Results) else None)

    def append_column(self, header: str, values: Sequence[str]):
        """Appends a custom column to the table with the given header and corresponding values."""
        self.headers.append(header)
        self.additional_column[header] = values

    def __len__(self) -> int:
        return max(
            len(self.issues),
            max((len(values) for values in self.additional_column.values()), default=0),
        )

    def __iter__(self) -> Iterator[dict[str, str]]:
        i = 0
        for issue in self.issues:
            data_map = self._get_issue_row(issue, self.asset)
            for header, values in self.additional_column.items():
                data_map[header] = values[i] if i < len(values) else ""
            yield data_map
            i += 1

        length: int = len(self)
        while i < length:
            data_map = {}
            for header, values in self.additional_column.items():
                data_map[header] = values[i] if i < len(values) else ""
            yield data_map
            i += 1


def export_csv_file(
    csv_output_path: str | pathlib.Path,
    results: Results | ResultsList,
    metadata: ValidationContext | None = None,
) -> None:
    """Export validation results to a CSV file.

    Mirrors :func:`export_json_file`. When *metadata* is provided (i.e. the
    validation was profile- or feature-scoped), Profile, Feature, and
    Requirement columns are appended; otherwise the standard 6-column format
    is preserved for backwards compatibility.

    Args:
        csv_output_path: Path to write the CSV file.
        results: Validation results to export.
        metadata: Optional :class:`ValidationContext` from the engine.
    """
    csv_data = RowCSVTable.from_(results)
    if metadata:
        num_issues = max(len(csv_data), 1)
        if metadata.profiles:
            value = ", ".join(f"{p.profile.id} ({p.profile.version})" for p in metadata.profiles)
            csv_data.append_column("Profile", [value] * num_issues)
        if metadata.features:
            value = ", ".join(f"{f.feature.id} ({f.feature.version})" for f in metadata.features)
            csv_data.append_column("Feature", [value] * num_issues)
        csv_data.append_column("Requirement", [csv_data._get_requirement_str(issue) for issue in csv_data.issues])
    csv_data.export_csv(csv_output_path)
