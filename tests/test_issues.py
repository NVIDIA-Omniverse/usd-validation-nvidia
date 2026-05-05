# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from collections.abc import Callable
from enum import Enum
from unittest.mock import Mock

from common import get_url
from pxr import Sdf, Usd

from nvidia_usd_validation import (
    AnchoredAssetPathsChecker,
    EditTargetId,
    EditTargetIdList,
    Issue,
    IssueGroupsBy,
    IssuePredicate,
    IssuePredicates,
    IssueSeverity,
    LayerId,
    PrimId,
    StageId,
    Suggestion,
)
from nvidia_usd_validation.capabilities import Requirements


class MyRuleChecker:
    pass


class IssueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        super().setUp()
        self.layer = Mock(spec=Sdf.Layer)
        self.layer.identifier = get_url("helloworld.usda")
        self.stage = Mock(spec=Usd.Stage)
        self.stage.GetRootLayer.return_value = self.layer
        self.node = Mock(spec=Sdf.PrimSpec)
        self.node.path = "/World"
        self.node.layer = self.layer
        self.prim = Mock(spec=Usd.Prim)
        self.prim.GetStage.return_value = self.stage
        self.prim.GetPrimPath.return_value = self.node.path
        self.prim.GetPrimStack.return_value = [self.node]
        self.prim.GetName.return_value = "PrimA"
        # Parent Prim
        parent_prim = Mock(spec=Usd.Prim)
        parent_prim.GetPath.return_value = Sdf.Path.absoluteRootPath
        parent_prim.GetName.return_value = "PrimParent"
        self.prim.GetParent.return_value = parent_prim
        # Variants
        mocked_variant_sets = Mock(spec=Usd.VariantSets)
        mocked_variant_sets.GetNames.return_value = ["VariantA", "VariantB"]
        mocked_variant_set = Mock(spec=Usd.VariantSet)
        mocked_variant_set.GetVariantSelection.return_value = "Selected_Variant"
        mocked_variant_sets.GetVariantSet.return_value = mocked_variant_set
        self.prim.GetVariantSets.return_value = mocked_variant_sets
        parent_prim.GetVariantSets.return_value = mocked_variant_sets

    async def test_issue_construct_rule(self):
        # Given
        class Rule:
            pass

        # When / Then
        with self.assertRaises(ValueError):
            Issue(message="message", severity=IssueSeverity.ERROR, rule=Rule())

    async def test_issue_construct_message(self):
        # Given / When / Then
        with self.assertRaises(ValueError):
            Issue(message=None, severity=IssueSeverity.ERROR, rule=MyRuleChecker)

    async def test_issue_construct_severity(self):
        # Given / When / Then
        with self.assertRaises(ValueError):
            Issue(message="message", severity=None, rule=MyRuleChecker)

    async def test_suggestions_from_suggestion(self):
        """Issue(suggestion=s) → suggestions == (s,)"""
        s = Suggestion(callable=lambda stage, at: None, message="fix it")
        issue = Issue(message="msg", severity=IssueSeverity.ERROR, suggestion=s)
        self.assertEqual(issue.suggestions, (s,))
        self.assertIs(issue.suggestion, s)

    async def test_suggestions_from_suggestions_list(self):
        """Issue(suggestions=[s1, s2]) → suggestion == s1"""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        issue = Issue(message="msg", severity=IssueSeverity.ERROR, suggestions=[s1, s2])
        self.assertEqual(issue.suggestions, (s1, s2))
        self.assertIs(issue.suggestion, s1)

    async def test_suggestion_and_suggestions_raises(self):
        """Passing both suggestion and suggestions raises ValueError."""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        with self.assertRaises(ValueError):
            Issue(message="msg", severity=IssueSeverity.ERROR, suggestion=s1, suggestions=[s2])

    async def test_suggestions_empty_when_no_suggestion(self):
        """Issue() → suggestion is None, suggestions == ()"""
        issue = Issue(message="msg", severity=IssueSeverity.ERROR)
        self.assertEqual(issue.suggestions, ())
        self.assertIsNone(issue.suggestion)

    async def test_suggestions_validates_items(self):
        """suggestions items must be Suggestion instances"""
        with self.assertRaises(TypeError):
            Issue(message="msg", severity=IssueSeverity.ERROR, suggestions=["not a suggestion"])

    async def test_issue_none_has_empty_suggestions(self):
        """Issue.none() still works and has empty suggestions"""
        issue = Issue.none()
        self.assertEqual(issue.suggestions, ())
        self.assertIsNone(issue.suggestion)

    async def test_issue_hashable_and_equals(self):
        issue1 = Issue(
            message="A message",
            severity=IssueSeverity.ERROR,
            rule=MyRuleChecker,
            at=self.prim,
        )
        issue2 = Issue(
            message="A message",
            severity=IssueSeverity.ERROR,
            rule=MyRuleChecker,
            at=self.prim,
        )

        self.assertEqual(issue1, issue2)
        self.assertEqual(hash(issue1), hash(issue2))

        d = {issue1: "value"}
        self.assertEqual(d[issue2], "value")
        self.assertEqual(len(d), 1)

    async def test_suggestion_hashable_and_equals(self):
        def func(a, b):
            pass

        suggestion1 = Suggestion(
            message="A suggestion",
            callable=func,
            at=[self.prim],
        )
        suggestion2 = Suggestion(
            message="A suggestion",
            callable=func,
            at=[self.prim],
        )

        self.assertEqual(suggestion1, suggestion2)
        self.assertEqual(hash(suggestion1), hash(suggestion2))

        d = {suggestion1: "value"}
        self.assertEqual(d[suggestion2], "value")
        self.assertEqual(len(d), 1)


