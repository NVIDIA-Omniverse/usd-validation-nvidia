# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import tempfile
import unittest

from usd_validation_nvidia import (
    LocalUriResolver,
    UriResolver,
    make_absolute_url_if_possible,
    make_relative_url_if_possible,
    normalize_url,
)


class LocalUriResolverTests(unittest.TestCase):
    def test_satisfies_protocol(self):
        self.assertIsInstance(LocalUriResolver(), UriResolver)

    def test_is_uri_found_file(self):
        resolver = LocalUriResolver()
        with tempfile.NamedTemporaryFile() as f:
            self.assertTrue(resolver.is_uri_found(f.name))

    def test_is_uri_found_missing(self):
        resolver = LocalUriResolver()
        self.assertFalse(resolver.is_uri_found("/does/not/exist.usd"))

    def test_is_uri_prefix_directory(self):
        resolver = LocalUriResolver()
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(resolver.is_uri_prefix(d))

    def test_is_uri_prefix_file(self):
        resolver = LocalUriResolver()
        with tempfile.NamedTemporaryFile() as f:
            self.assertFalse(resolver.is_uri_prefix(f.name))

    def test_list_uris(self):
        resolver = LocalUriResolver()
        with tempfile.TemporaryDirectory() as d:
            names = ["a.usd", "b.usd"]
            for name in names:
                with open(os.path.join(d, name), "w"):
                    pass
            result = resolver.list_uris(d)
            self.assertEqual(sorted(os.path.basename(p) for p in result), sorted(names))

    def test_parent_uri(self):
        resolver = LocalUriResolver()
        parent = resolver.parent_uri("/some/path/file.usd")
        self.assertEqual(parent, "/some/path")

    def test_join_uri(self):
        resolver = LocalUriResolver()
        joined = resolver.join_uri("/some/path", "file.usd")
        self.assertEqual(joined, os.path.join("/some/path", "file.usd"))

    def test_basename_file(self):
        resolver = LocalUriResolver()
        self.assertEqual(resolver.basename("/some/path/file.usd"), "file.usd")

    def test_basename_directory(self):
        resolver = LocalUriResolver()
        self.assertEqual(resolver.basename("/some/path/subdir"), "subdir")

    def test_relative_uri_child(self):
        resolver = LocalUriResolver()
        rel = resolver.relative_uri("/some/base", "/some/base/child/file.usd")
        self.assertEqual(rel, "./child/file.usd")

    def test_relative_uri_sibling(self):
        resolver = LocalUriResolver()
        rel = resolver.relative_uri("/some/base", "/some/other/file.usd")
        self.assertEqual(rel, "../other/file.usd")

    def test_relative_uri_parent(self):
        resolver = LocalUriResolver()
        rel = resolver.relative_uri("/some/base/sub", "/some/file.usd")
        self.assertEqual(rel, "../../file.usd")


class UrlUtilsTests(unittest.IsolatedAsyncioTestCase):
    def test_make_absolute_url_if_possible(self):
        self.assertEqual(make_absolute_url_if_possible(""), "")

        relative_path = os.path.join("relative_sublayers", "asset.usda")
        self.assertEqual(make_absolute_url_if_possible(relative_path), os.path.abspath(relative_path))

        absolute_path = os.path.abspath(relative_path)
        self.assertEqual(make_absolute_url_if_possible(absolute_path), absolute_path)

        if os.name == "nt":
            drive_path = "c:\\parent\\asset.usda"
            self.assertEqual(make_absolute_url_if_possible(drive_path), os.path.abspath(drive_path))

        for url in [
            "file:///C:/parent/asset.usda",
            "https://localhost/parent/asset.usda",
            "omniverse://localhost/parent/asset.usda",
        ]:
            self.assertEqual(make_absolute_url_if_possible(url), url)

    def test_normalize_url(self):
        if os.name == "nt":
            url = normalize_url("c:\\test.usd")
            self.assertEqual(url, "C:/test.usd")

            url = normalize_url("file:/c:/test.usd")
            self.assertEqual(url, "C:/test.usd")

            url = normalize_url("file:///c:/test.usd")
            self.assertEqual(url, "C:/test.usd")
        else:
            url = normalize_url("/test.usd")
            self.assertEqual(url, "/test.usd")

            url = normalize_url("file:/test.usd")
            self.assertEqual(url, "/test.usd")

            url = normalize_url("file:///test.usd")
            self.assertEqual(url, "/test.usd")

        # If it has netloc, it will keep url untouched.
        url = normalize_url("file://localhost/c:/test.usd")
        self.assertEqual(url, "file://localhost/c:/test.usd")

        # For urls not prefixed with "file:" or local paths, it will keep them untouched.
        url = normalize_url("https://localhost/test.usd")
        self.assertEqual(url, "https://localhost/test.usd")

        # For anonymous layer identifie, it will keep it untouched.
        url = normalize_url("anon:0EFDEF")
        self.assertEqual(url, "anon:0EFDEF")

    def test_make_relative_url(self):
        if os.name == "nt":
            relative_url = make_relative_url_if_possible("c:/parent/child/test.usd", "C:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("c:\\parent\\child\\test.usd", "C:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("file:/c:/parent/child/test.usd", "C:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible(
                "file:/c:/parent/child/test.usd", "file:/C:/parent/another/test.usd"
            )
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("c:/parent/child/test.usd", "file:/C:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible(
                "file:///c:/parent/child/test.usd", "file:/C:/parent/another/test.usd"
            )
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible(
                "file://localhost/c:/parent/child/test.usd", "file:/C:/parent/another/test.usd"
            )
            self.assertEqual(relative_url, "file:/C:/parent/another/test.usd")
        else:
            relative_url = make_relative_url_if_possible("/parent/child/test.usd", "/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("file:/parent/child/test.usd", "/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("file:/parent/child/test.usd", "file:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible("/parent/child/test.usd", "file:/parent/another/test.usd")
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible(
                "file:///parent/child/test.usd", "file:/parent/another/test.usd"
            )
            self.assertEqual(relative_url, "../another/test.usd")

            relative_url = make_relative_url_if_possible(
                "file://localhost/parent/child/test.usd", "file:/parent/another/test.usd"
            )
            self.assertEqual(relative_url, "file:/parent/another/test.usd")

        # Schemes are different.
        relative_url = make_relative_url_if_possible(
            "https://localhost/parent/child/test.usd", "file://localhost/parent/another/test.usd"
        )
        self.assertEqual(relative_url, "file://localhost/parent/another/test.usd")

        # Net locations are different
        relative_url = make_relative_url_if_possible(
            "https://localhost/parent/child/test.usd", "https://localhost2/parent/another/test.usd"
        )
        self.assertEqual(relative_url, "https://localhost2/parent/another/test.usd")

        relative_url = make_relative_url_if_possible(
            "https://localhost/parent/child/test.usd", "https://localhost/parent/another/test.usd"
        )
        self.assertEqual(relative_url, "../another/test.usd")

        relative_url = make_relative_url_if_possible(
            "https://localhost/parent/child/test.usd", "https://localhost/parent/another/test.usd", True
        )
        self.assertEqual(relative_url, "../../another/test.usd")
