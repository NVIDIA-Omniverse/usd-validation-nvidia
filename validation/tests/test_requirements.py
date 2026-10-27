# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from dataclasses import dataclass, field
from unittest.mock import Mock

from usd_validation_nvidia import (
    BaseRuleChecker,
    Parameter,
    RequirementsRegistry,
    add_registry_requirement_callback,
    register_requirements,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO
from usd_validation_nvidia.capabilities import RequirementRef as RequirementRefDTO


class MyRule1(BaseRuleChecker): ...


class MyRule2(BaseRuleChecker): ...


class MyRule3(BaseRuleChecker): ...


class RequirementTests(unittest.TestCase):
    REQUIREMENT_001 = RequirementDTO(code="001", version="1.0.0", message="message")
    REQUIREMENT_002 = RequirementDTO(code="002", version="1.0.0", message="message")

    def setUp(self):
        register_requirements(self.REQUIREMENT_001)(MyRule1)
        register_requirements(self.REQUIREMENT_002)(MyRule2)

    def tearDown(self):
        unregister_requirements(MyRule1)
        unregister_requirements(MyRule2)

    def test_get_requirements_ok(self):
        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [self.REQUIREMENT_001])
        self.assertEqual(registry.get_requirements(MyRule2), [self.REQUIREMENT_002])
        self.assertEqual(registry.get_requirements(MyRule3), [])

    def test_get_latest_requirements_ok(self):
        registry = RequirementsRegistry()
        latest_reqs = registry.latest_requirements

        # Should contain both registered requirements
        self.assertIn(self.REQUIREMENT_001, latest_reqs)
        self.assertIn(self.REQUIREMENT_002, latest_reqs)

    def test_get_validator_ok(self):
        requirement = RequirementDTO(code="003", version="1.0.0")

        self.assertEqual(RequirementsRegistry().get_validator(self.REQUIREMENT_001), MyRule1)
        self.assertEqual(RequirementsRegistry().get_validator(self.REQUIREMENT_002), MyRule2)
        self.assertIsNone(RequirementsRegistry().get_validator(requirement))

    def test_get_validators_ok(self):
        requirement = RequirementDTO(code="003", version="1.0.0")

        self.assertCountEqual(
            RequirementsRegistry().get_validators([self.REQUIREMENT_001, self.REQUIREMENT_002]), [MyRule1, MyRule2]
        )
        self.assertCountEqual(
            RequirementsRegistry().get_validators([self.REQUIREMENT_001, self.REQUIREMENT_002, requirement]),
            [MyRule1, MyRule2],
        )

    def test_implemented_ok(self):
        requirement = RequirementDTO(code="003", version="1.0.0")

        self.assertTrue(RequirementsRegistry().is_implemented(self.REQUIREMENT_001))
        self.assertTrue(RequirementsRegistry().is_implemented(self.REQUIREMENT_002))
        self.assertFalse(RequirementsRegistry().is_implemented(requirement))

    def test_all_implemented_ok(self):
        requirement = RequirementDTO(code="003", version="1.0.0")

        self.assertTrue(RequirementsRegistry().all_implemented([self.REQUIREMENT_001, self.REQUIREMENT_002]))
        self.assertFalse(
            RequirementsRegistry().all_implemented([self.REQUIREMENT_001, self.REQUIREMENT_002, requirement])
        )

    def test_is_registered_ok(self):
        requirement = RequirementDTO(code="003", version="1.0.0")

        self.assertTrue(RequirementsRegistry().is_registered(MyRule1, self.REQUIREMENT_001))
        self.assertTrue(RequirementsRegistry().is_registered(MyRule2, self.REQUIREMENT_002))
        self.assertFalse(RequirementsRegistry().is_registered(MyRule3, requirement))

    def test_get_requirement_from_code_ok(self):
        self.assertEqual(RequirementsRegistry().find("001"), self.REQUIREMENT_001)
        self.assertIsNone(RequirementsRegistry().find("003"))

    def test_register_requirement_twice(self):
        with self.assertRaises(ValueError):
            register_requirements(self.REQUIREMENT_001)(MyRule3)

        self.assertEqual(RequirementsRegistry().get_requirements(MyRule1), [self.REQUIREMENT_001])
        self.assertEqual(RequirementsRegistry().get_requirements(MyRule3), [])
        self.assertEqual(RequirementsRegistry().get_validator(self.REQUIREMENT_001), MyRule1)
        self.assertTrue(RequirementsRegistry().is_registered(MyRule1, self.REQUIREMENT_001))

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

    def test_register_requirement_definitions_without_rule_bindings(self):
        registry = RequirementsRegistry()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        other_requirement = RequirementDTO(code="004", version="1.0.0", message="message")
        same_key_definition = RequirementDTO(
            code=requirement.code,
            version=requirement.version,
            message="Reloaded definition with the same key",
        )

        result = register_requirements(requirement, other_requirement)(None)

        try:
            self.assertIsNone(result)
            self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)
            self.assertIs(registry.find_requirement("004", "1.0.0"), other_requirement)
            self.assertIsNone(registry.get_validator(requirement))
            self.assertIsNone(registry.get_validator(other_requirement))
            self.assertNotIn(None, registry.rules)
        finally:
            unregister_requirements(same_key_definition, other_requirement)

        self.assertIsNone(registry.find_requirement("003", "1.0.0"))
        self.assertIsNone(registry.find_requirement("004", "1.0.0"))

    def test_definition_registration_is_reference_counted(self):
        registry = RequirementsRegistry()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        register_requirements(requirement)(None)
        register_requirements(requirement)(None)

        try:
            unregister_requirements(requirement)

            self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)

            unregister_requirements(requirement)

            self.assertIsNone(registry.find_requirement("003", "1.0.0"))
        finally:
            unregister_requirements(requirement)

    def test_definition_lifecycle_does_not_remove_preexisting_rule_registration(self):
        registry = RequirementsRegistry()
        duplicate_definition = RequirementDTO(
            code=self.REQUIREMENT_001.code,
            version=self.REQUIREMENT_001.version,
            message="A different owner",
        )
        register_requirements(duplicate_definition)(None)

        unregister_requirements(duplicate_definition)

        self.assertIs(registry.find_requirement("001", "1.0.0"), self.REQUIREMENT_001)
        self.assertEqual(registry.get_validator(self.REQUIREMENT_001), MyRule1)
        self.assertTrue(registry.is_registered(MyRule1, self.REQUIREMENT_001))

    def test_definition_ownership_transfers_when_concrete_rule_unregisters_first(self):
        registry = RequirementsRegistry()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        register_requirements(requirement)(MyRule3)
        register_requirements(requirement)(None)

        unregister_requirements(MyRule3)

        self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)

        unregister_requirements(requirement)

        self.assertIsNone(registry.find_requirement("003", "1.0.0"))

    def test_definition_unregistration_preserves_concrete_rule_binding(self):
        registry = RequirementsRegistry()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        register_requirements(requirement)(None)
        register_requirements(requirement)(MyRule3)

        try:
            unregister_requirements(requirement)

            self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)
            self.assertEqual(registry.get_validator(requirement), MyRule3)
            self.assertTrue(registry.is_registered(MyRule3, requirement))
        finally:
            unregister_requirements(MyRule3)
            unregister_requirements(requirement)

    def test_definition_ownership_tracks_active_metadata_lifecycle(self):
        registry = RequirementsRegistry()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        key = registry.create_key(requirement)
        register_requirements(requirement)(None)
        register_requirements(requirement)(MyRule3)

        unregister_requirements(requirement)

        self.assertNotIn(key, registry._definition_registration_counts)
        self.assertNotIn(key, registry._definition_owned_keys)

        register_requirements(requirement)(None)

        self.assertEqual(registry._definition_registration_counts[key], 1)
        self.assertNotIn(key, registry._definition_owned_keys)

        unregister_requirements(MyRule3)

        self.assertIn(key, registry._definition_owned_keys)
        self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)

        unregister_requirements(requirement)

        self.assertNotIn(key, registry._definition_registration_counts)
        self.assertNotIn(key, registry._definition_owned_keys)
        self.assertIsNone(registry.find_requirement("003", "1.0.0"))

    def test_requirement_ref_definition_registration_does_not_create_metadata(self):
        requirement_ref = RequirementRefDTO(code="REF.001", version="1.0.0")
        registry = RequirementsRegistry()

        register_requirements(requirement_ref)(None)

        self.assertIsNone(registry.find_requirement(requirement_ref.code, requirement_ref.version))
        self.assertNotIn(requirement_ref, list(registry))
        self.assertNotIn(None, registry.rules)

    def test_metadata_lifecycle_skips_requirement_refs_symmetrically(self):
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        requirement_ref = RequirementRefDTO(code="REF.001", version="1.0.0")
        registry = RequirementsRegistry()
        register_requirements(requirement, requirement_ref)(None)

        unregister_requirements(requirement, requirement_ref)

        self.assertIsNone(registry.find_requirement("003", "1.0.0"))
        self.assertIsNone(registry.find_requirement(requirement_ref.code, requirement_ref.version))

    def test_unregister_definition_preserves_reference_rule_binding(self):
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        requirement_ref = RequirementRefDTO(code=requirement.code, version=requirement.version)
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)
        register_requirements(requirement)(None)

        try:
            self.assertIs(registry.find_requirement("003", "1.0.0"), requirement)
            self.assertEqual(registry.get_requirements(MyRule3), [requirement])

            unregister_requirements(requirement)

            self.assertIsNone(registry.find_requirement("003", "1.0.0"))
            self.assertEqual(registry.get_requirements(MyRule3), [requirement_ref])
            self.assertEqual(registry.get_validator(requirement_ref), MyRule3)
            self.assertTrue(registry.is_registered(MyRule3, requirement_ref))
        finally:
            unregister_requirements(MyRule3)

    def test_requirement_ref_resolves_registered_definition(self):
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        requirement_ref = RequirementRefDTO(code=requirement.code, version=requirement.version)
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)

        try:
            self.assertEqual(registry.get_requirements(MyRule3), [requirement_ref])

            registry.add(requirement)

            self.assertEqual(registry.get_requirements(MyRule3), [requirement])
            self.assertEqual(registry.get_validator(requirement), MyRule3)
        finally:
            unregister_requirements(MyRule3)
        try:
            self.assertIs(
                registry.find_requirement(requirement.code, requirement.version),
                requirement,
            )
        finally:
            registry.remove(requirement)

    def test_removing_resolved_requirement_ref_keeps_validator_binding(self):
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        requirement_ref = RequirementRefDTO(code=requirement.code, version=requirement.version)
        registry = RequirementsRegistry()
        register_requirements(requirement_ref)(MyRule3)

        try:
            registry.add(requirement)
            self.assertEqual(registry.get_requirements(MyRule3), [requirement])

            registry.remove(requirement)

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
        self.assertEqual(registry.get_requirements(MyRule1), [self.REQUIREMENT_001])
        self.assertEqual(registry.get_validator(self.REQUIREMENT_001), MyRule1)
        self.assertTrue(registry.is_registered(MyRule1, self.REQUIREMENT_001))
        self.assertTrue(registry.is_implemented(self.REQUIREMENT_001))

        @register_requirements(self.REQUIREMENT_001, override=True)
        class MyRule4(MyRule1): ...

        try:
            # ``get_requirements`` returns only requirements where the rule is the
            # primary (last-registered) validator, so MyRule1 reports nothing here.
            self.assertEqual(registry.get_requirements(MyRule1), [])
            self.assertEqual(registry.get_requirements(MyRule4), [self.REQUIREMENT_001])
            self.assertEqual(registry.get_validator(self.REQUIREMENT_001), MyRule4)
            # ``is_registered`` reflects actual list membership (OMPE-64259): the
            # original rule is still in the registration list, just not the primary.
            self.assertTrue(registry.is_registered(MyRule1, self.REQUIREMENT_001))
            self.assertTrue(registry.is_registered(MyRule4, self.REQUIREMENT_001))
            self.assertTrue(registry.is_implemented(self.REQUIREMENT_001))
        finally:
            unregister_requirements(MyRule4)

    def test_overridden_rule_can_emit_issue(self):
        # OMPE-64259: a rule that has been overridden (not the primary validator
        # anymore) must still be allowed to emit Issues against the requirement —
        # otherwise Issue.__post_init__ raises "Rule X is not registered to
        # requirement Y" and the rule check fails uncaught.
        from usd_validation_nvidia import Issue, IssueSeverity

        @register_requirements(self.REQUIREMENT_001, override=True)
        class MyRule4(MyRule1): ...

        try:
            Issue(
                message="should not raise",
                severity=IssueSeverity.FAILURE,
                rule=MyRule1,
                requirement=self.REQUIREMENT_001,
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

        @register_requirements(self.REQUIREMENT_001, override=True)
        class MyRule4(MyRule1): ...

        try:
            self.assertTrue(registry.is_registered(MyRule1, self.REQUIREMENT_001))

            unregister_requirements(MyRule1)

            self.assertFalse(registry.is_registered(MyRule1, self.REQUIREMENT_001))
            self.assertTrue(registry.is_registered(MyRule4, self.REQUIREMENT_001))
            self.assertEqual(registry.get_validator(self.REQUIREMENT_001), MyRule4)
        finally:
            unregister_requirements(MyRule4)
            # setUp registered MyRule1; tearDown will try to unregister it again, so
            # restore it here so tearDown's call is a no-op-safe symmetric operation.
            register_requirements(self.REQUIREMENT_001)(MyRule1)

    def test_unregister_requirements_ok(self):
        unregister_requirements(MyRule1)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [])
        self.assertEqual(registry.get_validator(self.REQUIREMENT_001), None)
        self.assertFalse(registry.is_registered(MyRule1, self.REQUIREMENT_001))
        self.assertNotIn(self.REQUIREMENT_001, list(registry))

    def test_unregister_requirements_rejects_empty_arguments(self):
        with self.assertRaises(TypeError):
            unregister_requirements()

        self.assertEqual(RequirementsRegistry().get_validator(self.REQUIREMENT_001), MyRule1)

    def test_unregister_requirements_rejects_non_rule_class(self):
        with self.assertRaises(TypeError):
            unregister_requirements(RequirementDTO)

        self.assertEqual(RequirementsRegistry().get_validator(self.REQUIREMENT_001), MyRule1)

    def test_delitem_removes_requirement_mappings(self):
        registry = RequirementsRegistry()
        key = registry.create_key(self.REQUIREMENT_001)

        del registry[key]

        self.assertIsNone(registry.find("001"))
        self.assertEqual(registry.get_requirements(MyRule1), [])
        self.assertIsNone(registry.get_validator(self.REQUIREMENT_001))
        self.assertFalse(registry.is_registered(MyRule1, self.REQUIREMENT_001))
        self.assertNotIn(self.REQUIREMENT_001, list(registry))

    def test_delitem_removes_overridden_requirement_mappings(self):
        registry = RequirementsRegistry()

        @register_requirements(self.REQUIREMENT_001, override=True)
        class MyRule4(MyRule1): ...

        key = registry.create_key(self.REQUIREMENT_001)

        try:
            del registry[key]

            self.assertIsNone(registry.find("001"))
            self.assertEqual(registry.get_requirements(MyRule1), [])
            self.assertEqual(registry.get_requirements(MyRule4), [])
            self.assertIsNone(registry.get_validator(self.REQUIREMENT_001))
            self.assertFalse(registry.is_registered(MyRule1, self.REQUIREMENT_001))
            self.assertFalse(registry.is_registered(MyRule4, self.REQUIREMENT_001))
            self.assertNotIn(self.REQUIREMENT_001, list(registry))
        finally:
            unregister_requirements(MyRule4)

    def test_unregister_requirements_override(self):
        @register_requirements(self.REQUIREMENT_001, override=True)
        class MyRule4(MyRule1): ...

        unregister_requirements(MyRule4)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule1), [self.REQUIREMENT_001])
        self.assertEqual(registry.get_requirements(MyRule4), [])
        self.assertEqual(registry.get_validator(self.REQUIREMENT_001), MyRule1)
        self.assertTrue(registry.is_registered(MyRule1, self.REQUIREMENT_001))
        self.assertFalse(registry.is_registered(MyRule4, self.REQUIREMENT_001))
        self.assertTrue(registry.is_implemented(self.REQUIREMENT_001))
        self.assertIn(self.REQUIREMENT_001, list(registry))

    def test_unregister_requirements_multiple(self):
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        other_requirement = RequirementDTO(code="004", version="1.0.0", message="message")
        register_requirements(requirement, other_requirement)(MyRule3)

        unregister_requirements(MyRule3)

        registry = RequirementsRegistry()
        self.assertEqual(registry.get_requirements(MyRule3), [])
        self.assertEqual(registry.get_validator(requirement), None)
        self.assertFalse(registry.is_registered(MyRule3, requirement))
        self.assertNotIn(requirement, list(registry))
        self.assertEqual(registry.get_validator(other_requirement), None)
        self.assertFalse(registry.is_registered(MyRule3, other_requirement))
        self.assertNotIn(other_requirement, list(registry))

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
        self.assertEqual(registry.get_requirements(MyRule1), [self.REQUIREMENT_001])
        self.assertFalse(registry.is_registered(MyRule1, requirement))

        register_requirements(requirement)(MyRule1)
        self.assertEqual(registry.get_validator(requirement), MyRule1)
        self.assertEqual(registry.get_requirements(MyRule1), [self.REQUIREMENT_001, requirement])
        self.assertTrue(registry.is_registered(MyRule1, requirement))

    def test_add_callback_ok(self):
        callback = Mock()
        requirement = RequirementDTO(code="003", version="1.0.0", message="message")
        _subscription = add_registry_requirement_callback(callback)
        register_requirements(requirement)(MyRule3)
        try:
            callback.assert_called_once()
        finally:
            unregister_requirements(MyRule3)