class IssueGroupsByTest(unittest.IsolatedAsyncioTestCase):
    def test_asset(self):
        stage_id = StageId(root_layer=LayerId(identifier="helloworld.usda"))
        issues = [
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim1", asset=stage_id),
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim2", asset=stage_id),
        ]

        result = IssueGroupsBy.asset()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), stage_id)

    def test_rule(self):
        issues = [
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim1", rule=MyRuleChecker),
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim2", rule=MyRuleChecker),
        ]

        result = IssueGroupsBy.rule()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), MyRuleChecker)

    def test_message(self):
        issues = [
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim1", rule=MyRuleChecker),
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim2", rule=MyRuleChecker),
        ]

        result = IssueGroupsBy.message()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), "This is an error at .*")

    def test_severity(self):
        issues = [
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim1", rule=MyRuleChecker),
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim2", rule=MyRuleChecker),
        ]

        result = IssueGroupsBy.severity()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), IssueSeverity.ERROR)

    def test_code(self):
        issues = [
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim1", requirement=Requirements.AA_001),
            Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim2", requirement=Requirements.AA_001),
        ]

        result = IssueGroupsBy.code()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), Requirements.AA_001.code)

        # Test predicates
        p0 = IssuePredicates.HasCode()
        p1 = IssuePredicates.MatchesCode(Requirements.AA_001.code)
        p2 = IssuePredicates.MatchesCode(Requirements.AA_002.code)

        # Add an issue without code
        issues.append(Issue(severity=IssueSeverity.ERROR, message="This is an error at Prim3"))
        self.assertTrue(p0(issues[0]))
        self.assertTrue(p1(issues[0]))
        self.assertFalse(p2(issues[0]))
        self.assertFalse(p0(issues[2]))
        self.assertFalse(p1(issues[2]))
        self.assertFalse(p2(issues[2]))

    def test_requirement(self):
        class MyRequirement(Enum):
            REQ001 = ("001", "message", ("tag1", "tag2"))

            def __init__(self, code, message, tags):
                self.code = code
                self.message = message
                self.tags = tags

        issues = [
            Issue(severity=IssueSeverity.ERROR, requirement=MyRequirement.REQ001),
            Issue(severity=IssueSeverity.ERROR, requirement=MyRequirement.REQ001),
        ]
        self.assertEqual(issues[0].code, "001")
        self.assertEqual(issues[0].message, "message")
        self.assertEqual(issues[0].tags, ("tag1", "tag2"))

        result = IssueGroupsBy.code()(issues)
        groups = set()
        for group, issue in result:
            groups.add(group)
        self.assertEqual(len(groups), 1)
        self.assertEqual(next(iter(groups)), "001")


class MyRule:
    pass


