# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Minimal NVIDIA USD Validation plugin example."""

from pxr import Usd

from usd_validation_nvidia import BaseRuleChecker, register_rule, unregister_rule


# [snippet:custom-rule]
class ExampleDefaultPrimChecker(BaseRuleChecker):
    """Require the stage to define a valid default prim."""

    def CheckStage(self, stage: Usd.Stage) -> None:
        if not stage.GetDefaultPrim():
            self._AddFailedCheck("Stage must define a valid default prim.")


# [/snippet:custom-rule]


# [snippet:plugin-entry-point]
class Plugin:
    def on_startup(self) -> None:
        register_rule("Example")(ExampleDefaultPrimChecker)

    def on_shutdown(self) -> None:
        unregister_rule(ExampleDefaultPrimChecker)


# [/snippet:plugin-entry-point]
