default:
    just --list

test:
    uv run pytest -q

doctor:
    uv run go-ship-it doctor

build:
    uv build

package-acceptance:
    scripts/validate-packaged-install.py --wheel dist/go_ship_it-0.1.0-py3-none-any.whl

agent-cli-check:
    scripts/validate-agent-cli-integration.py

release-check:
    scripts/release-check.py
