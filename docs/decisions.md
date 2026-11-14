# Decisions log

Business plan: `~/Desktop/mvp-plan.md` (stage 1 = MVP).

## 2026-11-13 — module 1 (users, auth)

- Sign-in: e-mail + password, e-mail confirmation required before login.
  `users.password_hash` is nullable so Google / Apple / phone can be added later
  via a separate `user_identities` table.
- E-mail provider: **Brevo** (EU company, servers in the EU, plain SMTP, free tier).
  Behind an SMTP interface, so it can be swapped by changing `.env` only.
- Registration asks only for country (business type is obvious — keys;
  team size not needed).
- Roles in a workshop: `owner`, `master`. A user can own several workshops and
  work in several workshops.
- Platform admin: one `superadmin` (created by CLI) grants granular permissions
  (`users.*`, `catalog.*`).
- Data in EU servers (plan). GDPR: terms version + acceptance time stored;
  `DELETE /users/me` erases the account.

## Agreed for next modules

- **Catalog**: grown from workshops' real stock, never copied from manufacturer
  catalogs (EU database right). Internal brand-agnostic item id with many
  manufacturer codes (normalized: HU-66 = HU66). Every code and every
  cross-reference stores its **source** and **status** (proposed → confirmed,
  how many workshops confirmed). Two link types: full equivalent (both ways)
  and one-way "can replace". Admin queue: accept / merge / reject; merge and
  split items; CSV/Excel import for supplier exports.
- Catalog item kinds: blank, car key, remote/fob, transponder chip, cylinder,
  key shell, battery, key cutting machine, programmer, other.
  Car keys: frequency, chip type, FCC ID.
- Vehicle → key mapping: tables only, search in stage 2.
- **Inventory**: items may exist without a catalog link (linked later).
  Prices carry their own currency (USD / EUR / UAH); exchange rates with an
  option to peg UAH to USD/EUR. Storage locations as an extensible tree
  (workshop → rack → shelf, car → box). Every stock movement has a date.
- **Receipt** to a client: later, but the stock movement model must already
  have a "sale" type with price and optional client so a receipt can be added.

## 2026-11-13 — module 2 (catalog) built

- Search normalizes codes: spaces, dashes, dots, slashes ignored, case ignored;
  suffix letters kept (HU66P ≠ HU66).
- (brand, code) is unique in the whole catalog → a number always means one item.
- Manual admin entry requires an existing brand (protects from typos);
  import and accepted proposals create unknown brands automatically.
- Seed brands: Silca, JMA, Keyline, Errebi, Ilco, OEM.
- Merged items stay as pointers (`merged_into_id`), old ids keep working.
  TODO inventory module: repoint workshop stock on merge (marked in `merge_items`).
- Same proposal from several workshops = one proposal, one vote per workshop;
  queue sorted by votes. No auto-accept yet — a moderator decides.
- Import: dry run = real run rolled back, so the preview is exact. Revert removes
  the import's codes/links and archives items left without codes.

## 2026-11-13 — module 3 (workshop inventory) built

- Quantities are whole pieces. Stock can't go below zero.
- Every quantity change is a movement (initial / receipt / sale / writeoff / adjust /
  transfer) with date, author, balance after; movements are never edited.
  One-tap +/− = `adjust` ±1. A sale stores price and optional client → receipt later.
- Selling without a location takes from the fullest location; if stock is split and
  no single location has enough, the user must choose.
- A default "Main" location is created per workshop automatically.
- Locations: any depth tree; filtering by a location includes everything inside it.
- Prices: own currency per price; the owner sets manual workshop rates
  ("1 USD = 41.5 UAH"); value and `sale_price_in_base` use them. Auto rates (NBU/ECB) later.
- Masters without price access: purchase prices removed from every response,
  export, history; value screen forbidden; they can still move stock.
- Same brand+number twice in one workshop is refused (duplicate).
- New items auto-link to the catalog by exact number; unknown brand+number goes to
  the catalog moderation queue automatically (one vote per workshop).
- Import (owner only): column mapping suggested from headers in uk/ru/en/pl/de/fr/es/it;
  kind recognized from a kind column or the name ("Брелок…" → remote);
  decimal comma, "12 грн", "5 шт" understood; text in a number cell is a row error;
  duplicates skipped; location column creates locations. Dry run = rolled-back real run.
- Archive instead of delete; quantity must be 0 first.
- Photos stored in a local folder (`MEDIA_DIR`) for now — object storage before production.

## 2026-11-13 — brute-force protection

- In-memory sliding windows (`app/core/ratelimit.py`). One server process is fine;
  with several processes/servers move the store to Redis (same interface).
- Global: 300 requests/min per IP. Login: 20/min and 100/hour per IP.
  Register: 10/hour per IP. Forgot password / resend verification: 5 per 15 min per IP
  and max 3 mails per hour per address (silently). Links from mails (verify, reset,
  invitations): 20 per 15 min per IP. Refresh: 60/min. Sending invitations: 30/hour.
