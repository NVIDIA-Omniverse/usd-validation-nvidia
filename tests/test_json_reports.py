# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
import pathlib
import unittest
from tempfile import TemporaryDirectory

from common import get_url
from nvidia_usd_validation import (
    BaseRuleChecker,
    Issue,
    IssueJSONEncoder,
    IssueSeverity,
    LayerId,
    Results,
    ResultsList,
    Suggestion,
    export_json_file,
)


class MyRuleChecker(BaseRuleChecker):
    pass


class Location(LayerId):
    def as_str(self):
        return self.identifier


def suggestion(*args): ...


class IssueJSONEncoderTest(unittest.TestCase):
    maxDiff = None

    def test_issue_json_encoder(self):
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
        src_json = get_url("Reports/results.json")
        with TemporaryDirectory() as tmp:
            json_path: str = os.path.join(tmp, "results.json")
            export_json_file(json_path, ResultsList([results1, results2]))
            self.assertEqual(pathlib.Path(json_path).read_text(), pathlib.Path(src_json).read_text())

    def test_issue_json_suggestions_array(self):
        """JSON output includes a 'suggestions' array when an issue has multiple suggestions"""
        s1 = Suggestion(suggestion, "fix A")
        s2 = Suggestion(suggestion, "fix B")
        issue = Issue(
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            message="multi-fix issue",
            suggestions=[s1, s2],
        )
        result = json.loads(json.dumps(issue, cls=IssueJSONEncoder))
        self.assertIn("suggestions", result)
        self.assertEqual(len(result["suggestions"]), 2)
        self.assertEqual(result["suggestions"][0]["message"], "fix A")
        self.assertEqual(result["suggestions"][1]["message"], "fix B")
        self.assertEqual(result["suggestion"]["message"], "fix A")

    def test_issue_json_single_suggestion(self):
        """JSON output with single suggestion still works"""
        s = Suggestion(suggestion, "the fix")
        issue = Issue(
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            message="single-fix issue",
            suggestion=s,
        )
        result = json.loads(json.dumps(issue, cls=IssueJSONEncoder))
        self.assertIn("suggestions", result)
        self.assertEqual(len(result["suggestions"]), 1)
        self.assertEqual(result["suggestions"][0]["message"], "the fix")
        self.assertEqual(result["suggestion"]["message"], "the fix")

    def test_issue_json_no_suggestion(self):
        """JSON output with no suggestion has empty suggestions array"""
        issue = Issue(
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            message="no-fix issue",
        )
        result = json.loads(json.dumps(issue, cls=IssueJSONEncoder))
        self.assertIn("suggestions", result)
        self.assertEqual(result["suggestions"], [])
        self.assertIsNone(result["suggestion"])
