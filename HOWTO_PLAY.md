# How to Play Roll It & Bowl It

This guide covers everything from starting your first match to understanding the dice mechanics behind every delivery.

---

## First run

When you open the app for the first time, the database is automatically created and seeded with:
- 10 international teams (England, Australia, India, Pakistan, New Zealand, South Africa, West Indies, Sri Lanka, Bangladesh, Afghanistan)
- 18 venues
- Full player rosters with individual ratings
- A season schedule across all formats (T20, ODI, Test)

Navigate to **http://127.0.0.1:5001** in your browser. You'll land on the home screen showing current standings and upcoming fixtures.

---

## Starting a match

1. Go to the **Schedule** or **Fixtures** section
2. Find an upcoming match and click it
3. Choose **Play** to control the match yourself, or **Fast Sim** to let the AI resolve it instantly
4. Select your toss result and batting/bowling decision
5. The live match screen opens

---

## The live match screen

The screen is divided into:
- **Match header** — teams, score, overs, roll mode toggle
- **Dice panel** — the die face, stage label, and action buttons
- **Commentary feed** — ball-by-ball descriptions
- **Scorecards** — batting and bowling figures, updated after every ball

---

## Rolling the dice

### Auto-Roll mode (default)

Click **Roll** (or press Space or R). The die spins and lands, and the result is immediately recorded. All dice stages resolve without waiting for you. This is fast and good for grinding through overs you don't want to dwell on.

### Manual Roll mode

Manual mode puts each dice stage under your control. Switch to it using the toggle in the match header, or press **M** when no ball is in flight.

Here's what a full delivery looks like in Manual mode:

1. **Press Roll** — Stage 1 resolves. The die shows the delivery type.
   - If it's a clean outcome (boundary, dot, runs), the ball is recorded immediately.
   - If an appeal is possible, you get...

2. **HOWZAT!** — The display flashes up with the fielding team's appeal. The die is held, waiting.

3. **Press Appeal** (or A) — Stage 2 rolls. The die decides: is the batter out?
   - **NOT OUT**: Press **Continue** (or C) to move on. Stage 3 resolves what actually happened.
   - **OUT**: Press **Dismissal** (or D) to roll Stage 4 — the dismissal type.

4. **If caught**: A **Caught Where?** button appears. Press it to roll Stage 4b — which fielder took it and where on the field.

5. The ball is recorded. Commentary appears. Scorecards update.

Manual mode is more work but the tension of waiting on that Stage 2 roll is the whole point. When a tail-ender is hanging on and you hear "HOWZAT!" and have to decide whether to appeal — that's the game working as intended.

---

## The HOWZAT! Engine explained

Every delivery passes through the dice engine in up to four stages. You never roll dice that aren't relevant — a no-ball that goes for four doesn't need an appeal.

### Stage 1 — Delivery type

The first roll determines what kind of delivery this is:

- **Dot ball** — defended, missed, hit to a fielder
- **Runs** (1–6) — struck for runs
- **Wide / No-ball** — extras, plus a re-bowl
- **Wicket-possible** — the delivery has beaten or found the edge of the bat; an appeal follows

On a free hit (after a no-ball), a wicket-possible delivery skips the appeal and goes to Stage 3 — the batter cannot be out.

### Stage 2 — Appeal outcome

Is the batter out?

This is where batter rating matters most. The die result is compared against the batter's threshold:

| Batter rating | Out if roll is... | Wicket chance per appeal |
|--------------|-------------------|--------------------------|
| 5 (best)     | ≥ 6               | ~6.2% |
| 4            | ≥ 5               | ~11.2% |
| 3            | ≥ 4               | ~16.2% |
| 2            | ≥ 3               | ~21.2% |
| 1 (weakest)  | ≥ 2               | ~27.2% |

A rating-5 batter needs the die to show a 6 to be dismissed. A rating-1 batter is out on anything but a 1.

### Stage 3 — Not-out resolution

When the batter survives the appeal, Stage 3 says what actually happened: an inside edge past leg stump, a thick outside edge that fell short, a brilliant defensive shot, a bottom edge through to fine leg. These generate the commentary detail.

