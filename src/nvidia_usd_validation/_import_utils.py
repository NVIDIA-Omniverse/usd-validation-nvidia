# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import enum
import functools
from functools import cache
from types import FunctionType, MappingProxyType

__all__ = ["default_implementation", "default_implementation_method"]


class ImplementationFlavors(enum.Enum):
    """
    Supported implementation flavors.
    """

    DEFAULT = "default"
    """Default implementation runs only with Python."""

    NUMPY = "numpy"
    """Numpy implementation, requires numpy library."""


@cache
def is_numpy_installed() -> bool:
    """
    Returns true if numpy is installed.
    """
    try:
        import numpy  # noqa: F401

        return True
    except ImportError:
        return False


def default_implementation(function: FunctionType):
    """
    A single dispatch for multiple distributions. Example:

    .. code-block:: python

        @default_implementation
        def compute_value(...):
            ...

        @compute_value.numpy
        def _(...):
            import numpy as np
            ...

        # if numpy is installed will get the numpy implementation.
        result = compute_value(...)
    """
    registry: dict[ImplementationFlavors, FunctionType] = {ImplementationFlavors.DEFAULT: function}

    def dispatch(impl: ImplementationFlavors) -> FunctionType:
        try:
            return registry[impl]
        except KeyError:
            return registry[ImplementationFlavors.DEFAULT]

    def numpy(func: FunctionType) -> FunctionType:
        registry[ImplementationFlavors.NUMPY] = func
        return func

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if wrapper.is_numpy_installed():
            return dispatch(ImplementationFlavors.NUMPY)(*args, **kwargs)
        else:
            return dispatch(ImplementationFlavors.DEFAULT)(*args, **kwargs)

    wrapper.numpy = numpy
    wrapper.is_numpy_installed = is_numpy_installed
    wrapper.registry = MappingProxyType(registry)
    return wrapper


class default_implementation_method:  # noqa: N801
    """Single-dispatch generic method descriptor.

    Supports wrapping existing descriptors and handles non-descriptor
    callables as instance methods.

    .. code-block:: python

        class MyClass:
            @default_implementation
            @staticmethod
            def compute_value(...):
                ...

            @compute_value.numpy
            @staticmethod
            def _(...):
                import numpy as np
                ...

        # if numpy is installed will get the numpy implementation.
        result = MyClass.compute_value(...)
    """

    def __init__(self, method):
        self.method = method
        if isinstance(method, staticmethod | classmethod):
            self.wrapper = default_implementation(method.__func__)
        else:
            self.wrapper = default_implementation(method)

    def numpy(self, method):
        if isinstance(method, staticmethod | classmethod):
            return self.wrapper.numpy(method.__func__)
        else:
            return self.wrapper.numpy(method)

    def __get__(self, obj, cls):
        if isinstance(self.method, staticmethod):
            wrapper = self.wrapper
        elif isinstance(self.method, classmethod):
            wrapper = functools.partial(self.wrapper, cls)
        else:
            wrapper = functools.partial(self.wrapper, obj)
        wrapper.__isabstractmethod__ = self.__isabstractmethod__
        return wrapper

    @property
    def __isabstractmethod__(self) -> bool:
        return getattr(self.method, "__isabstractmethod__", False)
