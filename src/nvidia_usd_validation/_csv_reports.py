# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import csv
import io
import pathlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from functools import singledispatch

from ._identifiers import Identifier, StageId
from ._issues import Issue, IssueSeverity, IssuesList, Suggestion
from ._results import Results, ResultsList, to_issues_list
from ._validation_context import ValidationContext

__all__ = [
    "IssueCSVData",
    "export_csv_file",
]


@dataclass
class IssueCSVData:
    """
    A class for organizing and exporting issue data into a CSV format.

    Args:
        headers (list[str]): The headers for the CSV columns. By default, it includes "Asset", "Rule", "Message", "Suggestion", and "Location".
        assets (list[str]): The list of assets associated with the issues.
        rules (list[str]): The list of rules corresponding to each issue.
        messages (list[str]): Detailed messages for each issue.
        suggestions (list[str]): Suggestions for each issue.
        ats (list[str]): Locations of the issues.
        additional_column (dict[str, list[str]]): Additional custom columns that can be appended dynamically.
    """

    class _Headers(str, Enum):
        asset: str = "Asset"
        rule: str = "Rule"
        message: str = "Message"
        severity: str = "Severity"
        suggestion: str = "Suggestion"
        location: str = "Location"

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
    def from_(cls, value: Issue | list[Issue] | IssuesList | Results | ResultsList):
        """Creates an instance of IssueCSVData from given input."""
        issue_list = to_issues_list(value)

        def _parse_asset_str() -> list[str]:
            """Parses the assets from a list of issues and returns them as a list of strings."""

            @singledispatch
            def _get_asset_string(asset) -> str:
                return str(asset)

            @_get_asset_string.register(StageId)
            def _(asset: StageId) -> str:
                return asset.root_layer.identifier

            @_get_asset_string.register(Identifier)
            def _(asset: Identifier) -> str:
                return asset.as_str()

            @_get_asset_string.register(type(None))
            def _(asset: None) -> str:
                return "Unknown asset"

            assets = []
            for issue in issue_list:
                # Determine the asset value based on the type and availability
                if issue.asset:
                    assets.append(_get_asset_string(issue.asset))
                elif isinstance(value, Results) and value.asset:
                    assets.append(_get_asset_string(value.asset))
                else:
                    assets.append("Unknown asset")
            return assets

        def _get_severity_str(severity: IssueSeverity):
            severity_map = {
                IssueSeverity.ERROR: "Error",
                IssueSeverity.FAILURE: "Failure",
                IssueSeverity.WARNING: "Warning",
                IssueSeverity.INFO: "Info",
                IssueSeverity.NONE: "None",
            }
            return severity_map.get(severity, str(severity))

        def _get_rule_name(issue: Issue) -> str:
            try:
                return issue.rule.__name__
            except AttributeError:
                return "None"

        def _get_suggestion_str(suggestion) -> str:
            if suggestion is not None:
                # Suggestion might be a string, like in some unit tests
                if isinstance(suggestion, str):
                    return suggestion
                if isinstance(suggestion, Suggestion):
                    return suggestion.message
                raise TypeError(f"Unsupported type {type(suggestion)} of {suggestion}")
            return "None"

        def _get_location_str(at) -> str:
            if isinstance(at, tuple):
                return ", ".join(loc.as_str() for loc in at)
            if isinstance(at, Identifier):
                return at.as_str()
            return "None"

        def _get_requirement_str(issue: Issue) -> str:
            if issue.requirement is not None:
                return f"{issue.requirement.code}@{issue.requirement.version}"
            return ""

        assets = _parse_asset_str()
        if issue_list:
            rules, severities, messages, suggestions, ats = zip(
                *[
                    (
                        _get_rule_name(issue),
                        _get_severity_str(issue.severity),
                        issue.message or "None",
                        _get_suggestion_str(issue.suggestion),
                        _get_location_str(issue.at),
                    )
                    for issue in issue_list
                ]
            )
        else:
            rules, severities, messages, suggestions, ats = [], [], [], [], []

        requirements = [_get_requirement_str(issue) for issue in issue_list]

        return cls(
            list(IssueCSVData._Headers),
            assets,
            list(rules),
            list(messages),
            list(severities),
            list(suggestions),
            list(ats),
            requirements,
        )

    def append_column(self, header: str, values: Sequence[str]):
        """Appends a custom column to the IssueCSVData instance with the given header and corresponding values."""
        self.headers.append(header)
        self.additional_column[header] = values

    def _get_data_dict(self, headers: list[str] | None = None) -> dict[str, list[str]]:
        """Returns a dictionary mapping headers to their respective column data."""
        headers = headers if headers else self.headers
        header_data_map = {
            IssueCSVData._Headers.asset: self.assets,
            IssueCSVData._Headers.rule: self.rules,
            IssueCSVData._Headers.message: self.messages,
            IssueCSVData._Headers.severity: self.severities,
            IssueCSVData._Headers.suggestion: self.suggestions,
            IssueCSVData._Headers.location: self.ats,
        }

        data_dict = {}
        for header in headers:
            data_dict[header] = self.additional_column.get(header) or header_data_map.get(header, [])

        return data_dict

    def _get_csv_data(self, headers: list[str] | None = None) -> Iterator[list[str]]:
        """
        Returns a list of string lists representing the CSV data.
        The first list contains the headers. The rest of the lists contain the data rows.
        This method can be used to get the data and pass it to a CSV writer that expects
        iterabled for each row.
        Args:
            headers: list[str] | None - An optional list of headers to include in the CSV.
        Yields:
            An iterable containing a list with a string in it representing a row in the CSV data.
        """
        headers = headers if headers else self.headers
        export_data = self._get_data_dict(headers)
        yield headers
        for idx in range(max(len(data) for data in export_data.values())):
            row = []
            for header in headers:
                try:
                    data = export_data[header][idx]
                except IndexError:
                    data = ""
                row.append(data)
            yield row

    def get_csv_as_str(self, headers: list[str] | None = None, delimiter: str = ",") -> str:
        """
        Returns a string containing the list the data in CSV format.
        The result can be written to a file using regular file operations,
        or copied to the clipboard.
        Args:
            headers: list[str] | None - An optional list of headers to include in the CSV.
            delimiter: str - The delimiter to use in the CSV.
        Returns:
            A string containing the list the data in CSV format.
        """
        # Use the CSV package to write the data to a string
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output, delimiter=delimiter)
        for row in self._get_csv_data(headers):
            csv_writer.writerow(row)
        csv_string = csv_output.getvalue()
        csv_output.close()
        return csv_string

    def export_csv(self, file_url: str | pathlib.Path, headers: list[str] | None = None, delimiter: str = ","):
        """
        Exports the issue data to a CSV file at the given file path.
        This method writes the issue data into a CSV format using the specified file path.
        The default available headers are: "Asset", "Rule", "Severity", "Message", "Suggestion", and "Location".

        Args:
            file_url: str | pathlib.Path - The file path to write the CSV data to.
            headers: list[str] | None - An optional list of headers to include in the CSV.
            delimiter: str - The delimiter to use in the CSV.

        Example:

        .. code-block:: python

            result = await engine.validate_async(path)
            csvdata = IssueCSVData.from_(result)
            csvdata.append_column("idx", [str(idx) for idx in range(40)])
            csvdata.export_csv("/path/to/test.csv")
        """
        with open(file_url, "w", newline="") as csv_file:
            csv_file.write(self.get_csv_as_str(headers, delimiter))


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
    csv_data = IssueCSVData.from_(results)
    if metadata:
        num_issues = max(len(csv_data.assets), 1)
        if metadata.profiles:
            value = ", ".join(f"{p.profile.id} ({p.profile.version})" for p in metadata.profiles)
            csv_data.append_column("Profile", [value] * num_issues)
        if metadata.features:
            value = ", ".join(f"{f.feature.id} ({f.feature.version})" for f in metadata.features)
            csv_data.append_column("Feature", [value] * num_issues)
        csv_data.append_column("Requirement", csv_data.requirements)
    csv_data.export_csv(csv_output_path)
