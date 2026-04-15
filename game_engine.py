"""
game_engine.py — Pure dice logic for Roll It & Bowl It.
No Flask or database imports. All randomness via the random module.
Returns structured dicts; the Flask layer handles all DB writes.
"""

import random
import math
from datetime import date, timedelta
from itertools import combinations

# ── Commentary Bank ────────────────────────────────────────────────────────────

COMMENTARY = {
    'dot': [
        "{bowler} is right on the money — {batter} can't get it away.",
        "Tight line from {bowler}, {batter} defends solidly. No run.",
        "{batter} plays and misses! That one went past the outside edge.",
        "Dot ball. {bowler} building the pressure nicely.",
        "{batter} pushes at it and it goes straight to mid-off. Nothing doing.",
        "Defended back down the pitch by {batter}. Textbook stuff.",
        "{bowler} beats the bat! That's a beauty of a delivery.",
        "Probing length from {bowler} — {batter} wisely leaves it alone.",
        "{batter} dabs at it but the fielder cuts it off in the covers. Dot.",
        "{bowler} keeps it tight. {batter} is watchful, playing each ball on merit.",
        "Good discipline from both sides. {batter} isn't taking any chances.",
        "{bowler} angles it across {batter} — no shot offered, no run taken.",
        "That's a maiden-building delivery. {batter} has nothing to play at.",
        "Beaten! {bowler} gets it to move late and {batter} plays all around it.",
        "{batter} drops it dead at the crease. Terrific ball from {bowler}.",
        "Patted back watchfully by {batter}. The pressure is mounting at {score}/{wickets}.",
        "{bowler} hits a length and {batter} is content to leave it. Smart cricket.",
    ],
    'single': [
        "{batter} clips it off the pads and sets off smartly. A single.",
        "Pushed into the covers for one. {batter} and {bowler} exchange a glance.",
        "Worked away to square leg — they scamper through for a single.",
        "{batter} drops it just in front of cover point and calls immediately. One.",
        "A deft glance to fine leg brings up a single for {batter}.",
        "Inside edge, rolls to mid-on — they take the single without any fuss.",
        "{batter} nudges it through midwicket. Easy single, keeps the score ticking.",
        "Soft hands from {batter}, dropping the ball into the on-side. One run.",
        "Turned off the hip by {batter} — a comfortable single to square leg.",
        "Deflects off the pad down to fine leg. They take the easy single.",
        "{batter} walks across and flicks it to the on side. Single.",
        "Half-volley on the pads, {batter} clips it to mid-on. One run.",
        "Underedge, rolls into the leg side — {batter} shouts yes immediately.",
        "A dink over the infield from {batter}. Good running, they get one.",
        "Worked behind square on the off side for a single. Neat play by {batter}.",
        "{batter} keeps it along the ground through point. Running well, takes one.",
    ],
    'two': [
        "{batter} drives through the gap between mid-off and extra cover — two runs!",
        "Swept to deep square leg, they run hard and come back for two.",
        "Pulled in front of square — good running between the wickets, two more.",
        "{batter} clips it into the gap at midwicket. Two very comfortable runs.",
        "Punched off the back foot through the covers — they turn for two.",
        "Driven firmly to long-off, the fielder slides to cut it off. Still two.",
        "{batter} goes over the top — lands just short of the boundary. Two.",
        "Worked to deep mid-on, {batter} calls quickly and they pinch two.",
        "Thick outside edge races away through the slip region — two runs.",
        "Glanced fine, the fielder has to chase and they complete two easily.",
        "Paddle sweep by {batter}, drops short of the man. They're running hard — two!",
        "Back-foot punch to deep cover, good running from both batters. Two.",
    ],
    'three': [
        "They run three! {batter} hits it into the gap and they really sprint.",
        "Driven to long-off and the fielder fumbles — {batter} converts one into three!",
        "{batter} hits it to deep mid-wicket, {score}/{wickets}. Excellent running, three!",
        "Top-edged sweep loops over the fielder's head — they come back for three.",
        "Into the gap, the ball reaches the boundary rope but spills back — three runs.",
        "Brilliant fielding almost cuts it off, but they get three on the last stride.",
        "The ball goes to the sweeper cover. They run two and sneak back for three.",
        "Driven hard to deep cover — the fielder's throw misses and they get three!",
    ],
    'four': [
        "{batter} drives through the covers and it races to the boundary! FOUR!",
        "Thunderous pull shot from {batter} — that's been hammered to the midwicket fence!",
        "Glanced off the hip, fine leg can't cut it off. FOUR runs!",
        "Cut hard through point, too fast for the fielder. {batter} gets four!",
        "Beautiful cover drive from {batter}! Timed to perfection — FOUR!",
        "Whipped off the pads past square leg. {batter} watches it to the rope.",
        "Back-foot punch through extra cover. Nothing the fielder can do — FOUR!",
        "Smashed straight down the ground! {bowler} watches it go to the boundary.",
        "Edged wide of slip! {batter} didn't mean that but it's four all the same.",
        "Swept fine with tremendous power by {batter} — four more to the total!",
        "Flicked off middle stump, raced to the square leg fence. FOUR!",
        "Driven superbly through mid-off, rolls to the boundary. Classy from {batter}!",
        "Top-edged sweep goes over the keeper's head and one-bounces the boundary!",
        "Slog-swept over midwicket by {batter} — lands just in play, scurries away. FOUR!",
        "On-driven with a full swing of the bat. That barely left the ground. FOUR!",
        "Cracked through point off the back foot — that's a boundary in a blink!",
    ],
    'six': [
        "{batter} launches it into the stands! That's gone all the way! SIX!",
        "MASSIVE hit from {batter}! {bowler} watches it sail over the midwicket rope!",
        "Down the ground and OVER the long-on boundary! What a shot from {batter}!",
        "Slog-sweep into the crowd! {batter} is absolutely timing it perfectly!",
        "Over long-off! {batter} gets under it perfectly — SIX!",
        "Maximum! {batter} makes that look effortless. The crowd loves it!",
        "BANG! Into the upper tier! {batter} with a flat-batted whack over extra cover!",
        "Stepped out and lofted {bowler} over long-on. Didn't even look — SIX!",
        "Pulled from outside off stump over square leg. Outrageous shot! SIX!",
        "Inside-out over extra cover, never going anywhere but over the rope! MAXIMUM!",
        "Reverse swept for SIX! {batter} is playing a different game from everyone else!",
        "Short ball and {batter} is in position early — smashed flat over midwicket. SIX!",
        "Over the covers for six! {batter} goes aerial and finds the gap perfectly!",
        "Tonked! {batter} hits it high and hard and it clears long-off comfortably!",
        "SIX! {batter} connects sweetly off the meat of the bat. {bowler} looks to the sky.",
    ],
    'wide': [
        "{bowler} strays down the leg side — wide called. An extra for the batting side.",
        "Too far outside off, the umpire's arm shoots out. Wide. {bowler} grimaces.",
        "Down leg, the keeper has to dive. Wide signalled. Not the line {bowler} wanted.",
        "Sprays it off target. Wide! Adds unnecessary pressure on {bowler}.",
        "That's well wide of the stumps. The umpire calls wide without hesitation.",
        "Loses the length and it goes very wide. {bowler} shakes their head.",
        "Down the leg side, keeper can't collect cleanly. Wide called by the umpire.",
        "{bowler} drags it too far across. Wide. Not ideal at this stage.",
        "Too straight and sliding down leg — wide. The umpire was watching for it.",
        "That one got away from {bowler}. Wide. {batter} watches it go by.",
    ],
    'no_ball': [
        "NO BALL! {bowler}'s front foot lands well over the crease. Free hit coming up!",
        "Called no ball — {bowler} has overstepped. The next ball is a free hit!",
        "{bowler} can't afford that — front foot over the line. No ball, and a free hit!",
        "The umpire calls no ball! {bowler} has given {batter} a free licence next ball.",
        "No ball! {bowler} gets too eager and oversteps. Free hit for {batter}!",
        "An expensive mistake from {bowler} — no ball! {batter} will love the next one.",
        "No ball called! That cost a run and hands {batter} a free hit. Not ideal!",
        "Overstepped! No ball, and the crowd cheers in anticipation of the free hit.",
    ],
    'free_hit_announced': [
        "FREE HIT! {batter} cannot be out off this delivery except run out. Time to attack!",
        "It's a FREE HIT! {batter} steps away from the crease with a smile.",
        "FREE HIT! {bowler} must be disappointed — {batter} can swing hard here.",
        "The fielders move in but {batter} has a free hit coming. No fear!",
        "FREE HIT! The crowd buzzes with anticipation. What will {batter} do?",
        "FREE HIT! {batter} looks up and picks the gap. This could be expensive for {bowler}.",
    ],
    'bowled': [
        "BOWLED! {bowler} has done it! The off stump is cartwheeling! {batter} is gone!",
        "CLEAN BOWLED! {batter} is beaten all ends up — the stumps are shattered!",
        "Bowled! {bowler} finds the gap between bat and pad and the middle stump goes!",
        "THROUGH THE GATE! {batter} goes for the drive and is bowled through the gate!",
        "Bowled him! {batter} misses a full one and hears the death rattle. Out!",
        "BOWLED! The ball clips the top of off stump and the bail floats off. Brilliant!",
        "What a ball! {bowler} swings it back late and {batter} is bowled for {runs}.",
        "Beaten by turn! {batter} plays outside the line and the leg stump is clipped. BOWLED!",
        "Yorked! {bowler} squeezes it under the bat and crashes into the base of off stump!",
        "BOWLED! Nipped back off the seam and {batter} is done for {runs} off {balls} balls!",
        "Through the defences! {batter} couldn't read the change of pace. BOWLED!",
        "The stumps go! {batter} misjudges the length and is bowled by a good delivery.",
    ],
    'lbw': [
        "LBW! Up goes the finger! {batter} is plumb in front — no question about that!",
        "PLUMB! {batter} is hit on the knee-roll right in front of off stump. OUT!",
        "LBW! Raps {batter} on the front pad — the umpire has no hesitation!",
        "{bowler} gets one to swing back in and catches {batter} in front. LBW!",
        "Trapped in front! {batter} plays down the wrong line — out LBW for {runs}!",
        "That's given! {batter} is struck on the pad, ball would have clipped leg stump. LBW!",
        "GIVEN! {bowler} hits the pads and the umpire's finger goes up. {batter} walks.",
        "LBW! That one kept low and {batter} missed it completely. The finger goes up!",
        "{batter} misses the sweep and is struck plumb in front. LBW — out for {runs}!",
        "Sliding back in from off stump, hits {batter} on the back foot. LBW! OUT!",
        "The quicker one from {bowler} catches {batter} on the crease. LBW!",
        "Inswinger from {bowler} traps {batter} in front for {runs}. Game on!",
    ],
    'caught': [
        "CAUGHT! {batter} goes for {runs} — a fine catch ends the innings.",
        "TAKEN! {batter} gets a thick edge and it's snaffled in the cordon!",
        "Caught! {batter} mistimes the drive and the fielder takes it comfortably.",
        "Oh, that's gone! {batter} pulls it straight to the fielder. CAUGHT!",
        "Leading edge from {batter} loops up and is pouched! OUT for {runs}!",
        "CAUGHT! {batter} goes hard at it but gets it off the top edge. Taken!",
        "A superb catch! {batter} drives hard but finds the fielder at covers. Out!",
        "{batter} holes out for {runs} — mistimed, and the fielder judges it perfectly.",
        "A sharp chance and it's taken! {batter} walks off for {runs}.",
        "CAUGHT! {batter} could only find the fielder on the boundary. Frustrating!",
    ],
    'caught_behind': [
        "CAUGHT BEHIND! {batter} gets a thin nick and the keeper takes it cleanly!",
        "Edged! {batter} pokes at one outside off — straight into the keeper's gloves!",
        "The keeper goes up and it's CAUGHT! {batter} dangles the bat and pays the price!",
        "Nicked off! {batter} goes for the drive, gets an outside edge — keeper pouches it!",
        "A feather! {batter} barely touched it but the keeper heard it — caught behind!",
        "REVIEW WOULD BE FUTILE! That's a thick outside edge into the keeper's gloves!",
        "Caught behind! {batter} loses shape on the cut shot and nicks it through.",
        "The ball moves off the seam and clips the edge — keeper gleeful. CAUGHT BEHIND!",
        "{bowler} gets the away-swinger to work — {batter} nibbles and is caught behind!",
        "{batter} goes back to cut but the ball rises on him. Edged! Caught behind for {runs}!",
    ],
    'caught_slip': [
        "CAUGHT AT SLIP! {bowler} extracts great movement and {batter} is gone!",
        "Classic slip catch! {batter} pushes at a wide one and it flies to first slip!",
        "GONE! Faint edge from {batter} and the slip fielder dives to his right — taken!",
        "Caught slip! {bowler} pitches it up, {batter} drives and it nicks the outside edge!",
        "A regulation nick to slip! {batter} had no idea the ball was moving that much.",
        "Edged to slip and taken! {batter} goes for {runs} in the slips cordon.",
        "A sharp chance and it's snaffled! {batter} pokes outside off — taken at slip!",
        "{batter} feels for one outside off and the edge is swallowed at first slip!",
    ],
    'caught_ring': [
        "CAUGHT at mid-on! {batter} drills it back but the fielder takes a sharp catch!",
        "Straight to mid-off! {batter} drives and finds the fielder. CAUGHT!",
        "Caught and bowled! {bowler} reaches down and takes a return catch. OUT!",
        "Sharp chance at cover and it's taken! {batter} was going hard at that.",
        "Mistimed drive to mid-wicket — the fielder takes it calmly. CAUGHT!",
        "Skied! {batter} gets underneath it and the fielder settles under the ball. CAUGHT!",
        "Straight to extra cover — {batter} finds the fielder for {runs}. OUT!",
        "{batter} hits it hard but straight to the fielder in the ring. Caught!",
    ],
    'caught_midfield': [
        "CAUGHT at mid-off! {batter} goes for the big hit and doesn't get all of it!",
        "Holed out to long-on! {batter} looks to the sky — gone for {runs}.",
        "CAUGHT at covers! {batter} tries the flashy drive, finds the fielder perfectly.",
        "Finds the fielder at mid-wicket! {batter} goes for the pull but mistimes it.",
        "Pulled to deep midwicket — the fielder settles and takes it cleanly. OUT!",
        "{batter} goes for the big one but gets a leading edge to covers. Caught!",
        "Hits it high towards long-off and the fielder runs in to hold a good catch!",
    ],
    'caught_fine': [
        "CAUGHT at fine leg! {batter} top-edges the pull and the fielder runs around!",
        "Top-edged sweep and it goes to fine leg — taken! {batter} is furious.",
        "The sweep goes wrong for {batter} — top edge, fine leg, caught. Out for {runs}!",
        "Miscued pull to third man! {batter} thought it was going over, but it's caught!",
        "TAKEN at deep fine leg! {batter} gets too much top edge on the hook shot.",
        "Caught at third man! {batter} dabs at it but gets more top edge than intended.",
        "Pull shot but too much top edge — fine leg runs round and takes the catch!",
        "Skies it fine! {batter} tries the ramp and fine leg runs in for a great catch!",
    ],
    'caught_boundary': [
        "CAUGHT ON THE BOUNDARY! {batter} hit it well but not quite far enough!",
        "The fielder on the rope holds on! {batter} thought that was six — it's OUT!",
        "Great catch on the boundary! {batter} looked like a six before the fielder intervened!",
        "CAUGHT near the rope! The fielder times the jump perfectly — incredible catch!",
        "So close to a six but the fielder at long-on judges it brilliantly. CAUGHT!",
        "That looked like going over, but the boundary fielder holds on! {batter} goes for {runs}.",
        "Almost! The fielder on the rope takes the catch just inside. {batter} is stunned!",
        "Caught just inside the boundary — the umpire confirms it's OUT! {batter} can't believe it.",
    ],
    'stumped': [
        "STUMPED! {batter} dances down the track and misses — the keeper does the rest!",
        "What a stumping! {batter} is out of the crease and the keeper removes the bails!",
        "Stumped! {batter} comes down to drive but the turn beats the bat. Gone!",
        "STUMPED! {batter} has no answer to the turn — the keeper is up and whips the bails!",
        "Down the track and beaten! The keeper gathers and {batter} is stumped in a flash!",
        "{batter} advances but can't make contact — the keeper whips off the bails! STUMPED!",
        "Tossed up by {bowler} — {batter} leaves the crease and is stumped! Classic!",
        "STUMPED! {batter} over-committed to the drive and the keeper does the rest.",
        "Quick as lightning — stumped! {batter} couldn't get back in time after missing the flick.",
        "Beautiful! {bowler} draws {batter} out and the keeper completes a sharp stumping!",
    ],
    'run_out': [
        "RUN OUT! There's been a terrible mix-up and {batter} has to go!",
        "Direct hit from the fielder — {batter} was miles short! RUN OUT!",
        "A mix-up between the batters — {batter} is left stranded and is run out!",
        "RUN OUT! The throw hits the stumps with {batter} diving but short!",
        "Called through, sent back, OUT! Communication breakdown costs {batter} dearly.",
        "What a throw! Direct hit and {batter} is run out for {runs}. Dreadful calling!",
        "RUN OUT! {batter} responds too late to the call — the fielder hits the stumps!",
        "Brilliant fielding! The ball comes in flat and fast — {batter} is run out!",
    ],
    'leg_bye': [
        "Clips the pad and rolls away — they take a leg bye. No run to the batter.",
        "Off the thigh pad, {batter} sets off and they take a leg bye.",
        "Leg bye! Hits the front pad and trickles into the leg side for a run.",
        "Deflects off the pad — the umpire raises the arm for a leg bye.",
        "Leg bye signalled — the ball brushed the pad and {batter} set off smartly.",
        "Rapped on the pad, the ball rolls behind square and they take a leg bye.",
        "Leg bye! The ball angles in and clips {batter}'s thigh on the way to fine leg.",
        "Off the knee-roll, the ball squirts to square leg. Leg bye. One extra.",
    ],
    'bye': [
        "That goes through to the keeper — wait, they've taken a bye! The keeper fumbled!",
        "BYES! The ball misses everything and the keeper can't collect. One extra.",
        "Keeper can't hold it — they set off for a bye and make it safely.",
        "The ball goes through to the boundary rope — FOUR byes! Expensive lapse.",
        "A bye! Both missed it — the batter and the keeper — and they scamper through.",
        "Through the keeper and they run a bye. Fortunate for the batting side.",
    ],
    'fifty': [
        "FIFTY! {batter} raises the bat to a standing ovation! A superb innings!",
        "{batter} brings up a half-century with {runs} from {balls} balls! Outstanding!",
        "Fifty up for {batter}! What a knock — the crowd are on their feet!",
        "Half-century! {batter} has been masterful in this innings. Well deserved!",
        "Fifty for {batter}! Reaches the milestone with a boundary and punches the air!",
        "The fifty comes up for {batter} — what a knock this has been at {score}/{wickets}!",
        "{batter} goes to fifty — composed, intelligent batting. This innings has class.",
        "FIFTY! {batter} points the bat to the dressing room. A milestone well earned.",
        "Fifty runs for {batter}! In the zone, and this is just the beginning.",
        "Half-century completed! {batter} looks up and savours the moment.",
    ],
    'century': [
        "CENTURY! {batter} raises the bat and the crowd erupts! A brilliant hundred!",
        "ONE HUNDRED! {batter} has done it — removes the helmet, soaks in the applause!",
        "{batter} completes a magnificent century! The dressing room is on its feet!",
        "A hundred for {batter}! This is a special innings. Hundred up with a boundary!",
        "WHAT A KNOCK! {batter} reaches three figures — an absolutely sublime innings!",
        "Century! The bat goes up, the helmet comes off. {batter} has been magnificent.",
        "Three figures! {batter} from {balls} balls! The crowd will remember this one.",
        "{batter} has done it! A century at {score}/{wickets}. Absolutely outstanding!",
        "A HUNDRED! {batter} punches the air — this performance deserves every bit of that.",
        "Ton up for {batter}! A masterclass in batting. Wonderful to watch.",
    ],
    'one_fifty': [
        "ONE HUNDRED AND FIFTY! {batter} is absolutely ON FIRE today!",
        "150 for {batter}! A phenomenal innings — this is world-class batting!",
        "{batter} marches to 150 and shows no sign of stopping! Incredible!",
        "A hundred and fifty runs! {batter} is writing their name into the history books!",
        "150 up! {batter} is commanding, dominant. This is a special performance!",
        "What an innings from {batter} — 150 and still going! The bowlers are suffering!",
        "150! {batter} raises the bat once more — the crowd gives another standing ovation!",
        "A phenomenal 150 for {batter}! One of the great innings we'll see this season.",
    ],
    'double_century': [
        "TWO HUNDRED! {batter} has made cricketing history today! Absolutely remarkable!",
        "DOUBLE CENTURY! {batter} joins the immortals. What a monumental achievement!",
        "200 runs for {batter}! This is the stuff of legends. Incredible batting!",
        "A DOUBLE HUNDRED! The ground erupts — {batter} has played the innings of a lifetime!",
        "200 and still going! {batter} is in another dimension today. Simply extraordinary!",
        "{batter} raises the bat for a double century! This will be talked about for years!",
    ],
    'five_fer': [
        "FIVE WICKETS for {bowler}! A magnificent five-for — what a bowling performance!",
        "FIVE-FER! {bowler} has the five-wicket haul — the figures read {figures}!",
        "{bowler} has five! A stunning display of bowling. {figures} — a performance for the ages!",
        "Five wickets for {bowler}! What an effort — the batting side is in tatters!",
        "FIVE FOR {bowler}! Well and truly into the record books with {figures}!",
        "A five-wicket haul! {bowler} is celebrating — {figures} in this innings!",
        "{bowler} takes their fifth wicket! {figures} — one of the great bowling spells!",
        "FIVE WICKETS! {bowler} has been devastating. What a day to be a bowler!",
    ],
    'ten_wicket_haul': [
        "TEN WICKETS IN THE MATCH! {bowler} has achieved something extraordinary!",
        "A TEN-WICKET HAUL! {bowler} is immortalised — this is cricketing greatness!",
        "10 wickets for {bowler} in the match! What a performance to remember forever!",
        "TEN FOR! {bowler} has bowled the innings of a lifetime across two spells!",
        "Incredible! {bowler} completes a ten-wicket match haul. History is made!",
        "TEN WICKETS! The crowd gives {bowler} a standing ovation. Simply magnificent.",
    ],
    'century_partnership': [
        "A CENTURY PARTNERSHIP! {partnership} runs together — this stand is match-defining!",
        "100-run partnership! The batting duo have put the bowling to the sword!",
        "The hundred partnership comes up! A brilliant stand that's shifted the match.",
        "Century stand! They've batted magnificently together for {partnership} runs.",
        "A HUNDRED for the partnership! The fielders look deflated. What a stand!",
        "Partnership century! Every run has been earned with skill and determination.",
        "{partnership} runs between these two — a batting partnership for the memory!",
        "Hundred partnership! The team in the dressing room are loving every moment of this.",
    ],
    'last_wicket_wag': [
        "The tail is wagging! The last wicket is adding valuable runs here.",
        "Last pair at the crease and they're fighting hard — every run counts!",
        "A valuable last-wicket partnership developing here. Determined stuff!",
        "The number 11 is contributing! This could be a telling stand yet.",
        "The bowlers are frustrated — the last wicket is proving stubborn!",
        "Last-wicket resistance! Every run they add increases the pressure on the opposition.",
    ],
    'batter_on_99': [
        "{batter} is on 99! One run away from a century — the nerves must be incredible!",
        "99 not out! {batter} is a single away from a hundred. The whole ground is watching!",
        "{batter} on 99 — can they get that final run? The tension is unbearable!",
        "One short of a century! {batter} on 99. Take a deep breath...",
        "The crowd goes quiet — {batter} is on 99. A hundred within touching distance!",
        "99 for {batter}! One more run and it's a century. Pressure like no other in cricket!",
    ],
    'new_batting_record': [
        "A NEW BATTING RECORD! {batter} has set a new high score in The Almanack!",
        "History is made! {batter} has broken the batting record with this knock!",
        "Record-breaking innings from {batter}! The Almanack will be updated tonight.",
        "A NEW HIGH SCORE! {batter} has surpassed all previous marks. Outstanding!",
        "Record shattered! {batter} goes beyond the previous best. A truly special innings!",
        "{batter} breaks the record! The Almanack has a new entry at the top.",
    ],
    'new_bowling_record': [
        "A NEW BOWLING RECORD! {bowler}'s figures surpass all previous bests in The Almanack!",
        "History in the making! {bowler} sets a new record with figures of {figures}!",
        "Record-breaking bowling from {bowler}! The Almanack has a new entry!",
        "A NEW RECORD! {bowler} has taken more wickets in an innings than anyone before!",
        "The Almanack will need updating — {bowler} has set a new bowling record today!",
        "{bowler} shatters the bowling record! What a performance for the history books!",
    ],
    'match_pressure': [
        "{required} needed off {overs} overs — can they do it? The tension is immense!",
        "This is going to the wire! {required} runs needed with {overs} overs remaining.",
        "The asking rate is climbing — {required} off {overs}. This is a run chase!",
        "Drama unfolds: {required} to win from {overs} overs. The game is on a knife-edge!",
        "The pressure is building with every ball. {required} from {overs}. It's anyone's game!",
        "Every delivery counts now — {required} needed off {overs}. Breathtaking cricket!",
        "Can they pull off the chase? {required} off {overs}. The crowd is on its feet!",
        "The pressure is immense — {required} needed from {overs} remaining overs!",
    ],
    'innings_end': [
        "And that's the end of the innings! {score}/{wickets} the final total.",
        "Innings complete: {score}/{wickets}. A target is set for the opposition.",
        "All out for {score}! The innings is over. {wickets} wickets to the bowlers.",
        "The innings closes at {score}/{wickets}. A total to defend.",
        "That's it! Innings over: {score}/{wickets}. Now the fielding side takes on the bat.",
        "End of innings — {score} for {wickets}. The stage is set for the second innings.",
    ],
    'new_batter': [
        "{batter} makes their way to the crease. A key moment in this match.",
        "New batter in — {batter} will be looking to steady the innings.",
        "Here comes {batter}. The team needs runs — can they provide them?",
        "{batter} walks out to join the remaining resistance at {score}/{wickets}.",
        "New partnership needed. {batter} arrives at the crease with intent.",
        "The next batter is {batter} — they'll need to get their eye in quickly here.",
        "{batter} strides to the crease. Big moment. Big opportunity.",
        "A fresh face at the crease — {batter} will be eager to make their mark.",
    ],
}

