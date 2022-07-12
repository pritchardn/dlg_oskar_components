__package__ = "dlg_oskar_components"
# The following imports are the binding to the DALiuGE system
from dlg import droputils, utils

# extend the following as required
from .apps import OSKARInterferometer

__all__ = ["OSKARInterferometer"]
