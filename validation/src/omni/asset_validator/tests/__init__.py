# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

import usd_validation_nvidia.tests
from usd_validation_nvidia.tests import *  # noqa: F403

__all__ = usd_validation_nvidia.tests.__all__