- Account lockout: 5 wrong passwords for an e-mail in 15 min → locked 15 min (also
  counts wrong passwords in change-password / delete-account). Trade-off: someone can
  temporarily lock a known e-mail; acceptable vs. password guessing.
- Behind nginx/Caddy set `TRUST_PROXY_HEADERS=true` so the real client IP is used.

## 2026-11-13 — frontend architecture (agreed)

- Monorepo `frontend/`: `apps/web` (Vue 3 + Vite SPA, the product, `app.<domain>`),
  `apps/shop` (Nuxt on its own Node server, public SEO pages, `<domain>`),
  `packages/ui` (shared Vue components + Tailwind theme), `packages/api`
  (TS client generated from OpenAPI). Styles: Tailwind 4 (SCSS only if needed).
- Shop audience: car owners AND workshops that sell keys publicly.
- Key page before marketplace: description, which cars / doors it fits,
  "find a workshop" button. One page per catalog item per language
  (`/uk/keys/<slug>`), other codes and merged items 301 to it; hreflang,
  canonical, JSON-LD, OG previews for messengers, sitemap from API.
- Pages render on the server with caching, refreshed when data changes (no rebuilds).
- No designer: UI must be simple enough for anyone ("a grandmother can use it").

## 2026-11-13 — shop details (agreed)

- Workshop public profile: address, city, map point, phone, Viber/Telegram, hours.
- Opt-in: "show me in search" + per-item "show availability". Default: nothing public.
- Verification (EDRPOU / tax no. in UA, VAT no. in EU): lay down the fields and status
  now (`verification_status`, `tax_id`, `verified_at`), do NOT require it yet.
- Public price: workshop chooses exact / "from N" / "ask"; default "ask for price".
- Contact: Call, Viber, Telegram, Route buttons; count clicks (proof for paid plan).
  Lead form later (personal data → GDPR).
- Door keys: lock/cylinder fits (lock brand, model, profile) like vehicle fits,
  same moderation flow.
- Publish a key page only with real content (description + fits). Only own or
  licensed photos; "not affiliated with Silca, JMA…" note.
- Photos: own photo standard (light box, fixed angles, ruler) for top items + photos
  from workshops via in-app guided camera (license in terms, moderator picks the
  best) + supplier photos only with written permission. Every image stores source
  and license so it can be removed by source. No copied or AI-generated key photos.
  Server pipeline: background removal (self-hosted rembg), auto-crop, AVIF/WebP
  sizes, 1:1 / 4:3 / 16:9 crops, ≥1200 px for Google.
- Analytics: admin metrics screen (registrations, stock moved ≥50 items, weekly
  active — by country/language) + cookieless EU analytics (Plausible or Umami).
- Hosting: start on Railway, EU West (Amsterdam). Everything in Docker so a move to
  Hetzner + Coolify stays easy. Photos in S3-compatible storage. Own nightly
  pg_dump to object storage regardless of the platform's backups. Sentry for errors.
