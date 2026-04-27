"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/agency_contact.py."""
import warnings

warnings.warn(
    "services.project_agency_contact_service is deprecated; "
    "import from services.contract.agency_contact (or services.contract)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.agency_contact import *  # noqa: F401,F403,E402
from .contract.agency_contact import ProjectAgencyContactService  # noqa: F401,E402
