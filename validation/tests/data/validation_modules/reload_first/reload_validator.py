# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from usd_validation_nvidia import BaseRuleChecker, register_requirements, register_rule
from usd_validation_nvidia.capabilities import RequirementRef

REQUIREMENT = RequirementRef(code="com.example.RELOAD.001", version="1.0.0")


@register_rule("LooseModule")
@register_requirements(REQUIREMENT)
class FirstRule(BaseRuleChecker):
    pass
