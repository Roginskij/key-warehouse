# Notes for the frontend

Living document: everything the frontend needs to know about the backend.
Full, always-current API schema: `http://localhost:8000/docs` (Swagger) and
`/openapi.json` (can generate a typed TS client, e.g. `openapi-typescript`).

All endpoints are under `/api/v1`.

## Errors

Every error has the same shape:

```json
{"error": {"code": "auth.invalid_credentials", "message": "English fallback", "params": {}}}
```

Validation (422):

```json
{"error": {"code": "validation_error", "message": "Invalid request",
           "fields": [{"field": "password", "code": "string_too_short", "message": "..."}]}}
```

**Translate by `code`**, never show `message` to users. Known codes:

| code | when |
|---|---|
| `auth.unauthorized` | no token |
| `auth.invalid_token` | access token bad/expired → call `/auth/refresh` |
| `auth.invalid_credentials` | wrong e-mail or password |
| `auth.email_not_verified` | login before confirming e-mail → offer "resend" |
| `auth.account_disabled` | blocked by admin |
| `auth.email_taken` | register with existing e-mail |
| `auth.terms_not_accepted` | checkbox not ticked |
| `auth.invalid_or_expired_link` | verify / reset link used or expired |
| `auth.invalid_refresh_token` | refresh failed → go to login screen |
| `auth.wrong_password` | change password / delete account |
| `reference.unknown_country`, `reference.unknown_currency` | |
| `workshops.not_found` | also returned when user is not a member |
| `workshops.owner_required`, `workshops.last_owner`, `workshops.member_not_found` | |
| `invitations.invalid_or_expired`, `invitations.already_member`, `invitations.login_required`, `invitations.wrong_account`, `invitations.account_details_required` | |
| `users.transfer_ownership_first` (`params.workshop_ids`), `users.superadmin_cannot_delete` | |
| `admin.permission_required`, `admin.superadmin_required`, `admin.user_not_found`, `admin.cannot_block_superadmin` | |
| `validation_error` | per-field errors in `fields` |

## Auth flow

- Access token: JWT, lives 15 min, send as `Authorization: Bearer <token>`.
- Refresh token: opaque string, lives 30 days, **rotated on every refresh** —
  always store the new one. Reusing an old refresh token kills the whole session.
  Refresh exactly once on 401 `auth.invalid_token` (guard against parallel refreshes).
- Storage: tokens are returned in JSON (works for PWA / mobile). If we serve the
  frontend from the same domain later, we can switch refresh to an httpOnly cookie.

Screens / routes the e-mails link to (`FRONTEND_URL` + path):

| path | what to do |
|---|---|
| `/verify-email?token=…` | `POST /auth/verify-email {token}` → returns tokens, user is logged in |
| `/reset-password?token=…` | form with new password → `POST /auth/reset-password {token, new_password}` |
| `/invite?token=…` | `POST /invitations/preview {token}` → if `account_exists` ask to log in then `POST /invitations/accept {token}` with auth; else form name+password+terms → accept returns tokens |

Registration form fields: email, password (8–128), full_name, locale, country_code,
workshop_name, accept_terms. After success show "check your e-mail".
`POST /auth/resend-verification` and `/auth/forgot-password` always return 204.

## Languages, countries, currency

- UI languages: `GET /reference/languages` (uk, en, pl, de, fr, es, it). User's
  choice is `user.locale` (`PATCH /users/me`); default from browser language.
- Country names come in English — display with `Intl.DisplayNames([locale], {type: 'region'})`.
- Language and country are independent settings (plan decision).
- Workshop has `base_currency` (default from country, owner can change).
  Each price has its own currency; the owner sets workshop rates (see Inventory).
- Format numbers/dates with `Intl.NumberFormat` / `Intl.DateTimeFormat` by locale.

## Workshops and roles

- `GET /users/me` returns the user and all their workshops with `role`.
  One user can belong to several workshops → workshop switcher.
- Roles: `owner`, `master`.
- Admin panel: show only if `user.is_superadmin` or `user.permissions` not empty;
  show sections by permission (`users.view`, `users.manage`, `catalog.*`).

## Planned (not built yet)

- Non-fiscal receipt for a sale (later fiscal), offline mode, QR labels.
- Sign-in with Google/Apple/phone — DB is ready (password is optional on a user).

## Catalog (module 2)

Workshop side (any signed-in user):

| endpoint | what |
|---|---|
| `GET /catalog/items?q=&kind=` | search by ANY code of any brand (`hu-66` = `HU66` = `hu 66`) or by name; exact code matches first |
| `GET /catalog/items/{id}` | item card + `can_be_replaced_by` (keys usable instead of it) + `can_replace`. Ids of merged items redirect — compare the returned `id` |
| `GET /catalog/brands` | brand list for pickers |
| `POST /catalog/proposals` | `{workshop_id, proposal: {type, ...}}` — see types below |
| `GET /catalog/proposals?workshop_id=` | what this workshop proposed and the status |

Proposal types (`proposal.type`):
- `new_item` — `{kind, name, codes:[{brand, code}], frequency_mhz?, chip_type?, fcc_id?}`
- `equivalent` — `{a:{brand,code}, b:{brand,code}, kind?, name?}` "these two numbers are the same key"
- `substitute` — `{item:{brand,code}, substitute:{brand,code}, note?}` "substitute can be used instead of item" (one way)
- `add_code` — `{item_id, code:{brand,code}}`