### Stage 4 — Dismissal type

When the batter is out, Stage 4 rolls for how: bowled, caught, lbw, run out, stumped, hit wicket. The available modes depend on the delivery — a spinner can't bowl you out in a way that only fast bowling can produce.

### Stage 4b — Catch location

When the dismissal is caught, one more roll determines who took the catch and where: slip cordon, mid-on, deep square, the keeper... This feeds the commentary ("caught at third slip") and fielding statistics.

---

## Batter and bowler ratings

Players have ratings from 1 to 5.

**Batter rating** controls how hard they are to dismiss (see Stage 2 table above). It also influences scoring — higher-rated batters are more likely to score runs on scoring deliveries.

**Bowler rating** influences how often they generate wicket-possible deliveries in Stage 1. A rating-5 pace bowler beats the bat more often than a rating-1 part-timer.

You can see individual player ratings on the team roster pages.

---

## Match formats

### T20
- 20 overs per side
- One innings each
- Usually completed in one sitting
- **Tip**: The tension banner is most active here — close chases with 2 overs left are where Manual mode shines

### ODI
- 50 overs per side
- One innings each
- Fast-sim the powerplay and death overs if you want, play the middle overs manually

### Test
- Up to 5 days
- Two innings per side
- Follow-on rule applies (team trailing by 200+ runs in a two-innings match may be asked to bat again)
- Declarations are supported

---

## Tension suggestion banner

When the game detects a tense situation, a banner slides in suggesting you switch to Manual mode. Conditions that trigger it:

- **T20 finish**: ≤ 2 overs remaining with fewer than 15 runs needed
- **Last wicket**: the final batting pair is at the crease
- **Century approach**: a batter is on 95 or more
- **High required rate**: run rate needed exceeds 12 per over
- **Tied match**: scores are level with 1 over or fewer to play

Click the banner to switch to Manual mode immediately, or dismiss it (× button) to not see it again that innings.

---

## Fast sim

Press **F** or use the fast-sim button to resolve the rest of the current match instantly. The AI plays out every remaining ball using the same dice engine — same probabilities, same rules, just without the animation delay. Useful for:

- Skipping through a match you've already won comfortably
- Simulating unplayed fixtures in the schedule
- Running through Test matches quickly

---

## AI vs AI matches

When both teams are controlled by the AI (fast-sim or world simulation), the roll mode toggle is locked to Auto and hidden. Manual mode requires a human to press the buttons.

---

## Keyboard shortcuts reference

| Key | What it does |
|-----|--------------|
| **Space** or **R** | Roll the next ball (when idle) |
| **A** | Appeal — roll Stage 2 (Manual mode, after HOWZAT!) |
| **C** | Continue — not out, move on (Manual mode) |
| **D** | Dismissal — roll Stage 4 (Manual mode, batter out) |
| **D** | Toggle dark mode (when not in a dismissal state) |
| **M** | Switch roll mode between Auto and Manual |
| **F** | Fast-sim the rest of this match |

---

## Scorecards and records

Every ball is recorded to the database. After the match:

- Full batting and bowling scorecards are available
- Partnership records update
- Individual career records update (highest score, best bowling figures, etc.)
- Team head-to-head records update
- Season standings update with points, NRR, and run totals

Records are permanent unless you reset the world from the admin panel.

---

## Broadcast mode

Broadcast mode slows down all animations and adds dramatic pauses between stages. The HOWZAT! display holds for two seconds before the Appeal button appears, giving a streamed audience time to react. Toggle it from the settings panel in the match screen.

---

## Tips

- **Rating 1 batters are fragile** — don't expect tail-enders to hang around. A 27% dismissal rate per wicket-possible ball means they'll usually fall within a few overs.
- **Manual mode for the last five overs of a T20 chase** is where the game is at its best. Every appeal is genuinely tense when you have to press the button.
- **Fast-sim group stages**, play the knockouts manually. The world sim keeps everything consistent.
- **The tension banner is opt-in** — it won't keep pestering you if you dismiss it. One dismiss per innings.
- **Test cricket in Manual mode** is a commitment. Consider Auto for the first three days and switching to Manual when the match gets tight.
