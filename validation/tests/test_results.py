# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia import Issue, IssueSeverity, Results, Suggestion


class MyRuleChecker:
    pass


class ResultsTest(unittest.TestCase):
    def test_str(self):
        # Given
        result = Results(
            asset="Any asset", issues=[Issue(severity=IssueSeverity.FAILURE, rule=MyRuleChecker, message="failure")]
        )
        # When
        actual = str(result)
        # Then
        self.assertEqual(
            actual,
            """Results(
    asset="Any asset",
    issues=[
        Issue(
            message="failure",
            severity=IssueSeverity.FAILURE,
            rule=MyRuleChecker,
            at=None,
            suggestion=None
        )
    ]
)""",
        )

    def test_create_preserves_suggestions(self):
        """Results.create copies issues via dataclasses.replace; suggestions must be preserved."""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        issue = Issue(severity=IssueSeverity.FAILURE, message="issue", suggestions=[s1, s2])
        result = Results.create(asset="my.usd", issues=[issue])
        created_issue = next(iter(result.issues))
        self.assertEqual(created_issue.suggestions, (s1, s2))
        self.assertIs(created_issue.suggestion, s1)
