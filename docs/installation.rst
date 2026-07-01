Installation
############

``usd-validation-nvidia`` is a pure-Python package. It requires Python 3.10 - 3.12 and
OpenUSD 22.11 or later.

From PyPI
=========

.. code-block:: bash

    pip install usd-validation-nvidia

Optional dependencies
=====================

The core package depends only on OpenUSD. Two optional extras are available:

.. code-block:: bash

    # Bundle usd-core (when OpenUSD is not already provided by your environment)
    pip install usd-validation-nvidia[usd]

    # Add NumPy, used to accelerate some geometry checks
    pip install usd-validation-nvidia[numpy]

    # Both
    pip install usd-validation-nvidia[usd,numpy]

Use the ``[usd]`` extra when ``usd-core`` (or a full USD build) is not already on your
``PYTHONPATH``; skip it inside DCCs or runtimes that already provide USD.

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
the requirement specs in ``specs/`` by ``usd-profiles-nvidia``. To build a wheel from a
checkout, generate the capabilities package first, then build:

.. code-block:: bash

    uv run \
      --no-project \
      --with usd-profiles-nvidia \
      python -m usd_profiles_nvidia.codegen \
        --docs-root specs \
        --destination-dir src \
        --package-name usd_validation_nvidia.capabilities \
        --reverse-domain com.nvidia.usd

    uv build -o dist

The repository tooling wraps these steps; see ``CONTRIBUTING.md`` and ``AGENTS.md`` for the
full local development setup.
