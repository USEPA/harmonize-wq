from pathlib import Path

import nox

RUN_DEPS = ["geopandas", "pint", "dataretrieval"]

FORMAT_DEPS = ["ruff >= 0.3.5"]
TESTS_DEPS = ["pytest", "coverage"]

ROOT_PATH = Path.cwd()
SRC_PATH = ROOT_PATH / "harmonize_wq"
TESTS_PATH = SRC_PATH / "tests"
DOCS_PATH = ROOT_PATH / "docs"

nox.options.reuse_venv = "yes"
nox.options.sessions = ["format"]


@nox.session
def format(session):
    """Apply coding style standards to code."""
    session.install(*FORMAT_DEPS)
    session.run("ruff", "format", SRC_PATH)
    session.run("ruff", "check", "--fix", SRC_PATH)


@nox.session
def tests(session):
    """Run tests and compute code coverage."""
    session.install(*RUN_DEPS)
    session.install(*TESTS_DEPS)
    session.run("coverage", "run", "-m", "pytest", *session.posargs, TESTS_PATH)
