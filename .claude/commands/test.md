Build the wheel and run the test suite locally.

1. Generate capabilities: run `./repo.sh usd_profiles_codegen` on Linux/macOS or `.\repo.bat usd_profiles_codegen` on Windows
2. Build the wheel: run `./repo.sh uv -- build -o dist` on Linux/macOS or `.\repo.bat uv -- build -o dist` on Windows
3. Clear stale cached wheels: run `./repo.sh uv -- cache clean nvidia-usd-validation` (or `.\repo.bat` on Windows)
4. Find the built wheel in `dist/` — it matches `nvidia_usd_validation-*.whl`. On Linux use `ls dist/nvidia_usd_validation-*.whl | tail -1`; on Windows use `Get-ChildItem dist\nvidia_usd_validation-*.whl | Select-Object -Last 1 -ExpandProperty Name`
5. Run the tests: `./repo.sh uv -- run --no-project --no-cache --with dist/<wheel-filename> --with usd-core==25.05 python -m unittest discover -s tests -v` (or `.\repo.bat` on Windows)

Report the results. If the build fails, stop and show the error. If tests fail, show which tests failed and why.
