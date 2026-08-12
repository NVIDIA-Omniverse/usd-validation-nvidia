# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import importlib
import importlib.util
import os
import unittest

import usd_profiles_nvidia


class TestOmniCompat(unittest.TestCase):

    def test_root_shim_exports_version(self):
        import omni.usd_profiles

        self.assertEqual(omni.usd_profiles.__version__, usd_profiles_nvidia.__version__)
        self.assertIs(omni.usd_profiles.CapabilityGraph, usd_profiles_nvidia.CapabilityGraph)
        self.assertEqual(omni.usd_profiles.__all__, ["CapabilityGraph", "__version__"])

        namespace: dict[str, str] = {}
        exec("from omni.usd_profiles import *", namespace)
        self.assertEqual(namespace["__version__"], usd_profiles_nvidia.__version__)
        self.assertIs(namespace["CapabilityGraph"], usd_profiles_nvidia.CapabilityGraph)

    def test_public_subpackage_shims_export_same_objects(self):
        module_exports = {
            "codegen": ["PythonGenerator"],
            "graph": ["CapabilityGraph", "CapabilityGraphBuilder", "CapabilityGraphDeserializer", "encode_graph"],
            "json": ["JsonDeserialize", "JsonFeaturesParser", "JsonSerialize"],
            "markdown": ["DocumentParser", "ProfilesParser"],
            "model": [
                "BuildCapabilityGraph",
                "Capability",
                "CapabilityNode",
                "Version",
            ],
            "parsers": ["ProfilesParser", "SpecificationsParser"],
            "store": ["RequirementStore", "SpecificationsStore"],
            "toml": ["PROFILES_TOML", "TomlFeaturesParser", "TomlProfilesParser"],
        }

        for module_name, export_names in module_exports.items():
            with self.subTest(module_name=module_name):
                old_module = importlib.import_module(f"omni.usd_profiles.{module_name}")
                new_module = importlib.import_module(f"usd_profiles_nvidia.{module_name}")

                self.assertIs(old_module.__all__, new_module.__all__)
                for export_name in export_names:
                    self.assertIs(getattr(old_module, export_name), getattr(new_module, export_name))

    def test_omni_serialization_shim_uses_json_package(self):
        old_module = importlib.import_module("omni.usd_profiles.serialization")
        new_module = importlib.import_module("usd_profiles_nvidia.json")

        self.assertIs(old_module.__all__, new_module.__all__)
        self.assertIs(old_module.JsonDeserialize, new_module.JsonDeserialize)
        self.assertIs(old_module.JsonSerialize, new_module.JsonSerialize)

    def test_codegen_main_shim_uses_new_entry_point(self):
        old_main = importlib.import_module("omni.usd_profiles.codegen.__main__")
        new_main = importlib.import_module("usd_profiles_nvidia.codegen.__main__")

        self.assertIs(old_main.main, new_main.main)

    @unittest.skipUnless(importlib.util.find_spec("sphinx"), "Sphinx is not installed")
    def test_sphinx_shims_export_same_objects(self):
        module_exports = {
            "directives": ["features_table_setup", "requirements_table_setup"],
            "ext": ["setup"],
            "ext.directives": ["setup"],
            "ext.initialize": ["setup"],
            "ext.roles": ["setup"],
            "ext.static": ["setup"],
            "initialize": ["build_jsons_setup", "build_specs_setup"],
            "roles": ["compatibility_setup", "tag_setup"],
            "static": ["static_setup", "style_setup"],
        }

        for module_name, export_names in module_exports.items():
            with self.subTest(module_name=module_name):
                old_module = importlib.import_module(f"omni.usd_profiles.sphinx.{module_name}")
                new_module = importlib.import_module(f"usd_profiles_nvidia.sphinx.{module_name}")

                for export_name in export_names:
                    self.assertIs(getattr(old_module, export_name), getattr(new_module, export_name))

    def test_omni_root_remains_namespace_package(self):
        repo_root = os.path.dirname(os.path.dirname(__file__))

        self.assertFalse(os.path.exists(os.path.join(repo_root, "src", "omni", "__init__.py")))
