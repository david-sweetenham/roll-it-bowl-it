'use strict';

/* ============================================================
   canvas.js — Section 8 visualisations for Roll It & Bowl It
   ============================================================ */

// ── Internal helpers ──────────────────────────────────────────────────────────

function _canvas(id) {
  const el = document.getElementById(id);
  return el ? { el, ctx: el.getContext('2d') } : null;
}

function _fillBg(ctx, w, h, col = '#0a1628') {
  ctx.fillStyle = col;
  ctx.fillRect(0, 0, w, h);
}

// ── Wagon Wheel ───────────────────────────────────────────────────────────────

/**
 * drawWagonWheel(canvasId, deliveries, batterId=null)
 * 400×400. Centre = batting crease. Lines radiate per shot_angle.
 * 0=straight (up), 90=square leg (left), 270=cover (right).
 */
function drawWagonWheel(canvasId, deliveries, batterId = null) {
  const c = _canvas(canvasId);
  if (!c) return;
  const { el: canvas, ctx } = c;

  const W = 400, H = 400;
  canvas.width  = W;
  canvas.height = H;
  const cx = W / 2, cy = H / 2;
  const R         = W / 2 - 14;
  const boundaryR = Math.round(R * 0.91);   // 85% of half-width ≈ 170
  const circleR   = Math.round(R * 0.585);  // 55% ≈ 110

  // Field background
  _fillBg(ctx, W, H, '#0b1e0b');
  ctx.beginPath();
  ctx.arc(cx, cy, boundaryR, 0, Math.PI * 2);
  ctx.fillStyle = '#0d240d';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, circleR, 0, Math.PI * 2);
  ctx.fillStyle = '#102810';
  ctx.fill();

  // Boundary circle
  ctx.beginPath();
  ctx.arc(cx, cy, boundaryR, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.32)';
  ctx.lineWidth = 2;
  ctx.stroke();

  // 30-yard dashed circle
  ctx.save();
  ctx.setLineDash([6, 5]);
  ctx.beginPath();
  ctx.arc(cx, cy, circleR, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.restore();

  // Pitch strip
  ctx.fillStyle = 'rgba(190,155,80,0.20)';
  ctx.fillRect(cx - 7, cy - 75, 14, 150);

  // Direction guide lines
  for (let a = 0; a < 360; a += 45) {
    const rad = (a - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(rad) * boundaryR, cy + Math.sin(rad) * boundaryR);
    ctx.strokeStyle = 'rgba(255,255,255,0.055)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Filter by batter
  let draws = deliveries;
  if (batterId != null) {
    const bid = parseInt(batterId, 10);
    draws = deliveries.filter(d => d.striker_id === bid);
  }

  // Colour map
  const COL = {
    dot:    'rgba(255,255,255,0.30)',
    single: 'rgba(100,200,255,0.60)',
    two:    'rgba(100,200,255,0.80)',
    three:  'rgba(255,200,100,0.80)',
    four:   'rgba(100,255,100,1.00)',
    six:    'rgba(255,215,0,1.00)',
    wicket: 'rgba(255,60,60,0.90)',
  };
  const LEN = {
    dot:    22, single: 42, two: 62, three: 74,
    four:   boundaryR,
    six:    boundaryR + 26,
  };

  // Draw each shot
  for (const d of draws) {
    if (d.shot_angle == null) continue;
    const ot = d.outcome_type;
    if (!COL[ot]) continue;          // skip wides/no-balls/byes

    const rad = d.shot_angle * Math.PI / 180;
    // cricket angle convention: 0=up, 90=left, 270=right
    const dx  = -Math.sin(rad);
    const dy  = -Math.cos(rad);
    const len = LEN[ot] ?? 35;

    const ex = cx + dx * len;
    const ey = cy + dy * len;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ex, ey);
    ctx.strokeStyle = COL[ot];
    ctx.lineWidth   = (ot === 'four' || ot === 'six' || ot === 'wicket') ? 2.5 : 1.5;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(ex, ey, ot === 'wicket' ? 5 : 3, 0, Math.PI * 2);
    ctx.fillStyle = COL[ot];
    ctx.fill();
  }

  // Crease dot
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.fill();

  // Legend bar
  const legend = [
    [COL.four,   '4'],
    [COL.six,    '6'],
    [COL.single, '1-3'],
    [COL.wicket, 'W'],
    [COL.dot,    '.'],
  ];
  let lx = 8;
  ctx.font = '10px monospace';
  for (const [col, label] of legend) {
    ctx.fillStyle = col;
    ctx.fillRect(lx, H - 16, 10, 10);
    ctx.fillStyle = 'rgba(255,255,255,0.55)';
    ctx.textAlign = 'left';
    ctx.fillText(label, lx + 13, H - 7);
    lx += 38;
  }

  // Title
  ctx.fillStyle = 'rgba(255,255,255,0.25)';
  ctx.font = '10px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('WAGON WHEEL', cx, 14);
}

