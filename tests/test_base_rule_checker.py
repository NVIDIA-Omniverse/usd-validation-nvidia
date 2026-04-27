# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from dataclasses import dataclass
from unittest.mock import Mock

from common import get_url
from nvidia_usd_validation import BaseRuleChecker, Issue, IssueSeverity, ParameterMapping, ParameterType, Suggestion
from pxr import Sdf, Usd


@dataclass
class TestParameter:
    """Test parameter class that conforms to the Parameter protocol."""

    display_name: str
    type: ParameterType
    assigned_value: float | str | None
    enum_values: tuple[str, ...] | None = None


class MyRuleChecker(BaseRuleChecker):
    """
    Check that all active prims are meshes for xforms
    """

    def CheckPrim(self, prim) -> None:
        if prim.GetTypeName() not in ("Mesh", "Xform") and prim.IsActive():
            self._AddFailedCheck(
                message=f"Prim <{prim.GetPath()}> has unsupported type '{prim.GetTypeName()}'.",
                at=prim,
                suggestion=Suggestion(
                    lambda _, _prim: _prim.SetActive(False),
                    "Disable Prim",
                ),
            )


class BaseRuleCheckerTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        super().setUp()
        self.message = "A message"
        self.suggestion = Mock(spec=Suggestion)
        self.layer = Mock(spec=Sdf.Layer)
        self.layer.identifier = get_url("helloworld.usda")
        self.stage = Mock(spec=Usd.Stage)
        self.stage.GetRootLayer.return_value = self.layer
        self.node = Mock(spec=Sdf.PrimSpec)
        self.node.path = "/World/cube"
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

        # Parameter setup for parameter-related tests
        self.up_axis_param = TestParameter(
            display_name="up_axis", type=ParameterType.ENUM, assigned_value="Z", enum_values=("X", "Y", "Z")
        )
        self.tolerance_param = TestParameter(display_name="tolerance", type=ParameterType.FLOAT, assigned_value=0.001)
        self.test_parameters = ParameterMapping([self.up_axis_param, self.tolerance_param])

    def test_GetDescription(self):
        class Test0(BaseRuleChecker):
            pass

        class Test1(BaseRuleChecker):
            """"""

        class Test2(BaseRuleChecker):
            """Single line doc."""

        class Test3(BaseRuleChecker):
            """First line doc.
            Args
                a: First argument
            """

        class Test4(BaseRuleChecker):
            """
            Second line doc.
            Args
                a: First argument
            """

        class Test5(BaseRuleChecker):
            @classmethod
            def GetDescription(cls):
                return "\n".join(["Third line doc.", "Args", "    a: First argument"])

        self.assertEqual(Test0.GetDescription(), f"Docstring not found for rule class {Test0.__name__}.")
        self.assertEqual(Test1.GetDescription(), f"Docstring not found for rule class {Test1.__name__}.")
        self.assertEqual(Test2.GetDescription(), "Single line doc.")
        self.assertEqual(Test3.GetDescription(), "First line doc.\nArgs\n    a: First argument")
        self.assertEqual(Test4.GetDescription(), "Second line doc.\nArgs\n    a: First argument")
        self.assertEqual(Test5.GetDescription(), "Third line doc.\nArgs\n    a: First argument")

    async def test_add_failed_check_message(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddFailedCheck(
            message=self.message,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(), [Issue(severity=IssueSeverity.FAILURE, rule=MyRuleChecker, message=self.message)]
        )

    async def test_add_error_message(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddError(
            message=self.message,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(), [Issue(severity=IssueSeverity.ERROR, rule=MyRuleChecker, message=self.message)]
        )

    async def test_add_warning_message(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddWarning(
            message=self.message,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(), [Issue(severity=IssueSeverity.WARNING, rule=MyRuleChecker, message=self.message)]
        )

    async def test_add_failed_check(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddFailedCheck(
            message=self.message,
            at=self.prim,
            suggestion=self.suggestion,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(),
            [
                Issue(
                    message=self.message,
                    severity=IssueSeverity.FAILURE,
                    rule=MyRuleChecker,
                    at=self.prim,
                    suggestion=self.suggestion,
                )
            ],
        )

    async def test_add_error_check(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddError(
            message=self.message,
            at=self.prim,
            suggestion=self.suggestion,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(),
            [
                Issue(
                    message=self.message,
                    severity=IssueSeverity.ERROR,
                    rule=MyRuleChecker,
                    at=self.prim,
                    suggestion=self.suggestion,
                )
            ],
        )

    async def test_add_warning_check(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddWarning(
            message=self.message,
            at=self.prim,
            suggestion=self.suggestion,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(),
            [
                Issue(
                    message=self.message,
                    severity=IssueSeverity.WARNING,
                    rule=MyRuleChecker,
                    at=self.prim,
                    suggestion=self.suggestion,
                )
            ],
        )

    async def test_add_info_check(self):
        # Given / When
        checker = MyRuleChecker()
        checker._AddInfo(
            message=self.message,
            at=self.prim,
        )
        # Then
        self.assertEqual(
            checker.GetIssues(),
            [
                Issue(
                    message=self.message,
                    severity=IssueSeverity.INFO,
                    rule=MyRuleChecker,
                    at=self.prim,
                )
            ],
        )

    async def test_add_failed_check_with_suggestions(self):
        """_AddFailedCheck with suggestions= passes through to Issue"""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        checker = MyRuleChecker()
        checker._AddFailedCheck(message=self.message, suggestions=[s1, s2])
        issues = checker.GetIssues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].suggestions, (s1, s2))
        self.assertIs(issues[0].suggestion, s1)

    async def test_add_error_with_suggestions(self):
        """_AddError with suggestions= passes through to Issue"""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        s2 = Suggestion(callable=lambda stage, at: None, message="fix B")
        checker = MyRuleChecker()
        checker._AddError(message=self.message, suggestions=[s1, s2])
        issues = checker.GetIssues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].suggestions, (s1, s2))

    async def test_add_warning_with_suggestions(self):
        """_AddWarning with suggestions= passes through to Issue"""
        s1 = Suggestion(callable=lambda stage, at: None, message="fix A")
        checker = MyRuleChecker()
        checker._AddWarning(message=self.message, suggestions=[s1])
        issues = checker.GetIssues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].suggestions, (s1,))

    async def test_add_failed_check_backwards_compat(self):
        """_AddFailedCheck with suggestion= still works (1 suggestion)"""
        s = Suggestion(callable=lambda stage, at: None, message="fix it")
        checker = MyRuleChecker()
        checker._AddFailedCheck(message=self.message, suggestion=s)
        issues = checker.GetIssues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].suggestions, (s,))
        self.assertIs(issues[0].suggestion, s)

    def test_parameters_property(self):
        """Test that the parameters property works correctly."""
        # Test with None parameters (default) - should get empty ParameterMapping
        checker = MyRuleChecker()
        self.assertIsNotNone(checker.parameters)
        self.assertEqual(len(checker.parameters), 0)

        # Test with a proper ParameterMapping object
        checker = MyRuleChecker(parameters=self.test_parameters)
        self.assertEqual(checker.parameters, self.test_parameters)
        self.assertIsNotNone(checker.parameters)
        self.assertEqual(len(checker.parameters), 2)

    def test_parameters_access(self):
        """Test that parameters can be accessed via the property."""
        checker = MyRuleChecker(parameters=self.test_parameters)

        # Verify parameters are accessible
        self.assertEqual(checker.parameters, self.test_parameters)
        # Verify we can access parameter
        retrieved_param = checker.parameters["up_axis"]
        self.assertEqual(retrieved_param.assigned_value, "Z")

    def test_parameters_with_keyword_argument(self):
        """Test that the parameters argument works with keyword syntax."""
        checker = MyRuleChecker(parameters=self.test_parameters)
        self.assertEqual(checker.parameters, self.test_parameters)

    def test_deprecated_parameters_backward_compatibility(self):
        """Test that deprecated parameters still work for backward compatibility."""
        # Test with old-style positional arguments
        checker = MyRuleChecker(False, False, True)
        self.assertFalse(checker._verbose)
        self.assertFalse(checker._consumerLevelChecks)
        self.assertTrue(checker._assetLevelChecks)
        self.assertIsNotNone(checker.parameters)
        self.assertEqual(len(checker.parameters), 0)

        # Test with old-style keyword arguments
        checker = MyRuleChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=False)
        self.assertTrue(checker._verbose)
        self.assertTrue(checker._consumerLevelChecks)
        self.assertFalse(checker._assetLevelChecks)
        self.assertIsNotNone(checker.parameters)
        self.assertEqual(len(checker.parameters), 0)

    def test_default_values_for_deprecated_parameters(self):
        """Test default values of deprecated parameters."""
        checker = MyRuleChecker()
        self.assertFalse(checker._verbose)
        self.assertFalse(checker._consumerLevelChecks)
        self.assertTrue(checker._assetLevelChecks)  # Default is True