# ── Core Functions ─────────────────────────────────────────────────────────────

def roll_die() -> int:
    return random.randint(1, 6)


def _stage1_scoring_outcome(stage1_roll, scoring_mode='modern', format='T20',
                            bowler_rating=3):
    """Resolve the literal scoring face for Stage 1, with light modern moderation."""
    if stage1_roll == 1:
        return 'single', 1
    if stage1_roll == 2:
        return 'two', 2
    if stage1_roll == 3:
        return 'three', 3
    if stage1_roll == 4:
        if scoring_mode == 'modern' and format == 'Test':
            drag_back = 0.18 if bowler_rating >= 5 else 0.10 if bowler_rating >= 4 else 0.0
            if drag_back and random.random() < drag_back:
                return 'three', 3
        return 'four', 4
    if stage1_roll == 6:
        if scoring_mode == 'modern' and format in ('ODI', 'Test'):
            keep_threshold = 4 if format == 'ODI' else 5
            if roll_die() < keep_threshold:
                return 'four', 4
        return 'six', 6
    return None, 0


def bowl_ball(batter_rating, bowler_rating, bowling_type,
              is_free_hit=False, partnership_balls=0,
              scoring_mode='modern', format='T20') -> dict:
    """Four-stage HOWZAT system. Returns a complete result dict."""

    result = {
        'stage1': None,
        'stage2': None,
        'stage3': None,
        'stage4': None,
        'stage4b': None,
        'outcome_type': None,
        'runs': 0,
        'extras_type': None,
        'extras_runs': 0,
        'dismissal_type': None,
        'caught_type': None,
        'shot_angle': None,
        'is_free_hit': is_free_hit,
        'next_is_free_hit': False,
        'commentary_key': 'dot',
    }

    # ── Stage 1: The Ball ──────────────────────────────────────────────────────
    s1 = roll_die()
    result['stage1'] = s1

    if s1 != 5:
        outcome_type, runs = _stage1_scoring_outcome(
            s1, scoring_mode=scoring_mode, format=format, bowler_rating=bowler_rating
        )

        # Extras check: roll a d6, on 6 check for wide/no-ball
        extras_roll = roll_die()
        if extras_roll == 6:
            extras_sub = roll_die()
            if extras_sub == 5:
                # Wide
                result['outcome_type'] = 'wide'
                result['extras_type'] = 'wide'
                result['extras_runs'] = 1
                result['runs'] = 0
                result['commentary_key'] = 'wide'
                result['shot_angle'] = generate_shot_angle('wide', 0)
                return result
            elif extras_sub == 6:
                # No-ball
                result['outcome_type'] = 'no_ball'
                result['extras_type'] = 'no_ball'
                result['extras_runs'] = 1
                result['runs'] = 0
                result['next_is_free_hit'] = True
                result['commentary_key'] = 'no_ball'
                result['shot_angle'] = generate_shot_angle('no_ball', 0)
                return result

        result['outcome_type'] = outcome_type
        result['runs'] = runs
        result['shot_angle'] = generate_shot_angle(outcome_type, runs)

        if outcome_type == 'single':
            result['commentary_key'] = 'single'
        elif outcome_type == 'two':
            result['commentary_key'] = 'two'
        elif outcome_type == 'three':
            result['commentary_key'] = 'three'
        elif outcome_type == 'four':
            result['commentary_key'] = 'four'
        elif outcome_type == 'six':
            result['commentary_key'] = 'six'

        return result

    # ── Stage 2: The Appeal ────────────────────────────────────────────────────
    s2 = roll_die()
    result['stage2'] = s2

    # Determine OUT threshold by batter_rating
    out_threshold = {5: 6, 4: 5, 3: 4, 2: 3, 1: 2}.get(batter_rating, 4)
    is_out = s2 >= out_threshold

    if is_out and is_free_hit:
        # Free hit — batter safe (except run out, which Stage 4 may give)
        # Treat as not out for Stage 3
        is_out = False

    if is_out:
        # Proceed to Stage 4
        s4 = roll_die()
        result['stage4'] = s4

        if s4 in (1,):
            result['dismissal_type'] = 'bowled'
            result['outcome_type'] = 'wicket'
            result['commentary_key'] = 'bowled'
        elif s4 == 2:
            result['dismissal_type'] = 'lbw'
            result['outcome_type'] = 'wicket'
            result['commentary_key'] = 'lbw'
        elif s4 in (3, 4, 5):
            # Caught — Stage 4b
            s4b = roll_die()
            result['stage4b'] = s4b
            result['dismissal_type'] = 'caught'
            result['outcome_type'] = 'wicket'
            caught_map = {
                1: 'caught_behind',
                2: 'caught_slip',
                3: 'caught_ring',
                4: 'caught_midfield',
                5: 'caught_fine',
                6: 'caught_boundary',
            }
            result['caught_type'] = caught_map[s4b]
            result['commentary_key'] = caught_map[s4b]
        elif s4 == 6:
            if bowling_type == 'spin':
                sub = roll_die()
                if sub <= 4:
                    result['dismissal_type'] = 'stumped'
                    result['outcome_type'] = 'wicket'
                    result['commentary_key'] = 'stumped'
                else:
                    # caught_behind — Stage 4b forced
                    result['dismissal_type'] = 'caught'
                    result['caught_type'] = 'caught_behind'
                    result['outcome_type'] = 'wicket'
                    result['commentary_key'] = 'caught_behind'
            else:
                sub = roll_die()
                if sub == 1:
                    result['dismissal_type'] = 'run_out'
                    result['outcome_type'] = 'wicket'
                    result['commentary_key'] = 'run_out'
                else:
                    # Caught — Stage 4b
                    s4b = roll_die()
                    result['stage4b'] = s4b
                    result['dismissal_type'] = 'caught'
                    result['outcome_type'] = 'wicket'
                    caught_map = {
                        1: 'caught_behind',
                        2: 'caught_slip',
                        3: 'caught_ring',
                        4: 'caught_midfield',
                        5: 'caught_fine',
                        6: 'caught_boundary',
                    }
                    result['caught_type'] = caught_map[s4b]
                    result['commentary_key'] = caught_map[s4b]

        # Bowled/LBW/run_out have no shot angle; caught/stumped may
        if result['dismissal_type'] in ('bowled', 'lbw', 'run_out'):
            result['shot_angle'] = None
        else:
            result['shot_angle'] = generate_shot_angle('wicket_caught', 0)

        return result

    # ── Stage 3: Not Out Resolution ────────────────────────────────────────────
    s3 = roll_die()
    result['stage3'] = s3

    if s3 in (1, 2):
        # Dot ball
        result['outcome_type'] = 'dot'
        result['runs'] = 0
        result['commentary_key'] = 'dot'
        result['shot_angle'] = generate_shot_angle('dot', 0)
    elif s3 == 3:
        # Leg bye
        sub = roll_die()
        leg_bye_runs = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4}[sub]
        # Bowler quality modifier
        if bowler_rating == 5 and random.random() < 0.30:
            leg_bye_runs = 0
            result['outcome_type'] = 'dot'
            result['commentary_key'] = 'dot'
            result['shot_angle'] = generate_shot_angle('dot', 0)
        elif bowler_rating == 4 and random.random() < 0.15:
            leg_bye_runs = 0
            result['outcome_type'] = 'dot'
            result['commentary_key'] = 'dot'
            result['shot_angle'] = generate_shot_angle('dot', 0)
        else:
            result['outcome_type'] = 'leg_bye'
            result['extras_type'] = 'leg_bye'
            result['extras_runs'] = leg_bye_runs
            result['commentary_key'] = 'leg_bye'
            result['shot_angle'] = generate_shot_angle('single', leg_bye_runs)
    elif s3 == 4:
        # Bye
        sub = roll_die()
        bye_runs = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4}[sub]
        if bowler_rating == 5 and random.random() < 0.30:
            bye_runs = 0
            result['outcome_type'] = 'dot'
            result['commentary_key'] = 'dot'
            result['shot_angle'] = generate_shot_angle('dot', 0)
        elif bowler_rating == 4 and random.random() < 0.15:
            bye_runs = 0
            result['outcome_type'] = 'dot'
            result['commentary_key'] = 'dot'
            result['shot_angle'] = generate_shot_angle('dot', 0)
        else:
            result['outcome_type'] = 'bye'
            result['extras_type'] = 'bye'
            result['extras_runs'] = bye_runs
            result['commentary_key'] = 'bye'
            result['shot_angle'] = generate_shot_angle('dot', 0)
    elif s3 == 5:
        # Wide
        result['outcome_type'] = 'wide'
        result['extras_type'] = 'wide'
        result['extras_runs'] = 1
        result['commentary_key'] = 'wide'
        result['shot_angle'] = generate_shot_angle('wide', 0)
    elif s3 == 6:
        # No-ball
        result['outcome_type'] = 'no_ball'
        result['extras_type'] = 'no_ball'
        result['extras_runs'] = 1
        result['next_is_free_hit'] = True
        result['commentary_key'] = 'no_ball'
        result['shot_angle'] = generate_shot_angle('no_ball', 0)

    return result


