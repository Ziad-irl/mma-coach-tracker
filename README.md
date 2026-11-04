# MMA Coach Tracker

A small, fast desktop app for an MMA coach to keep track of:

- **Member subscriptions**: monthly or custom plans, with expiry dates
- **Equipment sales**: gloves, shin guards, rash guards, and so on, with stock
- **Debts**: what each player still owes, and the payments they make

It is built for **old hardware**. The target machine is a 32-bit PC running Windows 7.

## Why this stack

| Choice | Reason |
|---|---|
| Python 3.8 (32-bit) | Last Python release that supports Windows 7 |
| Tkinter | Ships with Python, uses native widgets and very little RAM |
| SQLite | One file, no server, no install |
| No third-party runtime dependencies | Nothing to break, nothing to download |

## Status

Work in progress.
