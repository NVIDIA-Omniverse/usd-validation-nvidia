# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Reference-based NVIDIA USD Validation feature plugin example."""

from example_validate_references import Features

from usd_validation_nvidia import register_features, unregister_features

# [snippet:referenced-features]
EXAMPLE_DEFAULT_PRIM_FEATURE = Features.EX_001
EXAMPLE_DEPENDENT_FEATURE = Features.EX_002
# [/snippet:referenced-features]


# [snippet:plugin-entry-point]
class Plugin:
    def on_startup(self) -> None:
        register_features([EXAMPLE_DEFAULT_PRIM_FEATURE, EXAMPLE_DEPENDENT_FEATURE])

    def on_shutdown(self) -> None:
        unregister_features([EXAMPLE_DEFAULT_PRIM_FEATURE, EXAMPLE_DEPENDENT_FEATURE])


# [/snippet:plugin-entry-point]