def generate_shot_angle(outcome_type, runs) -> float:
    """Returns shot direction in degrees (0=straight, 90=off, 270=leg). None for no shot."""

    def clamp_angle(a):
        return a % 360

    def gauss_in_range(centre, spread):
        return clamp_angle(random.gauss(centre, spread))

    if outcome_type in ('bowled', 'lbw', 'run_out'):
        return None

    if outcome_type == 'dot':
        return random.uniform(0, 360)

    if outcome_type == 'single':
        if random.random() < 0.5:
            return gauss_in_range(90, 20)   # off side
        else:
            return gauss_in_range(270, 20)  # leg side

    if outcome_type == 'two':
        if random.random() < 0.6:
            return gauss_in_range(90, 30)   # cover/off
        else:
            return gauss_in_range(10, 20)   # straight

    if outcome_type == 'three':
        if random.random() < 0.5:
            return gauss_in_range(80, 22)   # deep cover / extra cover
        else:
            return gauss_in_range(255, 20)  # deep square / midwicket

    if outcome_type == 'four':
        zone = random.randint(1, 3)
        if zone == 1:
            return gauss_in_range(90, 15)   # cover drive
        elif zone == 2:
            return gauss_in_range(105, 15)  # square cut
        else:
            return gauss_in_range(260, 15)  # pull shot

    if outcome_type == 'six':
        zone = random.randint(1, 3)
        if zone == 1:
            return gauss_in_range(350, 10)  # long-on
        elif zone == 2:
            return gauss_in_range(30, 10)   # long-off
        else:
            return gauss_in_range(265, 12)  # midwicket

    if outcome_type == 'wide':
        if random.random() < 0.5:
            return gauss_in_range(165, 10)  # fine leg region
        else:
            return gauss_in_range(195, 10)  # third man region

    if outcome_type == 'stumped':
        return gauss_in_range(0, 10)        # straight/down the ground

    # leg_bye, bye, no_ball, wicket_caught, default
    return random.uniform(0, 360)


