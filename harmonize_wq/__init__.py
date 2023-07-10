from harmonize_wq import harmonize

try:
  from importlib.metadata import version, PackageNotFoundError
except ImportError:
  from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version('harmonize_wq')
except PackageNotFoundError:
    __version__ = "version-unknown"
