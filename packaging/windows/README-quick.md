# Echoes Quick Start

1. Put today's `items.csv` in this folder.
2. Double-click `import.cmd`.
3. Double-click `start.cmd`.

`items.csv` must contain exactly 60 valid items. A successful import deletes the old items, cards, and review records, then keeps only the new 60 items.

Each item needs 3 passes. `Easy` adds one pass, `Hard` subtracts one pass, and `Again` resets it to 0. At `3/3`, the item stops appearing. Missed items return after a very short gap; easier items wait longer as progress rises.

Useful files:

- `start.cmd`: start the app.
- `import.cmd`: import today's `items.csv`.
- `doctor.cmd`: show environment and database information.
- `data\`: local database folder.

Keys:

- `Space`: reveal answer.
- `1` / `2` / `3`: rate Again / Hard / Easy.
- `Esc`: switch to or from the cover log.
- `q`: quit.