// ── Over Grid ─────────────────────────────────────────────────────────────────

/**
 * drawOverGrid(canvasId, deliveries)
 * 36×36 cells, 3px gap, 6 per row (+ extras if any). Auto height.
 */
function drawOverGrid(canvasId, deliveries) {
  const c = _canvas(canvasId);
  if (!c) return;
  const { el: canvas, ctx } = c;

  const CELL = 36, GAP = 3;
  const CW   = CELL + GAP;
  const LPAD = 30, RPAD = 46;
  const HDR  = 18;

  // Group by over
  const overMap = new Map();
  for (const d of deliveries) {
    const ov = d.over_number ?? 0;
    if (!overMap.has(ov)) overMap.set(ov, []);
    overMap.get(ov).push(d);
  }

  if (!overMap.size) {
    canvas.width = 320; canvas.height = 48;
    _fillBg(ctx, 320, 48);
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    ctx.font = '13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No deliveries yet', 160, 30);
    return;
  }

  // Max balls in any one over (cap at 9 for wide/no-ball heavy overs)
  let maxCols = 6;
  for (const balls of overMap.values()) maxCols = Math.max(maxCols, balls.length);
  maxCols = Math.min(maxCols, 9);

  const overNums = [...overMap.keys()].sort((a, b) => a - b);
  const W = LPAD + maxCols * CW + RPAD;
  const H = HDR  + overNums.length * CW + GAP;

  canvas.width  = W;
  canvas.height = H;
  _fillBg(ctx, W, H);

  // Column header numbers
  ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.font = '10px monospace';
  ctx.textAlign = 'center';
  for (let i = 0; i < maxCols; i++) {
    ctx.fillText(String(i + 1), LPAD + i * CW + CELL / 2, 13);
  }
  ctx.textAlign = 'left';
  ctx.fillText('OV', 2, 13);
  ctx.fillText('TOT', LPAD + maxCols * CW + 3, 13);

  const BG = {
    dot:    '#1a2a3a', single: '#1a4a2a', two:    '#1a6a3a',
    three:  '#2a8a4a', four:   '#00cc44', six:    '#ffd700',
    wide:   '#445566', no_ball:'#664433', wicket: '#cc2222',
    bye:    '#334455', leg_bye:'#334455',
  };

  const label = d => {
    const ot = d.outcome_type;
    if (ot === 'dot')     return '.';
    if (ot === 'wicket')  return 'W';
    if (ot === 'wide')    return 'Wd';
    if (ot === 'no_ball') return 'NB';
    const r = (d.runs_scored || 0) + (d.extras_runs || 0);
    return r > 0 ? String(r) : '.';
  };

  for (let ri = 0; ri < overNums.length; ri++) {
    const ov    = overNums[ri];
    const balls = overMap.get(ov);
    const rowY  = HDR + ri * CW;
    let overRuns = 0;

    // Over label
    ctx.fillStyle = 'rgba(255,255,255,0.42)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(String(ov + 1), LPAD - 4, rowY + CELL / 2 + 4);

    const shown = Math.min(balls.length, maxCols);
    for (let ci = 0; ci < shown; ci++) {
      const d  = balls[ci];
      const x  = LPAD + ci * CW;
      const y  = rowY;
      const bg = BG[d.outcome_type] ?? '#1a2a3a';
      const lb = label(d);

      ctx.fillStyle = bg;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, y, CELL, CELL, 3);
      else                ctx.rect(x, y, CELL, CELL);
      ctx.fill();

      const dark = d.outcome_type === 'four' || d.outcome_type === 'six';
      ctx.fillStyle  = dark ? '#000' : '#fff';
      ctx.font       = lb.length > 1 ? 'bold 9px monospace' : 'bold 13px monospace';
      ctx.textAlign  = 'center';
      ctx.fillText(lb, x + CELL / 2, y + CELL / 2 + (lb.length > 1 ? 3 : 5));

      overRuns += (d.runs_scored || 0) + (d.extras_runs || 0);
    }

    // Row total
    ctx.fillStyle = 'rgba(255,255,255,0.58)';
    ctx.font      = 'bold 11px monospace';
    ctx.textAlign = 'left';
    ctx.fillText(String(overRuns), LPAD + maxCols * CW + 4, rowY + CELL / 2 + 4);
  }
}

