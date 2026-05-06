# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import io
import os
import pathlib
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import skipIf

from common import get_url
from pxr import Ar

import usd_validation_nvidia.capabilities as cap
from usd_validation_nvidia import (
    ByteAlignmentChecker,
    CategoryRuleRegistry,
    CompressionChecker,
    IssueGroupsBy,
    IssuePredicates,
    ProfileRegistry,
    StageMetadataChecker,
    UsdzPackageValidator,
    ValidationArgsExec,
    __version__,
    cli_main,
    create_validation_parser,
    register_profile,
    unregister_profile,
)
from usd_validation_nvidia.capabilities import Capability, Profile


class DummyChecker:
    pass


class ValidationParserTest(unittest.TestCase):

    def test_help(self):
        parser = create_validation_parser()
        f = io.StringIO()
        with redirect_stdout(f):
            parser.print_help()
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)
        self.assertIn("--rule", stdout)
        self.assertIn("--fix", stdout)
        self.assertIn("--stamp", stdout)
        self.assertIn("--predicate", stdout)
        self.assertIn("--variants", stdout)
        self.assertIn("--requirement", stdout)
        self.assertIn("--capability", stdout)
        self.assertIn("--feature", stdout)
        self.assertIn("--profile", stdout)
        self.assertIn("--parameter", stdout)
        self.assertIn("NAME=VALUE", stdout)

    def test_version(self):
        parser = create_validation_parser()
        f = io.StringIO()
        with redirect_stdout(f):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--version"])
        # It will present version
        stdout = f.getvalue()
        self.assertIn(__version__, stdout)

    def test_explain(self):
        parser = create_validation_parser()
        f = io.StringIO()
        with redirect_stdout(f):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--rule", "StageMetadataChecker", "--explain"])
        # It will present rules documentation
        stdout = f.getvalue()
        self.assertIn(StageMetadataChecker.GetDescription(), stdout)

    def test_e(self):
        parser = create_validation_parser()
        f = io.StringIO()
        with redirect_stdout(f):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--rule", "StageMetadataChecker", "-e"])
        # It will present rules documentation
        stdout = f.getvalue()
        self.assertIn(StageMetadataChecker.GetDescription(), stdout)

    def test_empty(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args([])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("required: ASSET", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_asset(self):
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        self.assertEqual(args.asset, ["asset.usda"])
        self.assertEqual(args.rule, [])
        self.assertEqual(args.fix, False)
        self.assertEqual(args.variants, True)
        self.assertEqual(args.predicate, None)
        self.assertEqual(args.requirement, [])
        self.assertEqual(args.capability, [])

    def test_rule(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--rule", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.rule, ["StageMetadataChecker"])

    @skipIf(UsdzPackageValidator.is_implemented(), "Test ByteAlignment and CompressionChecker.")
    def test_rule_byte_alignment_and_compression_checker(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--rule", "ByteAlignmentChecker", "--rule", "CompressionChecker", "asset.usda"])
        self.assertEqual(args.rule, ["ByteAlignmentChecker", "CompressionChecker"])

    @skipIf(not UsdzPackageValidator.is_implemented(), "Test UsdzPackageValidator.")
    def test_rule_usd_validation(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--rule", "UsdzPackageValidator", "asset.usda"])
        self.assertEqual(args.rule, ["UsdzPackageValidator"])

    def test_enable_rule(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--enable-rule", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.rule, ["StageMetadataChecker"])

    def test_disable_rule(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--disable-rule", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.disable_rule, ["StageMetadataChecker"])

    def test_D(self):
        parser = create_validation_parser()
        args = parser.parse_args(["-D", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.disable_rule, ["StageMetadataChecker"])

    def test_disableRules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--disableRules", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.disable_rule, ["StageMetadataChecker"])

    def test_r(self):
        parser = create_validation_parser()
        args = parser.parse_args(["-r", "StageMetadataChecker", "asset.usda"])
        self.assertEqual(args.rule, ["StageMetadataChecker"])

    def test_rule_nok(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--rule", "DummyChecker", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DummyChecker'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_custom_rule(self):
        CategoryRuleRegistry().add("DummyTest", DummyChecker)
        try:
            parser = create_validation_parser()
            args = parser.parse_args(["--rule", "DummyChecker", "asset.usda"])
            self.assertEqual(args.rule, ["DummyChecker"])
        finally:
            CategoryRuleRegistry().remove(DummyChecker)

    def test_non_existent_requirement(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--requirement", "DOES.NOT.EXIST", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DOES.NOT.EXIST'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_non_existent_capability(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--capability", "DOES.NOT.EXIST", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DOES.NOT.EXIST'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_category(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--category", "Basic", "asset.usda"])
        self.assertEqual(args.category, ["Basic"])

    def test_enable_category(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--enable-category", "Basic", "asset.usda"])
        self.assertEqual(args.category, ["Basic"])

    def test_disable_category(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--disable-category", "Basic", "asset.usda"])
        self.assertEqual(args.disable_category, ["Basic"])

    def test_c(self):
        parser = create_validation_parser()
        args = parser.parse_args(["-c", "Basic", "asset.usda"])
        self.assertEqual(args.category, ["Basic"])

    def test_category_nok(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--category", "DummyTest", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DummyTest'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_custom_category(self):
        CategoryRuleRegistry().add("DummyTest", DummyChecker)
        try:
            parser = create_validation_parser()
            args = parser.parse_args(["--category", "DummyTest", "asset.usda"])
            self.assertEqual(args.category, ["DummyTest"])
        finally:
            CategoryRuleRegistry().remove(DummyChecker)

    def test_requirement(self):
        parser = create_validation_parser()
        code: str = cap.Requirements.VG_019.code
        args = parser.parse_args(["--requirement", code, "asset.usda"])
        self.assertEqual(args.requirement, [code])

    def test_requirement_with_version(self):
        parser = create_validation_parser()
        code: str = cap.Requirements.VG_019.code
        version: str = cap.Requirements.VG_019.version
        args = parser.parse_args(["--requirement", f"{code}@{version}", "asset.usda"])
        self.assertEqual(args.requirement, [f"{code}@{version}"])

    def test_capability(self):
        parser = create_validation_parser()
        id: str = cap.Capabilities.GEOMETRY.id
        args = parser.parse_args(["--capability", id, "asset.usda"])
        self.assertEqual(args.capability, [id])

    def test_capability_with_version(self):
        parser = create_validation_parser()
        id: str = cap.Capabilities.GEOMETRY.id
        version: str = cap.Capabilities.GEOMETRY.version
        args = parser.parse_args(["--capability", f"{id}@{version}", "asset.usda"])
        self.assertEqual(args.capability, [f"{id}@{version}"])

    def test_feature(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        args = parser.parse_args(["--feature", feature_id, "asset.usda"])
        self.assertEqual(args.feature, [feature_id])

    def test_feature_with_version(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        version: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.version
        args = parser.parse_args(["--feature", f"{feature_id}@{version}", "asset.usda"])
        self.assertEqual(args.feature, [f"{feature_id}@{version}"])

    def test_enable_feature(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        args = parser.parse_args(["--enable-feature", feature_id, "asset.usda"])
        self.assertEqual(args.feature, [feature_id])

    def test_disable_feature(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        args = parser.parse_args(["--disable-feature", feature_id, "asset.usda"])
        self.assertEqual(args.disable_feature, [feature_id])

    def test_disable_feature_with_version(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        version: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.version
        args = parser.parse_args(["--disable-feature", f"{feature_id}@{version}", "asset.usda"])
        self.assertEqual(args.disable_feature, [f"{feature_id}@{version}"])

    def test_non_existent_feature(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--feature", "DOES.NOT.EXIST", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DOES.NOT.EXIST'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_non_existent_profile(self):
        parser = create_validation_parser()
        f = io.StringIO()
        g = io.StringIO()
        with redirect_stdout(f), redirect_stderr(g):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--profile", "DOES.NOT.EXIST", "asset.usda"])
        # It will show error
        stderr = g.getvalue()
        self.assertIn("invalid choice: 'DOES.NOT.EXIST'", stderr)
        # It will present HELP
        stdout = f.getvalue()
        self.assertIn("usage: validate", stdout)

    def test_fix(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--fix", "asset.usda"])
        self.assertEqual(args.fix, True)

    def test_f(self):
        parser = create_validation_parser()
        args = parser.parse_args(["-f", "asset.usda"])
        self.assertEqual(args.fix, True)

    def test_no_fix(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--no-fix", "asset.usda"])
        self.assertEqual(args.fix, False)

    def test_variants(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--variants", "asset.usda"])
        self.assertEqual(args.variants, True)

    def test_no_variants(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--no-variants", "asset.usda"])
        self.assertEqual(args.variants, False)

    def test_init_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--init-rules", "asset.usda"])
        self.assertEqual(args.init_rules, True)

    def test_no_init_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--no-init-rules", "asset.usda"])
        self.assertEqual(args.init_rules, False)

    def test_default_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--defaultRules", "asset.usda"])
        self.assertEqual(args.init_rules, True)

    def test_predicate(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--predicate", "Any", "asset.usda"])
        self.assertEqual(args.predicate, "Any")

    def test_p(self):
        parser = create_validation_parser()
        args = parser.parse_args(["-p", "Any", "asset.usda"])
        self.assertEqual(args.predicate, "Any")

    def test_group_by(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--group-by", "rule_name", "asset.usda"])
        self.assertEqual(args.group_by, "rule_name")

    def test_csv_output(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--csv-output", "/path/to/file.csv", "asset.usda"])
        self.assertEqual(args.csv_output, "/path/to/file.csv")

    def test_json_output(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--json-output", "/path/to/file.json", "asset.usda"])
        self.assertEqual(args.json_output, "/path/to/file.json")

    def test_parameter(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "tolerance=0.001", "asset.usda"])
        self.assertEqual(args.parameter, [("tolerance", 0.001)])

    def test_multiple_parameters(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "tolerance=0.001", "--parameter", "max_iterations=100", "asset.usda"])
        self.assertEqual(args.parameter, [("tolerance", 0.001), ("max_iterations", 100)])

    def test_parameter_with_equals_in_value(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "expression=a=b", "asset.usda"])
        self.assertEqual(args.parameter, [("expression", "a=b")])

    def test_parameter_empty_value(self):
        """Test that parameter with empty value is accepted (validation happens later)."""
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "name=", "asset.usda"])
        self.assertEqual(args.parameter, [("name", "")])

    def test_parameter_missing_equals(self):
        """Test that parameter without = raises error during parsing."""
        parser = create_validation_parser()
        with self.assertRaises(SystemExit):
            # argparse raises SystemExit on validation errors
            parser.parse_args(["--parameter", "tolerance", "asset.usda"])

    def test_parameter_empty_name(self):
        """Test that parameter with empty name raises error during parsing."""
        parser = create_validation_parser()
        with self.assertRaises(SystemExit):
            # argparse raises SystemExit on validation errors
            parser.parse_args(["--parameter", "=value", "asset.usda"])


class ValidationArgsTest(unittest.TestCase):

    def test_getters(self):
        parser = create_validation_parser()
        args = parser.parse_args(
            ["--no-init-rules", "--rule", "StageMetadataChecker", "--predicate", "Any", "asset.usda"]
        )
        args = ValidationArgsExec(args)
        self.assertEqual(args.rules, [StageMetadataChecker])
        self.assertEqual(args.requirements, [])
        self.assertEqual(args.capabilities, [])
        self.assertEqual(args.features, [])
        self.assertEqual(args.disabled_rules, [])
        self.assertEqual(args.category_rules, [])
        self.assertEqual(args.disable_category_rules, [])
        self.assertEqual(args.predicate, IssuePredicates.Any())
        self.assertEqual(args.group_by, IssueGroupsBy.rule_name())
        self.assertEqual(args.asset, "asset.usda")
        self.assertEqual(args.variants, True)
        self.assertEqual(args.fix, False)
        self.assertEqual(args.init_rules, False)

    def test_defaults(self):
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.rules, [])
        self.assertEqual(args.requirements, [])
        self.assertEqual(args.capabilities, [])
        self.assertEqual(args.features, [])
        self.assertEqual(args.disabled_rules, [])
        self.assertEqual(args.category_rules, [])
        self.assertEqual(args.disable_category_rules, [])
        self.assertEqual(args.predicate, IssuePredicates.Any())
        self.assertEqual(args.asset, "asset.usda")
        self.assertEqual(args.variants, True)
        self.assertEqual(args.fix, False)
        self.assertEqual(args.init_rules, True)

    def test_category(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--category", "Basic", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertSequenceEqual(args.category_rules, CategoryRuleRegistry().get_rules("Basic"))
        self.assertEqual(args.predicate, IssuePredicates.Any())
        self.assertEqual(args.asset, "asset.usda")
        self.assertEqual(args.variants, True)
        self.assertEqual(args.fix, False)

    @skipIf(UsdzPackageValidator.is_implemented(), "Test ByteAlignment and CompressionChecker.")
    def test_category_byte_alignment_and_compression_checker(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--category", "Basic", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertIn(ByteAlignmentChecker, args.enabled_category_rules)
        self.assertIn(CompressionChecker, args.enabled_category_rules)
        self.assertNotIn(UsdzPackageValidator, args.enabled_category_rules)

    @skipIf(not UsdzPackageValidator.is_implemented(), "Test UsdzPackageValidator.")
    def test_category_usdz_package_validator(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--category", "Basic", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertNotIn(ByteAlignmentChecker, args.enabled_category_rules)
        self.assertNotIn(CompressionChecker, args.enabled_category_rules)
        self.assertIn(UsdzPackageValidator, args.enabled_category_rules)

    def test_create_engine_init_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--init-rules", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertTrue(engine.init_rules)

    def test_create_engine_rule(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--rule", "StageMetadataChecker", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_rules, [StageMetadataChecker])

    def test_create_engine_rule_no_init_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--no-init-rules", "--rule", "StageMetadataChecker", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_rules, [StageMetadataChecker])

    def test_create_engine_rule_init_rules(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--init-rules", "--rule", "StageMetadataChecker", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_rules, [StageMetadataChecker])

    def test_create_engine_disable_category(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--init-rules", "--disable-category", "Geometry", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertSequenceEqual(engine.disabled_rules, CategoryRuleRegistry().get_rules("Geometry"))

    def test_create_engine_requirement(self):
        parser = create_validation_parser()
        code: str = cap.Requirements.VG_019.code
        args = parser.parse_args(["--requirement", code, "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_requirements, [cap.Requirements.VG_019])

    def test_create_engine_capability(self):
        parser = create_validation_parser()
        id: str = cap.Capabilities.GEOMETRY.id
        args = parser.parse_args(["--capability", id, "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_capabilities, [cap.Capabilities.GEOMETRY])

    def test_create_engine_capability_with_version(self):
        parser = create_validation_parser()
        id: str = cap.Capabilities.GEOMETRY.id
        version: str = cap.Capabilities.GEOMETRY.version
        args = parser.parse_args(["--capability", f"{id}@{version}", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(engine.enabled_capabilities, [cap.Capabilities.GEOMETRY])

    def test_features_getter(self):
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.features, [])
        self.assertEqual(args.enabled_features, [])
        self.assertEqual(args.disabled_features, [])

    def test_profiles_getter(self):
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.profiles, [])
        self.assertEqual(args.enabled_profiles, [])
        self.assertEqual(args.disabled_profiles, [])

    def test_create_engine_profile_with_version(self):
        profile = Profile(
            id="test-profile",
            version="1.0.0",
            path="",
            features=[],
            capabilities=[Capability(id="test-cap", version="1.0.0", path="", requirements=[])],
        )
        register_profile(profile)
        try:
            parser = create_validation_parser()
            args = parser.parse_args(["--profile", f"{profile.id}@{profile.version}", "asset.usda"])
            args = ValidationArgsExec(args)
            engine = args.create_engine()
            self.assertFalse(engine.init_rules)
            self.assertEqual(len(engine.enabled_profiles), 1)
            self.assertEqual(engine.enabled_profiles[0].id, profile.id)
        finally:
            unregister_profile(profile)

    def test_create_engine_feature_with_version(self):
        parser = create_validation_parser()
        feature_id: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        version: str = cap.Features.MINIMAL_PLACEABLE_VISUAL.version
        args = parser.parse_args(["--feature", f"{feature_id}@{version}", "asset.usda"])
        args = ValidationArgsExec(args)
        engine = args.create_engine()
        self.assertFalse(engine.init_rules)
        self.assertEqual(len(engine.enabled_features), 1)
        self.assertEqual(engine.enabled_features[0].id, feature_id)

    def test_group_by(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--group-by", "rule_name", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.group_by, IssueGroupsBy.rule_name())

    def test_csv_output(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--csv-output", "/path/to/report.csv", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.csv_output, "/path/to/report.csv")

    def test_json_output(self):
        parser = create_validation_parser()
        args = parser.parse_args(["--json-output", "/path/to/report.json", "asset.usda"])
        args = ValidationArgsExec(args)
        self.assertEqual(args.json_output, "/path/to/report.json")

    def test_run_validation_not_found(self):
        url = "notfound.usda"
        with self.assertLogs(level="INFO") as cm:
            parser = create_validation_parser()
            args = ValidationArgsExec(parser.parse_args(["--rule", "TypeChecker", url]))
            args.run_validation()

        value = os.linesep.join(cm.output)
        self.assertIn("Errors: 1", value)

    def test_run_validation(self):
        url = get_url("untyped.usda")
        file = NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        file.close()

        with redirect_stdout(io.StringIO()):
            parser = create_validation_parser()
            args = ValidationArgsExec(parser.parse_args(["--rule", "TypeChecker", "--csv-output", file.name, url]))
            args.run_validation()

        try:
            actual_text = pathlib.Path(file.name).read_text()
            self.assertIn("Asset,Rule,Message,Severity,Suggestion,Location", actual_text)
            self.assertIn("TypeChecker", actual_text)
        finally:
            os.unlink(file.name)

    def test_run_validation_no_issues(self):
        url = get_url("helloworld.usda")
        file = NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        file.close()

        with self.assertLogs(level="INFO") as cm:
            parser = create_validation_parser()
            args = ValidationArgsExec(parser.parse_args(["--rule", "TypeChecker", url]))
            args.run_validation()

        value = os.linesep.join(cm.output)
        self.assertNotIn("Failures: 0", value)
        self.assertNotIn("0 Failures", value)
        self.assertNotIn("Errors: 0", value)
        self.assertNotIn("0 Errors", value)
        self.assertNotIn("Warnings: 0", value)
        self.assertNotIn("0 Warnings", value)
        self.assertNotIn("Infos: 0", value)
        self.assertNotIn("0 Infos", value)
        self.assertIn("No issues found.", value)

    def test_run_validation_exit_codes(self):
        url = get_url("helloworld.usda")
        with redirect_stdout(io.StringIO()):
            parser = create_validation_parser()
            args = ValidationArgsExec(parser.parse_args(["--rule", "TypeChecker", url]))
            successful: bool = args.run_validation()
            self.assertTrue(successful)

        url = get_url("untyped.usda")
        with redirect_stdout(io.StringIO()):
            parser = create_validation_parser()
            args = ValidationArgsExec(parser.parse_args(["--rule", "TypeChecker", url]))
            successful: bool = args.run_validation()
            self.assertFalse(successful)

    def test_cli_main_exit_codes(self):
        url = get_url("helloworld.usda")
        with redirect_stdout(io.StringIO()):
            cli_main(["--rule", "TypeChecker", url])
            # Does not raise SystemExit

        url = get_url("untyped.usda")
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cli_main(["--rule", "TypeChecker", url])
            self.assertEqual(cm.exception.code, 1)

    def test_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "usd_validation_nvidia", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        retcode = result.returncode
        stdout = result.stdout

        self.assertEqual(retcode, 0)
        self.assertIn("usage:", stdout.lower())
        self.assertIn("--rule", stdout)
        self.assertIn("--fix", stdout)
        self.assertIn("--predicate", stdout)
        self.assertIn("--variants", stdout)
        self.assertIn("--requirement", stdout)
        self.assertIn("--capability", stdout)
        self.assertIn("--feature", stdout)
        self.assertIn("--profile", stdout)

    def test_omni_asset_validator_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "omni.asset_validator", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        retcode = result.returncode
        stdout = result.stdout

        self.assertEqual(retcode, 0)
        self.assertIn("usage:", stdout.lower())
        self.assertIn("--rule", stdout)
        self.assertIn("--fix", stdout)
        self.assertIn("--predicate", stdout)
        self.assertIn("--variants", stdout)
        self.assertIn("--requirement", stdout)
        self.assertIn("--capability", stdout)
        self.assertIn("--feature", stdout)
        self.assertIn("--profile", stdout)

    def test_cli_resolver_context(self):
        url = get_url("materialInScope.usda")

        with TemporaryDirectory() as temp_dir:
            mdl_file_path = pathlib.Path(temp_dir) / "OmniPBR.mdl"
            mdl_file_path.write_text("// THIS IS OmniPBR.mdl!")
            search_paths = [temp_dir]
            resolver_context = Ar.DefaultResolverContext(search_paths)

            with Ar.ResolverContextBinder(resolver_context):
                with self.assertLogs(level="INFO") as cm:
                    parser = create_validation_parser()
                    args = ValidationArgsExec(parser.parse_args(["--rule", "MaterialPathChecker", url]))
                    args.run_validation()

                    value = os.linesep.join(cm.output)
                    self.assertNotIn("Failures: 0", value)
                    self.assertNotIn("0 Failures", value)
                    self.assertNotIn("Errors: 0", value)
                    self.assertNotIn("0 Errors", value)
                    self.assertNotIn("Warnings: 0", value)
                    self.assertNotIn("0 Warnings", value)
                    self.assertNotIn("Infos: 0", value)
                    self.assertNotIn("0 Infos", value)
                    self.assertIn("No issues found.", value)

    def test_parameters_property(self):
        """Test that parameters property parses NAME=VALUE correctly."""
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "tolerance=0.001", "--parameter", "enabled=true", "asset.usda"])
        args = ValidationArgsExec(args)
        params = args.parameters
        self.assertEqual(params, {"tolerance": 0.001, "enabled": True})

    def test_parameters_property_empty(self):
        """Test that parameters property returns empty dict when no parameters provided."""
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        args = ValidationArgsExec(args)
        params = args.parameters
        self.assertEqual(params, {})

    def test_parameters_property_equals_in_value(self):
        """Test that parameters with = in value are parsed correctly."""
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "expression=a=b+c", "asset.usda"])
        args = ValidationArgsExec(args)
        params = args.parameters
        self.assertEqual(params, {"expression": "a=b+c"})

    def test_parameters_property_empty_value(self):
        """Test that parameter with empty value is allowed."""
        parser = create_validation_parser()
        args = parser.parse_args(["--parameter", "name=", "asset.usda"])
        args = ValidationArgsExec(args)
        params = args.parameters
        self.assertEqual(params, {"name": ""})

    def test_parameters_property_whitespace(self):
        """Test that whitespace around name and value is stripped."""
        parser = create_validation_parser()
        args = parser.parse_args(
            [
                "--parameter",
                "name = value",  # spaces around =
                "--parameter",
                " name2=value2 ",  # leading/trailing spaces
                "--parameter",
                "name3= value3 ",  # space after = and trailing
                "asset.usda",
            ]
        )
        args = ValidationArgsExec(args)
        params = args.parameters
        # All whitespace should be stripped from both name and value
        self.assertEqual(params, {"name": "value", "name2": "value2", "name3": "value3"})


class AutoDetectionTest(unittest.TestCase):
    """Tests for profile auto-detection mode (OMPE-89326)."""

    def test_should_auto_detect_false_with_explicit_profile(self):
        parser = create_validation_parser()
        # Can't test with --profile because no profiles registered in this env,
        # but we can test with --rule which also disables auto-detect
        args = parser.parse_args(["--rule", "StageMetadataChecker", "asset.usda"])
        exec = ValidationArgsExec(args)
        self.assertFalse(exec._should_auto_detect())

    def test_should_auto_detect_false_with_no_profiles_registered(self):
        parser = create_validation_parser()
        args = parser.parse_args(["asset.usda"])
        exec = ValidationArgsExec(args)
        # Auto-detect requires profiles to be in the registry
        if len(ProfileRegistry().latest_values()) == 0:
            self.assertFalse(exec._should_auto_detect())

    def test_should_auto_detect_false_with_feature(self):
        parser = create_validation_parser()
        feature_id = cap.Features.MINIMAL_PLACEABLE_VISUAL.id
        args = parser.parse_args(["--feature", feature_id, "asset.usda"])
        exec = ValidationArgsExec(args)
        self.assertFalse(exec._should_auto_detect())

    def test_auto_detect_no_rules_profile_counts_as_matched(self):
        """A profile with no requirements shows as PASS in Matching profiles output."""
        profile = Profile(
            id="empty-rules-profile",
            version="1.0.0",
            path="",
            features=[],
            capabilities=[Capability(id="empty-cap", version="1.0.0", path="", requirements=[])],
        )
        register_profile(profile)
        try:
            url = get_url("helloworld.usda")
            parser = create_validation_parser()
            exec = ValidationArgsExec(parser.parse_args([url]))
            with self.assertLogs(level="INFO") as cm:
                exec.run_validation()
            output = os.linesep.join(cm.output)
            self.assertIn("Matching profiles:", output)
            self.assertIn("empty-rules-profile", output)
            self.assertNotIn("Non-matching profiles:", output)
        finally:
            unregister_profile(profile)