def select_bowler(bowlers, over_number, format, last_bowler_id) -> int:
    """Select the best eligible bowler for this over."""

    over_cap = {'T20': 4, 'ODI': 10, 'Test': None}
    cap = over_cap.get(format)

    def eligible(b):
        if b['player_id'] == last_bowler_id:
            return False
        if cap is not None and b['overs_bowled'] >= cap:
            return False
        return True

    candidates = [b for b in bowlers if eligible(b)]

    if not candidates:
        # Fallback: anyone except last bowler (ignore cap)
        candidates = [b for b in bowlers if b['player_id'] != last_bowler_id]

    if not candidates:
        # Last resort: just return first bowler
        return bowlers[0]['player_id']

    # Sort: highest rating first, then fewest overs as tiebreaker
    candidates.sort(key=lambda b: (-b['bowling_rating'], b['overs_bowled']))
    return candidates[0]['player_id']


def calculate_nrr(runs_for, overs_for, runs_against, overs_against) -> float:
    if overs_for == 0:
        return -999.99
    if overs_against == 0:
        return 999.99
    nrr = (runs_for / overs_for) - (runs_against / overs_against)
    return round(nrr, 3)


def calculate_result(innings1_runs, innings1_wickets, innings2_runs, innings2_wickets,
                     format, innings2_complete, target=None) -> dict:
    """Calculate match result from innings data."""

    if target is None:
        target = innings1_runs + 1

    result = {
        'result_type': None,
        'winning_team': None,
        'margin_runs': None,
        'margin_wickets': None,
        'description': '',
    }

    if not innings2_complete:
        # Test match draw
        result['result_type'] = 'draw'
        result['description'] = 'Match drawn'
        return result

    if innings2_runs >= target:
        # Team 2 wins by wickets
        wickets_remaining = 10 - innings2_wickets
        result['result_type'] = 'wickets'
        result['winning_team'] = 2
        result['margin_wickets'] = wickets_remaining
        result['description'] = f'Team 2 won by {wickets_remaining} wicket{"s" if wickets_remaining != 1 else ""}'
    elif innings2_runs == innings1_runs and innings2_wickets == 10:
        result['result_type'] = 'tie'
        result['description'] = 'Match tied'
    else:
        # Team 1 wins by runs
        margin = innings1_runs - innings2_runs
        result['result_type'] = 'runs'
        result['winning_team'] = 1
        result['margin_runs'] = margin
        result['description'] = f'Team 1 won by {margin} run{"s" if margin != 1 else ""}'

    return result


