from harmonize_wq import harmonize
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version('harmonize_wq')
except PackageNotFoundError:
    __version__ = "version-unknown"
