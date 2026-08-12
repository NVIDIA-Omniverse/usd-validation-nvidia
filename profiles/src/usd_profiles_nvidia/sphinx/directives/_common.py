# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from functools import cache

from jinja2 import Environment, FileSystemLoader, select_autoescape


@cache
def get_directives_environment() -> Environment:
    """
    Return a cached Jinja2 Environment for directive templates.
    Not stored on app.env so Sphinx can pickle the build environment.
    """
    loader: FileSystemLoader = FileSystemLoader(os.path.dirname(__file__))
    return Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))