- Git: last step (user's choice).

## Reminders for the owner

- [ ] **Legal pages before launch:** privacy policy, terms of use (incl. photo license
      from workshops), cookie notice if any cookies, imprint where required. Lawyer check.
- [ ] **Retention period for deleted accounts** must be written in the privacy policy
      (e.g. 30 or 90 days), and a person's explicit erasure request must be done within a
      month (GDPR) — admin panel → Users → Deleted → "Delete for good".
- [ ] Trademark check of the chosen product name (EUIPO TMview, Ukrainian register)
      before buying domains.
- [ ] Privacy policy must also cover the **public site**: waitlist e-mails (purpose: one
      launch notice; deletion on request), contact-button click counts (no personal data,
      only workshop + channel + key), and the workshop's own consent to be listed.
- [ ] The **app** still loads the Inter font from Google Fonts. German courts have fined
      sites for this (IP sent to Google). Before launch: self-host the font or use system
      fonts like the public site does.

## 2026-11-13 — product name

**KeyVerhaus.** Domains free on 2026-11-13: keyverhaus.com / .eu / .app / .com.ua / .ua;
also buy keywarehaus.com (typo redirect). Trademark check still to do (see Reminders).

## 2026-11-13 — admin panel (frontend)

- `/admin` in the same web app, own graphite sidebar; visible only to superadmin or users
  with admin rights; every screen checks the right (`catalog.*`, `users.*`).
- Screens: Overview (plan metrics: workshops, moved stock 50+, active 7 days, by country,
  language, week — backend `GET /admin/metrics`), Catalog (search, item editor: numbers,
  one-way substitutes, merge duplicate, split, archive, history), Proposals queue (most
  votes first, accept with kind/name fix, reject with reason), Import (preview → save,
  revert by source), Brands, History, Users (block, rights — superadmin only).
- When a number enters the catalog (accepted proposal, manual add, import), workshop stock
  with that number that is not linked yet gets linked automatically.
- UserOut now includes `is_active`.

## 2026-11-13 — stock value screen, "download my data"

- `/value` screen (sidebar, "Ще"): total at purchase prices in base currency, per purchase
  currency, warning for currencies without a rate (owner → set rate), count of items without
  purchase price. Hidden for masters who may not see purchase prices.
- GDPR access: `GET /users/me/export` → JSON file (profile, workshops, sessions, invitations
  sent, the person's stock changes incl. client names they entered, catalog proposals they
  supported). Workshop stock itself stays in the owner's Excel export. Max 10/hour.

## 2026-11-13 — settings and 7 languages

- Settings ("Ще"): change password (signs out everywhere), edit workshop (owner: name, country,
  main currency), create another workshop, workshop switcher (phones too), delete account with
  password confirmation and a clear warning.
- App fully translated to uk, en, pl, de, fr, es, it. pl/de/fr/es/it are machine translations —
  native speakers should review the main screens (plan). The admin panel stays in uk/en.
- Frontend test `src/i18n/locales.test.ts`: every language has every key and every message
  compiles (`pnpm test`).

## 2026-11-13 — "delete my account" = switch off, admin erases later (user's decision)

- `DELETE /users/me` no longer erases: sets `deleted_at`, `is_active = false`, ends all sessions,
  removes the person from shared workshops; their own (single-member) workshops stay intact.
  Login answers `auth.account_deleted`.
- Admin → Users → filter "Deleted": "Restore" (users.manage) or "Delete for good"
  (superadmin only, `DELETE /admin/users/{id}`, only for already-deleted accounts) — erases the
  account and workshops where it was the only member, with stock.
- GDPR: allowed only with a stated retention period in the privacy policy and timely erasure on
  request (see Reminders). Possible later: automatic erasure after the period.

## 2026-11-13 — no blank screens

- Account without any workshop (e.g. an admin created by CLI, or removed from its only
  workshop): every stock page shows "You are not in any workshop yet" with a create-workshop
  form, an invitation hint and (for admins) a link to the admin panel.
- Every list page has an empty state with what to do next, and a load error shows the reason
  with "Try again" (`LoadError` component) instead of an empty page.

## 2026-11-13 — QR stickers for places (plan stage 1, "if time")

- Each storage place gets a QR sticker with a normal link `/l/{workshop_id}/{location_id}`:
  the phone's own camera opens it, and the in-app scanner (Stock and Places pages, library
  `qr-scanner`) does the same. It switches to that workshop and shows the stock of that place
  (incl. places inside it). Sticker of a workshop you are not in → explanation.
- Print page "QR-наклейки" (Places): standard A4 label sheets 21 (63.5×38.1), 8 (99.1×67.7),
  65 (38.1×21.2); choose places; skip first N labels for half-used sheets; QR + place name +
  parent + workshop. Print at 100% scale, no margins. QR made in the browser (`qrcode`).
- Camera in the browser needs https (fine after deploy; on a phone via local network it won't).

## 2026-11-13 — public part (shop) built

- **Nothing is public by default.** A workshop appears only after the owner switches on
  "Show my workshop in search" (Search profile screen) — that switch is the consent.
  City and at least one contact are required then. A stock item shows "in stock" only
  when it is ticked "Show on the search site"; quantity and purchase price never leave
  the backend. Prices follow the workshop's choice: ask / "from N" / exact.
- **Verification fields only for now:** tax / VAT number + status (none, pending,
  verified, rejected). Nothing is checked yet; verified workshops get a badge later.
- **Thin pages are not published:** a key page exists only for an active item with a
  description or car/lock fits (Google penalises empty pages). Slugs never change;
  a merged duplicate answers with a 301 to the main page.
- **Fits to locks and doors** next to fits to cars (lock maker, model/series, profile).
- **Catalog photos:** only own photos or ones given with permission; every photo records
  its source (own / workshop / supplier + note) and the uploader ticks "I have the right
  to publish". Stored as WebP 400/800/1600 px, at least 600 px wide on upload.
- **Site (apps/shop, Nuxt 4, server-rendered):** /<lang>/, /<lang>/keys, /<lang>/keys/<slug>,
  /<lang>/workshops in 7 languages; "/" goes by the browser language (ru → uk). Each page has
  canonical, hreflang for all languages + x-default, Open Graph, JSON-LD (Product,
  BreadcrumbList), sitemap.xml with alternates, robots.txt. Search result pages are noindex.
  HTML cached 10 min in production (stale-while-revalidate). The footer says brand names
  and codes are for compatibility only, no affiliation.
- **No Google on the site:** system fonts, maps open in OpenStreetMap.
- **Contact clicks** (call / Viber / Telegram / route) are counted per workshop and shown
  to the owner for 30 days — proof the listing brings customers.
- **Waitlist:** e-mail, who (workshop / car owner / other), country, language, explicit
  consent tick. A repeated e-mail gets the same answer (no "already registered" leak).
  Admin → Waitlist shows counts by country and role.
- Local demo: `uv run python -m app.seed_demo --shop` lists the demo workshop on the site.
- **Deploy note:** photos are files in `MEDIA_DIR`. On Railway that folder needs a volume
  (or move to S3-compatible storage), otherwise photos vanish on every deploy.