class IssuePredicatesTest(unittest.IsolatedAsyncioTestCase):
    def test_instance(self):
        def f0(issue: Issue) -> bool:
            return True

        f1: Callable[[Issue], bool] = lambda issue: True

        class F2(IssuePredicate):
            def __call__(self, issue: Issue) -> bool:
                return True

        self.assertIsInstance(f0, IssuePredicate)
        self.assertIsInstance(f1, IssuePredicate)
        self.assertIsInstance(F2, IssuePredicate)

    def test_and_one(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        issue = Issue(message="Hi", severity=IssueSeverity.ERROR, rule=MyRule)

        # When
        predicate = IssuePredicates.And(p0)

        # Then
        self.assertTrue(predicate(issue))

    def test_and_two(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        p1 = IssuePredicates.IsError()
        issue = Issue(message="Hi", severity=IssueSeverity.ERROR, rule=MyRule)

        # When
        predicate = IssuePredicates.And(p0, p1)

        # Then
        self.assertTrue(predicate(issue))

    def test_and_three(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        p1 = IssuePredicates.IsError()
        p2 = IssuePredicates.IsRule(MyRule)
        issue = Issue(message="Hi", severity=IssueSeverity.ERROR, rule=MyRule)

        # When
        predicate = IssuePredicates.And(p0, p1, p2)

        # Then
        self.assertTrue(predicate(issue))

    def test_or_one(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        issue = Issue(message="Hi", severity=IssueSeverity.ERROR, rule=MyRule)

        # When
        predicate = IssuePredicates.Or(p0)

        # Then
        self.assertTrue(predicate(issue))

    def test_or_two(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        p1 = IssuePredicates.IsError()
        issue = Issue(message="Hi", severity=IssueSeverity.WARNING, rule=MyRule)

        # When
        predicate = IssuePredicates.Or(p0, p1)

        # Then
        self.assertTrue(predicate(issue))

    def test_or_three(self):
        # Given
        p0 = IssuePredicates.ContainsMessage("Hi")
        p1 = IssuePredicates.IsError()
        p2 = IssuePredicates.IsRule(MyRule)
        issue = Issue(message="H", severity=IssueSeverity.WARNING, rule=MyRule)

        # When
        predicate = IssuePredicates.Or(p0, p1, p2)

        # Then
        self.assertTrue(predicate(issue))

    def test_repr(self):
        self.assertEqual(repr(IssuePredicates.Any()), "IssuePredicates.Any(){}")
        self.assertEqual(repr(IssuePredicates.IsFailure()), "IssuePredicates.IsFailure(){}")
        self.assertEqual(repr(IssuePredicates.IsWarning()), "IssuePredicates.IsWarning(){}")
        self.assertEqual(repr(IssuePredicates.IsError()), "IssuePredicates.IsError(){}")
        self.assertEqual(repr(IssuePredicates.ContainsMessage("hi")), "IssuePredicates.ContainsMessage('hi',){}")
        self.assertEqual(repr(IssuePredicates.IsRule("MyRule")), "IssuePredicates.IsRule('MyRule',){}")
        self.assertEqual(
            repr(IssuePredicates.IsRule(MyRule)), "IssuePredicates.IsRule(<class 'test_issues.MyRule'>,){}"
        )
        self.assertEqual(repr(IssuePredicates.HasLocation()), "IssuePredicates.HasLocation(){}")
        self.assertEqual(repr(IssuePredicates.HasRootLayer()), "IssuePredicates.HasRootLayer(){}")
        self.assertEqual(
            repr(IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule("MyRule"))),
            "IssuePredicates.And(IssuePredicates.IsFailure(){}, IssuePredicates.IsRule('MyRule',){}){}",
        )
        self.assertEqual(
            repr(IssuePredicates.Or(IssuePredicates.IsFailure(), IssuePredicates.IsRule("MyRule"))),
            "IssuePredicates.Or(IssuePredicates.IsFailure(){}, IssuePredicates.IsRule('MyRule',){}){}",
        )
        self.assertEqual(
            repr(IssuePredicates.HasCode()),
            "IssuePredicates.HasCode(){}",
        )
        self.assertEqual(
            repr(IssuePredicates.MatchesCode(Requirements.AA_001.code)),
            "IssuePredicates.MatchesCode('AA.001',){}",
        )

    def test_matches_token(self):
        issue = Issue(
            severity=IssueSeverity.ERROR,
            message="This is an error at Prim1",
            requirement=Requirements.AA_001,
            rule=AnchoredAssetPathsChecker,
        )

        self.assertTrue(IssuePredicates.MatchesToken(Requirements.AA_001.code)(issue))
        self.assertFalse(IssuePredicates.MatchesToken(Requirements.AA_002.code)(issue))

        self.assertTrue(IssuePredicates.MatchesToken("AnchoredAssetPathsChecker")(issue))
        self.assertFalse(IssuePredicates.MatchesToken("AnchoredAssetPathsChecker2")(issue))

        self.assertTrue(IssuePredicates.MatchesToken("Prim1")(issue))
        self.assertFalse(IssuePredicates.MatchesToken("Prim2")(issue))


class FixSitesForTests(unittest.IsolatedAsyncioTestCase):
    """Tests for Issue.fix_sites_for(), all_fix_sites, and default_fix_site."""

    def _make_issue(self, suggestion=None, suggestions=None):
        """Helper: create an Issue with a PrimId that has two spec locations."""
        layer_a = LayerId(identifier="/layers/a.usd")
        layer_b = LayerId(identifier="/layers/b.usd")
        self.target_a = EditTargetId(layer_id=layer_a, path=Sdf.Path("/Prim"))
        self.target_b = EditTargetId(layer_id=layer_b, path=Sdf.Path("/Prim"))
        stage_id = StageId(root_layer=layer_a)
        prim_id = PrimId(
            stage_id=stage_id,
            path=Sdf.Path("/Prim"),
            spec_ids=EditTargetIdList([self.target_a, self.target_b]),
        )
        return Issue(
            message="test issue",
            severity=IssueSeverity.FAILURE,
            at=prim_id,
            suggestion=suggestion,
            suggestions=suggestions,
        )

    async def test_fix_sites_for_no_suggestion(self):
        """No suggestion → all spec locations returned."""
        issue = self._make_issue()
        sites = issue.fix_sites_for()
        self.assertEqual(sites, [self.target_a, self.target_b])

    async def test_fix_sites_for_unconstrained_suggestion(self):
        """Suggestion with no at constraint → all spec locations returned."""
        s = Suggestion(callable=lambda stage, at: None, message="fix", at=None)
        issue = self._make_issue(suggestion=s)
        sites = issue.fix_sites_for(s)
        self.assertEqual(sites, [self.target_a, self.target_b])

    async def test_fix_sites_for_constrained_suggestion(self):
        """Suggestion constrained to layer_a → target_a first, then target_b."""
        layer_a_sdf = Mock(spec=Sdf.Layer)
        layer_a_sdf.identifier = "/layers/a.usd"
        s = Suggestion(callable=lambda stage, at: None, message="fix", at=[layer_a_sdf])
        issue = self._make_issue(suggestion=s)
        sites = issue.fix_sites_for(s)
        # target_a matches the constraint (included), target_b does not (excluded)
        self.assertEqual(sites[0], self.target_a)
        self.assertIn(self.target_b, sites)
        self.assertEqual(len(sites), 2)

    async def test_fix_sites_for_different_suggestions_different_results(self):
        """Two suggestions with different at constraints yield different orderings."""
        layer_a_sdf = Mock(spec=Sdf.Layer)
        layer_a_sdf.identifier = "/layers/a.usd"
        layer_b_sdf = Mock(spec=Sdf.Layer)
        layer_b_sdf.identifier = "/layers/b.usd"
        s1 = Suggestion(callable=lambda stage, at: None, message="fix in A", at=[layer_a_sdf])
        s2 = Suggestion(callable=lambda stage, at: None, message="fix in B", at=[layer_b_sdf])
        issue = self._make_issue(suggestions=[s1, s2])

        sites_s1 = issue.fix_sites_for(s1)
        sites_s2 = issue.fix_sites_for(s2)

        # s1 prefers target_a, s2 prefers target_b
        self.assertEqual(sites_s1[0], self.target_a)
        self.assertEqual(sites_s2[0], self.target_b)

    async def test_fix_sites_for_defaults_to_issue_suggestion(self):
        """fix_sites_for() with no arg uses issue.suggestion."""
        layer_a_sdf = Mock(spec=Sdf.Layer)
        layer_a_sdf.identifier = "/layers/a.usd"
        s = Suggestion(callable=lambda stage, at: None, message="fix", at=[layer_a_sdf])
        issue = self._make_issue(suggestion=s)
        # No argument → uses issue.suggestion (s)
        sites = issue.fix_sites_for()
        self.assertEqual(sites[0], self.target_a)

    async def test_all_fix_sites_delegates_to_fix_sites_for(self):
        """all_fix_sites uses fix_sites_for(self.suggestion)."""
        layer_a_sdf = Mock(spec=Sdf.Layer)
        layer_a_sdf.identifier = "/layers/a.usd"
        s = Suggestion(callable=lambda stage, at: None, message="fix", at=[layer_a_sdf])
        issue = self._make_issue(suggestion=s)
        self.assertEqual(issue.all_fix_sites, issue.fix_sites_for(s))

    async def test_default_fix_site_is_first_all_fix_sites(self):
        """default_fix_site is the first element of all_fix_sites."""
        s = Suggestion(callable=lambda stage, at: None, message="fix")
        issue = self._make_issue(suggestion=s)
        self.assertEqual(issue.default_fix_site, issue.all_fix_sites[0])

    async def test_fix_sites_for_no_at(self):
        """Issue with no at → empty list."""
        issue = Issue(message="msg", severity=IssueSeverity.FAILURE)
        self.assertEqual(issue.fix_sites_for(), [])
        self.assertEqual(issue.all_fix_sites, [])
        self.assertIsNone(issue.default_fix_site)
