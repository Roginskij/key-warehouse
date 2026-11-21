# KeyVerhaus — design rules

Mockups: https://claude.ai/artifact/7z6FRWGihqGd4BdbHV8EU5 (6 phone screens, Ukrainian copy).

## Principles ("a grandmother can use it")

- Phone first, one hand. Touch targets ≥ 44 px (main button 52).
- Web version: left sidebar menu, table with the quantity in the row, detail panel on the right
  (stacks under the table on narrow screens).
- Body text 16–17 px, titles 26–30 px bold. Never grey text lighter than #4B5563.
- One main action per screen: big yellow button (52 px) or floating "Додати".
- Bottom tab bar, 4 tabs with icon AND label: Склад, Замовити (badge = items below
  minimum), Місця, Ще. No hidden menus, no gestures needed.
- Plain words instead of terms: Продав / Привіз / Зламався (not sale / receipt / write-off).
- Undo instead of "are you sure?": after a sale / receipt / write-off a dark bar
  "Продано 1 · Скасувати" for 5 s.
- Empty states explain what to do next with one button.
- Import is a 3-step wizard: file → check columns (pre-filled) → preview → done.
- Colour is never the only signal: low stock = amber label WITH text "Мало · мінімум 5".

## Screen sizes (breakpoints)

| width | layout |
|---|---|
| < 768 (phones) | graphite header per page, bottom tab bar, cards, floating "Додати" |
| 768–1023 (tablets, phone landscape) | graphite sidebar (224 px, scrolls if short), light page header, cards; filters wrap |
| ≥ 1024 (laptops, desktops) | sidebar 256 px; stock becomes a table; item card and settings in two columns |
| ≥ 1280 | content up to 1152 px wide, centered |

No page may scroll sideways at any width (checked at 375, 768, 812×375, 900, 1280, 1440).

## Chosen theme: graphite + yellow (2026-11-13)

Dark graphite header and bottom bar (sidebar on web), warm light-grey screen,
white cards, soft yellow for main actions. Blue / gray-yellow / teal kept only as
comparison artboards in the mockups.

Rules:
- Yellow is a FILL with dark text, or yellow text/icons on the dark graphite bars.
  Never yellow text on white or light grey (unreadable).
- On light areas links and secondary actions are dark ink, not yellow.
- Low stock is orange (#FBE7DA / #8A3B12) so it does not merge with yellow buttons.
- An even paler yellow (#F5DE8F) was tried and rejected; #F2D06B is the one.
- Avoid pure black + bright yellow (too close to tool brands' trade dress).

## Tokens (Tailwind theme in packages/ui)

| token | value | use |
|---|---|---|
| ground | #ECEBE8 | screen background |
| surface | #FFFFFF | cards, inputs |
| line | #DAD9D4 (cards) / #C9C8C2 (inputs, 2 px) | borders |
| ink | #2B2B2E | text, dark buttons ("Продав"), undo bar |
| muted | #5A5A61 | secondary text on light |
| graphite | #3A3A3F | header, bottom bar, web sidebar |
| graphite-2 | #4A4A50 | search field / inactive chips on graphite, bar borders |
| on-graphite | #FFFFFF / muted #DAD9D4 | text on graphite |
| primary | #F2D06B, text #2B2B2E | main buttons, +, active tab, active chip, badge |
| primary-soft | #F8EDC4, text #2B2B2E | code chips, info notes, icon boxes |
| warn | #FBE7DA / #8A3B12 | "Мало", "треба +N" |
| toast action | #F2D06B on #2B2B2E | "Скасувати" |
| radius | 12–14 px controls, 14–18 px cards | |
| font | Inter 400/500/600/700 (Cyrillic + Latin) | |
