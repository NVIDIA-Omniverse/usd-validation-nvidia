# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import pathlib
import unittest
from tempfile import TemporaryDirectory

from common import get_url

from usd_validation_nvidia import (
    BaseRuleChecker,
    Issue,
    IssueCSVData,
    IssueSeverity,
    IssuesList,
    LayerId,
    Results,
    ResultsList,
    Suggestion,
)


class MyRuleChecker(BaseRuleChecker):
    pass


class AnotherRuleChecker(BaseRuleChecker):
    pass


class Location(LayerId):
    def as_str(self):
        return self.identifier


def suggestion(*args): ...


class ReportsCSVTest(unittest.TestCase):
    def test_csv_issues(self):
        # Given
        issue1 = Issue(
            asset="Asset1",
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            message="failure",
            suggestion=Suggestion(suggestion, "suggestion1"),
            at=Location("somewhere1"),
        )
        issue2 = Issue(
            asset="Asset2",
            severity=IssueSeverity.WARNING,
            rule=MyRuleChecker,
            message="warning",
            suggestion=Suggestion(suggestion, "suggestion12"),
            at=Location("somewhere2"),
        )

        # When
        src_csv = get_url("Reports/issue.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issue.csv")
            csv_data = IssueCSVData.from_(issue1)
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

        # When
        src_csv = get_url("Reports/issues.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issues.csv")
            csv_data = IssueCSVData.from_([issue1, issue2])
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

        # When
        src_csv = get_url("Reports/issues.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issues.csv")
            csv_data = IssueCSVData.from_(IssuesList([issue1, issue2]))
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_results(self):
        # Given
        results = Results(
            asset="Any asset",
            issues=[
                Issue(
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion1"),
                    at=Location("somewhere1"),
                ),
                Issue(
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion2"),
                    at=Location("somewhere2"),
                ),
            ],
        )

        # When
        src_csv = get_url("Reports/results.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "results.csv")
            csv_data = IssueCSVData.from_(results)
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_results_list(self):
        # Given
        results1 = Results(
            asset="Any asset",
            issues=[
                Issue(
                    asset="Asset1",
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion1"),
                    at=Location("somewhere1"),
                ),
                Issue(
                    asset="Asset2",
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion2"),
                    at=Location("somewhere2"),
                ),
            ],
        )
        results2 = Results(
            asset="Any asset",
            issues=[
                Issue(
                    asset="Asset3",
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion3"),
                    at=Location("somewhere3"),
                ),
                Issue(
                    asset="Asset4",
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion4"),
                    at=Location("somewhere4"),
                ),
            ],
        )

        # When
        results_list = ResultsList([results1, results2])
        src_csv = get_url("Reports/results_list.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "results_list.csv")
            csv_data = IssueCSVData.from_(results_list)
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_append_column(self):
        # Given
        result1 = Results(
            asset="Any asset",
            issues=[
                Issue(
                    asset="Asset1",
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion1"),
                    at=Location("somewhere1"),
                ),
                Issue(
                    asset="Asset2",
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion2"),
                    at=Location("somewhere2"),
                ),
            ],
        )
        result2 = Results(
            asset="Any asset",
            issues=[
                Issue(
                    asset="Asset3",
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion3"),
                    at=Location("somewhere3"),
                ),
                Issue(
                    asset="Asset4",
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion4"),
                    at=Location("somewhere4"),
                ),
            ],
        )

        # When
        results_list = ResultsList([result1, result2])
        src_csv = get_url("Reports/append_column.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "results_list.csv")
            csv_data = IssueCSVData.from_(results_list)
            csv_data.append_column("Test", range(10))
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_get_data_dict(self):
        # Given
        results1 = Results(
            asset="Any asset",
            issues=[
                Issue(
                    asset="Asset1",
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    message="failure",
                    suggestion=Suggestion(suggestion, "suggestion1"),
                    at=Location("somewhere1"),
                ),
                Issue(
                    asset="Asset2",
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    message="warning",
                    suggestion=Suggestion(suggestion, "suggestion2"),
                    at=Location("somewhere2"),
                ),
            ],
        )

        # When
        csv_data = IssueCSVData.from_(results1)
        csv_data.append_column("Test", [str(i) for i in range(9, 0, -1)])

        expected_data = {
            "Asset": [
                "Asset1",
                "Asset2",
            ],
            "Message": ["failure", "warning"],
            "Severity": ["Failure", "Warning"],
            "Location": ["somewhere1", "somewhere2"],
            "Rule": ["MyRuleChecker", "MyRuleChecker"],
            "Suggestion": ["suggestion1", "suggestion2"],
            "Test": ["9", "8", "7", "6", "5", "4", "3", "2", "1"],
        }
        # Then
        self.assertEqual(csv_data._get_data_dict(), expected_data)

    def test_csv_export_with_delimiters(self):
        # Issue for testing with data that contains characters that are also column delimiters (ex: ',')
        delimiter_comma = ","
        issue_with_comma_delimiter = Issue(
            asset=f"Asset{delimiter_comma} with delimiter",
            severity=IssueSeverity.INFO,
            rule=AnotherRuleChecker,
            message=f"info{delimiter_comma} with delimiter",
            suggestion=Suggestion(suggestion, f"suggestion{delimiter_comma} with delimiter"),
            at=Location(f"somewhere{delimiter_comma} with delimiter"),
        )
        # When
        src_csv = get_url("Reports/issues_with_comma_delimiters.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issues_with_comma_delimiters.csv")
            csv_data = IssueCSVData.from_(IssuesList([issue_with_comma_delimiter]))
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_as_str_with_delimiters(self):
        # Issue for testing with data that contains characters that are also column delimiters (ex: ',')
        delimiter_comma = ","
        issue_with_comma_delimiter = Issue(
            asset=f"Asset{delimiter_comma} with delimiter",
            severity=IssueSeverity.INFO,
            rule=AnotherRuleChecker,
            message=f"info{delimiter_comma} with delimiter",
            suggestion=Suggestion(suggestion, f"suggestion{delimiter_comma} with delimiter"),
            at=Location(f"somewhere{delimiter_comma} with delimiter"),
        )
        # When
        src_csv = get_url("Reports/issues_with_comma_delimiters.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issues_with_comma_delimiters.csv")
            csv_data = IssueCSVData.from_(IssuesList([issue_with_comma_delimiter]))
            csv_str = csv_data.get_csv_as_str(delimiter=delimiter_comma)
            with open(csv_path, "w", newline="") as f:
                f.write(csv_str)
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )

    def test_csv_export_with_empty_cells(self):
        # Issue for testing with data that contains characters that are also column delimiters (ex: ',')
        issue = Issue(
            asset=None,
            severity=IssueSeverity.FAILURE,
            rule=None,
            message="message",
            suggestion=None,
            at=None,
        )
        # When
        src_csv = get_url("Reports/issues_with_empty_cells.csv")
        with TemporaryDirectory() as tmp:
            csv_path: str = os.path.join(tmp, "issues_with_empty_cells.csv")
            csv_data = IssueCSVData.from_(IssuesList([issue]))
            csv_data.export_csv(csv_path)
            # Then
            self.assertEqual(
                pathlib.Path(src_csv).read_text(),
                pathlib.Path(csv_path).read_text(),
            )
