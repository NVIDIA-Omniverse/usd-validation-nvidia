Installation
############

``usd-validation-nvidia`` is a pure-Python package for validating OpenUSD assets.

From PyPI
=========

.. code-block:: bash

    pip install usd-validation-nvidia

Optional dependencies
=====================

The core package does not pin a USD provider. Optional extras are available:

.. code-block:: bash

    # Bundle usd-core (when OpenUSD is not already provided by your environment)
    pip install usd-validation-nvidia[usd]

    # Bundle usd-exchange (when USD Exchange is not already provided by your environment)
    pip install usd-validation-nvidia[usdex]

    # Add NumPy, used to accelerate some geometry checks
    pip install usd-validation-nvidia[numpy]

    # Both usd and NumPy
    pip install usd-validation-nvidia[usd,numpy]

    # Both usdex and NumPy
    pip install usd-validation-nvidia[usdex,numpy]

Do not install both ``[usd]`` and ``[usdex]`` in the same environment. Skip both
provider extras inside DCCs or runtimes that already provide USD.

For Python 3.10 - 3.13, use either ``[usd]`` or ``[usdex]``. For Python 3.14,
use ``[usd]`` because usd-core 26.8 supports Python 3.14.

Verifying the installation
==========================

.. code-block:: bash

    nvidia_usd_validate --version
    nvidia_usd_validate --help

.. code-block:: python

    from usd_validation_nvidia import ValidationEngine

    engine = ValidationEngine()
    results = engine.validate("path/to/asset.usda")
    for issue in results.issues():
        print(f"{issue.severity}: {issue.message}")

See :doc:`cli` for the command-line interface and :doc:`api` for the Python API.

Building from source
====================

The package ships a generated ``usd_validation_nvidia.capabilities`` module, produced from
the requirement specs in ``specs/`` by ``usd-profiles-nvidia`` (developed in-repo under
``profiles/``). To build a wheel from a checkout, generate the capabilities package first,
then build:

.. code-block:: bash

    uv run \
      --no-project \
      --with ./profiles \
      python -m usd_profiles_nvidia.codegen \
        --docs-root specs \
        --destination-dir validation/src \
        --package-name usd_validation_nvidia.capabilities \
        --reverse-domain com.nvidia.usd

    uv build --all-packages -o dist

The repository tooling wraps these steps; see ``CONTRIBUTING.md`` and ``AGENTS.md`` for the
full local development setup.
