# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.model import Naming, Version


class TestNaming(unittest.TestCase):
    def test_identifier_lowercase(self):
        self.assertEqual(Naming.identifier("minimal_placeable_visual"), "minimal_placeable_visual")

    def test_identifier_with_hyphens(self):
        self.assertEqual(Naming.identifier("naming-paths"), "naming_paths")

    def test_identifier_with_dots(self):
        self.assertEqual(Naming.identifier("foo.bar"), "foo_bar")

    def test_enum_name_uppercase(self):
        self.assertEqual(Naming.enum_name("geometry"), "GEOMETRY")

    def test_enum_name_with_version(self):
        self.assertEqual(
            Naming.enum_name("geometry", Version(1, 0, 0)),
            "GEOMETRY_V1_0_0",
        )

    def test_enum_name_non_alphanumeric(self):
        self.assertEqual(Naming.enum_name("naming-paths"), "NAMING_PATHS")

    def test_class_name(self):
        self.assertEqual(Naming.class_name("naming_paths"), "NamingPaths")

    def test_enum_name_with_namespace_stripped(self):
        """Namespace prefix is stripped before generating the enum name."""
        self.assertEqual(
            Naming.enum_name("com.nvidia.simready.materials", namespace="com.nvidia.simready"),
            "MATERIALS",
        )

    def test_enum_name_with_namespace_and_version(self):
        self.assertEqual(
            Naming.enum_name(
                "com.nvidia.simready.materials.MAT.001",
                version=Version(1, 0, 0),
                namespace="com.nvidia.simready",
            ),
            "MATERIALS_MAT_001_V1_0_0",
        )

    def test_enum_name_namespace_no_match_unchanged(self):
        """If the name doesn't start with namespace, no stripping occurs."""
        self.assertEqual(
            Naming.enum_name("geometry", namespace="com.nvidia.simready"),
            "GEOMETRY",
        )

    def test_enum_name_empty_namespace_unchanged(self):
        """Empty namespace means no stripping (backward compatibility)."""
        self.assertEqual(
            Naming.enum_name("com.nvidia.simready.materials"),
            "COM_NVIDIA_SIMREADY_MATERIALS",
        )

    def test_class_name_with_namespace_stripped(self):
        self.assertEqual(
            Naming.class_name("com.nvidia.simready.materials", namespace="com.nvidia.simready"),
            "Materials",
        )

    def test_class_name_namespace_no_match_unchanged(self):
        self.assertEqual(
            Naming.class_name("geometry", namespace="com.nvidia.simready"),
            "Geometry",
        )

    def test_enum_name_namespace_with_trailing_dot(self):
        """Trailing dot in namespace is normalized — same result as without."""
        self.assertEqual(
            Naming.enum_name("com.nvidia.simready.materials", namespace="com.nvidia.simready."),
            "MATERIALS",
        )

    def test_class_name_namespace_with_trailing_dot(self):
        self.assertEqual(
            Naming.class_name("com.nvidia.simready.materials", namespace="com.nvidia.simready."),
            "Materials",
        )