def simulate_innings_fast(batting_players, bowling_players, format, target=None,
                          scoring_mode='modern') -> dict:
    """Simulate a complete innings using bowl_ball() in a loop."""

    over_limits = {'T20': 20, 'ODI': 50, 'Test': 999}
    max_overs = over_limits.get(format, 50)
    over_cap = {'T20': 4, 'ODI': 10, 'Test': None}
    cap = over_cap.get(format)

    # State
    total_runs = 0
    total_wickets = 0
    current_over = 0
    current_ball = 0
    is_free_hit = False

    # Batter indices
    striker_idx = 0
    non_striker_idx = 1
    next_batter_idx = 2

    # Per-batter tracking
    batter_scores = []
    for i, p in enumerate(batting_players):
        batter_scores.append({
            'player_id': p['player_id'],
            'runs': 0,
            'balls': 0,
            'fours': 0,
            'sixes': 0,
            'dismissal_type': None,
            'not_out': True,
            'batting': i < 2,  # first two are in
        })

    # Per-bowler tracking
    bowler_map = {}
    for b in bowling_players:
        bowler_map[b['player_id']] = {
            'player_id': b['player_id'],
            'bowling_type': b.get('bowling_type', 'pace'),
            'bowling_rating': b.get('bowling_rating', 3),
            'overs_bowled': 0,
            'balls_bowled': 0,
            'runs': 0,
            'wickets': 0,
            'maidens': 0,
            '_this_over_runs': 0,
        }

    fall_of_wickets = []
    extras = {'wides': 0, 'no_balls': 0, 'byes': 0, 'leg_byes': 0, 'total': 0}
    deliveries = []

    last_bowler_id = None
    current_bowler_id = None

    def overs_float():
        return current_over + (current_ball / 6)

    def pick_new_bowler():
        nonlocal current_bowler_id
        bowler_list = list(bowler_map.values())
        bid = select_bowler(bowler_list, current_over, format, last_bowler_id)
        current_bowler_id = bid

    pick_new_bowler()

    # Innings loop
    while total_wickets < 10 and current_over < max_overs:
        # Check target
        if target is not None and total_runs >= target:
            break

        # Start of over
        if current_ball == 0:
            bowler_map[current_bowler_id]['_this_over_runs'] = 0

        striker = batter_scores[striker_idx]
        bowler = bowler_map[current_bowler_id]

        batter_rating = batting_players[striker_idx].get('batting_rating', 3)
        bowler_rating = bowler['bowling_rating']
        bowling_type = bowler['bowling_type']

        ball_result = bowl_ball(batter_rating, bowler_rating, bowling_type,
                                is_free_hit, 0,
                                scoring_mode=scoring_mode, format=format)
        deliveries.append(ball_result)

        is_free_hit = ball_result['next_is_free_hit']

        # Is this a legal delivery (counts toward the over)?
        is_legal = ball_result['outcome_type'] not in ('wide', 'no_ball')

        # Tally runs
        runs_scored = ball_result['runs']
        extras_scored = ball_result['extras_runs']
        total_runs += runs_scored + extras_scored

        # Update bowler figures (all deliveries, including extras)
        bowler['runs'] += runs_scored + extras_scored
        bowler['_this_over_runs'] += runs_scored + extras_scored

        if ball_result['outcome_type'] == 'wide':
            extras['wides'] += extras_scored
            extras['total'] += extras_scored
        elif ball_result['outcome_type'] == 'no_ball':
            extras['no_balls'] += extras_scored
            extras['total'] += extras_scored
        elif ball_result['extras_type'] == 'bye':
            extras['byes'] += extras_scored
            extras['total'] += extras_scored
        elif ball_result['extras_type'] == 'leg_bye':
            extras['leg_byes'] += extras_scored
            extras['total'] += extras_scored

        if ball_result['outcome_type'] == 'wicket':
            # Record dismissal
            striker['dismissal_type'] = ball_result['dismissal_type']
            striker['not_out'] = False
            bowler['wickets'] += 1
            total_wickets += 1

            fall_of_wickets.append({
                'wicket': total_wickets,
                'score': total_runs,
                'overs': overs_float(),
                'player_id': striker['player_id'],
            })

            # New batter in
            if next_batter_idx < len(batter_scores):
                batter_scores[next_batter_idx]['batting'] = True
                striker_idx = next_batter_idx
                next_batter_idx += 1
            else:
                break  # all out

        else:
            # Update striker stats for legal deliveries
            if is_legal:
                striker['balls'] += 1
                striker['runs'] += runs_scored
                if ball_result['outcome_type'] == 'four':
                    striker['fours'] += 1
                elif ball_result['outcome_type'] == 'six':
                    striker['sixes'] += 1

            # Strike rotation
            if is_legal:
                if runs_scored % 2 == 1:
                    striker_idx, non_striker_idx = non_striker_idx, striker_idx

        if is_legal:
            current_ball += 1
            bowler['balls_bowled'] += 1

            if current_ball == 6:
                # End of over
                if bowler['_this_over_runs'] == 0:
                    bowler['maidens'] += 1
                bowler['overs_bowled'] += 1
                current_over += 1
                current_ball = 0

                # Swap striker for end of over
                striker_idx, non_striker_idx = non_striker_idx, striker_idx

                # New bowler
                last_bowler_id = current_bowler_id
                pick_new_bowler()

    # Build result
    total_overs = current_over + (current_ball / 6)

    # Only include batters who actually batted (came to the crease)
    active_batter_scores = [b for b in batter_scores if b['batting']]
    # Remove internal 'batting' key
    clean_batter_scores = []
    for b in active_batter_scores:
        clean_batter_scores.append({
            'player_id': b['player_id'],
            'runs': b['runs'],
            'balls': b['balls'],
            'fours': b['fours'],
            'sixes': b['sixes'],
            'dismissal_type': b['dismissal_type'],
            'not_out': b['not_out'],
        })

    # Build bowler figures — only bowlers who bowled at least one ball
    bowler_figures = []
    for b in bowler_map.values():
        if b['overs_bowled'] > 0 or b['balls_bowled'] > 0:
            bowler_figures.append({
                'player_id': b['player_id'],
                'overs': b['overs_bowled'],
                'balls': b['balls_bowled'] % 6,
                'runs': b['runs'],
                'wickets': b['wickets'],
                'maidens': b['maidens'],
            })

    return {
        'total_runs': total_runs,
        'total_wickets': total_wickets,
        'overs_completed': round(total_overs, 2),
        'batter_scores': clean_batter_scores,
        'bowler_figures': bowler_figures,
        'fall_of_wickets': fall_of_wickets,
        'extras': extras,
        'deliveries': deliveries,
    }


# ── Simulation Constants ───────────────────────────────────────────────────────

# Test over boundaries where sessions end (0-indexed over_number).
# Day structure: Morning 0-33 (34 ov), Afternoon 34-54 (21 ov), Evening 55-89 (35 ov).
# Maximum 5 days.
_TEST_SESSION_BOUNDARIES: list = []
for _d in range(5):
    _base = _d * 90
    _TEST_SESSION_BOUNDARIES.extend([_base + 34, _base + 55, _base + 90])

_TEST_DAY_BOUNDARIES: list = [90 * _d for _d in range(1, 6)]  # 90, 180, …, 450


