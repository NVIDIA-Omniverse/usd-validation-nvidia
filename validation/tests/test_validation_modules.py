# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import sys
import unittest
from pathlib import Path
from types import ModuleType

from usd_validation_nvidia import (
    BaseRuleChecker,
    CategoryRuleRegistry,
    RegisteredValidationModules,
    RequirementsRegistry,
    register_validation_modules,
    unregister_validation_modules,
)
from usd_validation_nvidia.capabilities import RequirementRef

from validation.tests.common import get_url


class RegisteredValidationModulesTest(unittest.TestCase):
    def test_registered_validation_modules_deduplicates_public_fields(self):
        class DuplicateRule(BaseRuleChecker):
            pass

        module = ModuleType("loose_module")
        registered_validation_modules = RegisteredValidationModules(
            rules=(DuplicateRule, DuplicateRule),
            modules=(module, module),
            paths=("C:/tmp/validators", "C:/tmp/validators"),
        )

        self.assertEqual((DuplicateRule,), registered_validation_modules.rules)
        self.assertEqual((module,), registered_validation_modules.modules)
        self.assertEqual(("loose_module",), registered_validation_modules.module_names)
        self.assertEqual(("C:/tmp/validators",), registered_validation_modules.paths)
        self.assertTrue(registered_validation_modules.has_rule_name("DuplicateRule"))
        self.assertTrue(registered_validation_modules.has_module_name("loose_module"))


