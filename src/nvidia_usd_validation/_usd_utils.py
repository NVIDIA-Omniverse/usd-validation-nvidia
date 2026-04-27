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
        if type_indicator.HasSdfType():
            return type_indicator.GetSdfType()
        elif hasattr(type_indicator, "GetSdrType"):
            return Sdf.ValueTypeNames.Find(type_indicator.GetSdrType())
        elif hasattr(type_indicator, "GetNdrType"):  # TODO: Remove after USD 25.08
            return Sdf.ValueTypeNames.Find(type_indicator.GetNdrType())
        else:
            return Sdf.ValueTypeNames.Token

    return Sdf.ValueTypeNames.Find(type_indicator[1]) or type_indicator[0]
