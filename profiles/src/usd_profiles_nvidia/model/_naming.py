# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import re

from ._version import Version


class Naming:
    @classmethod
    def identifier(cls, name: str) -> str:
        """
        Convert a name to an identifier. An identifier:
        - Has underscores instead of non-alphanumeric characters
        - Is converted to lowercase

        Args:
            name: The name to convert.
        """
        identifier: str = name
        identifier = re.sub(r"[^A-Za-z0-9]", "_", identifier)
        identifier = re.sub(r"_+", "_", identifier)
        identifier = identifier.lower()
        return identifier

    @classmethod
    def _strip_namespace(cls, name: str, namespace: str) -> str:
        return name.removeprefix(f"{namespace.rstrip('.')}.")

    @classmethod
    def enum_name(cls, name: str, version: str | Version | None = None, namespace: str = "") -> str:
        """
        Convert a name to an enum name. An enum name:
        - Has underscores instead of non-alphanumeric characters
        - Is converted to uppercase

        If ``namespace`` is provided, ``namespace.`` is stripped from the front
        of ``name`` before conversion.

        Args:
            name: The name to convert.
            version: The version to append (optional).
            namespace: Reverse-domain namespace without trailing dot (optional).
        """
        if namespace:
            name = cls._strip_namespace(name, namespace)
        enum_name: str = f"{name}{f'-v{version}' if version else ''}"
        enum_name = re.sub(r"[^A-Za-z0-9]", "_", enum_name)
        enum_name = re.sub(r"_+", "_", enum_name)
        enum_name = enum_name.upper()
        return enum_name

    @classmethod
    def class_name(cls, name: str, namespace: str = "") -> str:
        """
        Convert a name to a class name. A class name:
        - Has capitalized first letters
        - Removes underscores, hyphens and dots

        If ``namespace`` is provided, ``namespace.`` is stripped from the front
        of ``name`` before conversion.

        Args:
            name: The name to convert.
            namespace: Reverse-domain namespace without trailing dot (optional).
        """
        if namespace:
            name = cls._strip_namespace(name, namespace)
        return "".join(token.capitalize() for token in re.split(r"[_\-\.]", name))
