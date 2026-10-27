# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import unittest
from hashlib import sha256

from usd_profiles_nvidia.api import (
    Capability,
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
    Feature,
    FeatureRef,
    Parameter,
    ParameterType,
    Profile,
    Requirement,
    RequirementRef,
)
from usd_profiles_nvidia.codegen._py_model import (
    PyCapability,
    PyExample,
    PyExampleStore,
    PyFeature,
    PyParameter,
    PyProfile,
    PyRequirement,
    PythonStoreView,
)
from usd_profiles_nvidia.model import Specifications
from usd_profiles_nvidia.parsers import SpecificationsParser
from usd_profiles_nvidia.store import ExampleStore, SpecificationsStore


class TestPythonModel(unittest.TestCase):
    def test_parameter_adds_python_enum_name(self):
        parameter = Parameter(display_name="max faces", type=ParameterType.INT, assigned_value=10)

        py_parameter = PyParameter(parameter)

        self.assertIs(py_parameter.parameter, parameter)
        self.assertEqual(py_parameter.enum_name, "MAX_FACES")
        self.assertEqual(py_parameter.assigned_value, 10)

    def test_example_adds_python_enum_name_and_resource_filename(self):
        content = 'def Xform "Root" {}'
        example = Example(
            snippet=ExampleSnippet(language=ExampleSnippetLanguage.USD, inline_content=content),
            display_name="Valid root",
            result=ExampleResult.SUCCESS,
        )

        py_example = PyExample(example)

        self.assertIs(py_example.example, example)
        self.assertEqual(py_example.enum_name, "VALID_ROOT_OK")
        self.assertEqual(py_example.filename, f"{sha256(content.encode('utf-8')).hexdigest()[:12]}.usd")

    def test_example_store_rejects_python_enum_name_collisions(self):
        examples = (
            Example(
                snippet=ExampleSnippet(language=ExampleSnippetLanguage.USD, inline_content="first"),
                display_name="Valid root",
                result=ExampleResult.SUCCESS,
            ),
            Example(
                snippet=ExampleSnippet(language=ExampleSnippetLanguage.USD, inline_content="second"),
                display_name="Valid-root",
                result=ExampleResult.SUCCESS,
            ),
        )
        store = PyExampleStore(ExampleStore([Requirement(code="REQ.001", examples=examples)]))

        with self.assertRaisesRegex(ValueError, "VALID_ROOT_OK"):
            list(store)

    def test_requirement_wraps_api_requirement(self):
        requirement = Requirement(
            code="materials.MAT.001",
            version="1.0.0",
            path="capabilities/materials/requirements/mat-001",
            validator="oav:mat-001",
        )

        py_requirement = PyRequirement(requirement, namespace="com.nvidia.simready")

        self.assertEqual(py_requirement.namespaced_id, "com.nvidia.simready.materials.MAT.001")
        self.assertEqual(py_requirement.enum_id, "MATERIALS_MAT_001")
        self.assertEqual(py_requirement.enum_id_version, "MATERIALS_MAT_001_V1_0_0")
        self.assertEqual(py_requirement.path, "capabilities/materials/requirements/mat-001")
        self.assertEqual(py_requirement.html_path, "capabilities/materials/requirements/mat-001.html")
        self.assertEqual(py_requirement.validator, "oav:mat-001")
        self.assertEqual(py_requirement.display_name, "materials.MAT.001")

    def test_html_path_is_none_without_metadata_path(self):
        self.assertEqual(PyRequirement(Requirement(code="REQ.001")).path, "")
        self.assertIsNone(PyRequirement(Requirement(code="REQ.001")).html_path)
        self.assertIsNone(PyCapability(Capability(id="materials", version="1.0.0", path="", requirements=[])).html_path)
        self.assertIsNone(PyFeature(Feature(id="rigid_body_physics", version="", path="", requirements=[])).html_path)
        self.assertIsNone(PyProfile(Profile(id="prop_robotics_neutral", version="", path="")).html_path)

    def test_capability_wraps_model_requirements(self):
        requirement = Requirement(code="materials.MAT.001", version="1.0.0")
        capability = Capability(id="materials", version="1.0.0", path="", requirements=[requirement])

        py_capability = PyCapability(capability, namespace="com.nvidia.simready")

        self.assertEqual(py_capability.namespaced_id, "com.nvidia.simready.materials")
        self.assertEqual(py_capability.enum_id, "MATERIALS")
        self.assertEqual(py_capability.enum_id_version, "MATERIALS_V1_0_0")
        self.assertEqual(py_capability.class_name, "Materials")
        self.assertEqual(py_capability.requirements[0].namespaced_id, "com.nvidia.simready.materials.MAT.001")

    def test_store_view_adds_python_namespace_without_mutating_models(self):
        docs_root = os.path.join(os.path.dirname(__file__), "resources", "namespace-spec")
        specifications = SpecificationsParser(
            root_dir=docs_root,
        ).parse()
        store = PythonStoreView(
            SpecificationsStore(specifications),
            namespace="com.nvidia.simready",
        )

        capability = next(iter(store.capabilities))
        feature = next(iter(store.features))
        profile = next(iter(store.profiles))
        requirement = next(iter(store.requirements))

        self.assertEqual(capability.namespaced_id, "com.nvidia.simready.materials")
        self.assertEqual(feature.namespaced_id, "com.nvidia.simready.rigid_body_physics")
        self.assertEqual(profile.namespaced_id, "com.nvidia.simready.prop_robotics_neutral")
        self.assertEqual(requirement.namespaced_id, "com.nvidia.simready.materials.MAT.001")

        self.assertEqual(getattr(specifications.capabilities[0], "namespace", ""), "")
        self.assertEqual(getattr(specifications.features[0], "namespace", ""), "")
        self.assertEqual(getattr(specifications.profiles[0], "namespace", ""), "")
        self.assertEqual(getattr(specifications.requirements[0], "namespace", ""), "")

    def test_requirement_refs_resolve_local_and_external(self):
        local_requirements = [
            Requirement(code="REQ.001", version="1.0.0"),
            Requirement(code="REQ.002", version="1.0.0"),
            Requirement(code="REQ.003", version="1.0.0"),
            Requirement(code="com.nvidia.usd.REQ.004", version="1.0.0"),
        ]
        feature = Feature(
            id="mixed",
            version="1.0.0",
            path="features/mixed",
            requirements=[
                RequirementRef("REQ.001"),
                RequirementRef("com.nvidia.usd.REQ.002"),
                RequirementRef("com.nvidia.usd.REQ.003", "1.0.0"),
                RequirementRef("com.nvidia.usd.REQ.004", "1.0.0"),
                RequirementRef("com.nvidia.simready.REQ.001", "1.0.0"),
            ],
        )
        specifications = Specifications(
            capabilities=[
                Capability(id="local", version="1.0.0", path="path", requirements=local_requirements),
            ],
            features=[feature],
            profiles=[],
        )
        store = PythonStoreView(SpecificationsStore(specifications), namespace="com.nvidia.usd")

        refs = store.requirements.find_all(feature.requirements)

        self.assertEqual(refs[0].enum_id_version, "REQ_001_V1_0_0")
        self.assertEqual(refs[1].enum_id_version, "REQ_002_V1_0_0")
        self.assertEqual(refs[2].enum_id_version, "REQ_003_V1_0_0")
        self.assertEqual(refs[3].enum_id_version, "REQ_004_V1_0_0")
        self.assertIsInstance(refs[4], RequirementRef)
        self.assertEqual(refs[4].code, "com.nvidia.simready.REQ.001")
        self.assertEqual(refs[4].version, "1.0.0")

    def test_unresolved_requirement_refs_are_preserved(self):
        store = PythonStoreView(
            SpecificationsStore(Specifications(capabilities=[], features=[], profiles=[])),
            namespace="com.nvidia.simready",
        )

        refs = store.requirements.find_all(
            [
                RequirementRef("namespace.REQ_0", "1.0.0"),
                RequirementRef("com.nvidia.simready.local.MISSING", "1.0.0"),
            ]
        )

        self.assertEqual(refs[0], RequirementRef("namespace.REQ_0", "1.0.0"))
        self.assertEqual(refs[1], RequirementRef("com.nvidia.simready.local.MISSING", "1.0.0"))

    def test_feature_dependencies_resolve_local_and_preserve_external_refs(self):
        base = Feature(id="base", version="1.0.0", path="features/base", requirements=[])
        current = Feature(
            id="current",
            version="1.0.0",
            path="features/current",
            requirements=[],
            dependencies=[
                FeatureRef("base", "1.0.0"),
                FeatureRef("com.nvidia.external.feature", "2.0.0"),
            ],
        )
        store = PythonStoreView(
            SpecificationsStore(Specifications(capabilities=[], features=[base, current], profiles=[])),
            namespace="com.nvidia.simready",
        )

        dependencies = store.features.find_dependencies(current)

        self.assertEqual(dependencies[0].namespaced_id, "com.nvidia.simready.base")
        self.assertEqual(dependencies[0].version, "1.0.0")
        self.assertEqual(dependencies[1], FeatureRef("com.nvidia.external.feature", "2.0.0"))
