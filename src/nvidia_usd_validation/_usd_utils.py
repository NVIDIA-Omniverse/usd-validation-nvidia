# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["get_sdf_type_for_shader_property"]

from pxr import Sdf, Sdr, Usd


def get_sdf_type_for_shader_property(sdr_property: Sdr.ShaderProperty) -> Sdf.ValueTypeName:
    """Get the Sdf type from an Sdr property, handling different USD versions."""

    # Note the ndr_type/type_indicator[1] below is holding a Tf.Token, so look up the corresponding Sdf.ValueTypeName
    type_indicator = sdr_property.GetTypeAsSdfType()

    if Usd.GetVersion() >= (0, 24, 11):
        return (
            type_indicator.GetSdfType()
            if type_indicator.HasSdfType()
            else Sdf.ValueTypeNames.Find(type_indicator.GetNdrType())
        )

    return Sdf.ValueTypeNames.Find(type_indicator[1]) or type_indicator[0]
