# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from usd_profiles_nvidia.api import Feature, FeatureRef, Profile, ProfileFeature
from usd_profiles_nvidia.descriptors._features import (
    FeatureDescriptorDecoder,
    FeatureDescriptorEnricher,
)
from usd_profiles_nvidia.descriptors._identifiers import qualify_identifier


class ProfileDescriptorDecoder:
    """Decode authored profile mappings into public API DTOs without resolving features."""

    def decode_all(self, data: Any, *, path: str) -> list[Profile]:
        """Decode one or more direct or version-table profile descriptors."""
        if not isinstance(data, Mapping):
            raise TypeError(f"expected a top-level object, got {type(data).__name__}")
        if self._is_direct_profile(data) or self._is_wrapped_profile(data):
            return [self.decode(data, path=path)]
        return self._decode_version_table(data, path=path)

    @staticmethod
    def _is_direct_profile(data: Mapping[str, Any]) -> bool:
        """Return whether a mapping has the scalar fields of a direct profile."""
        return isinstance(data.get("id"), str) or isinstance(data.get("version"), str)

    @classmethod
    def _is_wrapped_profile(cls, data: Mapping[str, Any]) -> bool:
        """Return whether ``profile`` contains a direct profile rather than a version table."""
        wrapped = data.get("profile")
        return isinstance(wrapped, Mapping) and cls._is_direct_profile(wrapped)

    def decode(self, data: Mapping[str, Any], *, path: str) -> Profile:
        """Decode one direct or wrapped profile descriptor."""
        if not isinstance(data, Mapping):
            raise TypeError(f"expected a top-level object, got {type(data).__name__}")
        profile_data = data.get("profile", data)
        if not isinstance(profile_data, Mapping):
            raise TypeError(f"'profile' must be an object, got {type(profile_data).__name__}")
        return self._decode_profile(profile_data, path=path)

    def _decode_version_table(self, data: Mapping[str, Any], *, path: str) -> list[Profile]:
        """Decode the versioned profile-table layout used by SimReady descriptors."""
        profiles: list[Profile] = []
        for profile_id, versions in data.items():
            if not isinstance(profile_id, str):
                raise TypeError(f"profile id must be a string, got {type(profile_id).__name__}")
            if not isinstance(versions, Mapping):
                raise TypeError(
                    f"Profile '{profile_id}' must be an object, got {type(versions).__name__}: {versions!r}"
                )
            for version, profile_data in versions.items():
                if not isinstance(version, str):
                    raise TypeError(f"profile version must be a string, got {type(version).__name__}")
                if not isinstance(profile_data, Mapping):
                    raise TypeError(
                        f"Profile '{profile_id}' version '{version}' must be an object, "
                        f"got {type(profile_data).__name__}: {profile_data!r}"
                    )
                profiles.append(self._decode_profile({**profile_data, "id": profile_id, "version": version}, path=path))
        return profiles

    def _decode_profile(self, data: Mapping[str, Any], *, path: str) -> Profile:
        profile_id = data["id"]
        version = data["version"]
        features = data.get("profile_features", data.get("features", []))
        capabilities = data.get("capabilities", [])
        display_name = data.get("display_name", data.get("name"))
        message = data.get("message", data.get("description"))
        if not isinstance(profile_id, str) or not profile_id:
            raise TypeError("'id' must be a non-empty string")
        if not isinstance(version, str) or not version:
            raise TypeError("'version' must be a non-empty string")
        if not isinstance(features, list):
            raise TypeError(f"'features' must be a list, got {type(features).__name__}")
        if not isinstance(capabilities, list):
            raise TypeError(f"'capabilities' must be a list, got {type(capabilities).__name__}")
        if capabilities:
            raise ValueError("profile descriptor capabilities are not supported")
        if display_name is not None and not isinstance(display_name, str):
            raise TypeError(f"'display_name' must be a string, got {type(display_name).__name__}")
        if message is not None and not isinstance(message, str):
            raise TypeError(f"'message' must be a string, got {type(message).__name__}")
        profile_path = data.get("path", path)
        if not isinstance(profile_path, str):
            raise TypeError(f"'path' must be a string, got {type(profile_path).__name__}")

        profile_features = [self._decode_profile_feature(feature) for feature in features]
        return Profile(
            id=profile_id,
            version=version,
            path=profile_path,
            features=[profile_feature.feature for profile_feature in profile_features],
            profile_features=profile_features,
            display_name=display_name,
            message=message,
        )

    @staticmethod
    def _decode_profile_feature(value: Any) -> ProfileFeature:
        if not isinstance(value, Mapping):
            raise TypeError(f"profile feature must be an object, got {type(value).__name__}")
        optional = value.get("optional", False)
        if not isinstance(optional, bool):
            raise TypeError(f"'optional' must be a bool, got {type(optional).__name__}")

        if "feature" in value:
            feature_id, version = FeatureDescriptorDecoder._decode_versioned_ref(value["feature"])
        elif "id" in value:
            feature_id, version = FeatureDescriptorDecoder._decode_versioned_ref(value)
        else:
            feature_id, version = FeatureDescriptorDecoder._decode_versioned_ref(
                {key: entry for key, entry in value.items() if key != "optional"}
            )
        return ProfileFeature(FeatureRef(feature_id, version), optional=optional)


@dataclass(frozen=True, kw_only=True)
class ProfileDescriptorEnricher:
    """Add loader namespace context to parsed profile descriptors."""

    reverse_domain: str = ""

    def enrich(self, profile: Profile) -> Profile:
        """Qualify the profile id and its feature references without resolving them."""
        return replace(
            profile,
            id=qualify_identifier(profile.id, self.reverse_domain),
            features=[self._enrich_feature(feature) for feature in profile.features],
            profile_features=[
                replace(profile_feature, feature=self._enrich_feature(profile_feature.feature))
                for profile_feature in profile.profile_features
            ],
        )

    def _enrich_feature(self, feature: Feature | FeatureRef) -> Feature | FeatureRef:
        feature_id = qualify_identifier(feature.id, self.reverse_domain)
        if isinstance(feature, FeatureRef):
            return replace(feature, id=feature_id)
        enriched = FeatureDescriptorEnricher(reverse_domain=self.reverse_domain).enrich(feature)
        return replace(enriched, id=feature_id)
