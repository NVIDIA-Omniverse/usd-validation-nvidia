# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
import pathlib
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from common import get_url

from nvidia_usd_validation import (
    BaseRuleChecker,
    FeatureStatus,
    Issue,
    IssueJSONEncoder,
    IssueSeverity,
    LayerId,
    ProfileStatus,
    RequirementStatus,
    Results,
    ResultsList,
    Suggestion,
    ValidationContext,
    export_json_file,
)
from nvidia_usd_validation.capabilities import Requirement as CapRequirement


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

    def test_issue_json_tree_metadata(self):
        """JSON output includes tree-structured metadata with pass/fail when provided"""
        mock_req = Mock()
        mock_req.code = "VG.001"
        mock_req.version = "1.0.0"
        mock_feature = Mock()
        mock_feature.id = "FET001"
        mock_feature.version = "1.0.0"
        mock_profile = Mock()
        mock_profile.id = "Robot-Body-Isaac"
        mock_profile.version = "1.0.0"

        metadata = ValidationContext(
            profiles=[
                ProfileStatus(
                    profile=mock_profile,
                    status="FAIL",
                    features=[
                        FeatureStatus(
                            feature=mock_feature,
                            status="PASS",
                            requirements=[RequirementStatus(requirement=mock_req, status="PASS")],
                        )
                    ],
                )
            ]
        )
        results = Results(
            asset="test.usd",
            issues=[Issue(severity=IssueSeverity.FAILURE, rule=MyRuleChecker, message="failure")],
        )
        encoder = IssueJSONEncoder(metadata=metadata)
        result = json.loads(encoder.encode(ResultsList([results])))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("profiles", result)
        profile = result["profiles"][0]
        self.assertEqual(profile["id"], "Robot-Body-Isaac")
        self.assertEqual(profile["status"], "FAIL")
        self.assertEqual(profile["features"][0]["status"], "PASS")
        self.assertIn("rules", result)

    def test_issue_json_no_metadata(self):
        """JSON output omits metadata fields when not provided"""
        results = Results(
            asset="test.usd",
            issues=[Issue(severity=IssueSeverity.FAILURE, rule=MyRuleChecker, message="failure")],
        )
        result = json.loads(json.dumps(ResultsList([results]), cls=IssueJSONEncoder))
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("profiles", result)
        self.assertNotIn("features", result)

    def test_export_json_file_with_tree_metadata(self):
        """export_json_file includes tree-structured metadata when provided"""
        mock_req = Mock()
        mock_req.code = "VG.001"
        mock_req.version = "1.0.0"
        mock_feature = Mock()
        mock_feature.id = "FET001"
        mock_feature.version = "1.0.0"

        metadata = ValidationContext(
            features=[
                FeatureStatus(
                    feature=mock_feature,
                    status="PASS",
                    requirements=[RequirementStatus(requirement=mock_req, status="PASS")],
                )
            ]
        )
        results = Results(
            asset="test.usd",
            issues=[Issue(severity=IssueSeverity.FAILURE, rule=MyRuleChecker, message="failure")],
        )
        with TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "results.json")
            export_json_file(json_path, ResultsList([results]), metadata=metadata)
            data = json.loads(pathlib.Path(json_path).read_text())
            self.assertIn("features", data)
            self.assertEqual(data["features"][0]["id"], "FET001")
            self.assertEqual(data["features"][0]["status"], "PASS")
            self.assertIn("rules", data)

    def test_issue_json_with_requirement(self):
        """JSON output includes requirement info when present on an issue"""
        req = CapRequirement(code="VG.001", version="1.0.0")
        issue = Issue(
            severity=IssueSeverity.FAILURE,
            message="failure with requirement",
            requirement=req,
        )
        result = json.loads(json.dumps(issue, cls=IssueJSONEncoder))
        self.assertIn("requirement", result)
        self.assertEqual(result["requirement"]["code"], "VG.001")
        self.assertEqual(result["requirement"]["version"], "1.0.0")

    def test_issue_json_without_requirement(self):
        """JSON output omits requirement when not present on an issue"""
        issue = Issue(
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            message="no requirement",
        )
        result = json.loads(json.dumps(issue, cls=IssueJSONEncoder))
        self.assertNotIn("requirement", result)