def simulate_to(target: str, state: dict) -> dict:
    """
    Simulate the current innings forward from *state* until *target* is reached
    or the innings ends, whichever comes first.  Pure logic — no DB or UI calls.

    target values:
        'wicket'  — stop after next dismissal
        'over'    — stop at end of the current/next complete over
        'session' — stop at next Test session boundary; ODI/T20 runs to innings end
        'day'     — stop at end of current Test day; ODI/T20 runs to innings end
        'innings' — stop at end of innings
        'match'   — stop at end of innings (Flask caller loops for multi-innings)

    state keys (all mutable fields are updated in the returned copy):
        format, max_overs, target (run-chase), innings_number,
        over_number, ball_in_over, is_free_hit,
        total_runs, total_wickets,
        batting_players  [{player_id, name, batting_rating, runs, balls, dismissed, in}]
        striker_idx, non_striker_idx, next_batter_idx,
        bowling_players  [{player_id, name, bowling_type, bowling_rating,
                           overs_bowled, balls_bowled, runs, wickets, maidens,
                           _this_over_runs}]
        bowler_map       {player_id: <same dicts as bowling_players>}  (built if absent)
        last_bowler_id, current_bowler_id

    Returns:
        {
            'state':           updated deep-copy of state,
            'sim_digest':      {balls_bowled, runs_scored, wickets_fallen,
                                overs_completed, key_events, wicket_events,
                                start_score, end_score, result_string},
            'innings_complete': bool,
            'match_complete':   bool,
        }
    """
    import copy as _copy
    state = _copy.deepcopy(state)

    fmt           = state['format']
    max_overs     = state.get('max_overs')
    target_runs   = state.get('target')
    innings_num   = state.get('innings_number', 1)
    scoring_mode  = state.get('scoring_mode', 'modern')

    over_number   = state['over_number']
    ball_in_over  = state['ball_in_over']
    is_free_hit   = state.get('is_free_hit', False)
    total_runs    = state['total_runs']
    total_wickets = state['total_wickets']
    runs_at_100_overs = state.get('runs_at_100_overs')
    wickets_at_100_overs = state.get('wickets_at_100_overs')
    runs_at_110_overs = state.get('runs_at_110_overs')
    wickets_at_110_overs = state.get('wickets_at_110_overs')

    batting_players = state['batting_players']
    striker_idx     = state['striker_idx']
    non_striker_idx = state['non_striker_idx']
    next_batter_idx = state['next_batter_idx']

    bowling_players = state['bowling_players']
    bowler_map = state.get('bowler_map')
    if bowler_map is None:
        bowler_map = {b['player_id']: b for b in bowling_players}

    last_bowler_id    = state.get('last_bowler_id')
    current_bowler_id = state.get('current_bowler_id')

    # Pre-compute session/day stop boundary for Test
    start_over = over_number
    stop_at_over = None
    if target in ('session', 'day'):
        boundaries = _TEST_SESSION_BOUNDARIES if target == 'session' else _TEST_DAY_BOUNDARIES
        stop_at_over = next((b for b in boundaries if b > start_over), None)

    # Digest tracking
    start_runs    = total_runs
    start_wickets = total_wickets
    legal_balls   = 0
    key_events: list = []
    wicket_events: list = []

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_bowler():
        nonlocal current_bowler_id
        bl = list(bowler_map.values())
        bid = select_bowler(bl, over_number, fmt, last_bowler_id)
        current_bowler_id = bid
        bowler_map[bid]['_this_over_runs'] = 0

    if current_bowler_id is None or current_bowler_id not in bowler_map:
        _pick_bowler()

    def _innings_over() -> bool:
        if total_wickets >= 10:
            return True
        if max_overs is not None and over_number >= max_overs:
            return True
        if target_runs is not None and total_runs >= target_runs:
            return True
        return False

    def _stop_condition() -> bool:
        if target == 'wicket':
            return total_wickets > start_wickets
        if target == 'over':
            return ball_in_over == 0 and legal_balls > 0
        if target in ('session', 'day'):
            if fmt != 'Test':
                return False  # ODI/T20: run to innings end
            return stop_at_over is not None and over_number >= stop_at_over
        # 'innings' or 'match': never stop early
        return False

    # ── Main loop ─────────────────────────────────────────────────────────────

    _iterations = 0
    while not _innings_over() and _iterations < 5000:
        _iterations += 1

        if _stop_condition():
            break

        if current_bowler_id is None or current_bowler_id not in bowler_map:
            _pick_bowler()

        if striker_idx >= len(batting_players) or non_striker_idx >= len(batting_players):
            break

        striker = batting_players[striker_idx]
        bowler  = bowler_map[current_bowler_id]

        ball = bowl_ball(
            batter_rating     = striker['batting_rating'],
            bowler_rating     = bowler['bowling_rating'],
            bowling_type      = bowler['bowling_type'],
            is_free_hit       = is_free_hit,
            partnership_balls = 0,
            scoring_mode      = scoring_mode,
            format            = fmt,
        )

        is_free_hit = ball['next_is_free_hit']
        is_legal    = ball['outcome_type'] not in ('wide', 'no_ball')
        is_wicket   = ball['outcome_type'] == 'wicket'
        runs        = ball['runs']
        extras      = ball['extras_runs']
        total_added = runs + extras

        total_runs += total_added
        bowler['runs'] = bowler.get('runs', 0) + total_added
        bowler['_this_over_runs'] = bowler.get('_this_over_runs', 0) + total_added

        otype = ball['outcome_type']

        if is_wicket:
            total_wickets += 1
            striker['dismissed'] = True
            striker['in']        = False
            bowler['wickets']    = bowler.get('wickets', 0) + 1

            dism = ball.get('dismissal_type', 'out')
            wicket_events.append({
                'batter':         striker.get('name', str(striker['player_id'])),
                'runs':           striker.get('runs', 0),
                'dismissal_type': dism,
            })

            if bowler['wickets'] == 5:
                key_events.append(
                    f"FIVE-FER! {bowler.get('name', 'Bowler')} takes 5th wicket"
                )

            # New batter
            if next_batter_idx < len(batting_players):
                batting_players[next_batter_idx]['in'] = True
                striker_idx     = next_batter_idx
                next_batter_idx += 1
            else:
                total_wickets = 10
                break

        else:
            if is_legal and otype not in ('wide', 'no_ball', 'leg_bye', 'bye'):
                before = striker.get('runs', 0)
                striker['runs'] = before + runs
                for thresh, label in ((50, 'Fifty'), (100, 'Century'),
                                      (150, '150!'), (200, 'Double century!')):
                    if before < thresh <= striker['runs']:
                        key_events.append(
                            f"{label} for {striker.get('name', 'Batter')} "
                            f"({striker['runs']} runs)"
                        )
            if is_legal:
                striker['balls'] = striker.get('balls', 0) + 1
                if runs % 2 == 1:
                    striker_idx, non_striker_idx = non_striker_idx, striker_idx

        if is_legal:
            legal_balls  += 1
            ball_in_over += 1
            bowler['balls_bowled'] = bowler.get('balls_bowled', 0) + 1

            if ball_in_over == 6:
                if bowler.get('_this_over_runs', 0) == 0:
                    bowler['maidens'] = bowler.get('maidens', 0) + 1
                bowler['overs_bowled'] = bowler.get('overs_bowled', 0) + 1
                over_number  += 1
                ball_in_over  = 0
                bowler['_this_over_runs'] = 0

                if over_number == 100 and runs_at_100_overs is None:
                    runs_at_100_overs = total_runs
                    wickets_at_100_overs = total_wickets
                if over_number == 110 and runs_at_110_overs is None:
                    runs_at_110_overs = total_runs
                    wickets_at_110_overs = total_wickets

                # End-of-over: swap ends
                striker_idx, non_striker_idx = non_striker_idx, striker_idx

                last_bowler_id    = current_bowler_id
                current_bowler_id = None
                _pick_bowler()

    # ── Post-loop ─────────────────────────────────────────────────────────────

    innings_complete = _innings_over()

    # Last-wicket event note
    if total_wickets == 9 and not innings_complete:
        key_events.append('Last-wicket stand — the tail is fighting hard!')

    key_events = key_events[:5]

    # Determine match completion for limited-overs 2nd innings
    match_complete = False
    result_string  = None

    if innings_complete and fmt in ('ODI', 'T20') and innings_num == 2:
        match_complete = True
        if target_runs is not None:
            if total_runs >= target_runs:
                w_left = 10 - total_wickets
                result_string = (
                    f'Chasing team won by {w_left} wicket{"s" if w_left != 1 else ""}'
                )
            else:
                margin = (target_runs - 1) - total_runs
                result_string = (
                    f'Defending team won by {margin} run{"s" if margin != 1 else ""}'
                )
        else:
            result_string = 'Innings complete'

    # Write updated fields back into state
    state.update({
        'over_number':       over_number,
        'ball_in_over':      ball_in_over,
        'is_free_hit':       is_free_hit,
        'total_runs':        total_runs,
        'total_wickets':     total_wickets,
        'runs_at_100_overs': runs_at_100_overs,
        'wickets_at_100_overs': wickets_at_100_overs,
        'runs_at_110_overs': runs_at_110_overs,
        'wickets_at_110_overs': wickets_at_110_overs,
        'striker_idx':       striker_idx,
        'non_striker_idx':   non_striker_idx,
        'next_batter_idx':   next_batter_idx,
        'batting_players':   batting_players,
        'bowler_map':        bowler_map,
        'last_bowler_id':    last_bowler_id,
        'current_bowler_id': current_bowler_id,
    })

    return {
        'state': state,
        'sim_digest': {
            'balls_bowled':    legal_balls,
            'runs_scored':     total_runs    - start_runs,
            'wickets_fallen':  total_wickets - start_wickets,
            'overs_completed': over_number   - start_over,
            'key_events':      key_events,
            'wicket_events':   wicket_events,
            'start_score':     f'{start_runs}/{start_wickets}',
            'end_score':       f'{total_runs}/{total_wickets}',
            'result_string':   result_string,
        },
        'innings_complete': innings_complete,
        'match_complete':   match_complete,
    }


# ── World Mode: Quick Match Simulation ────────────────────────────────────────
# These functions are ENTIRELY SEPARATE from the ball-by-ball dice engine.
# No bowl_ball() calls. No delivery objects. Stats-based only.

