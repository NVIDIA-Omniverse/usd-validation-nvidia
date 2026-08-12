# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pkgutil import extend_path

from usd_profiles_nvidia import CapabilityGraph, __version__

__path__ = extend_path(__path__, __name__)

__all__ = ["CapabilityGraph", "__version__"]
