# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock

from usd_validation_nvidia import (
    BaseRuleChecker,
    Parameter,
    RequirementsRegistry,
    add_registry_requirement_callback,
    register_requirements,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import RequirementRef as RequirementRefDTO


class MyRequirement(Enum):
    REQ001 = ("001", "message", None, None, (), "1.0.0", ())
    REQ002 = ("002", "message", None, None, (), "1.0.0", ())
    REQ003 = ("003", "message", None, None, (), "1.0.0", ())
    REQ004 = ("004", "message", None, None, (), "1.0.0", ())

    def __init__(self, code, message, display_name=None, path=None, tags=(), version="1.0.0", parameters=()):
        self.code = code
        self.message = message
        self.display_name = display_name
        self.path = path
        self.tags = tags
        self.version = version
        self.parameters = parameters
        self.examples = ()


class MyRule1(BaseRuleChecker): ...


class MyRule2(BaseRuleChecker): ...


class MyRule3(BaseRuleChecker): ...


class RequirementTests(unittest.TestCase):
    def setUp(self):
        register_requirements(MyRequirement.REQ001)(MyRule1)
        register_requirements(MyRequirement.REQ002)(MyRule2)

    def tearDown(self):
        unregister_requirements(MyRule1)
        unregister_requirements(MyRule2)

    def test_get_requirements_ok(self):
        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [MyRequirement.REQ001])
        self.assertEqual(registry.get_requirements(MyRule2), [MyRequirement.REQ002])
        self.assertEqual(registry.get_requirements(MyRule3), [])

    def test_get_latest_requirements_ok(self):
        registry = RequirementsRegistry()
        latest_reqs = registry.latest_requirements

        # Should contain both registered requirements
        self.assertIn(MyRequirement.REQ001, latest_reqs)
        self.assertIn(MyRequirement.REQ002, latest_reqs)

    def test_get_validator_ok(self):
        self.assertEqual(RequirementsRegistry().get_validator(MyRequirement.REQ001), MyRule1)
        self.assertEqual(RequirementsRegistry().get_validator(MyRequirement.REQ002), MyRule2)
        self.assertIsNone(RequirementsRegistry().get_validator(MyRequirement.REQ003))

    def test_get_validators_ok(self):
        self.assertCountEqual(
            RequirementsRegistry().get_validators([MyRequirement.REQ001, MyRequirement.REQ002]), [MyRule1, MyRule2]
        )
        self.assertCountEqual(
            RequirementsRegistry().get_validators([MyRequirement.REQ001, MyRequirement.REQ002, MyRequirement.REQ003]),
            [MyRule1, MyRule2],
        )

    def test_implemented_ok(self):
        self.assertTrue(RequirementsRegistry().is_implemented(MyRequirement.REQ001))
        self.assertTrue(RequirementsRegistry().is_implemented(MyRequirement.REQ002))
        self.assertFalse(RequirementsRegistry().is_implemented(MyRequirement.REQ003))

    def test_all_implemented_ok(self):
        self.assertTrue(RequirementsRegistry().all_implemented([MyRequirement.REQ001, MyRequirement.REQ002]))
        self.assertFalse(
            RequirementsRegistry().all_implemented([MyRequirement.REQ001, MyRequirement.REQ002, MyRequirement.REQ003])
        )

    def test_is_registered_ok(self):
        self.assertTrue(RequirementsRegistry().is_registered(MyRule1, MyRequirement.REQ001))
        self.assertTrue(RequirementsRegistry().is_registered(MyRule2, MyRequirement.REQ002))
        self.assertFalse(RequirementsRegistry().is_registered(MyRule3, MyRequirement.REQ003))

    def test_get_requirement_from_code_ok(self):
        self.assertEqual(RequirementsRegistry().find("001"), MyRequirement.REQ001)
        self.assertIsNone(RequirementsRegistry().find("003"))

    def test_register_requirement_twice(self):
        with self.assertRaises(ValueError):
            register_requirements(MyRequirement.REQ001)(MyRule3)

        self.assertEqual(RequirementsRegistry().get_requirements(MyRule1), [MyRequirement.REQ001])
        self.assertEqual(RequirementsRegistry().get_requirements(MyRule3), [])
        self.assertEqual(RequirementsRegistry().get_validator(MyRequirement.REQ001), MyRule1)
        self.assertTrue(RequirementsRegistry().is_registered(MyRule1, MyRequirement.REQ001))

    def test_register_requirement_ref(self):
        requirement_ref = RequirementRefDTO(code="REF.001", version="1.0.0")

        register_requirements(requirement_ref)(MyRule3)

        try:
            registry = RequirementsRegistry()
            self.assertEqual(registry.get_requirements(MyRule3), [requirement_ref])
            self.assertEqual(registry.get_validator(requirement_ref), MyRule3)
            self.assertTrue(registry.is_registered(MyRule3, requirement_ref))
            self.assertIsNone(registry.find_requirement(requirement_ref.code, requirement_ref.version))
            self.assertNotIn(requirement_ref, list(registry))
        finally:
            unregister_requirements(MyRule3)

    def test_requirement_ref_resolves_registered_definition(self):
        requirement_ref = RequirementRefDTO(code=MyRequirement.REQ003.code, version=MyRequirement.REQ003.version)
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)

        try:
            self.assertEqual(registry.get_requirements(MyRule3), [requirement_ref])

            registry.add(MyRequirement.REQ003)

            self.assertEqual(registry.get_requirements(MyRule3), [MyRequirement.REQ003])
            self.assertEqual(registry.get_validator(MyRequirement.REQ003), MyRule3)
        finally:
            unregister_requirements(MyRule3)
        try:
            self.assertIs(
                registry.find_requirement(MyRequirement.REQ003.code, MyRequirement.REQ003.version),
                MyRequirement.REQ003,
            )
        finally:
            registry.remove(MyRequirement.REQ003)

    def test_removing_resolved_requirement_ref_keeps_validator_binding(self):
        requirement_ref = RequirementRefDTO(code=MyRequirement.REQ003.code, version=MyRequirement.REQ003.version)
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)

        try:
            registry.add(MyRequirement.REQ003)
            self.assertEqual(registry.get_requirements(MyRule3), [MyRequirement.REQ003])

            registry.remove(MyRequirement.REQ003)

            self.assertEqual(registry.get_requirements(MyRule3), [requirement_ref])
            self.assertEqual(registry.get_validator(requirement_ref), MyRule3)
            self.assertTrue(registry.is_registered(MyRule3, requirement_ref))
        finally:
            unregister_requirements(MyRule3)

    def test_unregister_requirement_ref(self):
        requirement_ref = RequirementRefDTO(code="REF.001", version="1.0.0")
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)

        unregister_requirements(MyRule3)

        self.assertEqual(registry.get_requirements(MyRule3), [])
        self.assertIsNone(registry.get_validator(requirement_ref))
        self.assertFalse(registry.is_registered(MyRule3, requirement_ref))
        self.assertIsNone(registry.find_requirement(requirement_ref.code, requirement_ref.version))

    def test_requirement_ref_issue_helpers(self):
        requirement_ref = RequirementRefDTO(code="REF.001", version="1.0.0")
        register_requirements(requirement_ref)(MyRule3)

        try:
            checker = MyRule3()
            checker._AddFailedCheck(message="failure", requirement=requirement_ref)
            checker._AddWarning(message="warning", requirement=requirement_ref)
            checker._AddError(message="error", requirement=requirement_ref)
            checker._AddInfo(message="info", requirement=requirement_ref)

            self.assertEqual(
                [issue.requirement for issue in checker.GetIssues()],
                [requirement_ref, requirement_ref, requirement_ref, requirement_ref],
            )
        finally:
            unregister_requirements(MyRule3)

    def test_register_invalid_requirement_raises(self):
        with self.assertRaisesRegex(
            TypeError, r"register_requirements expects Requirement or RequirementRef objects\."
        ):
            register_requirements(object())(MyRule3)

    def test_register_requirements_override(self):
        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [MyRequirement.REQ001])
        self.assertEqual(registry.get_validator(MyRequirement.REQ001), MyRule1)
        self.assertTrue(registry.is_registered(MyRule1, MyRequirement.REQ001))
        self.assertTrue(registry.is_implemented(MyRequirement.REQ001))

        @register_requirements(MyRequirement.REQ001, override=True)
        class MyRule4(MyRule1): ...

        try:
            # ``get_requirements`` returns only requirements where the rule is the
            # primary (last-registered) validator, so MyRule1 reports nothing here.
            self.assertEqual(registry.get_requirements(MyRule1), [])
            self.assertEqual(registry.get_requirements(MyRule4), [MyRequirement.REQ001])
            self.assertEqual(registry.get_validator(MyRequirement.REQ001), MyRule4)
            # ``is_registered`` reflects actual list membership (OMPE-64259): the
            # original rule is still in the registration list, just not the primary.
            self.assertTrue(registry.is_registered(MyRule1, MyRequirement.REQ001))
            self.assertTrue(registry.is_registered(MyRule4, MyRequirement.REQ001))
            self.assertTrue(registry.is_implemented(MyRequirement.REQ001))
        finally:
            unregister_requirements(MyRule4)

    def test_overridden_rule_can_emit_issue(self):
        # OMPE-64259: a rule that has been overridden (not the primary validator
        # anymore) must still be allowed to emit Issues against the requirement —
        # otherwise Issue.__post_init__ raises "Rule X is not registered to
        # requirement Y" and the rule check fails uncaught.
        from usd_validation_nvidia import Issue, IssueSeverity

        @register_requirements(MyRequirement.REQ001, override=True)
        class MyRule4(MyRule1): ...

        try:
            Issue(
                message="should not raise",
                severity=IssueSeverity.FAILURE,
                rule=MyRule1,
                requirement=MyRequirement.REQ001,
            )
        finally:
            unregister_requirements(MyRule4)

    def test_unregister_non_primary_rule_cleans_up(self):
        # OMPE-64259: unregistering a rule that is not the primary validator (because
        # another rule registered with override=True afterwards) must still remove it
        # from the requirement's rule list. Previously the unregister path iterated
        # ``get_requirements`` which only returns primary registrations, so the
        # original rule's entry leaked.
        registry = RequirementsRegistry()

        @register_requirements(MyRequirement.REQ001, override=True)
        class MyRule4(MyRule1): ...

        try:
            self.assertTrue(registry.is_registered(MyRule1, MyRequirement.REQ001))

            unregister_requirements(MyRule1)

            self.assertFalse(registry.is_registered(MyRule1, MyRequirement.REQ001))
            self.assertTrue(registry.is_registered(MyRule4, MyRequirement.REQ001))
            self.assertEqual(registry.get_validator(MyRequirement.REQ001), MyRule4)
        finally:
            unregister_requirements(MyRule4)
            # setUp registered MyRule1; tearDown will try to unregister it again, so
            # restore it here so tearDown's call is a no-op-safe symmetric operation.
            register_requirements(MyRequirement.REQ001)(MyRule1)

    def test_unregister_requirements_ok(self):
        unregister_requirements(MyRule1)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [])
        self.assertEqual(registry.get_validator(MyRequirement.REQ001), None)
        self.assertFalse(registry.is_registered(MyRule1, MyRequirement.REQ001))
        self.assertNotIn(MyRequirement.REQ001, list(registry))

    def test_delitem_removes_requirement_mappings(self):
        registry = RequirementsRegistry()
        key = registry.create_key(MyRequirement.REQ001)

        del registry[key]

        self.assertIsNone(registry.find("001"))
        self.assertEqual(registry.get_requirements(MyRule1), [])
        self.assertIsNone(registry.get_validator(MyRequirement.REQ001))
        self.assertFalse(registry.is_registered(MyRule1, MyRequirement.REQ001))
        self.assertNotIn(MyRequirement.REQ001, list(registry))

    def test_delitem_removes_overridden_requirement_mappings(self):
        registry = RequirementsRegistry()

        @register_requirements(MyRequirement.REQ001, override=True)
        class MyRule4(MyRule1): ...

        key = registry.create_key(MyRequirement.REQ001)

        try:
            del registry[key]

            self.assertIsNone(registry.find("001"))
            self.assertEqual(registry.get_requirements(MyRule1), [])
            self.assertEqual(registry.get_requirements(MyRule4), [])
            self.assertIsNone(registry.get_validator(MyRequirement.REQ001))
            self.assertFalse(registry.is_registered(MyRule1, MyRequirement.REQ001))
            self.assertFalse(registry.is_registered(MyRule4, MyRequirement.REQ001))
            self.assertNotIn(MyRequirement.REQ001, list(registry))
        finally:
            unregister_requirements(MyRule4)

    def test_unregister_requirements_override(self):
        @register_requirements(MyRequirement.REQ001, override=True)
        class MyRule4(MyRule1): ...

        unregister_requirements(MyRule4)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [MyRequirement.REQ001])
        self.assertEqual(registry.get_requirements(MyRule4), [])
        self.assertEqual(registry.get_validator(MyRequirement.REQ001), MyRule1)
        self.assertTrue(registry.is_registered(MyRule1, MyRequirement.REQ001))
        self.assertFalse(registry.is_registered(MyRule4, MyRequirement.REQ001))
        self.assertTrue(registry.is_implemented(MyRequirement.REQ001))
        self.assertIn(MyRequirement.REQ001, list(registry))

    def test_unregister_requirements_multiple(self):
        register_requirements(MyRequirement.REQ003, MyRequirement.REQ004)(MyRule3)

        unregister_requirements(MyRule3)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule3), [])
        self.assertEqual(registry.get_validator(MyRequirement.REQ003), None)
        self.assertFalse(registry.is_registered(MyRule3, MyRequirement.REQ003))
        self.assertNotIn(MyRequirement.REQ003, list(registry))
        self.assertEqual(registry.get_validator(MyRequirement.REQ004), None)
        self.assertFalse(registry.is_registered(MyRule3, MyRequirement.REQ004))
        self.assertNotIn(MyRequirement.REQ004, list(registry))

    def test_register_requirements_non_hashable(self):
        @dataclass
        class NonHashableRequirement:
            code: str
            version: str = "1.0.0"
            display_name: str | None = None
            message: str | None = None
            path: str | None = None
            tags: tuple[str, ...] = ()
            parameters: tuple[Parameter, ...] = ()
            examples: tuple = ()
            other: list[int] = field(default_factory=list)  # This field is not hashable

        requirement = NonHashableRequirement(
            "code", "1.0.0", "display_name", "message", "path", ("tag",), (), (), [1, 2, 3]
        )
        registry = RequirementsRegistry()
        self.assertEqual(registry.get_validator(requirement), None)
        self.assertEqual(registry.get_requirements(MyRule1), [MyRequirement.REQ001])
        self.assertFalse(registry.is_registered(MyRule1, requirement))

        register_requirements(requirement)(MyRule1)
        self.assertEqual(registry.get_validator(requirement), MyRule1)
        self.assertEqual(registry.get_requirements(MyRule1), [MyRequirement.REQ001, requirement])
        self.assertTrue(registry.is_registered(MyRule1, requirement))

    def test_add_callback_ok(self):
        callback = Mock()
        _subscription = add_registry_requirement_callback(callback)
        register_requirements(MyRequirement.REQ003)(MyRule3)
        try:
            callback.assert_called_once()
        finally:
            unregister_requirements(MyRule3)