def _team_effective_rating(team_data, player_states):
    """Return (avg_batting, avg_bowling) accounting for form and fatigue."""
    players = team_data.get('players', [])
    if not players:
        return 3.0, 3.0
    bat_total = 0.0
    bowl_total = 0.0
    for p in players:
        pid = p['id']
        state = player_states.get(pid, {})
        form = state.get('form_adjustment', 0)
        fatigue_pen = -0.5 if state.get('fatigue') else 0.0
        bat_total += max(1.0, min(5.0, p.get('batting_rating', 3) + form + fatigue_pen))
        bowl_total += max(0.0, min(5.0, p.get('bowling_rating', 3) + form + fatigue_pen))
    n = len(players)
    return bat_total / n, bowl_total / n


def _quick_innings_score(fmt, avg_batting, avg_bowling):
    """Generate a plausible innings total without simulating balls."""
    bases   = {'T20': 148, 'ODI': 255, 'Test': 310}
    spreads = {'T20':  28, 'ODI':  40, 'Test':  65}
    base   = bases.get(fmt, 200)
    spread = spreads.get(fmt, 40)
    adj    = (avg_batting - avg_bowling) * 8.0
    runs   = max(60, int(base + adj + random.gauss(0, spread)))
    if fmt == 'T20':
        wickets   = random.randint(3, 10)
        overs_str = '(20)'
    elif fmt == 'ODI':
        wickets   = random.randint(4, 10)
        overs_str = '(50)'
    else:
        wickets   = 10
        overs_str = ''
    return runs, wickets, overs_str


def _pick_top_performer(players, player_states, perf_type, fmt):
    """Pick and stat a top batter or bowler, weighted by rating + form."""
    eligible = [p for p in players if p.get(f'{perf_type}_rating', 0) > 0]
    if not eligible:
        eligible = players
    if not eligible:
        return None

    weights = []
    for p in eligible:
        r    = p.get(f'{perf_type}_rating', 3)
        form = player_states.get(p['id'], {}).get('form_adjustment', 0)
        weights.append(max(0.1, r + form))

    total_w = sum(weights)
    roll    = random.random() * total_w
    chosen  = eligible[-1]
    for p, w in zip(eligible, weights):
        roll -= w
        if roll <= 0:
            chosen = p
            break

    r    = chosen.get(f'{perf_type}_rating', 3)
    form = player_states.get(chosen['id'], {}).get('form_adjustment', 0)

    if perf_type == 'batting':
        base = {1: 12, 2: 22, 3: 38, 4: 60, 5: 88}.get(r, 38)
        if fmt == 'T20':
            base = int(base * 0.65)
        elif fmt == 'ODI':
            base = int(base * 0.85)
        stat = max(0, int(base + random.gauss(0, 10) + form * 5))
        return {'player_id': chosen['id'], 'name': chosen.get('name', ''),
                'runs': stat, 'team_id': chosen.get('team_id')}
    else:
        base = min(5, max(0, r - 1))
        stat = max(0, min(7, int(base + random.gauss(0, 1) + form)))
        return {'player_id': chosen['id'], 'name': chosen.get('name', ''),
                'wickets': stat, 'team_id': chosen.get('team_id')}


def quick_sim_match(fixture, world_state):
    """
    Fast stats-based match simulation for World Mode.
    ENTIRELY SEPARATE from bowl_ball() / the dice engine.
    Completes in <50ms per match.

    fixture    : {team1_id, team2_id, format, venue_id, ...}
    world_state: {teams: {tid: {name, home_venue_id, players:[...]}},
                  player_states: {pid: {form_adjustment, fatigue, ...}}}
    Returns    : {winner_id, loser_id, result_type, margin_runs, margin_wickets,
                  team1_score, team2_score, top_scorer, top_bowler, summary,
                  home_team_id}
    """
    fmt      = fixture.get('format', 'T20')
    team1_id = fixture['team1_id']
    team2_id = fixture['team2_id']
    venue_id = fixture.get('venue_id')

    teams         = world_state.get('teams', {})
    player_states = world_state.get('player_states', {})

    t1 = teams.get(team1_id, {'players': [], 'name': f'Team {team1_id}'})
    t2 = teams.get(team2_id, {'players': [], 'name': f'Team {team2_id}'})

    t1_bat, t1_bowl = _team_effective_rating(t1, player_states)
    t2_bat, t2_bowl = _team_effective_rating(t2, player_states)

    # Home advantage
    home_team_id = None
    if venue_id:
        if t1.get('home_venue_id') == venue_id:
            home_team_id = team1_id
            t1_bat += 0.3; t1_bowl += 0.3
        elif t2.get('home_venue_id') == venue_id:
            home_team_id = team2_id
            t2_bat += 0.3; t2_bowl += 0.3

    # Win probability: each side's attack = own batting + opponent's bowling weakness
    t1_attack = t1_bat + (5.0 - t2_bowl)
    t2_attack = t2_bat + (5.0 - t1_bowl)
    total     = max(0.01, t1_attack + t2_attack)
    t1_win_p  = t1_attack / total

    draw_prob = 0.22 if fmt == 'Test' else 0.0
    roll      = random.random()

    if fmt == 'Test' and roll < draw_prob:
        result_type = 'draw'
        winner_id   = None
        loser_id    = None
    elif roll < draw_prob + t1_win_p * (1.0 - draw_prob):
        winner_id   = team1_id
        loser_id    = team2_id
        result_type = random.choice(['runs', 'wickets']) if fmt != 'Test' else 'runs'
    else:
        winner_id   = team2_id
        loser_id    = team1_id
        result_type = random.choice(['runs', 'wickets']) if fmt != 'Test' else 'runs'

    # Generate raw innings scores
    t1_runs, t1_wkts, t1_overs = _quick_innings_score(fmt, t1_bat, t2_bowl)
    t2_runs, t2_wkts, t2_overs = _quick_innings_score(fmt, t2_bat, t1_bowl)

    margin_runs    = None
    margin_wickets = None

    if result_type == 'draw':
        pass
    elif winner_id == team1_id:
        if result_type == 'runs':
            margin_runs = random.randint(8, 80)
            t1_runs     = max(t2_runs + margin_runs, t1_runs)
        else:
            margin_wickets = random.randint(1, 8)
            t1_wkts        = 10 - margin_wickets
            t1_runs        = t2_runs + random.randint(1, 30)
    else:
        if result_type == 'runs':
            margin_runs = random.randint(8, 80)
            t2_runs     = max(t1_runs + margin_runs, t2_runs)
        else:
            margin_wickets = random.randint(1, 8)
            t2_wkts        = 10 - margin_wickets
            t2_runs        = t1_runs + random.randint(1, 30)

    t1_score = f"{t1_runs}/{t1_wkts} {t1_overs}".strip()
    t2_score = f"{t2_runs}/{t2_wkts} {t2_overs}".strip()

    # Top performers
    if winner_id:
        w_team  = t1 if winner_id == team1_id else t2
        l_team  = t2 if winner_id == team1_id else t1
        top_scorer = _pick_top_performer(w_team.get('players', []), player_states, 'batting', fmt)
        top_bowler = _pick_top_performer(l_team.get('players', []), player_states, 'bowling', fmt)
    else:
        all_p      = t1.get('players', []) + t2.get('players', [])
        top_scorer = _pick_top_performer(all_p, player_states, 'batting', fmt)
        top_bowler = _pick_top_performer(all_p, player_states, 'bowling', fmt)

    t1_name    = t1.get('name', f'Team {team1_id}')
    t2_name    = t2.get('name', f'Team {team2_id}')
    w_name     = t1_name if winner_id == team1_id else t2_name

    if result_type == 'draw':
        summary = f'Match drawn — {t1_name} {t1_runs} v {t2_name} {t2_runs}'
    elif result_type == 'runs':
        summary = f'{w_name} won by {margin_runs} run{"s" if margin_runs != 1 else ""}'
    else:
        summary = f'{w_name} won by {margin_wickets} wicket{"s" if margin_wickets != 1 else ""}'

    return {
        'winner_id':      winner_id,
        'loser_id':       loser_id,
        'result_type':    result_type,
        'margin_runs':    margin_runs,
        'margin_wickets': margin_wickets,
        'team1_score':    t1_score,
        'team2_score':    t2_score,
        'top_scorer':     top_scorer,
        'top_bowler':     top_bowler,
        'summary':        summary,
        'home_team_id':   home_team_id,
    }


def _update_world_state_form(world_state, fixture, match_result):
    """Update player form/fatigue in world_state (in-memory) after a quick sim match."""
    player_states = world_state.setdefault('player_states', {})
    teams         = world_state.get('teams', {})
    match_date    = fixture.get('scheduled_date', '')

    top_scorer = match_result.get('top_scorer') or {}
    top_bowler = match_result.get('top_bowler') or {}

    for team_data in teams.values():
        for p in team_data.get('players', []):
            pid   = p['id']
            state = player_states.setdefault(pid, {
                'form_adjustment': 0, 'fatigue': False,
                'career_runs': 0, 'career_wickets': 0,
                'career_matches': 0, 'last_match_dates': [],
            })
            state['career_matches'] = state.get('career_matches', 0) + 1

            if pid == top_scorer.get('player_id'):
                state['career_runs']    = state.get('career_runs', 0) + top_scorer.get('runs', 0)
                state['form_adjustment'] = min(1, state.get('form_adjustment', 0) + 1)
            if pid == top_bowler.get('player_id'):
                state['career_wickets'] = state.get('career_wickets', 0) + top_bowler.get('wickets', 0)
                state['form_adjustment'] = min(1, state.get('form_adjustment', 0) + 1)

            if match_date:
                dates = state.get('last_match_dates', [])
                if not isinstance(dates, list):
                    dates = []
                dates.append(match_date)
                dates = sorted(dates)[-10:]
                state['last_match_dates'] = dates
                if len(dates) >= 3:
                    try:
                        from datetime import date as _date
                        d_new = _date.fromisoformat(dates[-1])
                        d_old = _date.fromisoformat(dates[-3])
                        state['fatigue'] = (d_new - d_old).days <= 7
                    except (ValueError, IndexError):
                        state['fatigue'] = False


