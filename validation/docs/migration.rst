Migrating from omniverse-asset-validator
########################################

``usd-validation-nvidia`` is the successor to the ``omniverse-asset-validator`` (OAV)
Python module. The engine, rule interface, and CLI are the same; only the package and
import names change, and compatibility shims keep most existing code working.

What changed
============

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - omniverse-asset-validator
      - usd-validation-nvidia
    * - ``omniverse-asset-validator`` (Kit extension / ``omni`` package)
      - ``usd-validation-nvidia`` - a standalone, pure-Python package
    * - ``import omni.asset_validator.core``
      - ``import usd_validation_nvidia``
    * - ``from omni.asset_validator.core import ValidationEngine, IssueFixer``
      - ``from usd_validation_nvidia import ValidationEngine, IssueFixer``
    * - run inside Kit / ``python -m omni.asset_validator``
      - the ``nvidia_usd_validate`` CLI (``python -m omni.asset_validator`` still works)

The rule API is the same: rules still subclass ``BaseRuleChecker``, override the same
``Check*`` callbacks, report with ``_AddFailedCheck`` / ``_AddWarning`` / ..., and register
with ``register_rule``. See :doc:`authoring`.

Compatibility shims
===================

The package ships an ``omni.asset_validator`` namespace that re-exports everything from
``usd_validation_nvidia``, so existing imports keep resolving:

- ``omni.asset_validator`` and ``omni.asset_validator.core`` re-export the public API.
- ``omni.asset_validator.tests`` re-exports the test helpers.
- ``python -m omni.asset_validator`` runs the new CLI.

These shims ease the transition. New code should import ``usd_validation_nvidia`` directly;
the ``omni.asset_validator`` aliases are kept for backward compatibility and may be
deprecated in a future release.

Updating your project
=====================

#. Replace ``omniverse-asset-validator`` with ``usd-validation-nvidia`` in your
   dependencies. Add the ``[usd]`` extra if your environment does not already provide
   ``usd-core`` (see :doc:`installation`).
#. Update imports from ``omni.asset_validator`` / ``omni.asset_validator.core`` to
   ``usd_validation_nvidia``.
#. Replace any ``omni.asset_validator`` command-line invocation with ``nvidia_usd_validate``
   (see :doc:`cli`).
#. Custom rules carry over unchanged: keep your ``BaseRuleChecker`` subclasses and
   ``register_rule`` decorators, and confirm they appear in a default ``ValidationEngine``.
