# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Minimal requirement-backed NVIDIA USD Validation plugin example."""

from pxr import Usd
from example_requirements import Requirements

from usd_validation_nvidia import (
    BaseRuleChecker,
    register_requirements,
    register_rule,
    unregister_requirements,
    unregister_rule,
)


# [snippet:custom-requirement]
EXAMPLE_DEFAULT_PRIM = Requirements.EXAMPLE_001
# [/snippet:custom-requirement]


# [snippet:custom-rule]
class ExampleDefaultPrimRequirementChecker(BaseRuleChecker):
    """Require the stage to define a valid default prim."""

    def CheckStage(self, stage: Usd.Stage) -> None:
        if not stage.GetDefaultPrim():
            self._AddFailedCheck(
                message="Stage must define a valid default prim.",
                requirement=EXAMPLE_DEFAULT_PRIM,
            )


# [/snippet:custom-rule]


# [snippet:plugin-entry-point]
class Plugin:
    def on_startup(self) -> None:
        register_requirements(EXAMPLE_DEFAULT_PRIM)(ExampleDefaultPrimRequirementChecker)
        register_rule("Example")(ExampleDefaultPrimRequirementChecker)

    def on_shutdown(self) -> None:
        unregister_rule(ExampleDefaultPrimRequirementChecker)
        unregister_requirements(ExampleDefaultPrimRequirementChecker)
# [/snippet:plugin-entry-point]
