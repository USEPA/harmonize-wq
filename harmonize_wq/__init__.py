from importlib.metadata import PackageNotFoundError, version

from harmonize_wq import harmonize as harmonize

try:
    __version__ = version("harmonize_wq")
except PackageNotFoundError:
    __version__ = "version-unknown"
