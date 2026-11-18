# MMA Coach Tracker

A small, fast desktop app for an MMA coach to keep track of:

- **Member subscriptions**: monthly or custom plans, with expiry dates and renewals
- **Equipment sales**: gloves, shin guards, rash guards, and so on, with stock
- **Debts**: what each player still owes, and every payment they make
- **Attendance**: who trained today, how often each player comes, and who stopped coming

It is built for **old hardware**: a 32-bit PC running Windows 7. It opens in
about a second and uses about 25 MB of RAM. The interface works in **English
and Arabic** (right-to-left), and you can switch between them in Settings.

## Features

| Tab | What it does |
|---|---|
| Dashboard | Check-ins today, active and unsubscribed counts, total debt, income today and this month. Charts of check-ins over the last 30 days and income over 12 months. Lists of members expired or ending within 7 days, and subscribed members who haven't trained in 14+ days. Click a card to jump to that list |
| Attendance | Front-desk check-in: type part of a name or phone and press Enter. A coloured banner confirms it with this month's and this week's visit count, and warns in orange or red if the subscription is ending or expired or the player owes money. Shows today's check-ins (with undo) and this month's top attendees |
| Members | Search by name or phone, filter by All / Active / Ending soon / Owes money / Not training. Shows visits in the last 30 days and last visit. Add, archive or delete members. Double-click a member to open their account. Right-click for quick actions |
| Member window | Coloured initials, status and balance. Attendance stats: last 7 days, this month, last 30 days, average per week, weekly streak, last visit. A month calendar (green = trained, blue = subscribed) where clicking a day adds or removes a visit. Subscriptions and account history tabs |
| Equipment | Products with price and stock. Sell to a walk-in customer for cash, or to a member on credit. Undo a sale |
| Debts | Everyone who owes money, sorted by amount. Record a payment in one click |
| Settings | Language, text size, currency, subscription plans, backups, Excel export |

**Keyboard shortcuts:** `F2` check in, `F5` refresh, `Ctrl+F` search members, `Ctrl+N` new member,
`Delete` delete the selected member, `Enter` open the selected row, `Esc` close a window.

### Archive or delete?

- **Archive** hides a player who stopped coming but keeps their history and
  their payments in the income reports. Restore them at any time.
- **Delete** permanently removes the player with all their subscriptions,
  payments and purchases. Their payments also disappear from income reports.
  Use it for mistakes or duplicates.

### Attendance

One visit is counted per player per day. Checking in twice the same day
just says they are already in. "Last 7 days" includes today, and the weekly
streak counts back-to-back 7-day periods with at least one visit. The calendar
week starts on Saturday. Late entries and corrections are made by clicking
days in the member's calendar.

### Excel export

**Dashboard → Export to Excel** (or Settings) saves one `.xlsx` workbook.
It has a sheet each for members, debts, subscriptions, payments, charges,
sales, products, monthly income and attendance. Headers use the current language, and
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

## Demo mode (try it with sample data)

Double-click **`<App> Demo.bat`** next to the exe (for example `SpiderTeam Demo.bat`).
From source, use `run_demo.bat` or `python -m mma_tracker --demo`.

- It opens a separate database, `data\demo.db`. The real `data\tracker.db` is
  never opened, and no backups are made.
- It comes with 32 sample players (English and Arabic names) in every
  situation: training regularly, ending this week, just expired, paid but
  stopped coming, left months ago, and never subscribed. There are also
  12 months of payments, equipment sales (one item out of stock) and debts.
- Dates are generated relative to today, so the demo always looks current.
- An orange strip and `[DEMO]` in the title make it obvious which one is open.
- **Settings → Reset demo data** throws away your changes and recreates the
  sample data with fresh dates.

## Branded builds (one per gym)

A brand gives the app a gym's own name, window icon, exe icon and a logo on
the dashboard. Each brand lives in `brands/<brand>/`:

```
brands/spider-team/
  brand.json        {"name": "Spider Team", "exe": "SpiderTeam"}
  logo-source.jpg   the original logo
  icon.ico          generated: exe and window icon
  logo.png          generated: dashboard logo
```

Build it with `build.bat spider-team`. That gives `dist\SpiderTeam\SpiderTeam.exe`.
CI also uploads a `SpiderTeam-win32` artifact. A branded app keeps its own
`data` folder, so it never shares data with another copy.

To add a gym:

1. Create `brands/<name>/` with a `brand.json` and a square `logo-source.*` image.
2. Run `python tools/make_brand_icons.py brands/<name>` (needs Pillow, dev machine only).
3. Run `build.bat <name>`.

To try a brand from source: `set MMA_BRAND=spider-team` then `python -m mma_tracker`.

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
  i18n.py       English / Arabic strings (+ right-to-left fix for Tk)
  ui/           Tkinter screens; ui/visuals.py has the canvas charts,
                calendar, avatar and banner
tests/          unittest suite
```
