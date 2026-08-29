EVE Motor Market
Industry and trading tool for EVE Online. Plans builds down to the raw
materials, spreads the jobs across your characters, and keeps a journal of what
you actually earned.
What it does
Build planning — full recipe tree from the finished item down to ore and
reactions, with ME/TE per item category.
Run planner — distributes jobs across your characters based on their real
skills, job slots and implants, and tells you how many blueprint copies each
one needs.
Material reservation — a saved plan holds on to the material it needs, so
a second plan does not tell you to buy the same stack twice.
Trade journal — imports your transactions via ESI and shows real profit
after sales tax and broker fees, calculated from your actual skills and
standings.
Deal finder — daytrade and swing suggestions per hub, with your own fees
applied.
Install
Download the installer from
Releases.
Run it. No administrator rights needed — it installs to your user folder.
Start EVE Motor Market from the start menu.
Windows 10 or later. Nothing else to install.
First start
Open the Charaktere tab and link a character. Until you do, the tool has no
idea about your skills or standings and calculates with the untrained base case
(7.5 % sales tax, 3 % broker fee) — deliberately pessimistic, so nothing ever
looks better than it is.
After linking, use Einstellungen → Aus EVE holen to pull your real skills
and standings.
Your data
Everything stays on your machine, in:
```
%LOCALAPPDATA%\\\\\\\\EveTradeLedger
```
Settings, your trade journal and the item database live there. Uninstalling does
not delete this folder — if you want your data gone, remove it yourself.
Nothing is uploaded anywhere. The tool talks to EVE's own ESI servers and to
GitHub when you press the update button, and to nothing else.
Updates
The tool does not update itself. Einstellungen → Auf neue Programm-Version
prüfen asks GitHub whether a newer release exists and tells you where to get
it. Installing over an existing version keeps your settings and journal.
Source code
Only the built installer is published here. If you find a bug or want
something changed, open an
issue — a description
of what you did and what you expected is enough.
---
This tool is not a CCP Games product and is neither published nor endorsed by
CCP. The developer has signed the EVE Online Developer License Agreement. EVE
Online and all related trademarks belong to CCP hf.