// ── Manhattan Chart ───────────────────────────────────────────────────────────

/**
 * drawManhattan(canvasId, inn1Deliveries, inn2Deliveries)
 * Fills container width, 300px height. Bars per over, two innings side-by-side.
 */
function drawManhattan(canvasId, inn1Deliveries, inn2Deliveries) {
  const c = _canvas(canvasId);
  if (!c) return;
  const { el: canvas, ctx } = c;

  const H = 300;
  const W = canvas.parentElement ? Math.max(canvas.parentElement.clientWidth || 400, 300) : 600;
  canvas.width  = W;
  canvas.height = H;

  const MAR = { top: 22, right: 20, bottom: 44, left: 38 };
  const cW  = W - MAR.left - MAR.right;
  const cH  = H - MAR.top  - MAR.bottom;

  _fillBg(ctx, W, H);

  const buildData = (deliveries) => {
    const m = {};
    for (const d of deliveries) {
      const ov = d.over_number ?? 0;
      if (!m[ov]) m[ov] = { runs: 0, wickets: 0 };
      m[ov].runs += (d.runs_scored || 0) + (d.extras_runs || 0);
      if (d.outcome_type === 'wicket') m[ov].wickets++;
    }
    return m;
  };

  const d1 = buildData(inn1Deliveries);
  const d2 = buildData(inn2Deliveries);

  const allOvers = new Set([...Object.keys(d1), ...Object.keys(d2)].map(Number));
  if (!allOvers.size) {
    _noData(ctx, W, H);
    return;
  }

  const maxOv  = Math.max(...allOvers) + 1;
  const maxRaw = Math.max(...[...allOvers].flatMap(ov =>
    [(d1[ov]?.runs ?? 0), (d2[ov]?.runs ?? 0)]
  ), 5);
  const maxY   = Math.ceil((maxRaw + 2) / 5) * 5;

  const xOf  = ov => MAR.left + (ov / maxOv) * cW;
  const yOf  = r  => MAR.top  + cH - (Math.min(r, maxY) / maxY) * cH;
  const slotW = Math.max(3, (cW / maxOv) * 0.88);
  const barW  = Math.max(1, slotW / 2 - 1);

  // Grid
  for (let y = 0; y <= maxY; y += 5) {
    const py = yOf(y);
    ctx.beginPath();
    ctx.moveTo(MAR.left, py);
    ctx.lineTo(MAR.left + cW, py);
    ctx.strokeStyle = 'rgba(255,255,255,0.07)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.32)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(String(y), MAR.left - 4, py + 3);
  }

  // Bars
  for (let ov = 0; ov < maxOv; ov++) {
    const x0 = xOf(ov);

    // Inn 1 — blue
    const r1 = d1[ov]?.runs ?? 0;
    if (r1 > 0) {
      ctx.fillStyle = '#2255cc';
      ctx.fillRect(x0, yOf(r1), barW, yOf(0) - yOf(r1));
    }
    if (d1[ov]?.wickets) {
      ctx.fillStyle = '#ff9999';
      ctx.font = 'bold 8px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('W', x0 + barW / 2, yOf(r1) - 2);
    }

    // Inn 2 — orange
    const r2 = d2[ov]?.runs ?? 0;
    if (r2 > 0) {
      ctx.fillStyle = '#cc5522';
      ctx.fillRect(x0 + barW + 1, yOf(r2), barW, yOf(0) - yOf(r2));
    }
    if (d2[ov]?.wickets) {
      ctx.fillStyle = '#ffbbaa';
      ctx.font = 'bold 8px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('W', x0 + barW * 1.5 + 1, yOf(r2) - 2);
    }

    // X-axis label every 5 overs
    if (ov % 5 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.38)';
      ctx.font = '9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String(ov + 1), x0, H - MAR.bottom + 14);
    }
  }

  // Axes
  ctx.beginPath();
  ctx.moveTo(MAR.left, MAR.top);
  ctx.lineTo(MAR.left, MAR.top + cH + 1);
  ctx.lineTo(MAR.left + cW, MAR.top + cH + 1);
  ctx.strokeStyle = 'rgba(255,255,255,0.22)';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Title
  ctx.fillStyle = 'rgba(255,255,255,0.32)';
  ctx.font = '10px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('MANHATTAN', W / 2, 14);

  // Legend
  const ly = H - MAR.bottom + 26;
  ctx.fillStyle = '#2255cc';
  ctx.fillRect(MAR.left, ly - 8, 12, 10);
  ctx.fillStyle = '#cc5522';
  ctx.fillRect(MAR.left + 68, ly - 8, 12, 10);
  ctx.fillStyle = 'rgba(255,255,255,0.52)';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('1st innings', MAR.left + 16, ly);
  ctx.fillText('2nd innings', MAR.left + 84, ly);
}

