# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, fields, replace
from typing import Any

from usd_profiles_nvidia.api import Feature, FeatureRef, RequirementRef

_CORE_FEATURE_FIELDS = frozenset(field.name for field in fields(Feature))
_EXTERNAL_REVERSE_DOMAIN_PREFIXES = ("com.", "org.")


class FeatureDescriptorError(ValueError):
    """An invalid feature descriptor with its source path."""

    def __init__(self, path: str | os.PathLike[str], error: Exception):
        self.path = os.fspath(path)
        self.original_error = error
        super().__init__(f"Invalid feature descriptor {self.path}: {error}")


@contextmanager
def feature_descriptor_errors(path: str | os.PathLike[str]) -> Iterator[None]:
    """Add source-path context to expected descriptor parsing errors."""
    try:
        yield
    except FeatureDescriptorError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise FeatureDescriptorError(path, error) from error


class FeatureDescriptorDecoder:
    """Decode an authored feature mapping into a public API DTO."""

    def decode(self, data: Mapping[str, Any]) -> Feature:
        """Decode a feature without resolving or enriching its references."""
        if not isinstance(data, Mapping):
            raise TypeError(f"expected a top-level object, got {type(data).__name__}")

        feature_id = data["id"]
        version = data["version"]
        path = data.get("path", "")
        requirements = data.get("requirements", [])
        dependencies = data.get("dependencies", [])

        if not isinstance(feature_id, str):
            raise TypeError(f"'id' must be a string, got {type(feature_id).__name__}")
        if not isinstance(version, str):
            raise TypeError(f"'version' must be a string, got {type(version).__name__}")
        if not isinstance(path, str):
            raise TypeError(f"'path' must be a string, got {type(path).__name__}")
        if not isinstance(requirements, list):
            raise TypeError(f"'requirements' must be a list, got {type(requirements).__name__}")
        if not isinstance(dependencies, list):
            raise TypeError(f"'dependencies' must be a list, got {type(dependencies).__name__}")
        authored_custom_data = data.get("custom_data", {})
        if not isinstance(authored_custom_data, Mapping):
            raise TypeError(f"'custom_data' must be an object, got {type(authored_custom_data).__name__}")

        feature_data = {key: value for key, value in data.items() if key in _CORE_FEATURE_FIELDS}
        feature_data.update(
            id=feature_id,
            version=version,
            path=path,
            requirements=[self._decode_requirement_ref(value) for value in requirements],
            dependencies=[self._decode_feature_ref(value) for value in dependencies],
            custom_data={
                **authored_custom_data,
                **{key: value for key, value in data.items() if key not in _CORE_FEATURE_FIELDS},
            },
        )
        return Feature(**feature_data)

    def _decode_requirement_ref(self, value: Any) -> RequirementRef:
        code, version = self._decode_versioned_ref(value)
        return RequirementRef(code, version)

    @classmethod
    def _decode_feature_ref(cls, value: Any) -> FeatureRef:
        feature_id, version = cls._decode_versioned_ref(value)
        return FeatureRef(feature_id, version)

    @staticmethod
    def _decode_versioned_ref(value: Any) -> tuple[str, str | None]:
        if isinstance(value, str):
            identifier, separator, version = value.partition("@")
            if not identifier or (separator and not version) or (separator and "@" in version):
                raise ValueError(f"invalid versioned reference: {value!r}")
            return identifier, version if separator else None

        if not isinstance(value, Mapping):
            raise TypeError(f"reference must be a string or object, got {type(value).__name__}")

        if "id" in value or "code" in value:
            identifier = value.get("id", value.get("code"))
            version = value.get("version")
        else:
            if len(value) != 1:
                raise ValueError(f"expected exactly one identifier per reference, got: {list(value.keys())}")
            identifier, attributes = next(iter(value.items()))
            if attributes is None:
                version = None
            elif isinstance(attributes, Mapping):
                version = attributes.get("version")
            else:
                raise TypeError(
                    f"reference attributes for {identifier!r} must be an object, "
                    f"got {type(attributes).__name__}"
                )

        if not isinstance(identifier, str) or not identifier:
            raise TypeError("reference identifier must be a non-empty string")
        if version is not None and not isinstance(version, str):
            raise TypeError(f"reference version must be a string, got {type(version).__name__}")
        return identifier, version


@dataclass(frozen=True, kw_only=True)
class FeatureDescriptorEnricher:
    """Add loader context to parsed feature descriptors."""

    reverse_domain: str = ""

    def enrich(self, feature: Feature) -> Feature:
        """Qualify requirement references without resolving them."""
        requirements = [
            replace(requirement, code=self._qualify(requirement.code))
            if isinstance(requirement, RequirementRef)
            else requirement
            for requirement in feature.requirements
        ]
        return replace(feature, requirements=requirements)

    def _qualify(self, code: str) -> str:
        reverse_domain = self.reverse_domain.rstrip(".")
        if not reverse_domain:
            return code
        if code == reverse_domain or code.startswith(f"{reverse_domain}."):
            return code
        if code.startswith(_EXTERNAL_REVERSE_DOMAIN_PREFIXES):
            return code
        return f"{reverse_domain}.{code}"
