# MMA Coach Tracker

A small, fast desktop app for an MMA coach to keep track of:

- **Member subscriptions**: monthly or custom plans, with expiry dates and renewals
- **Equipment sales**: gloves, shin guards, rash guards, and so on, with stock
- **Debts**: what each player still owes, and every payment they make

It is built for **old hardware**: a 32-bit PC running Windows 7. It opens in
about a second and uses about 25 MB of RAM. The interface works in **English
and Arabic** (right-to-left), and you can switch between them in Settings.

## Features

| Tab | What it does |
|---|---|
| Dashboard | Active and unsubscribed member counts, total debt, income today and this month, members expired or ending within 7 days, income by month. Click a card to jump to that list |
| Members | Search by name or phone, filter by All / Active / Ending soon / Owes money. Add, archive or delete members. Double-click a member to open their account: new subscription, record payment, add a manual debt, sell equipment, full account history. Right-click for quick actions |
| Equipment | Products with price and stock. Sell to a walk-in customer for cash, or to a member on credit. Undo a sale |
| Debts | Everyone who owes money, sorted by amount. Record a payment in one click |
| Settings | Language, text size, currency, subscription plans, backups, Excel export |

**Keyboard shortcuts:** `F5` refresh, `Ctrl+F` search members, `Ctrl+N` new member,
`Delete` delete the selected member, `Enter` open the selected row, `Esc` close a window.

### Archive or delete?

- **Archive** hides a player who stopped coming but keeps their history and
  their payments in the income reports. Restore them at any time.
- **Delete** permanently removes the player with all their subscriptions,
  payments and purchases. Their payments also disappear from income reports.
  Use it for mistakes or duplicates.

### Excel export

**Dashboard → Export to Excel** (or Settings) saves one `.xlsx` workbook.
It has a sheet each for members, debts, subscriptions, payments, charges,
sales, products and monthly income. Headers use the current language, and
Arabic exports open right-to-left. It opens in Excel 2007 or newer and in
LibreOffice, and needs nothing extra installed.

### How money is tracked

Each member has one account:

- **Charges** are amounts they owe: subscriptions, equipment bought, manual debts.
- **Payments** are amounts they paid.
- **Balance** = charges − payments. A positive balance means they owe the coach.

When you add a subscription or a sale, enter what the member **paid now**.
Whatever is left over becomes debt automatically. Walk-in sales are always cash.

Renewing while a subscription is still running starts the new one the day
after the current one ends, so the member loses no days.

## Installing on the coach's PC (Windows 7, 32-bit)

### Option A: the ready-made app (recommended)

1. Download `MMACoachTracker-win32` from the latest successful
   [CI run](../../actions/workflows/ci.yml) (or build it yourself, see below).
2. Unzip it to a folder such as `C:\MMACoachTracker`.
3. Double-click `MMACoachTracker.exe`. You can make a desktop shortcut to it.

If Windows 7 says a DLL is missing, install **Windows 7 SP1** and update
**KB2999226** (Universal C Runtime), or the
[Visual C++ 2015-2022 x86 redistributable](https://aka.ms/vs/17/release/vc_redist.x86.exe).

### Option B: run from source

1. Install [Python 3.8.10, Windows x86](https://www.python.org/downloads/release/python-3810/)
   (the last Python installer for Windows 7). Tick "Add Python to PATH".
2. Copy this repository to the PC.
3. Double-click `run.bat`.

## Data and backups

- Everything is stored in one file: `data\tracker.db`, next to the app.
- Each day, the first time the app opens, it saves a copy to `data\backups\`
  and keeps the last 30.
- **Settings → Back up to file...** saves a copy anywhere, such as a USB stick.
  Do this regularly. Old PCs fail.
- To restore a backup, close the app and copy the backup over `data\tracker.db`.

## Development

No third-party packages are needed to run the app. Everything uses the
Python standard library (Tkinter + SQLite).

```bat
:: run
python -m mma_tracker

:: tests
python -m unittest discover -s tests -t .

:: build dist\MMACoachTracker\ (needs 32-bit Python 3.8)
build.bat
```

Keep the code compatible with **Python 3.8**:

- no `match`, no `list[int]`-style hints, no `str.removeprefix`
- no SQLite features newer than 3.31, such as `RETURNING`

CI runs the tests and builds the exe on 32-bit Python 3.8 for every push.

### Layout

```
mma_tracker/
  db.py         schema and migrations
  store.py      all business logic (tested)
  backup.py     daily and manual backups
  xlsx.py       tiny stdlib-only .xlsx writer
  export.py     what goes into the Excel export
  i18n.py       English / Arabic strings
  ui/           Tkinter screens
tests/          unittest suite
```
