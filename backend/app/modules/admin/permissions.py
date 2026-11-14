from enum import StrEnum


class AdminPerm(StrEnum):
    """Rights in the admin panel. The superadmin has all of them implicitly
    and is the only one who can grant them."""

    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    CATALOG_VIEW = "catalog.view"
    CATALOG_EDIT = "catalog.edit"
    CATALOG_MODERATE = "catalog.moderate"  # approve / merge / reject proposed items
    CATALOG_IMPORT = "catalog.import"
