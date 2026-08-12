# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from ._build_jsons import setup as build_jsons_setup
from ._build_specs import setup as build_specs_setup

__all__ = ["build_jsons_setup", "build_specs_setup"]
