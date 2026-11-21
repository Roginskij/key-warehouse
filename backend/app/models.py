"""Import every model so SQLAlchemy metadata (and Alembic) sees all tables."""

from app.modules.admin.models import StaffInvitation  # noqa: F401, E402
from app.modules.auth.models import ActionToken, RefreshToken  # noqa: F401
from app.modules.catalog.models import (  # noqa: F401  # noqa: F401, E402
    AttributeDef,
    AttributeOption,
    Brand,
    CatalogAudit,
    CatalogImage,
    CatalogImport,
    CatalogItem,
    CatalogProposal,
    DuplicateDismissal,
    ItemCode,
    ItemLockFit,
    ItemSubstitute,
    ItemVehicleFit,
    LockMake,
    LockModel,
    ProposalVote,
    VehicleMake,
    VehicleModel,
)
from app.modules.inventory.models import (  # noqa: F401
    CurrencyRate,
    InventoryAudit,
    InventoryItem,
    StockLevel,
    StockMovement,
    StorageLocation,
)
from app.modules.reference.models import Country, Currency, TradeZone  # noqa: F401
from app.modules.shop.models import WaitlistEntry  # noqa: F401, E402
from app.modules.users.models import AdminPermission, User  # noqa: F401
from app.modules.workshops.models import (  # noqa: F401
    ContactClick,  # noqa: F401, E402
    Invitation,
    Membership,
    Workshop,
)
