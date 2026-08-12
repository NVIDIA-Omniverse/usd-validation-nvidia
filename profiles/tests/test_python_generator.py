# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import importlib
import json
import os
import sys
import unittest
from contextlib import contextmanager
from tempfile import TemporaryDirectory


@contextmanager
def import_generated_module(root_dir: str, module_name: str):
    sys.path.insert(0, root_dir)
    try:
        yield importlib.import_module(module_name)
    finally:
        sys.path.pop(0)
        for loaded_module_name in list(sys.modules):
            if loaded_module_name == module_name or loaded_module_name.startswith(f"{module_name}."):
                del sys.modules[loaded_module_name]


class TestPythonGenerator(unittest.TestCase):
    def assert_files(self, output_dir: str, destination_dir: str) -> None:
        self.assertTrue(os.path.exists(output_dir))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_capabilities.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_examples.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_features.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_parameters.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_profiles.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_protocols.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_api", "_requirements.py")))
        self.assertFalse(os.path.exists(os.path.join(output_dir, "_api", "__pycache__")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_protocols.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_requirements.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_capabilities.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_profiles.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "_features.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "capabilities.json")))
        self.assertFalse(os.path.exists(os.path.join(destination_dir, "capabilities.json")))
        self.assertFalse(os.path.exists(os.path.join(output_dir, "resources", "capabilities.json")))

    def assert_protocols(self, module) -> None:
        self.assertTrue(hasattr(module, "RequirementProtocol"))
        self.assertTrue(hasattr(module, "CapabilityProtocol"))
        self.assertTrue(hasattr(module, "FeatureRefProtocol"))
        self.assertTrue(hasattr(module, "FeatureProtocol"))
        self.assertTrue(hasattr(module, "ProfileFeatureProtocol"))
        self.assertTrue(hasattr(module, "ProfileProtocol"))
        self.assertTrue(hasattr(module, "FeatureRef"))
        self.assertTrue(hasattr(module, "RequirementRef"))
        self.assertTrue(hasattr(module, "RequirementRefProtocol"))
        self.assertTrue(hasattr(module, "Requirements"))
        self.assertTrue(hasattr(module, "Capabilities"))
        self.assertTrue(hasattr(module, "Features"))
        self.assertTrue(hasattr(module, "Profiles"))
        self.assertTrue(hasattr(module, "ProfileFeature"))

        default_capability = module.Capability("empty", "1.0.0", "")
        default_feature = module.Feature("empty", "1.0.0", "")
        default_profile = module.Profile("empty", "1.0.0", "")
        self.assertEqual(default_capability.requirements, [])
        self.assertEqual(default_feature.requirements, [])
        self.assertEqual(default_feature.dependencies, [])
        self.assertEqual(default_profile.features, [])
        self.assertEqual(default_profile.capabilities, [])
        self.assertEqual(default_profile.profile_features, [])

        for requirement in module.Requirements:
            self.assertIsInstance(requirement, module.RequirementProtocol)
        for capability in module.Capabilities:
            self.assertIsInstance(capability, module.CapabilityProtocol)
        for feature in module.Features:
            self.assertIsInstance(feature, module.FeatureProtocol)
            for dependency in feature.dependencies:
                self.assertTrue(
                    isinstance(dependency, module.FeatureProtocol)
                    or isinstance(dependency, module.FeatureRefProtocol)
                )
        for profile in module.Profiles:
            self.assertIsInstance(profile, module.ProfileProtocol)
            for profile_feature in profile.profile_features:
                self.assertIsInstance(profile_feature, module.ProfileFeatureProtocol)

    def test_codegen_py(self):
        """Test basic code generation (legacy, no reverse_domain)."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "simple-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="omni.profiles",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "omni", "profiles")
            self.assert_files(output_dir, generator.destination_dir)
            with open(os.path.join(output_dir, "capabilities.json"), encoding="utf-8") as f:
                graph_data = json.load(f)
            self.assertEqual(
                graph_data["capabilities"]["omni.profiles.geometry"]["validators"],
                ["omni.profiles:VG.RTX.002"],
            )

            with import_generated_module(os.path.join(tmpdirname, "python"), "omni.profiles") as profiles:

                self.assert_protocols(profiles)
                self.assertTrue(hasattr(profiles.Capabilities, "GEOMETRY"))
                self.assertEqual(profiles.Capabilities.GEOMETRY.id, "geometry")

                self.assertTrue(hasattr(profiles.Requirements, "VG_RTX_002_V1_0_0"))
                self.assertEqual(profiles.Requirements.VG_RTX_002_V1_0_0.code, "VG.RTX.002")
                self.assertEqual(profiles.Requirements.VG_RTX_002_V1_0_0.version, "1.0.0")
                self.assertIsNone(profiles.Requirements.VG_RTX_002_V1_0_0.validator)

    def test_codegen_with_examples(self):
        """Test code generation with requirement examples."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "simple-profile")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="omni.profile_examples",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "omni", "profile_examples")
            self.assert_files(output_dir, generator.destination_dir)

            with import_generated_module(
                os.path.join(tmpdirname, "python"), "omni.profile_examples"
            ) as profile_examples:

                invalid_example = profile_examples.Examples.SCATTERED_XFORMS_WITHOUT_COMMON_ROOT_NOK
                valid_example = profile_examples.Examples.ALL_XFORMS_UNDER_SINGLE_ROOT_OK
                self.assertEqual(invalid_example.display_name, "Scattered Xforms without common root")
                self.assertEqual(valid_example.display_name, "All Xforms under single root")
                self.assertEqual(invalid_example.result, profile_examples.ExampleResult.FAILURE)
                self.assertTrue(invalid_example.snippet.content)
                self.assertEqual(
                    profile_examples.Requirements.HI_001_V1_0_0.examples,
                    (invalid_example, valid_example),
                )

    def test_codegen_with_parameters(self):
        """Test code generation with parameters (legacy, no reverse_domain)."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "param-test-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="omni.test_params",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "omni", "test_params")
            self.assert_files(output_dir, generator.destination_dir)

            with import_generated_module(os.path.join(tmpdirname, "python"), "omni.test_params") as test_params:

                self.assert_protocols(test_params)
                self.assertTrue(hasattr(test_params.Capabilities, "TEST"))
                self.assertEqual(test_params.Capabilities.TEST.id, "test")

                self.assertTrue(hasattr(test_params.Requirements, "VG_RTX_003_V1_0_0"))
                self.assertEqual(test_params.Requirements.VG_RTX_003_V1_0_0.code, "VG.RTX.003")
                self.assertTrue(hasattr(test_params.Parameters, "UP_AXIS"))
                self.assertTrue(hasattr(test_params.Parameters, "NESTING_LEVEL"))
                self.assertTrue(hasattr(test_params.Parameters, "ENABLED"))

                self.assertTrue(hasattr(test_params.Requirements, "VG_RTX_004_V1_0_0"))
                self.assertEqual(test_params.Requirements.VG_RTX_004_V1_0_0.code, "VG.RTX.004")
                self.assertTrue(hasattr(test_params.Parameters, "MODE"))

    def test_codegen_with_optional_profile_features(self):
        """Test code generation exposes optional profile feature references."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "optional-profile-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="omni.optional_profiles",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "omni", "optional_profiles")
            self.assert_files(output_dir, generator.destination_dir)

            with import_generated_module(
                os.path.join(tmpdirname, "python"), "omni.optional_profiles"
            ) as optional_profiles:

                self.assert_protocols(optional_profiles)
                profile = optional_profiles.Profiles.OPTIONAL_PROFILE_V1_0_0
                self.assertEqual(
                    profile.features,
                    [
                        optional_profiles.Features.REQUIRED_V1_0_0,
                        optional_profiles.Features.EXTRA_V1_0_0,
                    ],
                )
                self.assertEqual(
                    profile.profile_features,
                    [
                        optional_profiles.ProfileFeature(optional_profiles.Features.REQUIRED_V1_0_0),
                        optional_profiles.ProfileFeature(optional_profiles.Features.EXTRA_V1_0_0, optional=True),
                    ],
                )

    def test_codegen_with_feature_dependencies(self):
        """Test code generation exposes feature dependency references."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "feature-dependency-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="omni.feature_deps",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "omni", "feature_deps")
            self.assert_files(output_dir, generator.destination_dir)
            with open(os.path.join(output_dir, "capabilities.json"), encoding="utf-8") as f:
                graph_data = json.load(f)
            self.assertEqual(
                graph_data["capabilities"]["omni.feature_deps.FET003_BASE_PHYSX"]["predecessors"],
                ["omni.feature_deps", "omni.feature_deps.FET003_BASE_NEUTRAL"],
            )

            with import_generated_module(os.path.join(tmpdirname, "python"), "omni.feature_deps") as feature_deps:
                self.assert_protocols(feature_deps)
                feature = feature_deps.Features.FET003_BASE_PHYSX_V0_1_0
                self.assertEqual(
                    feature.dependencies,
                    [feature_deps.Features.FET003_BASE_NEUTRAL_V0_1_0],
                )
                string_dep_feature = feature_deps.Features.FET004_BASE_STRING_DEP_V0_1_0
                self.assertEqual(
                    string_dep_feature.dependencies,
                    [feature_deps.Features.FET003_BASE_NEUTRAL_V0_1_0],
                )

    def test_codegen_with_external_requirement_refs(self):
        """External requirement refs generate RequirementRef values while local refs stay local enums."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "external-requirement-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="usd.generated",
                reverse_domain="com.nvidia.usd",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "usd", "generated")
            self.assert_files(output_dir, generator.destination_dir)

            with import_generated_module(os.path.join(tmpdirname, "python"), "usd.generated") as generated:

                expected_requirements = [
                    generated.Requirements.REQ_001_V1_0_0,
                    generated.Requirements.REQ_002_V1_0_0,
                    generated.Requirements.REQ_003_V1_0_0,
                    generated.Requirements.REQ_004_V1_0_0,
                    generated.RequirementRef("com.nvidia.simready.REQ.001", "1.0.0"),
                ]
                inline_feature = generated.Features.MIXED_REQUIREMENTS_V1_0_0
                json_feature = generated.Features.MIXED_REQUIREMENTS_JSON_V1_0_0
                self.assertEqual(inline_feature.requirements, expected_requirements)
                self.assertEqual(json_feature.requirements, expected_requirements)
                self.assertEqual(generated.Requirements.REQ_001_V1_0_0.code, "com.nvidia.usd.REQ.001")
                self.assertEqual(generated.Requirements.REQ_002_V1_0_0.code, "com.nvidia.usd.REQ.002")
                self.assertEqual(generated.Requirements.REQ_003_V1_0_0.code, "com.nvidia.usd.REQ.003")
                self.assertEqual(generated.Requirements.REQ_004_V1_0_0.code, "com.nvidia.usd.REQ.004")

    def test_codegen_with_reverse_domain(self):
        """reverse_domain auto-qualifies short names; enum members have the prefix stripped."""
        from usd_profiles_nvidia.codegen import PythonGenerator

        docs_root = os.path.join(os.path.dirname(__file__), "resources", "namespace-spec")
        with TemporaryDirectory() as tmpdirname:
            generator = PythonGenerator(
                docs_root=docs_root,
                destination_dir=os.path.join(tmpdirname, "python"),
                package_name="simready.foundations.core",
                reverse_domain="com.nvidia.simready",
            )
            generator.generate()

            output_dir = os.path.join(tmpdirname, "python", "simready", "foundations", "core")
            self.assert_files(output_dir, generator.destination_dir)
            with open(os.path.join(output_dir, "capabilities.json"), encoding="utf-8") as f:
                graph_data = json.load(f)
            self.assertEqual(graph_data["schema"], "usd-profiles/capability-dag")
            self.assertIn("com.nvidia.simready", graph_data["capabilities"])
            self.assertIn("com.nvidia.simready.materials", graph_data["capabilities"])
            self.assertIn(
                "com.nvidia.simready.materials.MAT.001",
                graph_data["capabilities"]["com.nvidia.simready.materials"]["requirements"],
            )
            self.assertIn("com.nvidia.simready.rigid_body_physics", graph_data["capabilities"])
            self.assertIn("com.nvidia.simready.prop_robotics_neutral", graph_data["capabilities"])

            with import_generated_module(os.path.join(tmpdirname, "python"), "simready.foundations.core") as core:

                self.assertTrue(hasattr(core.Requirements, "MATERIALS_MAT_001_V1_0_0"))
                self.assertEqual(
                    core.Requirements.MATERIALS_MAT_001_V1_0_0.code,
                    "com.nvidia.simready.materials.MAT.001",
                )

                self.assertTrue(hasattr(core.Features, "RIGID_BODY_PHYSICS_V1_0_0"))
                self.assertEqual(
                    core.Features.RIGID_BODY_PHYSICS_V1_0_0.id,
                    "com.nvidia.simready.rigid_body_physics",
                )

                self.assertTrue(hasattr(core.Profiles, "PROP_ROBOTICS_NEUTRAL"))
                self.assertEqual(
                    core.Profiles.PROP_ROBOTICS_NEUTRAL.id,
                    "com.nvidia.simready.prop_robotics_neutral",
                )

                self.assertTrue(hasattr(core.Capabilities, "MATERIALS"))
                self.assertEqual(
                    core.Capabilities.MATERIALS.id,
                    "com.nvidia.simready.materials",
                )