Brand in proposals is free text (unknown brands are created on acceptance).

Item kinds: `blank, car_key, remote, transponder, cylinder, key_shell, battery, machine, programmer, other`.

Admin side (`/admin/catalog/...`, by permissions): brands; items (list with
`status`, `import_id` filters; create; edit; add/remove code; `merge`; `split`);
substitutes; proposals queue (sorted by votes, `accept` with optional `kind`/`name`
fix, `reject` with note); `import` (multipart: `file`, `source_label`,
`default_kind?`, `dry_run` — show the dry-run report as a preview, then send
again with `dry_run=false`); `imports` list and `DELETE imports/{id}` (revert);
`audit` history. Import template: `docs/catalog-import-template.csv`.

Catalog error codes: `catalog.item_not_found`, `catalog.code_taken` (params: brand, code,
item_id — offer "open that item"), `catalog.unknown_brand`, `catalog.empty_code`,
`catalog.code_not_found`, `catalog.brand_exists`, `catalog.brand_not_found`,
`catalog.item_not_active`, `catalog.bad_merge`, `catalog.bad_split`, `catalog.bad_status`,
`catalog.bad_substitute`, `catalog.substitute_not_found`, `catalog.bad_proposal`,
`catalog.proposal_not_found`, `catalog.proposal_decided`, `catalog.proposal_conflict`
(params.item_ids — merge them first), `catalog.proposal_unresolved`, `catalog.kind_required`,
`catalog.import_bad_format`, `catalog.import_empty`, `catalog.import_too_big`,
`catalog.import_no_brands`, `catalog.import_not_found`, `catalog.import_reverted`.

## Inventory (module 3) — `/workshops/{wid}/inventory/...`

Main screens and their endpoints:

| screen | endpoints |
|---|---|
| Stock list | `GET items?q=&kind=&location_id=&low_stock=&stale=&linked=&archived=&sort=name\|quantity\|updated` — `q` finds by own number, ANY catalog number of the linked item, name, brand, car |
| Item card | `GET items/{id}`, `PATCH items/{id}`, `DELETE items/{id}` (archive, needs qty 0), `POST items/{id}/restore`, photo `PUT/GET items/{id}/photo` (jpeg/png/webp ≤ 5 MB; GET needs the auth header → fetch as blob) |
| One-tap +/− | `POST items/{id}/movements {"type":"adjust","quantity":1}` / `-1` → returns `{movement, item}` |
| Sale / receipt / write-off / transfer | same endpoint, `type`: `sale` (price defaults to item sale price; `client_name`, `client_phone` optional), `receipt`, `writeoff`, `transfer` (`location_id` → `to_location_id`) |
| History | `GET movements?item_id=&type=&user_id=&date_from=&date_to=` (journal) and `GET audit?item_id=` (edits of prices/names) |
| Storage locations | `GET/POST locations`, `PATCH/DELETE locations/{id}`; flat list with `parent_id` → build the tree; `is_default` location: show a translated "Main" label |
| Time to order | `GET reorder` |
| Currency rates | `GET rates`, `PUT rates/{USD} {"rate": "41.5"}` (owner) — `sale_price_in_base` on items uses them |
| Excel import | (owner) `POST import/analyze` (file) → show `headers`, `sample`, preselect `suggested_mapping`; user fixes mapping → `POST import` (file, `mapping` JSON string, `default_kind`, `currency`, `location_id`, `dry_run=true`) → show report → same with `dry_run=false` |
| Excel export | `GET export` → .xlsx file |
| Catalog link | created items return `catalog`: `linked` / `proposed` / `none`; `GET items/{id}/catalog-suggestions`, `PUT items/{id}/catalog-link {catalog_item_id \| null}` |

Rules to reflect in UI:
- Out-of-stock errors: `inventory.insufficient_stock` (`params.available`),
  `inventory.location_required` (stock split — ask which location).
- Import report rows are the row numbers of the user's file.

Inventory error codes: `inventory.item_not_found`, `inventory.location_not_found`,
`inventory.duplicate` (params.item_id — offer to open it), `inventory.insufficient_stock`,
`inventory.location_required`, `inventory.bad_quantity`, `inventory.bad_transfer`,
`inventory.bad_movement_type`, `inventory.item_archived`, `inventory.item_has_stock`,
`inventory.location_is_default`,
`inventory.location_has_children`, `inventory.location_not_empty`, `inventory.location_cycle`,
`inventory.rate_for_base`, `inventory.photo_too_big`, `inventory.photo_bad_format`,
`inventory.photo_not_found`, `inventory.import_too_big`, `inventory.import_bad_mapping`,
`reference.unknown_currency`.

## Rate limits (brute-force protection)

Any endpoint can answer **429** with `Retry-After` header and
`{"error": {"code": "rate_limited" | "auth.too_many_attempts", "params": {"retry_after": 60}}}`.
Show "too many attempts, try again in N min". `auth.too_many_attempts` = this account
is locked for up to 15 min after 5 wrong passwords (login, change password, delete account).
`forgot-password` / `resend-verification` keep answering 204 even when the mail is
not sent because of the per-address cap (3 per hour) — wording should say
"if the address is registered, a mail is on its way".
