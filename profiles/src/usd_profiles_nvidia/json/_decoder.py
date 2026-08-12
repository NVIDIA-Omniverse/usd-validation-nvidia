# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import json
from collections.abc import Mapping
from dataclasses import fields

from usd_profiles_nvidia.api import Capability, Feature, FeatureRef, Requirement, RequirementRef
from usd_profiles_nvidia.model import (
    Compatibility,
    Example,
    ExampleResult,
    ExampleSnippet,
    ExampleSnippetLanguage,
    IdVersion,
    Metadata,
    Parameter,
    ParameterType,
    Profile,
    ProfileFeature,
    Tag,
    Version,
)

__all__ = ["JsonDeserialize"]

_FEATURE_FIELDS = frozenset(field.name for field in fields(Feature))
_FEATURE_JSON_FIELDS = _FEATURE_FIELDS | {"metadata"}


class JsonDeserialize(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    @classmethod
    def object_hook(cls, dct):
        if "capability" in dct:
            return cls.decode_capability(dct["capability"])
        elif "profile" in dct:
            return cls.decode_profile(dct["profile"])
        elif "feature" in dct and isinstance(dct["feature"], dict):
            return cls.decode_feature(dct["feature"])
        elif "code" in dct and "tags" in dct:
            return cls.decode_requirement(dct)
        elif "type" in dct and "display_name" in dct and "assigned_value" in dct:
            return cls.decode_parameter(dct)
        elif "path" in dct:
            return cls.decode_metadata(dct)
        elif "snippet" in dct and ("name" in dct or "display_name" in dct) and "result" in dct:
            return cls.decode_example(dct)
        elif "language" in dct and "content" in dct:
            return cls.decode_example_snippet(dct)
        else:
            return dct

    @classmethod
    def decode_capability(cls, dct):
        metadata = dct.get("metadata")
        return Capability(
            id=dct["id"],
            version=dct.get("version", ""),
            requirements=dct.get("requirements", []),
            path=(metadata.path if isinstance(metadata, Metadata) else dct.get("path")) or "",
        )

    @classmethod
    def decode_profile(cls, dct):
        return Profile(
            id=dct["id"],
            version=dct.get("version"),
            display_name=dct.get("name"),
            message=dct.get("description"),
            features=cls.decode_profile_features(dct.get("features")),
            metadata=dct.get("metadata", Metadata()),
        )

    @classmethod
    def decode_feature(cls, dct):
        metadata = dct.get("metadata")
        authored_custom_data = dct.get("custom_data", {})
        if not isinstance(authored_custom_data, Mapping):
            raise TypeError(f"'custom_data' must be an object, got {type(authored_custom_data).__name__}")

        feature_data = {key: value for key, value in dct.items() if key in _FEATURE_FIELDS}
        feature_data.update(
            id=dct["id"],
            version=dct.get("version", ""),
            path=metadata.path if isinstance(metadata, Metadata) else dct.get("path", ""),
            requirements=cls.decode_requirement_refs(dct.get("requirements")),
            dependencies=cls.decode_feature_refs(dct.get("dependencies")),
            custom_data={
                **authored_custom_data,
                **{key: value for key, value in dct.items() if key not in _FEATURE_JSON_FIELDS},
            },
        )
        return Feature(**feature_data)

    @classmethod
    def decode_requirement(cls, dct):
        metadata = dct.get("metadata")
        return Requirement(
            code=dct["code"],
            version=dct.get("version"),
            display_name=dct.get("name"),
            compatibility=(
                Compatibility.from_name(dct["compatibility"]).display_name if dct.get("compatibility") else None
            ),
            tags=cls.decode_tags(dct.get("tags")),
            validator=dct.get("validator"),
            parameters=tuple(dct.get("parameters", ())),
            path=metadata.path if isinstance(metadata, Metadata) else None,
            message=dct.get("message"),
            examples=tuple(dct.get("examples", ())),
        )

    @classmethod
    def decode_parameter(cls, dct):
        return Parameter(
            display_name=dct["display_name"],
            type=ParameterType(dct["type"]),
            assigned_value=dct.get("assigned_value"),
            enum_values=dct.get("enum_values"),
        )

    @classmethod
    def decode_example(cls, dct):
        return Example(
            snippet=dct["snippet"],
            display_name=dct.get("display_name") or dct.get("name") or "",
            result=ExampleResult(dct["result"]),
        )

    @classmethod
    def decode_example_snippet(cls, dct):
        return ExampleSnippet(
            language=ExampleSnippetLanguage(dct["language"]),
            content=dct["content"],
        )

    @classmethod
    def decode_metadata(cls, dct):
        return Metadata(
            path=dct.get("path"),
        )

    @classmethod
    def decode_version(cls, version: str | None):
        if version is not None:
            return Version(version)
        else:
            return None

    @classmethod
    def decode_tags(cls, tags: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
        if tags is None:
            return ()
        if isinstance(tags, str):
            tags = (tags,)
        result: list[str] = []
        for tag in tags:
            try:
                result.append(Tag.from_name(tag).display_name)
            except AttributeError:
                continue
        return tuple(result)

    @classmethod
    def decode_profile_features(cls, features: list[dict] | None) -> list[ProfileFeature]:
        if features is not None:
            return [cls.decode_profile_feature(feature) for feature in features]
        else:
            return []

    @classmethod
    def decode_profile_feature(cls, feature: dict) -> ProfileFeature:
        return ProfileFeature(
            feature=cls.decode_id_version(feature["feature"]),
            optional=feature["optional"],
        )

    @classmethod
    def decode_id_versions(cls, id_versions: list[str] | None) -> list[IdVersion]:
        if id_versions is not None:
            return [IdVersion.parse(id_version) for id_version in id_versions]
        else:
            return []

    @classmethod
    def decode_requirement_refs(cls, id_versions: list[str] | None) -> list[RequirementRef]:
        return [
            RequirementRef(id_version.id, str(id_version.version) if id_version.version is not None else None)
            for id_version in cls.decode_id_versions(id_versions)
        ]

    @classmethod
    def decode_feature_refs(cls, id_versions: list[str] | None) -> list[FeatureRef]:
        return [
            FeatureRef(id_version.id, str(id_version.version) if id_version.version is not None else None)
            for id_version in cls.decode_id_versions(id_versions)
        ]

    @classmethod
    def decode_id_version(cls, id_version: str | None) -> IdVersion | None:
        if id_version is not None:
            return IdVersion.parse(id_version)
        else:
            return None
