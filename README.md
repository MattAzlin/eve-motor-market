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

1. Download the installer from
   [Releases](https://github.com/PeanutMotor/eve-motor-market/releases).
2. Run it. No administrator rights needed — it installs to your user folder.
3. Start **EVE Motor Market** from the start menu.

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

Settings, your trade journal and the item database