class RegisterValidationModulesTest(unittest.TestCase):
    def test_register_validation_modules_file_ok(self):
        requirement = RequirementRef(code="com.example.LOOSE.001", version="1.0.0")
        module_path = Path(get_url("validation_modules/loose_validator.py"))
        search_path = str(module_path.parent.resolve())

        registered_validation_modules = register_validation_modules(str(module_path))
        try:
            rule = registered_validation_modules.rules[0]
            self.assertIsInstance(registered_validation_modules, RegisteredValidationModules)
            self.assertTrue(registered_validation_modules.has_rule_name("LooseRule"))
            self.assertTrue(registered_validation_modules.has_module_name("loose_validator"))
            self.assertEqual((search_path,), registered_validation_modules.paths)
            self.assertIn(rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertIs(RequirementsRegistry().get_validator(requirement), rule)
            self.assertIn(search_path, sys.path)
        finally:
            unregister_validation_modules(registered_validation_modules)

    def test_unregister_validation_modules_file_ok(self):
        requirement = RequirementRef(code="com.example.LOOSE.001", version="1.0.0")
        module_path = Path(get_url("validation_modules/loose_validator.py"))
        search_path = str(module_path.parent.resolve())

        registered_validation_modules = register_validation_modules(str(module_path))
        rule = registered_validation_modules.rules[0]
        unregister_validation_modules(registered_validation_modules)

        self.assertNotIn(rule, CategoryRuleRegistry().rules)
        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("loose_validator", sys.modules)
        self.assertNotIn(search_path, sys.path)

    def test_register_validation_modules_partial_nok(self):
        requirement = RequirementRef(code="com.example.BROKEN.001", version="1.0.0")
        module_path = Path(get_url("validation_modules/broken_validator.py"))
        search_path = str(module_path.parent.resolve())

        with self.assertRaisesRegex(RuntimeError, "broken validation module"):
            register_validation_modules(module_path)

        self.assertNotIn(
            "BrokenRule",
            tuple(rule.__name__ for rule in CategoryRuleRegistry().rules),
        )
        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("broken_validator", sys.modules)
        self.assertNotIn(search_path, sys.path)

    def test_register_validation_modules_dir_ok(self):
        package_requirement = RequirementRef(code="com.example.PACKAGE.001", version="1.0.0")
        units_requirement = RequirementRef(code="com.example.PACKAGE.UNITS.001", version="1.0.0")
        package_path = Path(get_url("validation_modules/package_validators"))
        search_path = str(package_path.parent.resolve())

        registered_validation_modules = register_validation_modules(package_path)
        try:
            rules_by_name = {rule.__name__: rule for rule in registered_validation_modules.rules}
            package_rule = rules_by_name["PackageValidator"]
            geometry_rule = rules_by_name["GeometryValidator"]
            units_rule = rules_by_name["UnitsValidator"]

            self.assertEqual(
                {"GeometryValidator", "PackageValidator", "UnitsValidator"},
                set(rules_by_name),
            )
            self.assertTrue(registered_validation_modules.has_module_name("package_validators"))
            self.assertEqual((search_path,), registered_validation_modules.paths)
            self.assertIn(package_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertIn(units_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertNotIn(geometry_rule, CategoryRuleRegistry().rules)
            self.assertIs(RequirementsRegistry().get_validator(package_requirement), package_rule)
            self.assertIs(RequirementsRegistry().get_validator(units_requirement), units_rule)
            self.assertIn("package_validators.validation", sys.modules)
            self.assertIn("package_validators.geometry.validation", sys.modules)
            self.assertIn("package_validators.units.validation", sys.modules)
        finally:
            unregister_validation_modules(registered_validation_modules)

    def test_unregister_validation_modules_dir_ok(self):
        package_requirement = RequirementRef(code="com.example.PACKAGE.001", version="1.0.0")
        units_requirement = RequirementRef(code="com.example.PACKAGE.UNITS.001", version="1.0.0")
        package_path = Path(get_url("validation_modules/package_validators"))
        search_path = str(package_path.parent.resolve())

        registered_validation_modules = register_validation_modules(package_path)
        rules_by_name = {rule.__name__: rule for rule in registered_validation_modules.rules}
        package_rule = rules_by_name["PackageValidator"]
        units_rule = rules_by_name["UnitsValidator"]
        unregister_validation_modules(registered_validation_modules)

        self.assertNotIn(package_rule, CategoryRuleRegistry().rules)
        self.assertNotIn(units_rule, CategoryRuleRegistry().rules)
        self.assertIsNone(RequirementsRegistry().get_validator(package_requirement))
        self.assertIsNone(RequirementsRegistry().get_validator(units_requirement))
        self.assertNotIn("package_validators", sys.modules)
        self.assertNotIn("package_validators.validation", sys.modules)
        self.assertNotIn("package_validators.geometry", sys.modules)
        self.assertNotIn("package_validators.geometry.validation", sys.modules)
        self.assertNotIn("package_validators.units", sys.modules)
        self.assertNotIn("package_validators.units.validation", sys.modules)
        self.assertNotIn(search_path, sys.path)

    def test_register_validation_modules_reload_ok(self):
        requirement = RequirementRef(code="com.example.RELOAD.001", version="1.0.0")
        first_module_path = Path(get_url("validation_modules/reload_first/reload_validator.py"))
        second_module_path = Path(get_url("validation_modules/reload_second/reload_validator.py"))
        first_search_path = str(first_module_path.parent.resolve())
        second_search_path = str(second_module_path.parent.resolve())

        first_registered_validation_modules = register_validation_modules(first_module_path)
        try:
            first_rule = first_registered_validation_modules.rules[0]
            self.assertTrue(first_registered_validation_modules.has_rule_name("FirstRule"))
            self.assertIn(first_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertIs(RequirementsRegistry().get_validator(requirement), first_rule)
            self.assertIn(first_search_path, sys.path)
        finally:
            unregister_validation_modules(first_registered_validation_modules)

        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("reload_validator", sys.modules)
        self.assertNotIn(first_search_path, sys.path)

        second_registered_validation_modules = register_validation_modules(second_module_path)
        try:
            second_rule = second_registered_validation_modules.rules[0]

            self.assertTrue(second_registered_validation_modules.has_rule_name("SecondRule"))
            self.assertIs(
                sys.modules[second_registered_validation_modules.module_names[0]],
                second_registered_validation_modules.modules[0],
            )
            self.assertTrue(second_registered_validation_modules.has_module_name("reload_validator"))
            self.assertEqual((second_search_path,), second_registered_validation_modules.paths)
            self.assertIn(second_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertIs(RequirementsRegistry().get_validator(requirement), second_rule)
            self.assertIn(second_search_path, sys.path)
        finally:
            unregister_validation_modules(second_registered_validation_modules)

        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("reload_validator", sys.modules)
        self.assertNotIn(second_search_path, sys.path)

    def test_register_validation_modules_nested_ok(self):
        requirement = RequirementRef(code="com.example.RELOAD.001", version="1.0.0")
        first_module_path = Path(get_url("validation_modules/reload_first/reload_validator.py"))
        second_module_path = Path(get_url("validation_modules/requirement_override/override_validator.py"))
        first_search_path = str(first_module_path.parent.resolve())
        second_search_path = str(second_module_path.parent.resolve())

        first_registered_validation_modules = register_validation_modules(first_module_path)
        try:
            first_rule = first_registered_validation_modules.rules[0]
            second_registered_validation_modules = register_validation_modules(second_module_path)
            try:
                second_rule = second_registered_validation_modules.rules[0]

                self.assertTrue(first_registered_validation_modules.has_rule_name("FirstRule"))
                self.assertTrue(second_registered_validation_modules.has_rule_name("OverrideRule"))
                self.assertTrue(first_registered_validation_modules.has_module_name("reload_validator"))
                self.assertTrue(second_registered_validation_modules.has_module_name("override_validator"))
                self.assertIn(first_rule, CategoryRuleRegistry().get_rules("LooseModule"))
                self.assertIn(second_rule, CategoryRuleRegistry().get_rules("LooseModule"))
                self.assertTrue(RequirementsRegistry().is_registered(first_rule, requirement))
                self.assertIs(RequirementsRegistry().get_validator(requirement), second_rule)
                self.assertIn(first_search_path, sys.path)
                self.assertIn(second_search_path, sys.path)
            finally:
                unregister_validation_modules(second_registered_validation_modules)

            self.assertIn(first_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertNotIn(second_rule, CategoryRuleRegistry().rules)
            self.assertIs(RequirementsRegistry().get_validator(requirement), first_rule)
            self.assertIn("reload_validator", sys.modules)
            self.assertNotIn("override_validator", sys.modules)
            self.assertIn(first_search_path, sys.path)
            self.assertNotIn(second_search_path, sys.path)
        finally:
            unregister_validation_modules(first_registered_validation_modules)

        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("reload_validator", sys.modules)
        self.assertNotIn(first_search_path, sys.path)

    def test_register_validation_modules_nested_nok(self):
        requirement = RequirementRef(code="com.example.RELOAD.001", version="1.0.0")
        loose_requirement = RequirementRef(code="com.example.LOOSE.001", version="1.0.0")
        first_module_path = Path(get_url("validation_modules/reload_first/reload_validator.py"))
        second_module_path = Path(get_url("validation_modules/reload_second/reload_validator.py"))
        loose_module_path = Path(get_url("validation_modules/loose_validator.py"))
        first_search_path = str(first_module_path.parent.resolve())
        second_search_path = str(second_module_path.parent.resolve())
        loose_search_path = str(loose_module_path.parent.resolve())

        first_registered_validation_modules = register_validation_modules(first_module_path)
        try:
            first_rule = first_registered_validation_modules.rules[0]
            first_module = first_registered_validation_modules.modules[0]

            with self.assertRaisesRegex(ValueError, "already registered: reload_validator"):
                register_validation_modules([second_module_path, loose_module_path])

            self.assertIn(first_rule, CategoryRuleRegistry().get_rules("LooseModule"))
            self.assertIs(RequirementsRegistry().get_validator(requirement), first_rule)
            self.assertIsNone(RequirementsRegistry().get_validator(loose_requirement))
            self.assertIs(sys.modules["reload_validator"], first_module)
            self.assertNotIn("loose_validator", sys.modules)
            self.assertIn(first_search_path, sys.path)
            self.assertNotIn(second_search_path, sys.path)
            self.assertNotIn(loose_search_path, sys.path)
        finally:
            unregister_validation_modules(first_registered_validation_modules)

        self.assertIsNone(RequirementsRegistry().get_validator(requirement))
        self.assertNotIn("reload_validator", sys.modules)
        self.assertNotIn(first_search_path, sys.path)

    def test_register_validation_modules_collects_plain_rule_classes(self):
        module_path = Path(get_url("validation_modules/plain_validator.py"))

        registered_validation_modules = register_validation_modules((module_path,))
        rule = registered_validation_modules.rules[0]
        try:
            self.assertTrue(registered_validation_modules.has_rule_name("PlainRule"))
            self.assertNotIn(rule, CategoryRuleRegistry().rules)
        finally:
            unregister_validation_modules(registered_validation_modules)

        self.assertNotIn("plain_validator", sys.modules)


if __name__ == "__main__":
    unittest.main()