// ── Run Rate Graph ────────────────────────────────────────────────────────────

/**
 * drawRunRateGraph(canvasId, deliveries, target=null)
 * Fills container width, 200px height. Per-over RR + running avg; required RR if target.
 */
function drawRunRateGraph(canvasId, deliveries, target = null) {
  const c = _canvas(canvasId);
  if (!c) return;
  const { el: canvas, ctx } = c;

  const H = 200;
  const W = canvas.parentElement ? Math.max(canvas.parentElement.clientWidth || 400, 300) : 600;
  canvas.width  = W;
  canvas.height = H;

  const MAR = { top: 24, right: 20, bottom: 34, left: 36 };
  const cW  = W - MAR.left - MAR.right;
  const cH  = H - MAR.top  - MAR.bottom;
  const MAX_RR = 12;

  _fillBg(ctx, W, H);

  if (!deliveries.length) { _noData(ctx, W, H); return; }

  // Aggregate per over
  const overRuns = {};
  let maxOv = 1;
  for (const d of deliveries) {
    const ov = d.over_number ?? 0;
    if (!overRuns[ov]) overRuns[ov] = 0;
    overRuns[ov] += (d.runs_scored || 0) + (d.extras_runs || 0);
    if (ov + 1 > maxOv) maxOv = ov + 1;
  }

  const xOf  = ov => MAR.left + ((ov + 0.5) / maxOv) * cW;
  const yOf  = rr => MAR.top  + cH - (Math.min(Math.max(rr, 0), MAX_RR) / MAX_RR) * cH;

  // Grid
  for (let rr = 0; rr <= MAX_RR; rr += 3) {
    const py = yOf(rr);
    ctx.beginPath();
    ctx.moveTo(MAR.left, py);
    ctx.lineTo(MAR.left + cW, py);
    ctx.strokeStyle = 'rgba(255,255,255,0.07)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.32)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(String(rr), MAR.left - 4, py + 3);
  }

  // Required RR dashed line
  if (target != null && maxOv > 1) {
    let cum = 0;
    ctx.save();
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    let first = true;
    for (let ov = 0; ov < maxOv; ov++) {
      cum += (overRuns[ov] || 0);
      const rem = maxOv - (ov + 1);
      if (rem <= 0) continue;
      const rrr = (target - cum) / rem;
      const px = xOf(ov);
      const py = yOf(rrr);
      first ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      first = false;
    }
    ctx.strokeStyle = 'rgba(255,80,80,0.70)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }

  // Per-over RR line (light blue)
  ctx.beginPath();
  let fp = true;
  for (let ov = 0; ov < maxOv; ov++) {
    const px = xOf(ov);
    const py = yOf(overRuns[ov] || 0);
    fp ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    fp = false;
  }
  ctx.strokeStyle = 'rgba(100,180,255,0.80)';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Cumulative average RR (darker blue)
  let cumSum = 0;
  ctx.beginPath();
  fp = true;
  for (let ov = 0; ov < maxOv; ov++) {
    cumSum += (overRuns[ov] || 0);
    const avgRR = cumSum / (ov + 1);
    const px = xOf(ov);
    const py = yOf(avgRR);
    fp ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    fp = false;
  }
  ctx.strokeStyle = 'rgba(40,100,200,0.90)';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Axes
  ctx.beginPath();
  ctx.moveTo(MAR.left, MAR.top);
  ctx.lineTo(MAR.left, MAR.top + cH + 1);
  ctx.lineTo(MAR.left + cW, MAR.top + cH + 1);
  ctx.strokeStyle = 'rgba(255,255,255,0.22)';
  ctx.lineWidth = 1;
  ctx.stroke();

  // X-axis over labels
  const step = Math.max(1, Math.ceil(maxOv / 10));
  for (let ov = 0; ov < maxOv; ov += step) {
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(String(ov + 1), xOf(ov), H - MAR.bottom + 12);
  }

  // Title
  ctx.fillStyle = 'rgba(255,255,255,0.32)';
  ctx.font = '10px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('RUN RATE', W / 2, 14);

  // Legend
  const ly = H - MAR.bottom + 24;
  const drawLeg = (x, col, lbl) => {
    ctx.fillStyle = col;
    ctx.fillRect(x, ly - 5, 14, 2);
    ctx.fillStyle = 'rgba(255,255,255,0.48)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(lbl, x + 18, ly);
  };
  drawLeg(MAR.left,       'rgba(100,180,255,0.80)', 'Per-over RR');
  drawLeg(MAR.left + 90,  'rgba(40,100,200,0.90)',  'Avg RR');
  if (target != null) {
    drawLeg(MAR.left + 162, 'rgba(255,80,80,0.70)', 'Req. RR');
  }
}

// ── Innings Arc ───────────────────────────────────────────────────────────────

/**
 * drawInningsArc(canvasId, wickets, ballsFaced, maxOvers, score=null)
 * 200×120. Semicircle showing innings progress; colour by wickets.
 */
function drawInningsArc(canvasId, wickets, ballsFaced, maxOvers, score = null) {
  const c = _canvas(canvasId);
  if (!c) return;
  const { el: canvas, ctx } = c;

  const W = 200, H = 120;
  canvas.width  = W;
  canvas.height = H;

  const cx = W / 2, cy = H - 16;
  const R  = W / 2 - 14;
  const maxBalls = (maxOvers || 20) * 6;
  const progress = maxBalls > 0 ? Math.min(ballsFaced / maxBalls, 1) : 0;

  _fillBg(ctx, W, H);

  // Track (grey background arc)
  ctx.beginPath();
  ctx.arc(cx, cy, R, Math.PI, 0, false);
  ctx.strokeStyle = 'rgba(255,255,255,0.09)';
  ctx.lineWidth = 12;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Colour: green(0-3W) → amber(4-6W) → red(7-10W)
  const wFrac = (wickets || 0) / 10;
  let arcColour;
  if (wFrac < 0.35)      arcColour = '#22cc55';
  else if (wFrac < 0.65) arcColour = '#f39c12';
  else                   arcColour = '#cc2222';

  // Progress arc
  if (progress > 0) {
    ctx.beginPath();
    ctx.arc(cx, cy, R, Math.PI, Math.PI + progress * Math.PI, false);
    ctx.strokeStyle = arcColour;
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();
  }

  // Wicket tick marks (evenly spaced — actual fall positions unavailable here)
  if (wickets > 0) {
    for (let w = 1; w <= Math.min(wickets, 10); w++) {
      const angle = Math.PI + (w / 10) * Math.PI;
      const tx = cx + Math.cos(angle) * R;
      const ty = cy + Math.sin(angle) * R;
      const nx =  Math.sin(angle);
      const ny = -Math.cos(angle);
      ctx.beginPath();
      ctx.moveTo(tx - nx * 7, ty - ny * 7);
      ctx.lineTo(tx + nx * 7, ty + ny * 7);
      ctx.strokeStyle = 'rgba(255,80,80,0.85)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  // Centre text: score/wickets
  ctx.textAlign = 'center';
  if (score !== null) {
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 17px monospace';
    ctx.fillText(`${score}/${wickets}`, cx, cy - 14);
  } else {
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 13px monospace';
    ctx.fillText(`${wickets} wkts`, cx, cy - 14);
  }

  // "X ov left"
  const ovsCompleted = ballsFaced > 0 ? Math.floor(ballsFaced / 6) : 0;
  const ovLeft       = Math.max(0, (maxOvers || 20) - ovsCompleted);
  ctx.fillStyle = 'rgba(255,255,255,0.48)';
  ctx.font = '9px monospace';
  ctx.fillText(`${ovLeft} ov left`, cx, cy - 2);

  // End labels
  ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.font = '9px monospace';
  ctx.textAlign = 'left';
  ctx.fillText('0', cx - R - 1, cy + 14);
  ctx.textAlign = 'right';
  ctx.fillText(String(maxOvers || 20), cx + R + 1, cy + 14);
}

// ── Private helpers ───────────────────────────────────────────────────────────

function _noData(ctx, w, h) {
  ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.font = '13px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('No data', w / 2, h / 2);
}
