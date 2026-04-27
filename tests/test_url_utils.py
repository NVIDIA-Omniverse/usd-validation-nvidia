# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import unittest

from nvidia_usd_validation import make_relative_url_if_possible, normalize_url


class UrlUtilsTests(unittest.IsolatedAsyncioTestCase):
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
