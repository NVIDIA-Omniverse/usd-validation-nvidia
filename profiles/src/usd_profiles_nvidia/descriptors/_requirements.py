# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from dataclasses import dataclass, replace

from usd_profiles_nvidia.api import Capability, Requirement, RequirementRef

from ._identifiers import qualify_identifier, qualify_owned_identifier


@dataclass(frozen=True, kw_only=True)
class RequirementDescriptorEnricher:
    """Add loader namespace context to parsed requirement definitions."""

    reverse_domain: str = ""

    def enrich(self, requirement: Requirement | RequirementRef) -> Requirement | RequirementRef:
        """Qualify a requirement definition or lazy reference without resolving it."""
        qualifier = qualify_owned_identifier if isinstance(requirement, Requirement) else qualify_identifier
        return replace(
            requirement,
            code=qualifier(requirement.code, self.reverse_domain),
        )

    def enrich_capability(self, capability: Capability) -> Capability:
        """Qualify requirement values while preserving their owning capability."""
        return replace(
            capability,
            requirements=[self.enrich(requirement) for requirement in capability.requirements],
        )
