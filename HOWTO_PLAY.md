# How to Play Roll It & Bowl It

This guide covers the practical flow of playing matches, choosing worlds, and understanding the dice system.

## First Launch

On first run the app creates and seeds the database automatically with:

- international teams
- associate nations
- domestic and franchise sides
- venues
- player squads

Open:

```text
http://127.0.0.1:5000
```

You can set defaults such as scoring style and roll mode from the app settings, but both can still be overridden match by match.

## Starting a Match

1. Open `Play`
2. Choose `Cricket Type`
3. Choose `Format`
4. Pick teams
5. Choose `Scoring System`
6. Choose venue and date
7. Choose player mode
8. Take the toss

### Cricket Type

- `International` shows national teams
- `Domestic` shows counties, states, and franchise sides

When domestic cricket is selected, a league filter appears to narrow the team list.

### Format Labels

International:

- `Test`
- `ODI`
- `T20`

Domestic:

- `First-Class`
- `One-Day`
- `T20`

The domestic labels map onto the same underlying engine formats.

## Scoring Systems

### Classic

- `1` = 1 run
- `2` = 2 runs
- `3` = 3 runs
- `4` = 4 runs
- `5` = appeal
- `6` = 6 runs

### Modern

Modern keeps the same readable face meanings and the same appeal chain, but some scoring results are lightly moderated in longer formats to keep totals more cricket-shaped.

## Roll Modes

### Auto

- faster
- resolves the ball flow automatically
- good for AI vs AI, streaming, and faster play

### Manual

- preserves the full HOWZAT tension
- lets you step through appeals and dismissal outcomes
- best for close finishes, milestones, and dramatic sessions

You can also set a default roll mode in Settings.

## The HOWZAT Chain

Rolling a `5` starts the appeal sequence.

The game can then move through:

1. appeal outcome
2. not-out resolution
3. dismissal type
4. catch location

That is the signature part of the system. Normal scoring stays simple, but wickets become multi-step dramatic events.

## Batter and Bowler Ratings

Players have ratings from `1` to `5`.

- batting rating influences how difficult a player is to dismiss
- bowling rating influences how dangerous their deliveries are

Higher-rated batters survive appeal balls more often. Higher-rated bowlers create more pressure and better wicket chances.

## Live Match Screen

The live match view is built around:

- scoreboard and match context
- batting and bowling cards
- dice panel
- mini live wagon wheel
- commentary feed
- scorecard tabs
- story strip and alerts

Broadcast Mode is designed for 1080p/1440p recording and spectator play.

## Innings Breaks and Results

At innings breaks the game now pauses deliberately and shows:

- the innings score
- target or next-innings stakes
- auto-continue countdown
- a `Continue` button

Result screens show:

- winner and margin
- result summary
- notes cards and headline context

## Worlds

Worlds let you build a longer-running save with its own fixtures, records, and rankings.

### World Types

- `International`
- `Domestic`
- `Combined`

### Calendar Style

- `Realistic`
- `Random`

### Domestic Coverage

For realistic domestic worlds:

- `Selected Clubs`
- `Full League`

### Managed Teams

World saves can be:

- AI only
- one managed international team
- one managed domestic team
- one managed international plus one managed domestic team

### Player Lifecycle

Each world can be created with:

- `Ageless Players`
- `Retire & Regens`

In `Retire & Regens` worlds, players age per world save, retire at varied times, and get replaced by world-specific regens.

## Almanack

The Dice Cricketers' Almanack tracks the long-form history of the save:

- batting
- bowling
- all-rounders
- teams
- matches
- partnerships
- honours

It also surfaces:

- records under threat
- players in form
- upcoming milestone chances

## Archive Matches

Completed matches can be opened from history and viewed in archive mode.

- full playable matches show full scorecards
- simulated matches show reconstructed newspaper-style scorecards and summaries

## LAN Play / Viewing

To expose the app to other machines on your local network:

```bash
python start.py --lan
```

This is useful for:

- showing the game on a second screen
- local household play
- remote-control style streaming setups on the same network

## Tips

- `Classic + Manual` is the strongest “tabletop dice cricket” experience
- `Modern + Auto` is best for fast world progression
- Manual mode shines most in the last overs of a chase or around batting milestones
- Combined worlds get much richer if you choose managed international and domestic sides together
- `Retire & Regens` is best for deep alternate-history saves
