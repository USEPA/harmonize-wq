from harmonize_wq import harmonize

try:
  from importlib.metadata import version
except ImportError:
  from importlib_metadata import version

try:
    __version__ = version('harmonize_wq')
except PackageNotFoundError:
    __version__ = "version-unknown"
