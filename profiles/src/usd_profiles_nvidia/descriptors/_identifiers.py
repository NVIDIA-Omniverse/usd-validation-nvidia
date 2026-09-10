# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

_EXTERNAL_REVERSE_DOMAIN_PREFIXES = ("com.", "org.")


def qualify_owned_identifier(identifier: str, reverse_domain: str) -> str:
    """Qualify an owned definition unless it already uses the configured namespace."""
    reverse_domain = reverse_domain.rstrip(".")
    if (
        not reverse_domain
        or not identifier
        or identifier == reverse_domain
        or identifier.startswith(f"{reverse_domain}.")
    ):
        return identifier
    return f"{reverse_domain}.{identifier}"


def qualify_identifier(identifier: str, reverse_domain: str) -> str:
    """Qualify a local identifier while preserving configured and external namespaces."""
    reverse_domain = reverse_domain.rstrip(".")
    if not reverse_domain:
        return identifier
    if identifier == reverse_domain or identifier.startswith(f"{reverse_domain}."):
        return identifier
    if identifier.startswith(_EXTERNAL_REVERSE_DOMAIN_PREFIXES):
        return identifier
    return f"{reverse_domain}.{identifier}"
