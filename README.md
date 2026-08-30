# EVE Motor Market

Industry and trading tool for EVE Online. Plans builds down to the raw
materials, spreads the jobs across your characters, and keeps a journal of what
you actually earned.

## What it does

- **Build planning** — full recipe tree from the finished item down to ore and
  reactions, with ME/TE per item category.
- **Run planner** — distributes jobs across your characters based on their real
  skills, job slots and implants, and tells you how many blueprint copies each
  one needs.
- **Material reservation** — a saved plan holds on to the material it needs, so
  a second plan does not tell you to buy the same stack twice.
- **Trade journal** — imports your transactions via ESI and shows real profit
  after sales tax and broker fees, calculated from your actual skills and
  standings.
- **Deal finder** — daytrade and swing suggestions per hub, with your own fees
  applied.

## Install

1. Download `EVE Motor Market.exe` from
   [Releases](https://github.com/PeanutMotor/eve-motor-market/releases).
2. Run it. No installation, no administrator rights, no Python.
3. Windows will warn you on first launch because the file is not code-signed —
   click "More info", then "Run anyway".

Windows 10 or later. Nothing else to install.

## First start

Open the **Charaktere** tab and link a character. Until you do, the tool has no
idea about your skills or standings and calculates with the untrained base case
(7.5 % sales tax, 3 % broker fee) — deliberately pessimistic, so nothing ever
looks better than it is.

After linking, use **Einstellungen → Aus EVE holen** to pull your real skills
and standings.

## Your data

Everything stays on your machine, in:

```
%APPDATA%\EVE Motor Market
```

Settings, your trade journal and the item database live there. Deleting the
program does **not** delete this folder — if you want your data gone, remove it
yourself.

Nothing is uploaded anywhere. The tool talks to EVE's own ESI servers and to
GitHub when you press the update button, and to nothing else.

## Updates

The tool does not update itself. **Einstellungen → Auf neue Programm-Version
prüfen** asks GitHub
