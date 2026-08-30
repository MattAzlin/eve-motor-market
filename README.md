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
- **Trade journal** — real profit after sales tax and broker fees, calculated
  from your actual skills and standings.
- **Deal finder** — daytrade and swing suggestions per hub.

## Install

Download `EVE Motor Market.exe` from
[Releases](https://github.com/PeanutMotor/eve-motor-market/releases) and run it.
Windows 10 or later.

Windows warns on first launch because the file is not code-signed — click
"More info", then "Run anyway".

## First start

Open the **Charaktere** tab and link a character, then
**Einstellungen → Aus EVE holen** for your skills and standings. Until then the
tool calculates with untrained base values, so nothing looks better than it is.

## Your data

Everything stays on your machine, in `%APPDATA%\EVE Motor Market`. Nothing is
uploaded anywhere. The tool talks to EVE's ESI servers, and to GitHub when you
check for updates.

## Bugs and requests

Open an [issue](https://github.com/PeanutMotor/eve-motor-market/issues) — what
you did and what you expected is enough.

---

Not a CCP Games product, not endorsed by CCP. The developer has signed the EVE
Online Developer License Agreement. EVE Online and all related trademarks belong
to CCP hf.