def simulate_world_to(target, fixtures, world_state):
    """
    Simulate world mode calendar to the given target.
    Uses quick_sim_match() — NEVER the ball-by-ball dice engine.

    target     : 'next_match' | 'end_of_series' | 'date' | 'next_my_match'
    fixtures   : list of fixture dicts sorted by scheduled_date
    world_state: {my_team_id, current_date, target_date (for 'date'),
                  teams, player_states}

    Returns: {results, new_current_date, paused_at_fixture,
              matches_simulated, updated_player_states, truncated}
    """
    user_team_ids = set(world_state.get('user_team_ids') or [])
    if not user_team_ids and world_state.get('my_team_id'):
        user_team_ids.add(world_state.get('my_team_id'))
    if not user_team_ids and world_state.get('my_domestic_team_id'):
        user_team_ids.add(world_state.get('my_domestic_team_id'))
    target_date  = world_state.get('target_date')
    current_date = world_state.get('current_date', '')

    if target == 'next_my_match' and not user_team_ids:
        return {
            'results': [],
            'new_current_date': current_date,
            'paused_at_fixture': None,
            'matches_simulated': 0,
            'updated_player_states': world_state.get('player_states', {}),
            'truncated': False,
        }

    results    = []
    paused_at  = None
    truncated  = False

    # For 'end_of_series': find series_id of first upcoming fixture
    first_series_id = None
    if target == 'end_of_series':
        for fx in fixtures:
            if fx.get('status', 'scheduled') == 'scheduled':
                first_series_id = fx.get('series_id')
                break

    for fixture in fixtures:
        if fixture.get('status', 'scheduled') != 'scheduled':
            continue

        f_date = fixture.get('scheduled_date', '')

        if target == 'date' and target_date and f_date > target_date:
            break

        if fixture.get('is_user_match'):
            paused_at = fixture
            break

        if target == 'next_my_match' and user_team_ids:
            if fixture.get('team1_id') in user_team_ids or fixture.get('team2_id') in user_team_ids:
                paused_at = fixture
                break

        if target == 'end_of_series' and first_series_id is not None:
            if fixture.get('series_id') != first_series_id:
                break

        result = quick_sim_match(fixture, world_state)
        result['fixture_id']    = fixture.get('id')
        result['scheduled_date'] = f_date
        result['format']        = fixture.get('format', 'T20')
        result['team1_id']      = fixture.get('team1_id')
        result['team2_id']      = fixture.get('team2_id')
        result['series_id']     = fixture.get('series_id')
        result['world_id']      = fixture.get('world_id')
        results.append(result)

        _update_world_state_form(world_state, fixture, result)

        if f_date:
            current_date = f_date

        if target == 'next_match':
            break

    return {
        'results':                results,
        'new_current_date':       current_date,
        'paused_at_fixture':      paused_at,
        'matches_simulated':      len(results),
        'updated_player_states':  world_state.get('player_states', {}),
        'truncated':              truncated,
    }


def generate_fixture_calendar(team_ids, start_date_str, density, months=12) -> list:
    """Generate a fixture list for all team pairs over the given period."""

    gap_days = {'busy': 2, 'moderate': 4, 'relaxed': 7}.get(density, 4)

    start = date.fromisoformat(start_date_str)
    # Calculate end date
    end_month = start.month + months
    end_year = start.year + (end_month - 1) // 12
    end_month = ((end_month - 1) % 12) + 1
    end = date(end_year, end_month, 1)

    pairs = list(combinations(team_ids, 2))
    random.shuffle(pairs)

    fixtures = []
    current_date = start

    for t1, t2 in pairs:
        if current_date >= end:
            break

        # Test series: 2-3 matches
        n_tests = random.randint(2, 3)
        for i in range(n_tests):
            if current_date >= end:
                break
            fixtures.append({
                'team1_id': t1,
                'team2_id': t2,
                'scheduled_date': current_date.isoformat(),
                'format': 'Test',
                'series_name': f'Test Series',
                'suggested_venue_id': None,
            })
            current_date += timedelta(days=gap_days + 4)  # Tests take longer

        # ODI series: 3 matches
        for i in range(3):
            if current_date >= end:
                break
            fixtures.append({
                'team1_id': t1,
                'team2_id': t2,
                'scheduled_date': current_date.isoformat(),
                'format': 'ODI',
                'series_name': f'ODI Series',
                'suggested_venue_id': None,
            })
            current_date += timedelta(days=gap_days)

        # T20 series: 3 matches
        for i in range(3):
            if current_date >= end:
                break
            fixtures.append({
                'team1_id': t1,
                'team2_id': t2,
                'scheduled_date': current_date.isoformat(),
                'format': 'T20',
                'series_name': f'T20 Series',
                'suggested_venue_id': None,
            })
            current_date += timedelta(days=gap_days)

        # Gap between series
        current_date += timedelta(days=gap_days * 2)

    return fixtures


def update_rankings(current_rankings, match_result, home_team_id=None) -> dict:
    """Update team rankings based on match result."""

    rankings = dict(current_rankings)

    is_draw = match_result.get('is_draw', False)
    winning_team_id = match_result.get('winning_team_id')
    losing_team_id = match_result.get('losing_team_id')
    team1_id = match_result.get('team1_id')
    team2_id = match_result.get('team2_id')

    # Ensure both teams exist in rankings
    for tid in [team1_id, team2_id]:
        if tid and tid not in rankings:
            rankings[tid] = 0

    if is_draw:
        for tid in [team1_id, team2_id]:
            if tid:
                rankings[tid] = max(0, rankings.get(tid, 0) + 3)
    elif winning_team_id and losing_team_id:
        win_away = (winning_team_id != home_team_id) if home_team_id else False
        win_points = 10 if win_away else 7
        loss_points = 5 if win_away else 4

        rankings[winning_team_id] = max(0, rankings.get(winning_team_id, 0) + win_points)
        rankings[losing_team_id] = max(0, rankings.get(losing_team_id, 0) - loss_points)

    return rankings


JOURNAL_PROMPTS = [
    "Was there a turning point? What was it?",
    "Who was the unsung hero?",
    "What would have changed if the toss had gone the other way?",
    "Describe the match in one sentence.",
    "Any records threatened or broken?",
    "Which bowler surprised you most?",
    "Was the result a fair reflection of the play?",
    "Did anyone play beyond their rating today?",
    "If you were the captain, what would you have done differently?",
    "Which over was the most decisive?",
    "Was there a dropped catch or missed stumping that proved costly?",
    "How did the pitch play — did it deteriorate as the match went on?",
    "Who would you pick as the bowler of the match, and why?",
    "Was there a moment when you thought the match was won — and were you wrong?",
    "How good was the powerplay/opening session for each side?",
    "Did the batting order look right? Would you have changed it?",
    "How important was the partnership that made the difference?",
    "Was there a tactical masterclass from either captain?",
    "What one delivery changed everything?",
    "How did the lower order perform? Did they exceed or disappoint expectations?",
    "What would the losing side's captain say at the post-match press conference?",
    "Was there a player who failed to deliver on their rating today?",
    "Rate the match out of 10 and explain your score.",
    "How would this match be remembered in ten years?",
    "If this match had a title, what would it be?",
    "Was the winning margin flattering or harsh?",
    "Which partnership looked most dangerous at the crease?",
    "Did the pace or spin bowling dominate today?",
    "If you had to replay one over, which would it be?",
    "Was the DLS method needed? Would the result have been different without a weather interruption?",
    "How did the fielding affect the outcome?",
    "Describe the atmosphere in one word.",
    "Was there a moment of genuine individual brilliance?",
    "Did the team with the better individual ratings win?",
    "What would the scorecard look like if the match had gone an extra 5 overs?",
    "Was there a bowler who bowled beautifully without luck?",
    "How did nerves affect the run chase?",
    "Was the declaration — or lack of one — the right call?",
    "Which player would you want on your side in a tense run chase?",
    "Did the format suit the teams involved?",
    "Was there a maiden over that felt like three wickets?",
    "How would the opposition team's fans describe this match?",
    "Was there a comeback that almost worked?",
    "What single change to the batting order might have swung the result?",
    "If the coin had fallen differently, do you think the outcome would have changed?",
    "Name the three biggest moments of the match.",
    "Was there a retirement or injury that changed the course of play?",
    "What's the one stat from this match that tells the whole story?",
    "Would you want a rematch? What would you do differently?",
    "Write the headline a newspaper would use for this match.",
]


def generate_commentary(key, context, recency_buffer) -> str:
    """Select a commentary line, avoiding recent repeats, and interpolate context."""

    templates = COMMENTARY.get(key, COMMENTARY.get('dot', ['Good ball.']))

    # Filter out recently used templates
    available = [t for t in templates if t not in recency_buffer]
    if not available:
        available = templates  # reset if all have been used

    chosen = random.choice(available)

    # Update buffer
    recency_buffer.append(chosen)
    if len(recency_buffer) > 5:
        recency_buffer.pop(0)

    # Safe interpolation — missing keys become empty string
    class SafeDict(dict):
        def __missing__(self, key):
            return ''

    try:
        return chosen.format_map(SafeDict(context))
    except Exception:
        return chosen
