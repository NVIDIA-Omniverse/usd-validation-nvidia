# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from collections import OrderedDict, namedtuple

__all__ = ["DedupeInfo", "DedupeMetaclass"]

DedupeInfo = namedtuple("DedupeInfo", "hits misses maxsize currsize")


class DedupeMetaclass(type):
    """Metaclass that reuses recently-created equivalent hashable value instances.

    Classes using this metaclass should be immutable and have side-effect-free
    construction, because a temporary instance is created before cache lookup.
    """

    MAX_DEDUPE_ENTRIES: int = 128

    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        cls._dedupe_instances = OrderedDict()
        cls._dedupe_hits = 0
        cls._dedupe_misses = 0

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        try:
            deduped_instance = cls._dedupe_instances[instance]
            cls._dedupe_instances.move_to_end(instance)
            cls._dedupe_hits += 1
            return deduped_instance
        except TypeError:
            return instance
        except KeyError:
            pass
        cls._dedupe_instances[instance] = instance
        cls._dedupe_misses += 1
        if len(cls._dedupe_instances) > cls.MAX_DEDUPE_ENTRIES:
            cls._dedupe_instances.popitem(last=False)
        return instance

    def dedupe_info(cls) -> DedupeInfo:
        """Returns cache statistics for this deduplicated class."""
        return DedupeInfo(
            hits=cls._dedupe_hits,
            misses=cls._dedupe_misses,
            maxsize=cls.MAX_DEDUPE_ENTRIES,
            currsize=len(cls._dedupe_instances),
        )

