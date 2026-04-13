/* ============================================================
   app.js — Roll It & Bowl It: Dice Cricket Done Digitally
   Single-page application controller.
   ============================================================ */

'use strict';

// ── Global State ──────────────────────────────────────────────────────────────

const AppState = {
  currentScreen:     'home',
  activeMatch:       null,
  historicalMatchView: false,
  activeWorld:       null,
  activeTournament:  null,
  almanackFilters:   {},
  darkMode:          true,
  broadcastMode:     false,
  soundEnabled:      true,
  animationSpeed:    'normal',   // 'normal' | 'fast' | 'instant'
  defaultFormat:     'T20',
  defaultVenueId:    null,
  defaultScoringMode:'modern',
  recordPopups:      false,   // false = collect records and show at end of match
  playerMode:        'ai_vs_ai',   // 'ai_vs_ai' | 'human_vs_ai' | 'human_vs_human'
  humanTeamId:       null,         // team id for human-controlled team in human_vs_ai
  sessionStats: {
    matches:  0,
    runs:     0,
    wickets:  0,
    sixes:    0
  }
};

// ── Animation Speed Helper ────────────────────────────────────────────────────

/**
 * Return the duration (ms) that matches the current animation speed setting.
 * @param {number} normal  - duration at 'normal' speed
 * @param {number} fast    - duration at 'fast' speed
 * @param {number} instant - duration at 'instant' speed (usually 0)
 */
function animMs(normal, fast, instant = 0) {
  switch (AppState.animationSpeed) {
    case 'fast':    return fast;
    case 'instant': return instant;
    default:        return normal;
  }
}

const SCORING_MODE_META = {
  classic: {
    label: 'Classic',
    playHelp: 'Pure dice cricket: 1, 2, 3, 4 and 6 score exactly what the face shows. 5 triggers the HOWZAT appeal chain.',
    welcomeNote: 'Classic is the closest match to the old tabletop dice game and is the clearest mode for viewers.',
  },
  modern: {
    label: 'Modern',
    playHelp: 'Modern keeps the same face meanings and HOWZAT appeal chain, but in ODI and Test cricket a few big hits can be cut back.',
    welcomeNote: 'Modern keeps the old-school feel but makes longer-format scoring a touch more grounded.',
  }
};

const PLAY_SCOPE_META = {
  international: 'International mode shows national teams. Use this for Tests, ODIs, T20Is and broader world cricket.',
  domestic: 'Domestic mode shows county, state and franchise sides. Use the league filter below to narrow the team pool.'
};

const WORLD_SCOPE_META = {
  international: 'International worlds use national teams only and generate an international calendar.',
  domestic: 'Domestic worlds focus on league and franchise cricket. In realistic mode, pick at least one domestic competition.',
  combined: 'Combined worlds generate the international calendar and layer selected domestic leagues into the same save.'
};
const WORLD_DOMESTIC_TEAM_MODE_META = {
  selected: 'Only the domestic clubs you choose in Step 3 will be included in the world.',
  full_league: 'Every club from your selected domestic leagues will be included automatically.'
};

// ── Disclaimer Text ───────────────────────────────────────────────────────────

const DISCLAIMER_TEXT = {
  short: 'An independent fan-made project. Not affiliated with any cricket board, ' +
         'governing body, or commercial cricket organisation.',
  full: `Roll It & Bowl It is an independent fan-made project created for personal \
entertainment. It is not affiliated with, endorsed by, or connected to any \
cricket board, governing body, broadcaster, or commercial cricket organisation, \
including but not limited to the ICC, ECB, Cricket Australia, BCCI, or any \
other national or international cricket authority.

Player names used in pre-loaded squads are included for entertainment purposes \
only in the spirit of the dice cricket tradition. No association with or \
endorsement by any named individual is implied or should be inferred.

"Wisden" and "Wisden Cricketers' Almanack" are registered trademarks of \
John Wisden & Co. "The Dice Cricketers' Almanack" is an original name created \
for this project and is not affiliated with or derived from Wisden in any \
commercial sense.

This application is not a commercial product. It is free, open source, and \
intended solely for personal use and enjoyment.`
};

// ── Score / Overs Formatting Helpers ─────────────────────────────────────────

/**
 * Format a runs/wickets pair as a cricket score string.
 * 179/10 → "179 all out"   147/4 → "147/4"
 */
function formatScore(runs, wickets) {
  if (wickets >= 10) return `${runs} all out`;
  return `${runs}/${wickets}`;
}

/**
 * Convert a stored overs float to cricket display notation.
 * Handles two internal formats:
 *   - Cricket notation  (ball-by-ball): 13.5  = 13 overs 5 balls
 *   - True decimal      (simulation):   13.83 = 13 overs 5 balls
 * If the tenths digit > 5 it must be true decimal; otherwise treat as
 * cricket notation where the digit IS the ball count.
 */
function formatOvers(overs) {
  if (overs === null || overs === undefined || overs === '') return '0';
  const completeOvers = Math.floor(overs);
  const remainder = overs - completeOvers;
  const tenths = Math.round(remainder * 10);
  // Cricket notation (ball-by-ball): tenths digit IS the ball count (0–5)
  // True decimal (simulation): tenths digit can exceed 5, so use × 6 conversion
  let balls = tenths > 5 ? Math.round(remainder * 6) : tenths;
  if (balls >= 6) {
    return String(completeOvers + 1);
  }
  if (balls === 0) return `${completeOvers}`;
  return `${completeOvers}.${balls}`;
}

/**
 * Format individual bowler overs where complete overs and balls are stored
 * as separate integers (overs = complete overs, balls = 0-5 ball remainder).
 */
function formatBowlerOvers(completeOvers, balls) {
  if (!balls) return `${completeOvers}`;
  return `${completeOvers}.${balls}`;
}

function oversToLegalBalls(overs) {
  if (overs === null || overs === undefined || overs === '') return 0;
  const wholeOvers = Math.floor(Number(overs) || 0);
  const remainder = (Number(overs) || 0) - wholeOvers;
  const balls = Math.round(remainder * 10);
  return wholeOvers * 6 + balls;
}

// ── API Helper ────────────────────────────────────────────────────────────────

let _apiCallCount = 0;

function _apiLoadingShow() {
  _apiCallCount++;
  if (_apiCallCount === 1) {
    const bar = document.getElementById('api-loading-bar');
    if (bar) bar.classList.remove('hidden');
  }
}

function _apiLoadingHide() {
  _apiCallCount = Math.max(0, _apiCallCount - 1);
  if (_apiCallCount === 0) {
    const bar = document.getElementById('api-loading-bar');
    if (bar) bar.classList.add('hidden');
  }
}

async function api(method, endpoint, body = null) {
  // endpoint should start with /api/...
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }

  _apiLoadingShow();
  try {
    const res = await fetch(endpoint, opts);
    const data = await res.json();

    if (!res.ok) {
      let msg;
      if (res.status === 404)      msg = 'That record no longer exists.';
      else if (res.status === 500) msg = 'Server error — is start.py running?';
      else msg = data.error || data.message || `Unexpected error (HTTP ${res.status})`;
      showError(msg);
      return null;
    }
    return data;
  } catch (err) {
    if (err instanceof TypeError) {
      showError('Cannot reach server — is start.py running?');
    } else {
      showError('Unexpected error: ' + err.message);
    }
    return null;
  } finally {
    _apiLoadingHide();
  }
}

// ── Error Banner ──────────────────────────────────────────────────────────────

function showError(message) {
  const banner = document.getElementById('error-banner');
  const msg    = document.getElementById('error-message');
  msg.textContent = message;
  banner.classList.remove('hidden');
  clearTimeout(window._errorTimer);
  window._errorTimer = setTimeout(clearError, 5000);
}

function clearError() {
  const banner = document.getElementById('error-banner');
  banner.classList.add('hidden');
}

// ── Screen Router ─────────────────────────────────────────────────────────────

function showScreen(name) {
  // Guard: warn if leaving an active match (not when entering demo)
  if (AppState.currentScreen === 'match' && name !== 'match' && name !== 'demo') {
    const matchId = getMatchId();
    const matchStatus = MatchUI.lastState?.match?.status;
    if (matchId && matchStatus === 'in_progress') {
      if (!confirm('Leave active match? Progress will not be lost — you can return to it.')) {
        return;
      }
    }
  }

  document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));

  const target = document.getElementById('screen-' + name);
  if (target) {
    target.classList.add('active');
    AppState.currentScreen = name;
  } else {
    console.warn('showScreen: unknown screen:', name);
    return;
  }

  // Update nav active state
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.screen === name);
  });

  // Fire screen-specific load hooks
  onScreenLoad(name);
}

function onScreenLoad(name) {
  switch (name) {
    case 'welcome':           loadWelcomeScreen();       break;
    case 'home':              loadHomeScreen();          break;
    case 'play':              loadPlayScreen();          break;
    case 'match':             loadMatchScreen();         break;
    case 'teams':             loadTeamsScreen();         break;
    case 'venues':            loadVenuesScreen();        break;
    case 'settings':          loadSettingsScreen();      break;
    case 'journal':           loadJournalScreen();       break;
    case 'series':            loadSeriesScreen();        break;
    case 'series-detail':     /* loaded by loadSeriesDetail */ break;
    case 'tournament-detail': /* loaded by loadTournamentDetail */ break;
    case 'almanack':          loadAlmanackScreen();      break;
    case 'world':             loadWorldsScreen();        break;
    case 'world-detail':      /* loaded by loadWorldDetail() */ break;
    case 'world-sim-report':  /* loaded by simulateWorld() */   break;
    case 'world-calendar':    /* loaded by openWorldCalendar() */ break;
    case 'player-detail': break;  // loaded by loadPlayerDetail()
    case 'team-detail':   break;  // loaded by loadTeamDetail()
    case 'venue-detail':  break;  // loaded by loadVenueDetail()
    case 'demo':          break;  // loaded by DemoMode.start()
  }
}

function loadWelcomeScreen() {
  syncWelcomeScoringMode();
}

// ── Nav Wiring ────────────────────────────────────────────────────────────────

function initNav() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      showScreen(link.dataset.screen);
    });
  });

  document.getElementById('btn-broadcast').addEventListener('click', toggleBroadcastMode);
  document.getElementById('btn-sound').addEventListener('click', toggleSound);
  document.getElementById('btn-darkmode').addEventListener('click', toggleDarkMode);
  document.getElementById('btn-settings').addEventListener('click', () => showScreen('settings'));
}

// ── Mode Toggles ──────────────────────────────────────────────────────────────

function toggleBroadcastMode() {
  AppState.broadcastMode = !AppState.broadcastMode;
  document.body.classList.toggle('broadcast-mode', AppState.broadcastMode);
  const btn = document.getElementById('btn-broadcast');
  btn.classList.toggle('active', AppState.broadcastMode);
  btn.textContent = AppState.broadcastMode ? '📺 Broadcast ON' : '📺 Broadcast';

  const settingsBtn = document.getElementById('settings-broadcast');
  if (settingsBtn) {
    settingsBtn.textContent = AppState.broadcastMode ? 'On' : 'Off';
    settingsBtn.classList.toggle('active', AppState.broadcastMode);
  }
  try { localStorage.setItem('ribi_broadcast', AppState.broadcastMode ? '1' : '0'); } catch (_) {}
}

function toggleDarkMode() {
  AppState.darkMode = !AppState.darkMode;
  document.body.classList.toggle('light-mode', !AppState.darkMode);
  const btn = document.getElementById('btn-darkmode');
  btn.textContent = AppState.darkMode ? '☀️ Light' : '🌙 Dark';

  const settingsBtn = document.getElementById('settings-darkmode');
  if (settingsBtn) {
    settingsBtn.textContent = AppState.darkMode ? 'On' : 'Off';
    settingsBtn.classList.toggle('active', AppState.darkMode);
  }
  try { localStorage.setItem('ribi_dark_mode', AppState.darkMode ? '1' : '0'); } catch (_) {}

  // Keep Almanack CSS variables in sync with mode
  const isDark = AppState.darkMode;
  document.documentElement.style.setProperty('--almanack-text',     isDark ? '#e8dcc8' : '#2c1f0a');
  document.documentElement.style.setProperty('--almanack-text-muted', isDark ? '#a89878' : '#7a6040');
  document.documentElement.style.setProperty('--almanack-bg-tint',  isDark ? 'rgba(201,168,76,0.05)' : 'rgba(201,168,76,0.08)');
}

function toggleSound() {
  AppState.soundEnabled = !AppState.soundEnabled;
  const btn = document.getElementById('btn-sound');
  if (btn) {
    btn.textContent = AppState.soundEnabled ? '🔊 Sound' : '🔇 Mute';
    btn.classList.toggle('active', AppState.soundEnabled);
  }
  const settingsBtn = document.getElementById('settings-sound');
  if (settingsBtn) {
    settingsBtn.textContent = AppState.soundEnabled ? 'On' : 'Off';
    settingsBtn.classList.toggle('active', AppState.soundEnabled);
  }
  try { localStorage.setItem('ribi_sound', AppState.soundEnabled ? '1' : '0'); } catch (_) {}
}

function toggleRecordPopups() {
  AppState.recordPopups = !AppState.recordPopups;
  const btn = document.getElementById('settings-record-popups');
  if (btn) {
    btn.textContent = AppState.recordPopups ? 'On' : 'Off';
    btn.classList.toggle('active', AppState.recordPopups);
  }
  try { localStorage.setItem('ribi_record_popups', AppState.recordPopups ? '1' : '0'); } catch (_) {}
}

// ── Session Bar ───────────────────────────────────────────────────────────────

function updateSessionBar() {
  const s = AppState.sessionStats;
  const text = `This session: ${s.matches} match${s.matches !== 1 ? 'es' : ''} • ${s.runs} runs • ${s.wickets} wickets • ${s.sixes} sixes`;
  const el = document.getElementById('session-bar-text');
  if (el) el.textContent = text;
}

// ── Home Screen ───────────────────────────────────────────────────────────────

async function loadHomeScreen() {
  const statusEl   = document.getElementById('home-status');
  const dashEl     = document.getElementById('home-dashboard');
  if (!dashEl) return;

  if (statusEl) {
    statusEl.textContent = 'Connecting…';
    statusEl.className   = 'home-status';
  }

  const stats = await api('GET', '/api/stats/quick');

  if (statusEl) {
    if (stats !== null) {
      statusEl.textContent = '✓ The Almanack is ready';
      statusEl.classList.add('ok');
    } else {
      statusEl.textContent = '✗ Cannot connect to server';
      statusEl.classList.add('error');
    }
  }

  if (!stats) { dashEl.innerHTML = ''; return; }

  if (stats.matches === 0) {
    dashEl.innerHTML = `
      <div class="home-getstarted-card">
        <div class="empty-state-icon">🏏</div>
        <h3 class="empty-state-heading">Ready to play your first match?</h3>
        <p class="empty-state-sub">The Almanack is empty — play a match and it will come to life.</p>
        <div class="home-quick-actions" style="justify-content:center">
          <button class="btn btn-primary" onclick="showScreen('play')">Play Match</button>
          <button class="btn btn-secondary" onclick="showScreen('almanack')">View Almanack</button>
          <button class="btn btn-secondary" onclick="showScreen('world')">Browse Worlds</button>
        </div>
      </div>`;
    return;
  }

  const recentHtml = (stats.recent_results || []).map(r => {
    let result = '';
    if (r.result_type === 'draw') result = 'Draw';
    else if (r.result_type === 'tie') result = 'Tie';
    else if (r.winning_team_name) {
      result = r.result_type === 'runs'
        ? `${r.winning_team_name} won by ${r.margin_runs} run${r.margin_runs !== 1 ? 's' : ''}`
        : `${r.winning_team_name} won by ${r.margin_wickets} wkt${r.margin_wickets !== 1 ? 's' : ''}`;
    }
    return `<div class="home-result-card home-result-card-clickable"
      onclick="openPlayedMatch(${r.id || r.match_id})" title="View scorecard">
      <span class="badge badge-${(r.format||'').toLowerCase()}">${r.format}</span>
      ${_modeBadgeHtml(r.player_mode)}
      ${_canonBadgeHtml(r.canon_status)}
      <span class="home-result-teams">${r.team1_name} vs ${r.team2_name}</span>
      <span class="home-result-result">${result}</span>
      <span class="home-result-date">${r.match_date || ''}</span>
    </div>`;
  }).join('');

  const hs   = stats.highest_score;
  const most = stats.most_centuries;

  dashEl.innerHTML = `
    <div class="home-dash-row">
      <div class="home-dash-col">
        <div class="home-dash-section">
          <h3 class="home-dash-label">Recent Results</h3>
          ${recentHtml || '<p class="text-muted" style="font-size:var(--fs-sm)">No completed matches yet.</p>'}
        </div>
      </div>
      <div class="home-dash-col home-dash-col--right">
        <div class="home-dash-section">
          <h3 class="home-dash-label">Quick Stats</h3>
          <div class="home-stats-grid">
            <div class="home-stat-card"><div class="home-stat-value">${stats.matches.toLocaleString()}</div><div class="home-stat-label">Matches Played</div></div>
            <div class="home-stat-card"><div class="home-stat-value">${stats.total_runs.toLocaleString()}</div><div class="home-stat-label">Total Runs</div></div>
            <div class="home-stat-card"><div class="home-stat-value">${stats.total_wickets.toLocaleString()}</div><div class="home-stat-label">Total Wickets</div></div>
            <div class="home-stat-card"><div class="home-stat-value">${hs ? hs.runs : '—'}</div><div class="home-stat-label">Highest Score${hs ? ' (' + hs.player_name + ')' : ''}</div></div>
            <div class="home-stat-card"><div class="home-stat-value">${most ? most.centuries : '—'}</div><div class="home-stat-label">Most Centuries${most ? ' (' + most.player_name + ')' : ''}</div></div>
          </div>
        </div>
        <div class="home-dash-section">
          <h3 class="home-dash-label">Quick Actions</h3>
          <div class="home-quick-actions">
            <button class="btn btn-primary" onclick="showScreen('play')">Play Match</button>
            <button class="btn btn-secondary" onclick="showScreen('almanack')">View Almanack</button>
            <button class="btn btn-secondary" onclick="showScreen('world')">Browse Worlds</button>
          </div>
        </div>
      </div>
    </div>`;
}

// ── Play Screen ───────────────────────────────────────────────────────────────

function getDefaultScoringMode() {
  return ['classic', 'modern'].includes(AppState.defaultScoringMode)
    ? AppState.defaultScoringMode
    : 'modern';
}

function getSelectedPlayScoringMode() {
  return ['classic', 'modern'].includes(AppState._playScoringMode)
    ? AppState._playScoringMode
    : getDefaultScoringMode();
}

function syncWelcomeScoringMode() {
  const mode = getDefaultScoringMode();
  const classicBtn = document.getElementById('welcome-scoring-classic');
  const modernBtn = document.getElementById('welcome-scoring-modern');
  if (classicBtn) classicBtn.classList.toggle('active', mode === 'classic');
  if (modernBtn) modernBtn.classList.toggle('active', mode === 'modern');
  const noteEl = document.getElementById('welcome-scoring-note');
  if (noteEl) noteEl.textContent = SCORING_MODE_META[mode].welcomeNote;
}

function chooseWelcomeScoringMode(mode) {
  setDefaultScoringMode(mode);
  syncWelcomeScoringMode();
}

function getPlayCricketScope() {
  return AppState._playCricketScope === 'domestic' ? 'domestic' : 'international';
}

function syncPlayCricketScope() {
  const scope = getPlayCricketScope();
  const intlBtn = document.getElementById('play-scope-international');
  const domBtn = document.getElementById('play-scope-domestic');
  if (intlBtn) intlBtn.classList.toggle('active', scope === 'international');
  if (domBtn) domBtn.classList.toggle('active', scope === 'domestic');
  const helpEl = document.getElementById('play-scope-help');
  if (helpEl) helpEl.textContent = PLAY_SCOPE_META[scope];
  document.getElementById('play-domestic-league-section')?.classList.toggle('hidden', scope !== 'domestic');
}

function setPlayCricketScope(scope) {
  AppState._playCricketScope = scope === 'domestic' ? 'domestic' : 'international';
  if (scope !== 'domestic') {
    AppState._playDomesticLeague = '';
  }
  syncPlayCricketScope();
  syncPlayFormatLabels();
  applyPlayTeamFilters();
}

function setPlayDomesticLeague(league) {
  AppState._playDomesticLeague = league || '';
  applyPlayTeamFilters();
}

function populateDomesticLeagueFilter(teams) {
  const leagueSelect = document.getElementById('play-domestic-league');
  if (!leagueSelect) return;
  const leagues = [...new Set(
    (teams || [])
      .filter(t => t.team_type && t.team_type !== 'international' && t.league)
      .map(t => t.league)
  )].sort((a, b) => a.localeCompare(b));
  leagueSelect.innerHTML = [
    '<option value="">All domestic competitions</option>',
    ...leagues.map(l => `<option value="${escHtml(l)}">${escHtml(l)}</option>`)
  ].join('');
  if (AppState._playDomesticLeague && leagues.includes(AppState._playDomesticLeague)) {
    leagueSelect.value = AppState._playDomesticLeague;
  } else {
    AppState._playDomesticLeague = '';
    leagueSelect.value = '';
  }
}

function syncPlayFormatLabels() {
  const domestic = getPlayCricketScope() === 'domestic';
  document.querySelectorAll('.format-btn').forEach(btn => {
    const format = btn.dataset.format;
    const nameEl = btn.querySelector('.fmt-name');
    const oversEl = btn.querySelector('.fmt-overs');
    const descEl = btn.querySelector('.fmt-desc');
    if (!nameEl || !oversEl || !descEl) return;
    if (domestic) {
      if (format === 'Test') {
        nameEl.textContent = 'First-Class';
        oversEl.textContent = '2 innings each';
        descEl.textContent = 'Long-form domestic cricket with declarations and patience';
      } else if (format === 'ODI') {
        nameEl.textContent = 'One-Day';
        oversEl.textContent = '50 overs per side';
        descEl.textContent = 'List-A rhythm with room for both accumulation and attack';
      } else if (format === 'T20') {
        nameEl.textContent = 'T20';
        oversEl.textContent = '20 overs per side';
        descEl.textContent = 'Franchise pace, pressure overs and fast scoring';
      }
    } else {
      if (format === 'Test') {
        nameEl.textContent = 'Test';
        oversEl.textContent = '2 innings each';
        descEl.textContent = 'The ultimate examination — declare or fight to the last';
      } else if (format === 'ODI') {
        nameEl.textContent = 'ODI';
        oversEl.textContent = '50 overs per side';
        descEl.textContent = 'The tactical balance of strategy and power';
      } else if (format === 'T20') {
        nameEl.textContent = 'T20';
        oversEl.textContent = '20 overs per side';
        descEl.textContent = 'Fast-paced, big hitting, decided in an evening';
      }
    }
  });
}

function applyPlayTeamFilters() {
  const allTeams = AppState._playTeams || [];
  const scope = getPlayCricketScope();
  const league = AppState._playDomesticLeague || '';
  const filtered = allTeams.filter(t => {
    const isDomestic = !!t.team_type && t.team_type !== 'international';
    if (scope === 'international') {
      return !isDomestic;
    }
    if (!isDomestic) return false;
    if (league && t.league !== league) return false;
    return true;
  });

  const validIds = new Set(filtered.map(t => t.id));
  if (!validIds.has(AppState._selectedTeam1)) AppState._selectedTeam1 = null;
  if (!validIds.has(AppState._selectedTeam2)) AppState._selectedTeam2 = null;

  renderTeamSelector('team1-selector', filtered, 1);
  renderTeamSelector('team2-selector', filtered, 2);
  checkStartReady();
}

function syncPlayScoringMode() {
  const mode = getSelectedPlayScoringMode();
  const classicBtn = document.getElementById('play-scoring-classic');
  const modernBtn = document.getElementById('play-scoring-modern');
  if (classicBtn) classicBtn.classList.toggle('active', mode === 'classic');
  if (modernBtn) modernBtn.classList.toggle('active', mode === 'modern');
  const helpEl = document.getElementById('play-scoring-help');
  if (helpEl) helpEl.textContent = SCORING_MODE_META[mode].playHelp;
}

function selectPlayScoringMode(mode) {
  AppState._playScoringMode = mode === 'classic' ? 'classic' : 'modern';
  syncPlayScoringMode();
}

async function loadPlayScreen() {
  // Set default date
  const dateInput = document.getElementById('match-date');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }

  // Load teams into selectors
  const teams = await api('GET', '/api/teams');
  const teamList = teams && teams.teams ? teams.teams : [];

  AppState._playTeams = teamList;  // keep for mode selection team name lookup
  AppState._playCricketScope = AppState._playCricketScope || 'international';
  populateDomesticLeagueFilter(teamList);
  syncPlayCricketScope();
  syncPlayFormatLabels();
  applyPlayTeamFilters();

  // Load venues
  const venues = await api('GET', '/api/venues');
  const venueList = venues && venues.venues ? venues.venues : [];
  const venueSelect = document.getElementById('venue-select');
  if (venueSelect) {
    venueSelect.innerHTML = venueList.length
      ? venueList.map(v => `<option value="${v.id}">${v.name}${v.city ? ', ' + v.city : ''}</option>`).join('')
      : '<option value="">No venues available</option>';
    if (AppState.defaultVenueId && venueList.some(v => v.id === AppState.defaultVenueId)) {
      venueSelect.value = String(AppState.defaultVenueId);
    }
  }

  // Format buttons
  document.querySelectorAll('.format-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.format === AppState.defaultFormat);
    btn.addEventListener('click', () => {
      document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      checkStartReady();
    });
  });

  AppState._playScoringMode = getDefaultScoringMode();
  syncPlayScoringMode();

  checkStartReady();

  // Start match button
  const startBtn = document.getElementById('btn-start-match');
  if (startBtn) {
    // Re-bind to avoid duplicates
    startBtn.replaceWith(startBtn.cloneNode(true));
    document.getElementById('btn-start-match').addEventListener('click', startMatch);
  }
}

function renderTeamSelector(containerId, teams, slot) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!teams.length) {
    container.innerHTML = '<p class="text-muted" style="padding:12px;font-size:13px;">No teams match the current cricket type and league filter.</p>';
    return;
  }

  const selectedId = slot === 1 ? AppState._selectedTeam1 : AppState._selectedTeam2;
  const otherSelectedId = slot === 1 ? AppState._selectedTeam2 : AppState._selectedTeam1;
  container.innerHTML = teams.map(t => `
    <div class="team-option${selectedId === t.id ? ' selected' : ''}${otherSelectedId === t.id ? ' disabled' : ''}" data-id="${t.id}" data-slot="${slot}" onclick="selectTeam(this, ${slot})">
      <span class="team-badge" style="background:${t.badge_colour || '#444'}"></span>
      <span class="team-option-name">${t.name}</span>
      <span class="team-option-code">${t.short_code || ''}</span>
    </div>
  `).join('');
}

function selectTeam(el, slot) {
  if (el.classList.contains('disabled')) return;
  const container = el.closest('.team-selector');
  container.querySelectorAll('.team-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');

  if (slot === 1) AppState._selectedTeam1 = parseInt(el.dataset.id);
  if (slot === 2) AppState._selectedTeam2 = parseInt(el.dataset.id);

  // Dim the selected team in the OTHER selector
  const otherId = 'team' + (slot === 1 ? '2' : '1') + '-selector';
  const otherContainer = document.getElementById(otherId);
  if (otherContainer) {
    otherContainer.querySelectorAll('.team-option').forEach(o => {
      o.classList.toggle('disabled', o.dataset.id === el.dataset.id);
    });
  }

  checkStartReady();
}

function checkStartReady() {
  const btn = document.getElementById('btn-start-match');
  if (!btn) return;
  const t1 = AppState._selectedTeam1;
  const t2 = AppState._selectedTeam2;
  const fmt = document.querySelector('.format-btn.active');
  const ready = t1 && t2 && t1 !== t2 && fmt;
  btn.disabled = !ready;
}

// ── Mode Selection ────────────────────────────────────────────────────────────

function startMatch() {
  // Show mode selection modal instead of immediately starting
  const t1  = AppState._selectedTeam1;
  const t2  = AppState._selectedTeam2;
  const fmt = document.querySelector('.format-btn.active')?.dataset.format;
  if (!t1 || !t2 || !fmt) { showError('Please select two teams and a format.'); return; }
  _showModeModal();
}

function closeModeModal() {
  document.getElementById('mode-select-modal').classList.add('hidden');
  document.getElementById('human-team-modal').classList.add('hidden');
}

function setCanonChoice(choice) {
  AppState._canonChoice = choice;
  const yes = document.getElementById('canon-btn-yes');
  const no  = document.getElementById('canon-btn-no');
  if (!yes || !no) return;
  yes.classList.toggle('canon-btn-active', choice === 'canon');
  yes.dataset.canon = 'canon';
  no.classList.toggle('canon-btn-active',  choice === 'exhibition');
}

function _showModeModal() {
  // Reset canon choice to exhibition (standalone default)
  AppState._canonChoice = 'exhibition';
  setCanonChoice('exhibition');
  document.getElementById('mode-select-modal').classList.remove('hidden');
}

function selectMode(mode) {
  document.getElementById('mode-select-modal').classList.add('hidden');

  if (mode === 'human_vs_ai') {
    // Populate team choice buttons then show
    const teams = AppState._playTeams || [];
    const t1Id = AppState._selectedTeam1;
    const t2Id = AppState._selectedTeam2;
    const t1Name = teams.find(t => t.id === t1Id)?.name || 'Team 1';
    const t2Name = teams.find(t => t.id === t2Id)?.name || 'Team 2';
    document.getElementById('btn-mode-team1').textContent = t1Name;
    document.getElementById('btn-mode-team2').textContent = t2Name;
    document.getElementById('human-team-modal').classList.remove('hidden');
  } else {
    _doStartMatch(mode, null);
  }
}

function confirmHumanTeam(slot) {
  document.getElementById('human-team-modal').classList.add('hidden');
  const humanTeamId = slot === 1 ? AppState._selectedTeam1 : AppState._selectedTeam2;
  _doStartMatch('human_vs_ai', humanTeamId);
}

function backToModeSelect() {
  document.getElementById('human-team-modal').classList.add('hidden');
  document.getElementById('mode-select-modal').classList.remove('hidden');
}

async function _doStartMatch(playerMode, humanTeamId) {
  const t1  = AppState._selectedTeam1;
  const t2  = AppState._selectedTeam2;
  const fmt = document.querySelector('.format-btn.active')?.dataset.format;
  const venueEl = document.getElementById('venue-select');
  const venue = venueEl ? parseInt(venueEl.value) : null;
  const dateEl = document.getElementById('match-date');
  const date = dateEl?.value || new Date().toISOString().split('T')[0];
  const scoringMode = getSelectedPlayScoringMode();

  if (!t1 || !t2 || !fmt) { showError('Please select two teams and a format.'); return; }

  AppState.playerMode  = playerMode;
  AppState.humanTeamId = humanTeamId;

  const canonStatus = AppState._canonChoice || 'exhibition';
  const res = await api('POST', '/api/matches/start', {
    team1_id: t1, team2_id: t2, format: fmt,
    venue_id: venue, match_date: date,
    player_mode:    playerMode,
    human_team_id:  humanTeamId,
    canon_status:   canonStatus,
    scoring_mode:   scoringMode,
  });

  if (res) {
    AppState.historicalMatchView = false;
    AppState.activeMatch = res.match || res;
    AppState.activeMatch.match_id = res.match_id || res.match?.id;
    AppState.activeMatch.playerMode  = playerMode;
    AppState.activeMatch.humanTeamId = humanTeamId;
    AppState.activeMatch.scoring_mode = res.match?.scoring_mode || scoringMode;

    MatchUI.lastState = null;
    MatchUI.commentaryLines = [];
    MatchUI._recentOutcomes = [];
    MatchUI.allPlayers = {};
    MatchUI.recordsBroken = [];
    MatchUI.chosenBowlerId = null;
    _stopAiAutoPlay();

    // Switch screen
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('screen-match');
    if (target) { target.classList.add('active'); AppState.currentScreen = 'match'; }
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.dataset.screen === 'match');
    });
    showMatchToss();
  }
}

// ── Match Screen ──────────────────────────────────────────────────────────────

// State local to the match screen
const MatchUI = {
  commentaryLines:    [],   // [{overBall, text, cssClass}]
  lastState:          null, // most recent full match state
  tossCoinWinner:     null,
  allPlayers:         {},   // id -> {name, batting_rating, bowling_type, ...}
  batterScores:       {},   // player_id -> {runs, balls, fours, sixes, not_out}
  bowlerFigures:      {},   // player_id -> {overs, balls, runs, wickets, maidens}
  _journalPrompts:    [],   // cached journal prompt strings
  _journalPromptIdx:  0,    // rotation index
  recordsBroken:      [],   // accumulated this match when recordPopups is off
  aiPlay: {                 // AI vs AI / AI-turn auto-play state
    running:  false,
    paused:   false,
    speed:    'normal',     // 'slow'|'normal'|'fast'|'instant'
    _timer:   null,
  },
  chosenBowlerId:     null, // human-selected bowler for next over
  _bowlingPanelCb:    null, // resolve callback for bowling panel promise
  // ── Manual Roll / DiceState additions ──
  diceState:              'idle',   // current DiceState value
  rollMode:               'auto',   // 'auto' | 'manual'
  _pendingDelivery:       null,     // delivery object waiting for manual resolution
  _pendingRes:            null,     // full API response waiting for manual resolution
  _ballInProgress:        false,    // true between first Roll press and ball completion
  _transitionActive:      false,    // innings/result overlay is blocking live play
  _pendingRollModeSwitch: null,     // queued mode switch to apply after current ball
  _dismissedSuggestions:  [],       // suggestion keys dismissed this innings
  _storyState:            { key: '', primaryTone: 'neutral', alertedKey: '' },
  _liveWagonShots:        [],       // recent shot lines for the mini live wagon wheel
  _liveWagonInningsId:    null,     // current innings being shown on the mini wheel
  _liveWagonOverNumber:   null,     // over currently being shown on the mini wheel
};

// ── DiceState Machine ─────────────────────────────────────────────────────────

const DiceState = {
  IDLE:          'idle',          // Between balls, Roll button active
  ROLLING_S1:    'rolling_s1',   // Stage 1 animating
  HOWZAT:        'howzat',       // Stage 1 was appeal, awaiting Appeal press
  ROLLING_S2:    'rolling_s2',   // Stage 2 animating
  NOT_OUT:       'not_out',      // Stage 2 = not out, awaiting Continue
  OUT_PENDING:   'out_pending',  // Stage 2 = out, awaiting Dismissal press
  ROLLING_S3:    'rolling_s3',   // Stage 3 animating
  ROLLING_S4:    'rolling_s4',   // Stage 4 animating
  ROLLING_S4B:   'rolling_s4b',  // Stage 4b animating
  RESULT:        'result',       // Ball complete, showing result
  FREE_HIT:      'free_hit',     // Free hit announcement
  INNINGS_END:   'innings_end',  // Innings complete
  MATCH_END:     'match_end',    // Match complete
};

function _setDiceState(newState) {
  const old = MatchUI.diceState;
  MatchUI.diceState = newState;
  console.log(`[DiceState] ${old} → ${newState}`);
  _updateDiceStateUI(newState);
}

function _updateDiceStateUI(state) {
  const isManual = (MatchUI.rollMode === 'manual');
  const isRolling = [
    DiceState.ROLLING_S1, DiceState.ROLLING_S2, DiceState.ROLLING_S3,
    DiceState.ROLLING_S4, DiceState.ROLLING_S4B,
  ].includes(state);

  // Roll button — always managed
  const rollBtn = document.getElementById('btn-roll');
  if (rollBtn) {
    if (isManual) {
      // In manual mode, hide Roll when not idle
      rollBtn.classList.toggle('hidden', state !== DiceState.IDLE);
      rollBtn.disabled = false;
    } else {
      // In auto mode, just disable during rolls
      rollBtn.classList.remove('hidden');
      rollBtn.disabled = isRolling;
    }
  }

  if (!isManual) return; // Auto mode: only manage roll button above

  // HOWZAT display
  const howzatDisplay = document.getElementById('manual-howzat-display');
  if (howzatDisplay) howzatDisplay.classList.toggle('hidden', state !== DiceState.HOWZAT);

  // Manual action buttons container — visible when waiting for input
  const actionBtns = document.getElementById('manual-action-btns');
  const needsInput = [DiceState.HOWZAT, DiceState.NOT_OUT, DiceState.OUT_PENDING].includes(state);
  if (actionBtns) actionBtns.classList.toggle('hidden', !needsInput);

  // Individual buttons
  const appealBtn     = document.getElementById('btn-appeal');
  const continueBtn   = document.getElementById('btn-continue-notout');
  const dismissalBtn  = document.getElementById('btn-dismissal');
  if (appealBtn)    appealBtn.classList.toggle('hidden',    state !== DiceState.HOWZAT);
  if (continueBtn)  continueBtn.classList.toggle('hidden',  state !== DiceState.NOT_OUT);
  if (dismissalBtn) dismissalBtn.classList.toggle('hidden', state !== DiceState.OUT_PENDING);
  // btn-caught-where is managed explicitly by manualDismissal()

  // Die stage label — large in manual mode
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) {
    stageLabelEl.classList.toggle('manual-label', !isRolling);
  }
}

function getMatchId() {
  return AppState.activeMatch?.match_id || AppState.activeMatch?.id;
}

// ── Toss ──────────────────────────────────────────────────────────────────────

function showMatchToss() {
  document.getElementById('match-toss-screen').classList.remove('hidden');
  document.getElementById('match-innings-transition').classList.add('hidden');
  document.getElementById('match-result-screen').classList.add('hidden');
  document.getElementById('match-live').classList.add('hidden');

  const m = AppState.activeMatch;
  document.getElementById('toss-title').textContent =
    `${m.team1_name || m.format || 'Match'} — Toss`;
  document.getElementById('toss-team1').textContent = m.team1_name || 'Team 1';
  document.getElementById('toss-team2').textContent = m.team2_name || 'Team 2';
  document.getElementById('toss-result').classList.add('hidden');
  document.getElementById('toss-call-result').classList.add('hidden');
  document.getElementById('toss-choice-area').classList.add('hidden');
  document.getElementById('toss-lpc').classList.add('hidden');
  const coinInner = document.querySelector('#toss-coin .coin-inner');
  if (coinInner) coinInner.classList.remove('flipping-bat', 'flipping-ball');
  MatchUI.tossCoinWinner = null;

  const btn = document.getElementById('btn-flip-coin');
  btn.disabled = false;
  btn.onclick = flipCoin;
}

function flipCoin() {
  const m = AppState.activeMatch;
  const teams = [
    { id: m.team1_id, name: m.team1_name },
    { id: m.team2_id, name: m.team2_name },
  ];
  const winner = teams[Math.random() < 0.5 ? 0 : 1];
  MatchUI.tossCoinWinner = winner.id;
  const face = Math.random() < 0.5 ? 'bat' : 'ball';

  const coin     = document.getElementById('toss-coin');
  const inner    = coin.querySelector('.coin-inner');
  const btn      = document.getElementById('btn-flip-coin');
  const callEl   = document.getElementById('toss-call-result');
  btn.disabled = true;
  callEl.classList.add('hidden');
  SoundEngine.play('milestone');

  // Restart 3D flip animation landing on the chosen face
  inner.classList.remove('flipping-bat', 'flipping-ball');
  void inner.offsetWidth; // reflow to restart
  inner.classList.add(`flipping-${face}`);

  setTimeout(() => {
    const callText = face === 'bat' ? '🏏 Bat came up' : '🔴 Ball came up';
    callEl.textContent = callText;
    callEl.classList.remove('hidden');
    const resultEl = document.getElementById('toss-result');
    resultEl.textContent = `${winner.name} wins the toss!`;
    resultEl.classList.remove('hidden');

    const humanWonToss = AppState.playerMode === 'human_vs_ai'
      && winner.id === AppState.humanTeamId;
    const humanChooses = AppState.playerMode === 'human_vs_human' || humanWonToss;

    if (!humanChooses) {
      // AI vs AI, or human_vs_ai where the AI won: AI decides automatically
      const autoChoice = Math.random() < 0.5 ? 'bat' : 'field';
      const autoLabel  = autoChoice === 'bat' ? 'bat' : 'field';
      document.getElementById('toss-winner-line').textContent =
        `${winner.name} elect to ${autoLabel}`;
      confirmToss(autoChoice);
    } else {
      // Human won the toss: let them choose
      document.getElementById('toss-winner-line').textContent =
        `${winner.name} — choose to:`;
      document.getElementById('toss-choice-area').classList.remove('hidden');
    }
  }, 1650);
}

async function confirmToss(choice) {
  // Disable bat/field buttons immediately
  document.querySelectorAll('.toss-choices .btn').forEach(b => b.disabled = true);

  const res = await api('POST', `/api/matches/${getMatchId()}/toss`, {
    toss_winner_id: MatchUI.tossCoinWinner,
    toss_choice:    choice,
  });
  if (!res) return;

  // Show "Let's play cricket!" card
  document.getElementById('toss-choice-area').classList.add('hidden');
  document.getElementById('toss-result').classList.add('hidden');
  const lpc = document.getElementById('toss-lpc');
  lpc.classList.remove('hidden');

  const hold = AppState.broadcastMode ? 3000 : 1500;
  await sleep(hold);

  lpc.classList.add('hidden');
  MatchUI.lastState = res;
  buildAllPlayersMap(res);
  document.getElementById('match-toss-screen').classList.add('hidden');
  initLiveView(res);
}

// ── Live view init ────────────────────────────────────────────────────────────

function buildAllPlayersMap(state) {
  const players = [
    ...(state.batting_team_players || []),
    ...(state.bowling_team_players || []),
  ];
  players.forEach(p => { MatchUI.allPlayers[p.id] = p; });
}

const TEAM_FLAGS = {
  'Afghanistan': '🇦🇫',
  'Australia': '🇦🇺',
  'Bangladesh': '🇧🇩',
  'Canada': '🇨🇦',
  'India': '🇮🇳',
  'Ireland': '🇮🇪',
  'Namibia': '🇳🇦',
  'Netherlands': '🇳🇱',
  'Nepal': '🇳🇵',
  'New Zealand': '🇳🇿',
  'Oman': '🇴🇲',
  'Pakistan': '🇵🇰',
  'South Africa': '🇿🇦',
  'Sri Lanka': '🇱🇰',
  'UAE': '🇦🇪',
  'United Arab Emirates': '🇦🇪',
  'United States': '🇺🇸',
  'USA': '🇺🇸',
  'Zimbabwe': '🇿🇼',
};

function getTeamFlag(teamName) {
  if (!teamName) return '';
  const normalized = String(teamName).trim();
  if (!normalized) return '';
  if (TEAM_FLAGS[normalized]) return TEAM_FLAGS[normalized];
  const base = normalized.replace(/\s+(Men|Women|XI|A)\b.*$/i, '').trim();
  return TEAM_FLAGS[base] || '';
}

function renderTeamLabel(teamName, { compact = false } = {}) {
  const safeName = escHtml(teamName || '');
  if ((teamName || '').trim() === 'England') {
    return `<span class="tv-team-inline${compact ? ' compact' : ''}"><span class="tv-flag tv-flag-england" aria-label="England flag"></span><span class="tv-team-name">${safeName}</span></span>`;
  }
  if ((teamName || '').trim() === 'Scotland') {
    return `<span class="tv-team-inline${compact ? ' compact' : ''}"><span class="tv-flag tv-flag-scotland" aria-label="Scotland flag"></span><span class="tv-team-name">${safeName}</span></span>`;
  }
  const flag = getTeamFlag(teamName);
  if (!flag) return safeName;
  return `<span class="tv-team-inline${compact ? ' compact' : ''}"><span class="tv-flag" aria-hidden="true">${flag}</span><span class="tv-team-name">${safeName}</span></span>`;
}

function initLiveView(state) {
  const m = state.match || AppState.activeMatch;
  const matchId = m.id || getMatchId();
  const playerMode = AppState.activeMatch?.playerMode || m.player_mode || 'ai_vs_ai';
  AppState.playerMode  = playerMode;
  AppState.humanTeamId = AppState.activeMatch?.humanTeamId || m.human_team_id || null;

  // Title
  document.getElementById('match-title').innerHTML =
    `${renderTeamLabel(m.team1_name, { compact: true })} <span class="match-title-sep">vs</span> ${renderTeamLabel(m.team2_name, { compact: true })} — ${escHtml(m.format)}, ${escHtml(m.venue_name || '')}`;
  const contextBits = [];
  if (m.series_id) contextBits.push(`Series #${m.series_id}`);
  contextBits.push(`${SCORING_MODE_META[(m.scoring_mode === 'classic' ? 'classic' : 'modern')].label} Scoring`);
  document.getElementById('match-context').textContent = contextBits.join(' · ');
  updateHowzatLegend(m.scoring_mode);

  // Mode badge
  const modeBadgeEl = document.getElementById('match-mode-badge');
  if (modeBadgeEl) {
    const { label, cls } = _modeInfo(playerMode);
    modeBadgeEl.textContent = label;
    modeBadgeEl.className = `match-mode-badge badge badge-${cls}`;
  }

  // Show live view
  document.getElementById('match-live').classList.remove('hidden');

  // Declare button only in Test
  const declareBtn = document.getElementById('btn-declare');
  declareBtn.classList.toggle('hidden', m.format !== 'Test');

  // Day sim button only in Test
  const dayBtn = document.getElementById('btn-sim-day');
  if (dayBtn) dayBtn.classList.toggle('hidden', m.format !== 'Test');

  // AI vs AI playback controls
  const pbCtrl = document.getElementById('ai-playback-controls');
  if (pbCtrl) pbCtrl.classList.toggle('hidden', playerMode !== 'ai_vs_ai');

  // Restore AI speed preference
  try {
    const savedSpeed = localStorage.getItem('ribi_ai_speed');
    if (savedSpeed) {
      MatchUI.aiPlay.speed = savedSpeed;
      document.querySelectorAll('.ai-speed-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.speed === savedSpeed));
    }
  } catch (_) {}

  MatchUI.commentaryLines = [];
  document.getElementById('commentary-feed').innerHTML = '';
  renderDieFace(0);
  document.getElementById('die-stage-label').textContent = '';

  // Reset state machine
  MatchUI.diceState              = DiceState.IDLE;
  MatchUI._pendingDelivery       = null;
  MatchUI._pendingRes            = null;
  MatchUI._ballInProgress        = false;
  MatchUI._pendingRollModeSwitch = null;
  MatchUI._dismissedSuggestions  = [];

  // Restore roll mode preference
  try {
    const savedMode = localStorage.getItem('ribi_roll_mode');
    if (savedMode === 'manual' || savedMode === 'auto') {
      MatchUI.rollMode = savedMode;
    } else {
      MatchUI.rollMode = 'auto';
    }
  } catch (_) { MatchUI.rollMode = 'auto'; }

  // Roll mode toggle visibility
  const toggleEl = document.getElementById('roll-mode-toggle');
  if (toggleEl) {
    // Show toggle for all human-involved modes; hide only for pure AI vs AI
    toggleEl.classList.toggle('hidden', false);
    // AI vs AI: show toggle but force auto and grey it out
    if (playerMode === 'ai_vs_ai') {
      toggleEl.classList.add('forced');
      MatchUI.rollMode = 'auto';
      document.getElementById('roll-mode-forced-label')?.classList.remove('hidden');
    } else {
      toggleEl.classList.remove('forced');
      document.getElementById('roll-mode-forced-label')?.classList.add('hidden');
    }
    _applyRollMode(MatchUI.rollMode);
  }

  // Ensure all manual UI is hidden on init
  document.getElementById('manual-howzat-display')?.classList.add('hidden');
  document.getElementById('manual-action-btns')?.classList.add('hidden');
  document.getElementById('free-hit-banner')?.classList.add('hidden');
  document.getElementById('tension-suggestion')?.classList.add('hidden');

  updateLiveView(state);
  _drawInningsArcFromState(state);

  // Start AI auto-play if applicable
  if (playerMode === 'ai_vs_ai') {
    _startAiAutoPlay();
  }
}

function updateLiveView(state) {
  MatchUI.lastState = state;
  buildAllPlayersMap(state);

  const inn    = state.current_innings;
  const match  = state.match || AppState.activeMatch;

  if (!inn || MatchUI._liveWagonInningsId !== state.current_innings_id) {
    MatchUI._liveWagonInningsId = state.current_innings_id || null;
    MatchUI._liveWagonOverNumber = state.over_number ?? null;
    MatchUI._liveWagonShots = [];
  } else if (MatchUI._liveWagonOverNumber !== (state.over_number ?? null)) {
    MatchUI._liveWagonOverNumber = state.over_number ?? null;
    MatchUI._liveWagonShots = [];
  }
  renderLiveWagonWheel();

  // Scoreboard
  if (inn) {
    document.getElementById('sb-team').innerHTML =
      renderTeamLabel(inn.batting_team_name || inn.batting_team_code || '');
    document.getElementById('sb-score').textContent =
      formatScore(inn.total_runs, inn.total_wickets);
    const overs = inn.overs_completed || 0;
    document.getElementById('sb-overs').textContent = `${formatOvers(overs)} ov`;

    const legalBalls = state.over_number * 6 + state.ball_in_over;
    const crr = legalBalls >= 6
      ? (inn.total_runs / (legalBalls / 6)).toFixed(2)
      : '—';
    document.getElementById('sb-rr').textContent = `RR: ${crr}`;

    const chaseEl = document.getElementById('sb-chase');
    if (state.target) {
      chaseEl.classList.remove('hidden');
      document.getElementById('sb-target').textContent =
        `Target: ${state.target}`;
      const needed = state.target - inn.total_runs;
      const maxLegalBalls = oversToLegalBalls(state.max_overs || 0);
      const remainingBalls = Math.max(0, maxLegalBalls - legalBalls);
      const remOvers = remainingBalls / 6;
      const rrr = remOvers > 0 ? (needed / remOvers).toFixed(2) : '—';
      document.getElementById('sb-required').textContent =
        `Need ${needed} (RRR: ${rrr})`;
    } else {
      chaseEl.classList.add('hidden');
    }
  }

  // Batters
  renderBatterRow('batter1-row', state, true);
  renderBatterRow('batter2-row', state, false);

  // Bowler
  renderBowlerRow(state);

  // Story strip
  renderStoryStrip(state);

  // Situation panel (current over, partnership, fall of wickets)
  renderMatchSituationPanel(state);

  // Scorecard tab
  renderScorecardTab(state);

  // Buttons
  const fmt = state.format || match?.format;
  const isTest = fmt === 'Test';
  const allInningsComplete = !inn;
  document.getElementById('btn-declare').classList.toggle('hidden', !isTest);
  document.getElementById('btn-complete-match').classList.toggle(
    'hidden', !allInningsComplete
  );

  // Mode-aware indicators
  _updateModeControls(state);

  // Background tint
  applyMatchTint(state);
}

function renderBatterRow(rowId, state, isStriker) {
  const el = document.getElementById(rowId);
  if (!el) return;
  const pid = isStriker
    ? state.current_striker_id
    : state.current_non_striker_id;
  if (!pid) { el.innerHTML = ''; return; }

  const p = MatchUI.allPlayers[pid] || {};
  const bi = (state.batter_innings || []).find(
    b => b.player_id === pid && b.status === 'batting'
  ) || {};

  const runs   = bi.runs || 0;
  const balls  = bi.balls_faced || 0;
  const fours  = bi.fours || 0;
  const sixes  = bi.sixes || 0;
  const sr     = balls > 0 ? ((runs / balls) * 100).toFixed(1) : '0.0';

  el.innerHTML = `
    <div class="batter-name${isStriker ? ' on-strike' : ''}">${p.name || `Player ${pid}`}</div>
    <div class="batter-stats">${runs} (${balls}b) ${fours}x4 ${sixes}x6 SR:${sr}</div>
  `;
}

function renderBowlerRow(state) {
  const el = document.getElementById('bowler-row');
  if (!el) return;
  const pid = state.current_bowler_id;
  if (!pid) { el.innerHTML = '<div class="bowler-name text-muted">— awaiting bowler —</div>'; return; }

  const p  = MatchUI.allPlayers[pid] || {};
  const bwi = (state.bowler_innings || []).find(b => b.player_id === pid) || {};
  const overs    = bwi.overs || 0;
  const balls    = bwi.balls || 0;
  const maidens  = bwi.maidens || 0;
  const runs     = bwi.runs_conceded || 0;
  const wickets  = bwi.wickets || 0;
  const oversF   = overs + balls / 6;
  const econ     = oversF > 0 ? (runs / oversF).toFixed(2) : '0.00';

  el.innerHTML = `
    <div class="bowler-name">${p.name || `Player ${pid}`}</div>
    <div class="bowler-stats">${formatBowlerOvers(overs, balls)}-${maidens}-${runs}-${wickets}  Econ:${econ}</div>
  `;
}

function renderStoryStrip(state) {
  const el = document.getElementById('sb-story-strip');
  if (!el) return;

  const inn = state.current_innings;
  if (!inn) {
    el.classList.add('hidden');
    el.innerHTML = '';
    MatchUI._storyState = { key: '', primaryTone: 'neutral', alertedKey: '' };
    return;
  }

  const stories = [];
  const striker = (state.batter_innings || []).find(
    b => b.player_id === state.current_striker_id && b.status === 'batting'
  ) || {};
  const nonStriker = (state.batter_innings || []).find(
    b => b.player_id === state.current_non_striker_id && b.status === 'batting'
  ) || {};
  const bowler = (state.bowler_innings || []).find(
    b => b.player_id === state.current_bowler_id
  ) || {};
  const activePship = (state.partnerships || []).length
    ? state.partnerships[state.partnerships.length - 1]
    : null;

  const strikerName = (MatchUI.allPlayers[state.current_striker_id]?.name || '').split(' ').pop();
  const nonStrikerName = (MatchUI.allPlayers[state.current_non_striker_id]?.name || '').split(' ').pop();
  const bowlerName = (MatchUI.allPlayers[state.current_bowler_id]?.name || '').split(' ').pop();

  if (state.target) {
    const legalBalls = (state.over_number || 0) * 6 + (state.ball_in_over || 0);
    const maxLegalBalls = oversToLegalBalls(state.max_overs || 0);
    const ballsLeft = Math.max(0, maxLegalBalls - legalBalls);
    const runsNeeded = Math.max(0, state.target - inn.total_runs);
    if (runsNeeded > 0) {
      stories.push({ tone: 'pressure', text: `${runsNeeded} needed from ${ballsLeft} balls` });
    }
    if (ballsLeft > 0) {
      const rrr = runsNeeded / (ballsLeft / 6);
      if (rrr >= 12) stories.push({ tone: 'pressure', text: `Required rate ${rrr.toFixed(2)}` });
    }
    if ((10 - (inn.total_wickets || 0)) <= 2) {
      stories.push({ tone: 'danger', text: `${10 - (inn.total_wickets || 0)} wickets left` });
    }
  }

  for (const batter of [striker, nonStriker]) {
    const runs = batter.runs || 0;
    if (runs >= 90 && runs < 100) {
      const name = (MatchUI.allPlayers[batter.player_id]?.name || '').split(' ').pop();
      stories.push({ tone: 'milestone', text: `${name} nearing a century (${runs})` });
      break;
    }
    if (runs >= 45 && runs < 50) {
      const name = (MatchUI.allPlayers[batter.player_id]?.name || '').split(' ').pop();
      stories.push({ tone: 'milestone', text: `${name} closing on fifty (${runs})` });
      break;
    }
  }

  if (activePship) {
    const pr = activePship.runs || 0;
    if (pr >= 75) stories.push({ tone: 'hot', text: `${pr}-run stand: ${strikerName} & ${nonStrikerName}` });
    else if (pr >= 40) stories.push({ tone: 'neutral', text: `Partnership building: ${pr} runs` });
  }

  if (bowler.wickets >= 2 && bowlerName) {
    stories.push({ tone: 'danger', text: `${bowlerName} has ${bowler.wickets} wickets` });
  }
  if ((bowler.maidens || 0) > 0 && bowlerName) {
    stories.push({ tone: 'neutral', text: `${bowlerName} has bowled ${bowler.maidens} maiden${bowler.maidens > 1 ? 's' : ''}` });
  }

  const overBalls = state.current_over_deliveries || [];
  if (overBalls.length >= 3) {
    const recentRuns = overBalls.reduce((sum, d) => sum + (d.runs_scored || 0) + ((d.is_wide || d.is_no_ball) ? 1 : 0), 0);
    const wicketThisOver = overBalls.some(d => d.outcome_type === 'wicket');
    if (wicketThisOver) {
      stories.push({ tone: 'danger', text: 'Wicket in the over - pressure on' });
    } else if (recentRuns >= 10) {
      stories.push({ tone: 'hot', text: `${recentRuns} runs already in this over` });
    } else if (recentRuns === 0 && overBalls.length >= 4) {
      stories.push({ tone: 'neutral', text: 'Dot-ball pressure building' });
    }
  }

  const uniqueStories = [];
  const seen = new Set();
  for (const story of stories) {
    if (!story?.text || seen.has(story.text)) continue;
    seen.add(story.text);
    uniqueStories.push(story);
    if (uniqueStories.length >= 4) break;
  }

  if (!uniqueStories.length) {
    el.classList.add('hidden');
    el.innerHTML = '';
    MatchUI._storyState = { key: '', primaryTone: 'neutral', alertedKey: '' };
    return;
  }

  const storyKey = uniqueStories.map(story => `${story.tone}:${story.text}`).join('|');
  const primaryTone = uniqueStories[0]?.tone || 'neutral';
  const changed = storyKey !== MatchUI._storyState.key;
  const alertedKey = MatchUI._storyState.alertedKey || '';
  MatchUI._storyState = { key: storyKey, primaryTone, alertedKey };

  el.innerHTML = uniqueStories.map(story =>
    `<div class="story-pill story-pill-${story.tone}">${escHtml(story.text)}</div>`
  ).join('');
  el.classList.remove('hidden');
  el.classList.toggle('story-strip-live', changed);
  if (changed) {
    _queueStoryAlert(uniqueStories[0], storyKey);
    setTimeout(() => {
      if (document.getElementById('sb-story-strip') === el) {
        el.classList.remove('story-strip-live');
      }
    }, 950);
  }
}

function _queueStoryAlert(primaryStory, storyKey) {
  if (!primaryStory || !storyKey) return;
  if (!['pressure', 'danger', 'milestone', 'hot'].includes(primaryStory.tone)) return;
  if (MatchUI._storyState.alertedKey === storyKey) return;

  const toneLabel = {
    pressure: 'Pressure Watch',
    danger: 'Match Turning',
    milestone: 'Milestone Watch',
    hot: 'Momentum Shift'
  }[primaryStory.tone] || 'Story Update';

  GraphicQueue.add({
    type: 'story_alert',
    label: toneLabel,
    text: primaryStory.text,
    tone: primaryStory.tone
  });
  MatchUI._storyState.alertedKey = storyKey;
}

// ── Match situation panel ─────────────────────────────────────────────────────

function renderMatchSituationPanel(state) {
  const el = document.getElementById('sb-situation');
  if (!el) return;

  const inn = state.current_innings;
  if (!inn) { el.innerHTML = ''; return; }

  const parts = [];

  // ── Current over ball-by-ball ──────────────────────────────────────────────
  const overBalls = state.current_over_deliveries || [];
  if (state.ball_in_over > 0 || overBalls.length > 0) {
    const ballTokens = overBalls.map(d => {
      if (d.is_wide)    return '<span class="situ-ball situ-ball-wide">Wd</span>';
      if (d.is_no_ball) return '<span class="situ-ball situ-ball-nb">Nb</span>';
      const ot = d.outcome_type;
      if (ot === 'wicket') return '<span class="situ-ball situ-ball-wicket">W</span>';
      if (ot === 'six')    return '<span class="situ-ball situ-ball-six">6</span>';
      if (ot === 'four')   return '<span class="situ-ball situ-ball-four">4</span>';
      const r = d.runs_scored || 0;
      if (r > 0) return `<span class="situ-ball situ-ball-runs">${r}</span>`;
      return '<span class="situ-ball situ-ball-dot">·</span>';
    });
    // Pad to 6 slots with placeholders
    while (ballTokens.length < 6) {
      ballTokens.push('<span class="situ-ball situ-ball-empty"></span>');
    }
    const overNum = state.over_number + 1;
    parts.push(`<div class="situ-row situ-over-row">
      <span class="situ-label">Over ${overNum}</span>
      <span class="situ-balls">${ballTokens.join('')}</span>
    </div>`);
  }

  // ── Current partnership ────────────────────────────────────────────────────
  const partnerships = state.partnerships || [];
  const activePship = partnerships.length > 0 ? partnerships[partnerships.length - 1] : null;
  if (activePship) {
    const b1 = activePship.batter1_name || '';
    const b2 = activePship.batter2_name || '';
    const pr = activePship.runs || 0;
    const pb = activePship.balls || 0;
    // Shorten names to last name only
    const lastName = n => n.split(' ').pop();
    parts.push(`<div class="situ-row">
      <span class="situ-label">Partnership</span>
      <span class="situ-value"><strong>${pr}</strong> (${pb}b) &mdash; ${lastName(b1)} &amp; ${lastName(b2)}</span>
    </div>`);
  }

  // ── Fall of wickets ────────────────────────────────────────────────────────
  const fow = state.fall_of_wickets || [];
  if (fow.length > 0) {
    const fowTokens = fow.map(w => {
      const lastName = (w.batter_name || '').split(' ').pop();
      return `<span class="situ-fow-item" title="${w.batter_name}">${w.wicket_number}-${w.score_at_fall} <span class="situ-fow-name">${lastName}</span></span>`;
    });
    parts.push(`<div class="situ-row situ-fow-row">
      <span class="situ-label">FoW</span>
      <span class="situ-fow">${fowTokens.join('')}</span>
    </div>`);
  }

  el.innerHTML = parts.length ? parts.join('') : '';
}

// ── Die face rendering ────────────────────────────────────────────────────────

const DIE_PIPS = {
  0: '',  // question mark handled by CSS
  1: '<div class="pip" style="grid-area:2/2"></div>',
  2: '<div class="pip" style="grid-area:1/1"></div><div class="pip" style="grid-area:3/3"></div>',
  3: '<div class="pip" style="grid-area:1/1"></div><div class="pip" style="grid-area:2/2"></div><div class="pip" style="grid-area:3/3"></div>',
  4: '<div class="pip" style="grid-area:1/1"></div><div class="pip" style="grid-area:1/3"></div><div class="pip" style="grid-area:3/1"></div><div class="pip" style="grid-area:3/3"></div>',
  5: '<div class="pip" style="grid-area:1/1"></div><div class="pip" style="grid-area:1/3"></div><div class="pip" style="grid-area:2/2"></div><div class="pip" style="grid-area:3/1"></div><div class="pip" style="grid-area:3/3"></div>',
  6: '<div class="pip" style="grid-area:1/1"></div><div class="pip" style="grid-area:1/3"></div><div class="pip" style="grid-area:2/1"></div><div class="pip" style="grid-area:2/3"></div><div class="pip" style="grid-area:3/1"></div><div class="pip" style="grid-area:3/3"></div>',
};

function renderDieFace(face, stageLabel) {
  const el = document.getElementById('die-face');
  if (!el) return;
  el.dataset.face = face;
  const pipsEl = el.querySelector('.die-pips');
  if (face === 0) {
    pipsEl.innerHTML = '';
    pipsEl.style.display = 'flex';
    pipsEl.style.alignItems = 'center';
    pipsEl.style.justifyContent = 'center';
    pipsEl.innerHTML = '<span style="font-size:32px;color:var(--text-muted)">?</span>';
  } else {
    pipsEl.style.display = 'grid';
    pipsEl.style.gridTemplateColumns = 'repeat(3, 1fr)';
    pipsEl.style.gridTemplateRows = 'repeat(3, 1fr)';
    pipsEl.innerHTML = DIE_PIPS[face] || '';
  }
  if (stageLabel !== undefined) {
    setDieStageLabel(stageLabel || '');
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function setDieStageLabel(message = '', tone = 'neutral', allowHtml = false) {
  const labelEl = document.getElementById('die-stage-label');
  if (!labelEl) return;
  labelEl.classList.remove('tone-neutral', 'tone-hype', 'tone-alert', 'tone-wicket', 'tone-good');
  labelEl.classList.add(`tone-${tone}`);
  if (allowHtml) labelEl.innerHTML = message;
  else labelEl.textContent = message;
}

function _titleCaseWords(s) {
  return String(s || '')
    .split('_')
    .filter(Boolean)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function getCurrentMatchScoringMode() {
  return MatchUI.lastState?.match?.scoring_mode
    || AppState.activeMatch?.scoring_mode
    || getDefaultScoringMode();
}

function _liveWagonCanvas() {
  const canvas = document.getElementById('canvas-live-wagon');
  return canvas ? { canvas, ctx: canvas.getContext('2d') } : null;
}

function _drawLiveWagonBase(ctx, W, H) {
  const cx = W / 2;
  const cy = H / 2;
  const boundaryR = Math.min(W, H) * 0.42;
  const circleR = boundaryR * 0.62;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0b1e0b';
  ctx.fillRect(0, 0, W, H);
  ctx.beginPath();
  ctx.arc(cx, cy, boundaryR, 0, Math.PI * 2);
  ctx.fillStyle = '#102810';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, circleR, 0, Math.PI * 2);
  ctx.fillStyle = '#143114';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, boundaryR, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.lineWidth = 1.8;
  ctx.stroke();
  ctx.save();
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  ctx.arc(cx, cy, circleR, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.14)';
  ctx.lineWidth = 1.1;
  ctx.stroke();
  ctx.restore();
  ctx.fillStyle = 'rgba(190,155,80,0.22)';
  ctx.fillRect(cx - 5, cy - 34, 10, 68);
  ctx.beginPath();
  ctx.arc(cx, cy, 4, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.fill();
}

function _wagonOutcomeColour(outcomeType) {
  return {
    single: 'rgba(100,200,255,0.78)',
    two: 'rgba(100,200,255,0.88)',
    three: 'rgba(255,200,100,0.88)',
    four: 'rgba(100,255,100,1.00)',
    six: 'rgba(255,215,0,1.00)',
    wicket: 'rgba(255,60,60,0.92)',
    dot: 'rgba(255,255,255,0.32)',
  }[outcomeType] || 'rgba(180,220,255,0.55)';
}

function _wagonOutcomeLength(outcomeType, boundaryR) {
  return {
    dot: 20,
    single: 34,
    two: 52,
    three: 66,
    four: boundaryR,
    six: boundaryR + 18,
    wicket: 40,
  }[outcomeType] ?? 34;
}

function renderLiveWagonWheel() {
  const c = _liveWagonCanvas();
  if (!c) return;
  const { canvas, ctx } = c;
  const W = canvas.width;
  const H = canvas.height;
  const cx = W / 2;
  const cy = H / 2;
  const boundaryR = Math.min(W, H) * 0.42;
  _drawLiveWagonBase(ctx, W, H);

  for (const shot of MatchUI._liveWagonShots.slice(-10)) {
    if (shot.shot_angle == null) continue;
    const rad = shot.shot_angle * Math.PI / 180;
    const dx = -Math.sin(rad);
    const dy = -Math.cos(rad);
    const len = _wagonOutcomeLength(shot.outcome_type, boundaryR);
    const ex = cx + dx * len;
    const ey = cy + dy * len;
    const col = _wagonOutcomeColour(shot.outcome_type);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ex, ey);
    ctx.strokeStyle = col;
    ctx.lineWidth = (shot.outcome_type === 'four' || shot.outcome_type === 'six' || shot.outcome_type === 'wicket') ? 2.4 : 1.5;
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(ex, ey, shot.outcome_type === 'wicket' ? 4 : 2.5, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
  }
}

function animateLiveWagonShot(delivery) {
  if (!delivery || delivery.shot_angle == null) {
    renderLiveWagonWheel();
    return;
  }
  const c = _liveWagonCanvas();
  if (!c) return;
  const { canvas, ctx } = c;
  const W = canvas.width;
  const H = canvas.height;
  const cx = W / 2;
  const cy = H / 2;
  const boundaryR = Math.min(W, H) * 0.42;
  const rad = delivery.shot_angle * Math.PI / 180;
  const dx = -Math.sin(rad);
  const dy = -Math.cos(rad);
  const len = _wagonOutcomeLength(delivery.outcome_type, boundaryR);
  const ex = cx + dx * len;
  const ey = cy + dy * len;
  const col = _wagonOutcomeColour(delivery.outcome_type);
  const startMs = performance.now();
  const duration = animMs(AppState.broadcastMode ? 850 : 520, AppState.broadcastMode ? 420 : 260, 0);

  const frame = now => {
    renderLiveWagonWheel();
    if (duration === 0) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = col;
      ctx.lineWidth = 2.4;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(ex, ey, delivery.outcome_type === 'wicket' ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
      return;
    }
    const p = Math.min(1, (now - startMs) / duration);
    const mx = cx + (ex - cx) * p;
    const my = cy + (ey - cy) * p;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(mx, my);
    ctx.strokeStyle = col;
    ctx.lineWidth = (delivery.outcome_type === 'four' || delivery.outcome_type === 'six' || delivery.outcome_type === 'wicket') ? 2.4 : 1.5;
    ctx.stroke();
    if (p >= 1) {
      ctx.beginPath();
      ctx.arc(ex, ey, delivery.outcome_type === 'wicket' ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function updateHowzatLegend(scoringMode = getCurrentMatchScoringMode()) {
  const mode = scoringMode === 'classic' ? 'classic' : 'modern';
  const modeEl = document.getElementById('howzat-legend-mode');
  const rowEl = document.getElementById('howzat-legend-row');
  const noteEl = document.getElementById('howzat-legend-note');
  if (modeEl) modeEl.textContent = SCORING_MODE_META[mode].label;
  if (rowEl) {
    rowEl.innerHTML = mode === 'classic'
      ? [
          '1 Single', '2 Two', '3 Three',
          '4 Four', '5 Appeal', '6 Six'
        ].map(text => `<span class="howzat-legend-chip">${text}</span>`).join('')
      : [
          '1 Single', '2 Two', '3 Three',
          '4 Four*', '5 Appeal', '6 Six*'
        ].map(text => `<span class="howzat-legend-chip">${text}</span>`).join('');
  }
  if (noteEl) {
    noteEl.textContent = mode === 'classic'
      ? 'Classic keeps every scoring face exactly literal.'
      : 'Modern can occasionally drag a 4 or 6 back in longer formats.';
  }
}

function _stage1Meaning(delivery) {
  const s1 = delivery.stage1_roll;
  const mode = getCurrentMatchScoringMode();
  if (s1 === 1) return 'Single';
  if (s1 === 2) return 'Two runs';
  if (s1 === 3) return 'Three runs';
  if (s1 === 4) {
    if (mode === 'modern' && delivery.outcome_type === 'three') return 'Boundary check - three';
    return 'Four runs';
  }
  if (s1 === 5) return 'Appeal ball';
  if (s1 === 6) {
    if (mode === 'modern' && delivery.outcome_type === 'four') return 'Big hit held to four';
    return 'Six runs';
  }
  return 'Delivery';
}

function _autoOutcomePresentation(delivery) {
  const ot = delivery.outcome_type || '';
  const stage1Text = delivery.stage1_roll != null
    ? `S1 ${delivery.stage1_roll}: ${_stage1Meaning(delivery)}`
    : '';
  if (ot === 'wicket') {
    return {
      text: stage1Text
        ? `${stage1Text} - OUT! ${_titleCaseWords(delivery.dismissal_type || 'wicket')}`
        : `OUT! ${_titleCaseWords(delivery.dismissal_type || 'wicket')}`,
      tone: 'wicket'
    };
  }
  if (ot === 'six')  return { text: `${stage1Text} - SIX! MAXIMUM`, tone: 'hype' };
  if (ot === 'four') return { text: `${stage1Text} - FOUR! TO THE ROPE`, tone: 'good' };
  if (ot === 'three') return { text: `${stage1Text} - THREE RUNS`, tone: 'good' };
  if (ot === 'two')   return { text: `${stage1Text} - TWO RUNS`, tone: 'good' };
  if (ot === 'single') return { text: `${stage1Text} - SINGLE TAKEN`, tone: 'neutral' };
  if (ot === 'wide')  return { text: `${stage1Text || 'Stage 3'} - WIDE BALL`, tone: 'alert' };
  if (ot === 'no_ball') return { text: `${stage1Text || 'Stage 3'} - NO BALL - FREE HIT`, tone: 'alert' };
  if (ot === 'bye') return { text: `${stage1Text || 'Stage 3'} - BYE`, tone: 'neutral' };
  if (ot === 'leg_bye') return { text: `${stage1Text || 'Stage 3'} - LEG BYE`, tone: 'neutral' };
  if (delivery.is_free_hit && ot !== 'wicket') {
    return { text: `${stage1Text} - FREE HIT SURVIVED`, tone: 'good' };
  }
  return { text: `${stage1Text || 'Stage 3'} - DOT BALL`, tone: 'neutral' };
}

function _autoStageFrames(delivery) {
  const frames = [
    {
      roll: delivery.stage1_roll,
      label: delivery.is_free_hit
        ? `STAGE 1 - ${delivery.stage1_roll}: ${_stage1Meaning(delivery)}`
        : `STAGE 1 - ${delivery.stage1_roll}: ${_stage1Meaning(delivery)}`,
      tone: delivery.is_free_hit ? 'alert' : 'neutral',
      hold: delivery.stage2_roll != null ? null : 0
    }
  ];

  if (delivery.stage2_roll != null) {
    frames.push({
      roll: delivery.stage2_roll,
      label: 'HOWZAT! UP GOES THE APPEAL',
      tone: 'alert',
      hold: null
    });
  }
  if (delivery.stage3_roll != null) {
    frames.push({
      roll: delivery.stage3_roll,
      label: delivery.is_free_hit ? 'FREE HIT - SAFE' : 'NOT OUT',
      tone: delivery.is_free_hit ? 'good' : 'neutral',
      hold: null
    });
  }
  if (delivery.stage4_roll != null) {
    frames.push({
      roll: delivery.stage4_roll,
      label: `OUT - ${_titleCaseWords(delivery.dismissal_type || 'wicket')}`,
      tone: 'wicket',
      hold: null
    });
  }
  if (delivery.stage4b_roll != null) {
    frames.push({
      roll: delivery.stage4b_roll,
      label: 'CAUGHT - BUT WHERE?',
      tone: 'alert',
      hold: null
    });
  }
  return frames;
}

async function animateDice(delivery) {
  const dieEl = document.getElementById('die-face');
  dieEl.classList.add('rolling');
  const broadcast   = AppState.broadcastMode;
  const stagePause  = animMs(broadcast ? 260 : 180, broadcast ? 120 : 80, 0);
  const suspensePause = animMs(broadcast ? 520 : 280, broadcast ? 180 : 120, 0);
  const totalMsBase = animMs(broadcast ? 1300 : 800, broadcast ? 420 : 260, 0);
  const highlightHold = (() => {
    const ot = delivery.outcome_type;
    if (ot === 'wicket') return animMs(broadcast ? 1500 : 850, broadcast ? 420 : 260, 0);
    if (ot === 'six' || ot === 'four') return animMs(broadcast ? 1100 : 650, broadcast ? 320 : 180, 0);
    if (ot === 'wide' || ot === 'no_ball') return animMs(broadcast ? 800 : 500, broadcast ? 220 : 140, 0);
    return animMs(broadcast ? 520 : 320, broadcast ? 180 : 100, 0);
  })();
  const stages = _autoStageFrames(delivery);
  const finalRoll = stages[stages.length - 1]?.roll ?? delivery.stage1_roll;
  const finalOutcome = _autoOutcomePresentation(delivery);

  if (delivery.is_free_hit) {
    _showFreeHitBanner(true);
  }

  if (totalMsBase === 0) {
    renderDieFace(finalRoll);
    setDieStageLabel(finalOutcome.text, finalOutcome.tone);
    dieEl.classList.remove('rolling');
    return;
  }

  let elapsed = 0;
  for (const stage of stages) {
    renderDieFace(stage.roll);
    setDieStageLabel(stage.label, stage.tone);
    const hold = (stage.label.includes('HOWZAT!') || stage.label === 'NOT OUT' || stage.label.startsWith('OUT -'))
      ? suspensePause
      : stagePause;
    await sleep(hold);
    elapsed += hold;
  }

  // Show random faces for any remaining animation budget before the verdict
  const remaining = totalMsBase - elapsed;
  if (remaining > 0) {
    const flickers = Math.max(2, Math.floor(remaining / 120));
    for (let i = 0; i < flickers; i++) {
      renderDieFace(Math.ceil(Math.random() * 6));
      await sleep(remaining / flickers);
    }
  }

  // Land on the decisive face and hold long enough for the outcome to read on stream
  renderDieFace(finalRoll);
  setDieStageLabel(finalOutcome.text, finalOutcome.tone);
  await sleep(highlightHold);
  dieEl.classList.remove('rolling');
}

// ── Roll Ball ─────────────────────────────────────────────────────────────────

async function rollBall() {
  // Guard: don't start a new ball if one is in progress
  if (MatchUI.diceState !== DiceState.IDLE) return;

  const currentState = MatchUI.lastState;
  const needsHumanBowlerChoice =
    currentState?.current_innings &&
    currentState.current_bowler_id === null &&
    !_isAiTurn(currentState);
  if (needsHumanBowlerChoice && !MatchUI.chosenBowlerId) {
    await _maybeShowBowlingPanel(currentState);
    if (!MatchUI.chosenBowlerId) return;
  }

  _setDiceState(DiceState.ROLLING_S1);
  MatchUI._ballInProgress = true;

  const btn = document.getElementById('btn-roll');
  if (btn) btn.disabled = true;

  const matchId = getMatchId();
  const animPromise = sleep(animMs(AppState.broadcastMode ? 1000 : 600, AppState.broadcastMode ? 300 : 200, 0));

  // Include chosen bowler_id if human made a selection
  const ballPayload = {};
  if (MatchUI.chosenBowlerId) {
    ballPayload.bowler_id = MatchUI.chosenBowlerId;
    MatchUI.chosenBowlerId = null;
  }
  const resPromise = api('POST', `/api/matches/${matchId}/ball`, ballPayload);
  const [res] = await Promise.all([resPromise, animPromise.then(() => null)]);

  if (!res) {
    _setDiceState(DiceState.IDLE);
    MatchUI._ballInProgress = false;
    if (btn) btn.disabled = false;
    return;
  }

  const delivery = res.delivery || {};

  // Manual mode for human turns: step-by-step reveal
  if (MatchUI.rollMode === 'manual' && !_isAiTurn(MatchUI.lastState)) {
    await _manualRollBegin(res, delivery);
    return; // _manualRollBegin (and its continuations) own the rest
  }

  // Auto mode (or AI turn): animate all stages, then complete
  await animateDice(delivery);
  _setDiceState(DiceState.RESULT);
  await _completeBall(res, delivery);
}

// ── Post-ball processing (shared by auto and manual paths) ────────────────────

async function _completeBall(res, delivery) {
  const matchId = getMatchId();
  const btn = document.getElementById('btn-roll');

  // Capture pre-ball state for graphic construction (before any state update)
  const preBallState = MatchUI.lastState;

  // Sound
  const ot = delivery.outcome_type;
  SoundEngine.play(ot);

  // Update session stats
  if (ot !== 'wicket' && ot !== 'wide' && ot !== 'no_ball') {
    AppState.sessionStats.runs += (delivery.runs_scored || 0);
  }
  if (ot === 'wicket') AppState.sessionStats.wickets += 1;
  if (ot === 'six')    AppState.sessionStats.sixes += 1;

  // Commentary
  await appendCommentaryLine(res, delivery);

  // Refresh state
  let fresh = null;
  if (res.match_state) {
    fresh = await api('GET', `/api/matches/${matchId}`);
    if (fresh) {
      updateLiveView(fresh);
      _drawInningsArcFromState(fresh);
    }
  }

  if (delivery.shot_angle != null && !['wide', 'no_ball', 'bye', 'leg_bye'].includes(delivery.outcome_type)) {
    MatchUI._liveWagonShots.push({
      shot_angle: delivery.shot_angle,
      outcome_type: delivery.outcome_type,
    });
    MatchUI._liveWagonShots = MatchUI._liveWagonShots.slice(-10);
    animateLiveWagonShot(delivery);
  } else {
    renderLiveWagonWheel();
  }

  // Queue broadcast graphics (fire-and-forget — never blocks Roll button)
  _detectAndQueueGraphics(res, delivery, preBallState, fresh);

  // Background tint
  applyMatchTintFromDelivery(ot);

  // Hide free-hit banner now the ball is done
  _showFreeHitBanner(false);

  // Innings complete
  if (res.innings_complete && !res.match_complete) {
    _stopAiAutoPlay();
    // Clear any playing graphic before the innings break takes over
    GraphicQueue.clear();
    // Reset dismissed suggestions — new innings, fresh slate
    MatchUI._dismissedSuggestions = [];
    document.getElementById('tension-suggestion')?.classList.add('hidden');
    const newState = MatchUI.lastState;
    const prevInnings = (newState?.innings || []).find(i => i.status === 'complete');
    _setDiceState(DiceState.INNINGS_END);
    await showInningsTransition(prevInnings, newState?.target);
    if (AppState.playerMode === 'ai_vs_ai') _startAiAutoPlay();
  }

  // Match complete
  if (res.match_complete) {
    _setDiceState(DiceState.MATCH_END);
    _stopAiAutoPlay();
    GraphicQueue.clear();
    AppState.sessionStats.matches += 1;
    updateSessionBar();
    await showResultScreen(matchId);
    _setDiceState(DiceState.IDLE);
    MatchUI._ballInProgress = false;
    if (btn) btn.disabled = false;
    return;
  }

  updateSessionBar();
  _setDiceState(DiceState.IDLE);
  MatchUI._ballInProgress = false;

  // Apply any queued mode switch
  if (MatchUI._pendingRollModeSwitch) {
    const queuedMode = MatchUI._pendingRollModeSwitch;
    MatchUI._pendingRollModeSwitch = null;
    _applyRollMode(queuedMode);
    _showToast('Switched to ' + (queuedMode === 'manual' ? 'Manual' : 'Auto') + ' mode', 1500);
  }

  // Poll tension suggestion after each ball (for human matches)
  if (AppState.playerMode !== 'ai_vs_ai') {
    _pollTension();
  }

  // Human vs AI: check if AI should take over
  const freshState = MatchUI.lastState;
  if (AppState.playerMode === 'human_vs_ai' && freshState && _isAiTurn(freshState)) {
    const delayMs = _AI_SPEED_MS[MatchUI.aiPlay.speed] ?? 800;
    MatchUI.aiPlay.running = true;
    MatchUI.aiPlay._timer = setTimeout(_aiAutoPlayLoop, delayMs);
    return;
  }

  // Check if human bowling change is needed for new over
  if (freshState && freshState.current_bowler_id === null && !_isAiTurn(freshState)) {
    await _maybeShowBowlingPanel(freshState);
  }

  if (btn) btn.disabled = false;
}

// ── Manual Roll Flow ──────────────────────────────────────────────────────────

async function _manualRollBegin(res, delivery) {
  MatchUI._pendingDelivery = delivery;
  MatchUI._pendingRes      = res;

  // Show free hit banner if applicable
  if (delivery.is_free_hit) {
    _showFreeHitBanner(true);
  }

  // Animate Stage 1
  const s1Label = 'THE DELIVERY';
  await _manualAnimateStage(delivery.stage1_roll, s1Label);

  // Check if HOWZAT (stage2 exists = appeal was triggered)
  if (delivery.stage2_roll != null) {
    await _manualShowHowzat();
  } else {
    // Normal delivery — resolve immediately (stage3 if needed was pre-computed by API)
    _setDiceState(DiceState.RESULT);
    await _completeBall(res, delivery);
  }
}

/**
 * Animate a single die stage landing on the given face.
 * @param {number} face      - final face (1-6)
 * @param {string} labelText - stage label to display
 */
async function _manualAnimateStage(face, labelText) {
  const dieEl = document.getElementById('die-face');
  if (!dieEl) return;

  const broadcast  = AppState.broadcastMode;
  // Broadcast+Manual: 1.2s animation; normal: 0.7s
  const totalMs    = broadcast ? 1200 : 700;
  const flickerMs  = broadcast ? 80   : 60;

  dieEl.classList.add('rolling');
  dieEl.classList.remove('howzat-active');

  // Flicker through random faces
  const flickerCount = Math.floor(totalMs / flickerMs) - 2;
  for (let i = 0; i < flickerCount; i++) {
    renderDieFace(Math.ceil(Math.random() * 6), labelText);
    await sleep(flickerMs);
  }

  // Land on final face
  renderDieFace(face, labelText);
  dieEl.classList.remove('rolling');
}

async function _manualShowHowzat() {
  const delivery = MatchUI._pendingDelivery;
  const dieEl = document.getElementById('die-face');

  // Flash die red with HOWZAT styling
  if (dieEl) dieEl.classList.add('howzat-active');

  // Determine fielding team name for appeal text
  const state = MatchUI.lastState;
  const fieldingTeam = state?.current_innings?.bowling_team_name || 'The fielding team';

  // Update HOWZAT display
  const appealTeamEl = document.getElementById('howzat-appeal-team');
  if (appealTeamEl) {
    appealTeamEl.textContent = `${fieldingTeam.toUpperCase()} APPEAL!`;
  }

  // Play HOWZAT sound
  SoundEngine.play('howzat');

  // Broadcast mode: hold 2s before showing Appeal button for narrator
  const holdMs = AppState.broadcastMode ? 2000 : 500;
  await sleep(holdMs);

  // Transition to HOWZAT state (shows Appeal button)
  _setDiceState(DiceState.HOWZAT);
}

async function manualAppeal() {
  if (MatchUI.diceState !== DiceState.HOWZAT) return;

  const delivery = MatchUI._pendingDelivery;
  if (!delivery) return;

  _setDiceState(DiceState.ROLLING_S2);

  // Remove HOWZAT die styling
  const dieEl = document.getElementById('die-face');
  if (dieEl) dieEl.classList.remove('howzat-active');

  // Animate Stage 2
  await _manualAnimateStage(delivery.stage2_roll, 'THE UMPIRE CONSIDERS...');

  // Brief tension pause before result
  await sleep(AppState.broadcastMode ? 1000 : 500);

  // Determine outcome
  const isOut     = (delivery.outcome_type === 'wicket');
  const isFreeHit = delivery.is_free_hit;

  if (isOut && !isFreeHit) {
    // OUT! path
    await _manualShowOut();
  } else if (isOut && isFreeHit) {
    // Free hit overrides OUT → show "FREE HIT — cannot be out!" overlay
    await _manualShowFreeHitSave();
  } else {
    // NOT OUT path
    await _manualShowNotOut();
  }
}

async function _manualShowNotOut() {
  // Show NOT OUT message in stage label area
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) {
    stageLabelEl.innerHTML = '<span class="manual-result-notout">NOT OUT — the finger stays down</span>';
  }
  _setDiceState(DiceState.NOT_OUT);
}

async function _manualShowOut() {
  // Show OUT! in stage label area
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) {
    stageLabelEl.innerHTML = '<span class="manual-result-out">OUT!</span>';
  }
  SoundEngine.play('wicket');
  _setDiceState(DiceState.OUT_PENDING);
}

async function _manualShowFreeHitSave() {
  // Free hit prevents dismissal — show banner then continue to NOT OUT flow
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) {
    stageLabelEl.innerHTML = '<span class="manual-result-notout">FREE HIT — cannot be out!</span>';
  }
  _setDiceState(DiceState.NOT_OUT);
}

async function manualContinue() {
  if (MatchUI.diceState !== DiceState.NOT_OUT) return;

  const delivery = MatchUI._pendingDelivery;
  const res      = MatchUI._pendingRes;
  if (!delivery) return;

  _setDiceState(DiceState.ROLLING_S3);

  // Clear stage label
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) stageLabelEl.innerHTML = '';

  // Animate Stage 3 if it was rolled
  if (delivery.stage3_roll != null) {
    await _manualAnimateStage(delivery.stage3_roll, 'WHAT HAPPENED?');
  }

  _setDiceState(DiceState.RESULT);
  await _completeBall(res, delivery);
}

async function manualDismissal() {
  if (MatchUI.diceState !== DiceState.OUT_PENDING) return;

  const delivery = MatchUI._pendingDelivery;
  const res      = MatchUI._pendingRes;
  if (!delivery) return;

  _setDiceState(DiceState.ROLLING_S4);

  // Clear stage label
  const stageLabelEl = document.getElementById('die-stage-label');
  if (stageLabelEl) stageLabelEl.innerHTML = '';

  // Animate Stage 4 if present
  if (delivery.stage4_roll != null) {
    await _manualAnimateStage(delivery.stage4_roll, 'THE DISMISSAL');
  }

  // Check for caught — need Stage 4b
  if (delivery.dismissal_type === 'caught' && delivery.stage4b_roll != null) {
    // Show Caught Where? button
    const caughtWhereBtn = document.getElementById('btn-caught-where');
    const actionBtns = document.getElementById('manual-action-btns');
    if (actionBtns) actionBtns.classList.remove('hidden');
    if (caughtWhereBtn) caughtWhereBtn.classList.remove('hidden');
    // Stay in ROLLING_S4 state (with caught-where button visible)
    return;
  }

  // No Stage 4b needed — complete ball
  _setDiceState(DiceState.RESULT);
  await _completeBall(res, delivery);
}

async function manualCaughtWhere() {
  const delivery = MatchUI._pendingDelivery;
  const res      = MatchUI._pendingRes;
  if (!delivery) return;

  // Hide the caught-where button
  const caughtWhereBtn = document.getElementById('btn-caught-where');
  if (caughtWhereBtn) caughtWhereBtn.classList.add('hidden');

  _setDiceState(DiceState.ROLLING_S4B);

  // Animate Stage 4b
  if (delivery.stage4b_roll != null) {
    await _manualAnimateStage(delivery.stage4b_roll, 'CAUGHT — BUT WHERE?');
  }

  _setDiceState(DiceState.RESULT);
  await _completeBall(res, delivery);
}

// ── Roll Mode Toggle ──────────────────────────────────────────────────────────

/**
 * Set the rolling mode ('auto' or 'manual').
 * If a ball is in progress, the switch is queued until it completes.
 * @param {string} mode     - 'auto' | 'manual'
 * @param {boolean} silent  - if true, suppress the toast message
 */
function setRollMode(mode, silent = false) {
  if (mode !== 'auto' && mode !== 'manual') return;

  // AI vs AI: always force auto
  if (AppState.playerMode === 'ai_vs_ai') return;

  // If ball in progress switching Manual → Auto: queue switch
  if (MatchUI._ballInProgress && MatchUI.rollMode === 'manual' && mode === 'auto') {
    MatchUI._pendingRollModeSwitch = mode;
    if (!silent) {
      _showToast('Switching to Auto after this ball.', 2500);
    }
    return;
  }

  _applyRollMode(mode);
  if (!silent) {
    _showToast(mode === 'manual'
      ? '🎲 Manual mode — feel every appeal'
      : '⚡ Auto mode — all dice auto-resolve', 2000);
  }
}

/** Apply mode change immediately. */
function _applyRollMode(mode) {
  MatchUI.rollMode = mode;
  try { localStorage.setItem('ribi_roll_mode', mode); } catch (_) {}

  const autoBtn   = document.getElementById('btn-mode-auto');
  const manualBtn = document.getElementById('btn-mode-manual');
  if (autoBtn)   autoBtn.classList.toggle('active', mode === 'auto');
  if (manualBtn) manualBtn.classList.toggle('active', mode === 'manual');

  // Reset dismissed suggestions on mode change to manual
  if (mode === 'manual') {
    MatchUI._dismissedSuggestions = [];
  }

  // Hide tension banner when switching to manual
  if (mode === 'manual') {
    document.getElementById('tension-suggestion')?.classList.add('hidden');
  }
}

// ── Free Hit Banner ───────────────────────────────────────────────────────────

function _showFreeHitBanner(show) {
  const el = document.getElementById('free-hit-banner');
  if (el) el.classList.toggle('hidden', !show);
}

// ── Toast Utility ─────────────────────────────────────────────────────────────

function _showToast(message, durationMs = 2000) {
  if (durationMs === 0) return;
  const toast = document.createElement('div');
  toast.className = 'milestone-toast slide-up';
  toast.style.background = 'var(--surface2)';
  toast.style.border = '1px solid var(--border)';
  toast.innerHTML = `<div class="milestone-toast-text">${escHtml(message)}</div>`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    toast.style.opacity    = '0';
    toast.style.transform  = 'translateX(-50%) translateY(20px)';
    setTimeout(() => toast.remove(), 400);
  }, durationMs);
}

// ── Tension Suggestion System ─────────────────────────────────────────────────

async function _pollTension() {
  const matchId = getMatchId();
  if (!matchId) return;
  // Only poll when in auto mode — manual mode doesn't need suggestions
  if (MatchUI.rollMode !== 'auto') return;

  try {
    const data = await fetch(`/api/matches/${matchId}/tension`).then(r => r.ok ? r.json() : null);
    if (!data) return;
    if (data.suggest_manual && data.suggestion_key) {
      showTensionSuggestion(data);
    }
  } catch (_) {}
}

function showTensionSuggestion(data) {
  // Don't show if already dismissed this innings
  if (MatchUI._dismissedSuggestions.includes(data.suggestion_key)) return;
  // Don't show if already in manual mode
  if (MatchUI.rollMode === 'manual') return;
  // Don't show if toggle is not visible (AI vs AI)
  if (AppState.playerMode === 'ai_vs_ai') return;

  const el   = document.getElementById('tension-suggestion');
  const text = document.getElementById('tension-suggestion-text');
  if (!el || !text) return;

  text.textContent = data.suggestion_reason || '🎲 Switch to Manual mode?';
  el.dataset.key   = data.suggestion_key;
  el.classList.remove('hidden');
}

function tensionSuggestionClick() {
  const el = document.getElementById('tension-suggestion');
  if (!el) return;
  el.classList.add('hidden');
  setRollMode('manual');
}

function dismissTensionSuggestion() {
  const el = document.getElementById('tension-suggestion');
  if (!el) return;
  const key = el.dataset.key;
  if (key) MatchUI._dismissedSuggestions.push(key);
  el.classList.add('hidden');
}

// ── Simulation Controls ───────────────────────────────────────────────────────

async function simulateTo(target) {
  const matchId = getMatchId();
  if (!matchId) return;
  const shouldResumeAi = AppState.playerMode === 'ai_vs_ai' && MatchUI.aiPlay.running;
  _stopAiAutoPlay();

  // Disable all sim + roll buttons during simulation
  const allBtns = document.querySelectorAll('#btn-roll, .btn-sim, #btn-fast-sim');
  allBtns.forEach(b => { b.disabled = true; });

  // Snapshot score before
  const beforeState = MatchUI.lastState;
  const beforeInn   = beforeState?.current_innings;
  const beforeScore = beforeInn
    ? formatScore(beforeInn.total_runs, beforeInn.total_wickets)
    : '—';

  const res = await api('POST', `/api/matches/${matchId}/simulate`, { target });

  allBtns.forEach(b => { b.disabled = false; });

  if (!res) return;

  // Replace commentary with sim digest card
  const digest = res.sim_digest;
  if (digest) {
    renderSimDigest(digest, target, beforeScore);
  }

  // Refresh live view
  const fresh = await api('GET', `/api/matches/${matchId}`);
  if (fresh) {
    updateLiveView(fresh);
    _drawInningsArcFromState(fresh);
  }

  if (res.innings_complete && !res.match_complete) {
    _stopAiAutoPlay();
    GraphicQueue.clear();
    const newState = MatchUI.lastState;
    // Find the innings that just completed — use the highest innings_number among
    // complete innings, not the first, to avoid showing the 1st innings score when
    // the 2nd innings ends.
    const prevInn  = (newState?.innings || [])
      .filter(i => i.status === 'complete')
      .sort((a, b) => b.innings_number - a.innings_number)[0];
    await showInningsTransition(prevInn, newState?.target);
    if (AppState.playerMode === 'ai_vs_ai') _startAiAutoPlay();
  }

  if (res.match_complete) {
    _stopAiAutoPlay();
    GraphicQueue.clear();
    AppState.sessionStats.matches += 1;
    updateSessionBar();
    await showResultScreen(matchId);
    return;
  }

  if (shouldResumeAi && !MatchUI._transitionActive) {
    _startAiAutoPlay();
  }
}

function renderSimDigest(digest, target, beforeScore) {
  const feed = document.getElementById('commentary-feed');
  if (!feed) return;

  const targetLabels = {
    wicket: 'next wicket', over: 'end of over', session: 'session break',
    day: 'end of day', innings: 'end of innings', match: 'end of match',
  };
  const label = targetLabels[target] || target;

  // Wicket lines
  const wicketLines = (digest.wicket_events || []).map(w => {
    const dism = (w.dismissal_type || 'out').replace(/_/g, ' ');
    return `<div class="sd-wicket">🔴 ${w.batter} ${dism} for ${w.runs}</div>`;
  }).join('');

  // Key events
  const evLines = (digest.key_events || []).map(e =>
    `<div class="sd-event">⭐ ${e}</div>`
  ).join('');

  const overs = digest.overs_completed || 0;
  const oversDisp = formatOvers(overs);
  const overStr = oversDisp === '1' ? '1 over' : `${oversDisp} overs`;

  const html = `
    <div class="sim-digest-card">
      <div class="sd-header">
        <span class="sd-target">Simulated to ${label}</span>
        <span class="sd-range">${overStr} · ${digest.balls_bowled} balls</span>
      </div>
      <div class="sd-scores">
        <span class="sd-score-start">${beforeScore}</span>
        <span class="sd-arrow">→</span>
        <span class="sd-score-end">${digest.end_score || '—'}</span>
      </div>
      <div class="sd-summary">
        +${digest.runs_scored} runs · ${digest.wickets_fallen} wicket${digest.wickets_fallen !== 1 ? 's' : ''}
      </div>
      ${wicketLines}
      ${evLines}
      ${digest.result_string ? `<div class="sd-result">${digest.result_string}</div>` : ''}
    </div>`;

  // Prepend digest, keep any existing commentary below
  feed.insertAdjacentHTML('afterbegin', html);
}

// ── Commentary ────────────────────────────────────────────────────────────────

async function appendCommentaryLine(res, delivery) {
  const feed = document.getElementById('commentary-feed');
  if (!feed) return;

  const over   = delivery.over_number ?? '?';
  const ball   = delivery.ball_number ?? '?';
  const ot     = delivery.outcome_type || '';
  const text   = res.commentary || ot;

  let cssClass = 'cl-normal';
  if (ot === 'wicket')           cssClass = 'cl-wicket';
  else if (ot === 'six')         cssClass = 'cl-six';
  else if (ot === 'four')        cssClass = 'cl-boundary';
  else if (ot === 'wide' || ot === 'no_ball' || ot === 'bye' || ot === 'leg_bye')
                                  cssClass = 'cl-extras';
  else if (ot === 'dot')         cssClass = 'cl-dot';

  const div = document.createElement('div');
  div.className = `commentary-line ${cssClass}`;
  const prefix = `<span class="over-ball">${over}.${ball} •</span>`;
  const textSpan = document.createElement('span');
  div.innerHTML = prefix;
  div.appendChild(textSpan);
  feed.insertBefore(div, feed.firstChild);

  const wordDelay = animMs(AppState.broadcastMode ? 40 : 0, AppState.broadcastMode ? 10 : 0, 0);
  if (wordDelay > 0) {
    // Word-by-word reveal
    const words = text.split(' ');
    let built = '';
    for (const word of words) {
      built += (built ? ' ' : '') + escHtml(word);
      textSpan.innerHTML = built;
      await sleep(wordDelay);
    }
  } else {
    textSpan.innerHTML = escHtml(text);
  }

  // Keep max 15
  MatchUI.commentaryLines.unshift({ over, ball, text, cssClass });
  while (feed.children.length > 15) feed.removeChild(feed.lastChild);
  while (MatchUI.commentaryLines.length > 15) MatchUI.commentaryLines.pop();
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Milestones ────────────────────────────────────────────────────────────────

const MILESTONE_ICONS = {
  batter_50:   '🏏', batter_100: '💯', batter_150: '⭐', batter_200: '🌟',
  bowler_5fer: '🎳', bowler_10fer: '🏆',
  partnership_50: '🤝', partnership_100: '🤝', partnership_150: '🤝', partnership_200: '🤝',
};
const MILESTONE_LABELS = {
  batter_50:   'FIFTY!', batter_100: 'CENTURY!', batter_150: '150!', batter_200: 'DOUBLE CENTURY!',
  bowler_5fer: 'FIVE-FER!', bowler_10fer: 'TEN-WICKET HAUL!',
  partnership_50: '50 PARTNERSHIP', partnership_100: 'CENTURY PARTNERSHIP',
  partnership_150: '150 PARTNERSHIP', partnership_200: '200 PARTNERSHIP',
};

function showMilestoneToast(ms) {
  const broadcast = AppState.broadcastMode;
  const type  = ms.type;
  const icon  = MILESTONE_ICONS[type] || '🏏';
  const label = MILESTONE_LABELS[type] || type.toUpperCase();

  let playerName = '';
  if (ms.player_id && MatchUI.allPlayers[ms.player_id]) {
    playerName = MatchUI.allPlayers[ms.player_id].name;
  }

  SoundEngine.play('milestone');

  if (broadcast) {
    // Full-screen dim + centred card
    const dim = document.createElement('div');
    dim.className = 'milestone-toast-dim';
    const toast = document.createElement('div');
    toast.className = 'milestone-toast broadcast';
    toast.innerHTML = `
      <div class="milestone-toast-icon">${icon}</div>
      <div class="milestone-toast-type">${escHtml(label)}</div>
      <div class="milestone-toast-player">${escHtml(playerName)}</div>
    `;
    document.body.appendChild(dim);
    document.body.appendChild(toast);

    const broadcastHold = animMs(3000, 800, 0);
    if (broadcastHold === 0) {
      dim.remove(); toast.remove(); return;
    }
    return new Promise(resolve => {
      setTimeout(() => {
        toast.style.transition = 'opacity 0.5s ease';
        dim.style.transition   = 'opacity 0.5s ease';
        toast.style.opacity = '0';
        dim.style.opacity   = '0';
        setTimeout(() => { toast.remove(); dim.remove(); resolve(); }, 500);
      }, broadcastHold);
    });
  } else {
    // Slide-up from bottom toast
    const toast = document.createElement('div');
    toast.className = 'milestone-toast slide-up';
    toast.innerHTML = `
      <div class="milestone-toast-icon" style="font-size:24px">${icon}</div>
      <div class="milestone-toast-text">${escHtml(label)}${playerName ? ' — ' + escHtml(playerName) : ''}</div>
    `;
    const normalHold = animMs(2000, 600, 0);
    if (normalHold === 0) { return; }
    document.body.appendChild(toast);
    return new Promise(resolve => {
      setTimeout(() => {
        toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        toast.style.opacity    = '0';
        toast.style.transform  = 'translateX(-50%) translateY(20px)';
        setTimeout(() => { toast.remove(); resolve(); }, 400);
      }, normalHold);
    });
  }
}

// ── Record overlay ────────────────────────────────────────────────────────────

const RECORD_LABELS = {
  highest_individual_score: 'HIGHEST INDIVIDUAL SCORE',
  best_bowling_figures:     'BEST BOWLING FIGURES',
  highest_team_score:       'HIGHEST TEAM SCORE',
  highest_partnership:      'HIGHEST PARTNERSHIP',
  most_sixes_innings:       'MOST SIXES IN AN INNINGS',
  lowest_team_score:        'LOWEST TEAM SCORE',
};

function showRecordOverlay(rec) {
  // Accumulate for end-of-match summary (keep only the latest entry per type,
  // since a record might be broken multiple times in one match)
  const existing = MatchUI.recordsBroken.findIndex(r => r.type === rec.type);
  if (existing >= 0) MatchUI.recordsBroken[existing] = rec;
  else MatchUI.recordsBroken.push(rec);

  if (!AppState.recordPopups) return Promise.resolve();

  const broadcast = AppState.broadcastMode;
  const typeLabel = RECORD_LABELS[rec.type] || rec.type.toUpperCase().replace(/_/g, ' ');

  const dim = document.createElement('div');
  dim.className = 'record-overlay-dim';

  const card = document.createElement('div');
  card.className = 'record-overlay-card' + (broadcast ? ' broadcast' : '');
  card.innerHTML = `
    <div class="record-overlay-label">📖 NEW ALMANACK RECORD</div>
    <div class="record-overlay-type">${escHtml(typeLabel)}</div>
    <div class="record-overlay-value">${escHtml(String(rec.new_value))}</div>
    <div class="record-overlay-holder">${escHtml(rec.player_name || '')}</div>
    ${rec.previous_value != null
      ? `<div class="record-overlay-prev">Previous: ${escHtml(String(rec.previous_value))}${rec.previous_holder ? ' (' + escHtml(rec.previous_holder) + ')' : ''}</div>`
      : '<div class="record-overlay-prev">First ever record</div>'}
  `;

  document.body.appendChild(dim);
  document.body.appendChild(card);

  const hold = animMs(broadcast ? 4000 : 3000, broadcast ? 1200 : 800, 0);
  if (hold === 0) { card.remove(); dim.remove(); return; }
  return new Promise(resolve => {
    setTimeout(() => {
      card.style.transition = 'opacity 0.5s ease';
      dim.style.transition  = 'opacity 0.5s ease';
      card.style.opacity = '0';
      dim.style.opacity  = '0';
      setTimeout(() => { card.remove(); dim.remove(); resolve(); }, 500);
    }, hold);
  });
}

// ── Background tint ───────────────────────────────────────────────────────────

MatchUI._recentOutcomes = [];  // rolling last 10

function applyMatchTintFromDelivery(outcomeType) {
  MatchUI._recentOutcomes.push(outcomeType);
  if (MatchUI._recentOutcomes.length > 10) MatchUI._recentOutcomes.shift();
  applyMatchTint(null);
}

function applyMatchTint(_state) {
  const el = document.getElementById('screen-match');
  if (!el) return;
  el.classList.remove('situation-crisis', 'situation-dominant', 'situation-pressure', 'situation-hot', 'situation-milestone');

  const recent = MatchUI._recentOutcomes;
  // Check last 3 for wickets, last 10 for scoring dominance
  const last3     = recent.slice(-3);
  const wickets3  = last3.filter(o => o === 'wicket').length;
  const scoring10 = recent.filter(o => o === 'four' || o === 'six').length;
  const primaryTone = MatchUI._storyState?.primaryTone || 'neutral';

  if (wickets3 >= 2 || primaryTone === 'danger') {
    el.classList.add('situation-crisis');
  } else if (primaryTone === 'pressure') {
    el.classList.add('situation-pressure');
  } else if (scoring10 >= 3) {
    el.classList.add('situation-dominant');
  } else if (primaryTone === 'hot') {
    el.classList.add('situation-hot');
  } else if (primaryTone === 'milestone') {
    el.classList.add('situation-milestone');
  }
}

// ── Mode helpers ──────────────────────────────────────────────────────────────

function _modeInfo(mode) {
  if (mode === 'human_vs_ai')    return { label: 'Solo',  cls: 'solo' };
  if (mode === 'human_vs_human') return { label: '2P',    cls: '2p' };
  return                                { label: 'Auto',  cls: 'auto' };
}

function _modeBadgeHtml(mode) {
  if (!mode || mode === 'ai_vs_ai')    return '<span class="badge badge-auto">Auto</span>';
  if (mode === 'human_vs_ai')          return '<span class="badge badge-solo">Solo</span>';
  if (mode === 'human_vs_human')       return '<span class="badge badge-2p">2P</span>';
  return '';
}

function _canonBadgeHtml(status) {
  if (!status || status === 'canon') return '';   // canon is default — no badge needed
  if (status === 'exhibition') return '<span class="badge badge-exhibition" title="Exhibition — excluded from statistics">Exhib</span>';
  if (status === 'deleted')    return '<span class="badge badge-deleted" title="Soft-deleted">Deleted</span>';
  return '';
}

/** Returns true when the current batting/bowling team is AI-controlled. */
function _isAiTurn(state) {
  const mode = AppState.playerMode;
  if (mode === 'ai_vs_ai') return true;
  if (mode === 'human_vs_human') return false;
  // human_vs_ai: compare batting team id to humanTeamId
  const humanId = AppState.humanTeamId;
  const inn = state?.current_innings;
  if (!inn || !humanId) return true;
  // AI is in control when the batting team is NOT the human team AND bowling team is NOT the human
  // Since human manages both bat & bowl for their team, AI controls when neither is human:
  // actually human manages BOTH bat AND bowl for their team — only the OTHER team is AI
  const currentBattingTeam = inn.batting_team_id;
  const currentBowlingTeam = inn.bowling_team_id;
  return currentBattingTeam !== humanId && currentBowlingTeam !== humanId;
}

/** Returns true when human is the bowling team this over */
function _humanIsBowling(state) {
  if (AppState.playerMode !== 'human_vs_ai') return AppState.playerMode === 'human_vs_human';
  const humanId = AppState.humanTeamId;
  const inn = state?.current_innings;
  return inn && inn.bowling_team_id === humanId;
}

function _updateModeControls(state) {
  const mode = AppState.playerMode;
  const aiInd = document.getElementById('ai-indicator');
  const hvhBanner = document.getElementById('hvh-team-banner');
  const rollBtn = document.getElementById('btn-roll');

  if (mode === 'ai_vs_ai') {
    if (aiInd) aiInd.classList.add('hidden');
    if (hvhBanner) hvhBanner.classList.add('hidden');
    // Roll button hidden — AI controls everything
    if (rollBtn) { rollBtn.classList.add('hidden'); }
    return;
  }

  if (mode === 'human_vs_human') {
    if (aiInd) aiInd.classList.add('hidden');
    // In manual mode, roll button visibility is managed by _updateDiceStateUI
    if (MatchUI.rollMode !== 'manual') {
      if (rollBtn) rollBtn.classList.remove('hidden');
    }
    // Show team banner for current batting team
    if (hvhBanner && state?.current_innings) {
      const inn = state.current_innings;
      const teamName = inn.batting_team_name || '';
      const isNewOver = state.ball_in_over === 0 && state.current_bowler_id === null;
      const action = isNewOver ? 'YOUR OVER' : 'YOUR TURN';
      hvhBanner.textContent = `${teamName.toUpperCase()} — ${action}`;
      hvhBanner.classList.remove('hidden');
    } else if (hvhBanner) {
      hvhBanner.classList.add('hidden');
    }
    return;
  }

  if (mode === 'human_vs_ai') {
    if (hvhBanner) hvhBanner.classList.add('hidden');
    const isAiTurn = _isAiTurn(state);

    if (aiInd) {
      if (isAiTurn && state?.current_innings) {
        const inn = state.current_innings;
        const humanId = AppState.humanTeamId;
        const aiTeam = inn.batting_team_id === humanId ? inn.bowling_team_name : inn.batting_team_name;
        const action = inn.batting_team_id !== humanId ? 'batting' : 'bowling';
        aiInd.innerHTML = `<span class="ai-indicator-dot"></span> AI (${aiTeam}) is ${action}…`;
        aiInd.classList.remove('hidden');
      } else {
        aiInd.classList.add('hidden');
      }
    }
    if (rollBtn) {
      // In manual mode, visibility managed by _updateDiceStateUI; just handle text
      if (MatchUI.rollMode !== 'manual') rollBtn.classList.remove('hidden');
      if (isAiTurn) {
        rollBtn.disabled = true;
        rollBtn.innerHTML = '🤖 AI Controlling';
      } else if (MatchUI.diceState === DiceState.IDLE) {
        rollBtn.disabled = false;
        rollBtn.innerHTML = '🎲 Roll Ball<span class="kbd-hint">[Space]</span>';
      }
    }
  }
}

// ── AI vs AI Auto-play ─────────────────────────────────────────────────────────

const _AI_SPEED_MS = { slow: 2000, normal: 800, fast: 300, instant: 0 };

function _startAiAutoPlay() {
  MatchUI.aiPlay.running = true;
  MatchUI.aiPlay.paused  = false;
  _aiAutoPlayLoop();
}

function _stopAiAutoPlay() {
  MatchUI.aiPlay.running = false;
  MatchUI.aiPlay.paused  = false;
  if (MatchUI.aiPlay._timer) { clearTimeout(MatchUI.aiPlay._timer); MatchUI.aiPlay._timer = null; }
}

async function _aiAutoPlayLoop() {
  if (!MatchUI.aiPlay.running || MatchUI.aiPlay.paused || MatchUI._transitionActive) return;

  // Roll the next ball
  await rollBall();

  if (!MatchUI.aiPlay.running || MatchUI.aiPlay.paused || MatchUI._transitionActive) return;

  const delayMs = _AI_SPEED_MS[MatchUI.aiPlay.speed] ?? 800;
  if (delayMs <= 0) {
    _aiAutoPlayLoop();  // immediate recursion for instant mode
  } else {
    MatchUI.aiPlay._timer = setTimeout(_aiAutoPlayLoop, delayMs);
  }
}

function aiPlaybackPause() {
  MatchUI.aiPlay.paused = true;
  document.getElementById('btn-ai-pause')?.classList.add('hidden');
  document.getElementById('btn-ai-resume')?.classList.remove('hidden');
}

function aiPlaybackResume() {
  MatchUI.aiPlay.paused = false;
  document.getElementById('btn-ai-pause')?.classList.remove('hidden');
  document.getElementById('btn-ai-resume')?.classList.add('hidden');
  _aiAutoPlayLoop();
}

function setAiSpeed(speed) {
  MatchUI.aiPlay.speed = speed;
  document.querySelectorAll('.ai-speed-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.speed === speed));
  try { localStorage.setItem('ribi_ai_speed', speed); } catch (_) {}
}

// ── Bowling change panel ────────────────────────────────────────────────────────

/**
 * Show the bowling change panel. Returns a Promise that resolves with the
 * selected player_id when the human (or AI) makes a choice.
 */
function showBowlingChangePanel(bowlers, inningsState, matchFormat, teamName) {
  return new Promise(resolve => {
    MatchUI._bowlingPanelCb = resolve;

    const cap = { T20: 4, ODI: 10, Test: null }[matchFormat];
    const lastId = inningsState?.last_bowler_id;

    // Ask AI for recommendation
    const aiSuggestion = _aiChooseBowler(bowlers, inningsState, matchFormat);

    const titleEl = document.getElementById('bowling-panel-title');
    const subEl   = document.getElementById('bowling-panel-sub');
    const listEl  = document.getElementById('bowling-panel-list');

    if (titleEl) titleEl.textContent = teamName ? `${teamName} — Choose Bowler` : 'Choose Bowler';
    if (subEl)   subEl.textContent   = `Over ${(inningsState?.overs_completed || 0) + 1}`;

    if (listEl) {
      listEl.innerHTML = bowlers.map(b => {
        const isLast    = b.player_id === lastId;
        const atCap     = cap !== null && b.overs_bowled >= cap;
        const disabled  = isLast || atCap;
        const isAi      = b.player_id === aiSuggestion;
        const capsLeft  = cap !== null ? `${cap - b.overs_bowled}ov left` : '∞';
        const oversFmt  = formatBowlerOvers(b.overs_bowled, b.balls_bowled || 0);
        const disabledReason = isLast ? 'consecutive' : (atCap ? 'cap reached' : '');
        return `<div class="bowling-row${disabled ? ' bowling-row--disabled' : ''}${isAi ? ' bowling-row--ai' : ''}">
          <div class="bowling-row-name">
            ${escHtml(b.player_name || '')}
            <small>${escHtml(b.bowling_type || '')}${disabled ? ' · <em>' + disabledReason + '</em>' : ''}</small>
          </div>
          <div class="bowling-row-figs">${oversFmt} / ${b.maidens || 0} / ${b.runs_conceded || 0} / ${b.wickets || 0}</div>
          <div class="bowling-row-cap">${capsLeft}</div>
          ${isAi ? '<div class="bowling-row-star" title="AI recommendation">★</div>' : '<div></div>'}
          <button class="btn btn-secondary btn-sm bowling-row-btn"
            ${disabled ? 'disabled' : ''}
            onclick="_bowlingPanelSelect(${b.player_id})">Select</button>
        </div>`;
      }).join('');
    }

    document.getElementById('bowling-change-dim').classList.remove('hidden');
  });
}

function _aiChooseBowler(bowlers, inningsState, matchFormat) {
  // Simple local replica of ai_captain.choose_bowler for the AI recommendation star
  const cap = { T20: 4, ODI: 10, Test: null }[matchFormat];
  const lastId = inningsState?.last_bowler_id;
  const eligible = bowlers.filter(b =>
    b.player_id !== lastId &&
    (cap === null || b.overs_bowled < cap) &&
    (b.bowling_type !== 'none')
  );
  const pool = eligible.length ? eligible : bowlers.filter(b => b.player_id !== lastId);
  if (!pool.length) return null;
  pool.sort((a, b) => b.bowling_rating - a.bowling_rating);
  return pool[0]?.player_id ?? null;
}

function _bowlingPanelSelect(playerId) {
  document.getElementById('bowling-change-dim').classList.add('hidden');
  MatchUI.chosenBowlerId = playerId;
  if (MatchUI._bowlingPanelCb) {
    const cb = MatchUI._bowlingPanelCb;
    MatchUI._bowlingPanelCb = null;
    cb(playerId);
  }
}

async function bowlingPanelAiChoose() {
  const state = MatchUI.lastState;
  if (!state) { _bowlingPanelSelect(null); return; }
  const matchId = getMatchId();
  const fmt = state.format;
  const bowlers = (state.bowler_innings || []).map(b => ({
    player_id:    b.player_id,
    bowling_rating: b.bowling_rating || 1,
    bowling_type: b.bowling_type || 'none',
    overs_bowled: b.overs || 0,
    balls_bowled: b.balls || 0,
    wickets_this_spell: b.wickets || 0,
    runs_this_spell: b.runs_conceded || 0,
    last_bowled_over: null,
  }));
  const inningsState = {
    total_runs:      state.current_innings?.total_runs || 0,
    total_wickets:   state.current_innings?.total_wickets || 0,
    overs_completed: parseFloat(state.current_innings?.overs_completed || 0),
    target:          state.target,
    balls_remaining: ((state.max_overs || 999) - state.over_number) * 6,
    last_bowler_id:  state.last_bowler_id,
  };
  const res = await api('POST', `/api/matches/${matchId}/ai-decision`, {
    decision_type: 'bowling_change',
    context: { bowlers, innings_state: inningsState },
  });
  const chosen = res?.bowler_id ?? null;
  if (chosen) _showToast(`AI captain recommends ${MatchUI.allPlayers[chosen]?.name || 'this bowler'}`, 1800);
  _bowlingPanelSelect(chosen);
}

/**
 * Check if a bowling change panel is needed and show it.
 * Returns a promise that resolves when the bowler is chosen.
 * If no panel is needed, resolves immediately with null.
 */
async function _maybeShowBowlingPanel(state) {
  const mode = AppState.playerMode;
  const needsPanel =
    state?.current_innings &&
    state.current_bowler_id === null &&  // start of over
    (
      mode === 'human_vs_human' ||
      (mode === 'human_vs_ai' && _humanIsBowling(state))
    );

  if (!needsPanel) return null;

  const bowlerData = (state.bowler_innings || []).map(b => ({
    player_id:      b.player_id,
    player_name:    MatchUI.allPlayers[b.player_id]?.name || b.player_name || '',
    bowling_rating: b.bowling_rating || 1,
    bowling_type:   b.bowling_type || 'none',
    overs_bowled:   b.overs || 0,
    balls_bowled:   b.balls || 0,
    maidens:        b.maidens || 0,
    runs_conceded:  b.runs_conceded || 0,
    wickets:        b.wickets || 0,
  }));
  const inningsState = {
    last_bowler_id:  state.last_bowler_id,
    overs_completed: parseFloat(state.current_innings?.overs_completed || 0),
  };
  const teamName = state.current_innings?.bowling_team_name || '';
  return showBowlingChangePanel(bowlerData, inningsState, state.format, teamName);
}

// ── Innings transition ────────────────────────────────────────────────────────

async function showInningsTransition(completedInnings, target) {
  const el   = document.getElementById('match-innings-transition');
  const live = document.getElementById('match-live');
  const kickerEl = document.getElementById('innings-transition-kicker');
  const textEl = document.getElementById('innings-transition-text');
  const scorelineEl = document.getElementById('innings-transition-scoreline');
  const targetEl = document.getElementById('innings-transition-target');
  const stakesEl = document.getElementById('innings-transition-stakes');
  MatchUI._transitionActive = true;
  live.classList.add('hidden');
  el.classList.remove('hidden');

  const card = el.querySelector('.innings-transition-card, .innings-break-graphic');
  if (card) card.className = 'innings-transition-card';
  if (completedInnings) {
    const n   = completedInnings.innings_number;
    const ord = ['1st','2nd','3rd','4th'][n - 1] || `${n}th`;
    const scoreStr = formatScore(completedInnings.total_runs, completedInnings.total_wickets);
    const ovsStr   = completedInnings.overs_completed != null
      ? `(${formatOvers(completedInnings.overs_completed)} ov)` : '';
    const inningsData = (MatchUI.lastState?.innings || []).find(i => i.innings_number === n);
    let topScorer = '', bestBowling = '';
    if (inningsData?.batters?.length) {
      const top = [...inningsData.batters]
        .filter(b => b.status !== 'yet_to_bat')
        .sort((a, b) => (b.runs || 0) - (a.runs || 0))[0];
      if (top) {
        const notOut = top.not_out || top.status === 'batting' ? '*' : '';
        topScorer = `${top.player_name || ''} ${top.runs || 0}${notOut} (${top.balls_faced || 0}b)`;
      }
    }
    if (inningsData?.bowlers?.length) {
      const best = [...inningsData.bowlers]
        .filter(b => (b.overs || 0) > 0 || (b.balls || 0) > 0)
        .sort((a, b) => {
          const wa = b.wickets || 0, wb = a.wickets || 0;
          if (wa !== wb) return wa - wb;
          return (a.runs_conceded || 0) - (b.runs_conceded || 0);
        })[0];
      if (best) {
        bestBowling = `${best.player_name || ''} ${best.wickets || 0}/${best.runs_conceded || 0}`;
      }
    }
    const nextBatting = MatchUI.lastState?.current_innings?.batting_team_name || 'Next side';
    const freshMatch = MatchUI.lastState?.match || {};
    const maxOvers   = { T20: 20, ODI: 50, Test: null }[freshMatch.format] ?? null;
    const chaseText = target
      ? `${nextBatting} need ${target} to win`
      : `${nextBatting} coming out to begin the ${n + 1}${n + 1 === 2 ? 'nd' : n + 1 === 3 ? 'rd' : 'th'} innings`;
    const stakeLines = [];
    if (topScorer) stakeLines.push(`<div class="stake-line"><span class="stake-label">Top scorer</span><span class="stake-value">${escHtml(topScorer)}</span></div>`);
    if (bestBowling) stakeLines.push(`<div class="stake-line"><span class="stake-label">Best bowling</span><span class="stake-value">${escHtml(bestBowling)}</span></div>`);
    if (target && maxOvers) {
      stakeLines.push(`<div class="stake-line"><span class="stake-label">Required rate</span><span class="stake-value">${(target / maxOvers).toFixed(2)} from ${maxOvers} overs</span></div>`);
    } else if (completedInnings.total_wickets >= 10) {
      stakeLines.push(`<div class="stake-line"><span class="stake-label">Shape of innings</span><span class="stake-value">All out after ${formatOvers(completedInnings.overs_completed || 0)} overs</span></div>`);
    } else {
      stakeLines.push(`<div class="stake-line"><span class="stake-label">Shape of innings</span><span class="stake-value">${completedInnings.batting_team_name} closed on ${scoreStr}</span></div>`);
    }
    if (kickerEl) kickerEl.textContent = 'Innings Break';
    if (textEl) textEl.textContent = `${completedInnings.batting_team_name} ${ord} innings closed`;
    if (scorelineEl) scorelineEl.textContent = `${scoreStr} ${ovsStr}`.trim();
    if (targetEl) targetEl.textContent = chaseText;
    if (stakesEl) stakesEl.innerHTML = stakeLines.join('');
  } else {
    if (kickerEl) kickerEl.textContent = 'Innings Break';
    if (textEl) textEl.textContent = 'End of innings';
    if (scorelineEl) scorelineEl.textContent = '';
    if (targetEl) targetEl.textContent = target ? `Target: ${target}` : '';
    if (stakesEl) stakesEl.innerHTML = '';
  }

  // In broadcast mode the card stays until clicked; otherwise auto-advance
  const isBroadcast = AppState.broadcastMode;
  const maxHold = animMs(isBroadcast ? 99999 : 8000, isBroadcast ? 800 : 2000, 0);

  try {
    if (maxHold === 0) {
      el.classList.add('hidden');
      live.classList.remove('hidden');
    } else if (isBroadcast) {
      // Click or 8s timeout
      await new Promise(resolve => {
        const tid = setTimeout(resolve, 8000);
        const onClick = () => { clearTimeout(tid); el.removeEventListener('click', onClick); resolve(); };
        el.addEventListener('click', onClick);
      });
      el.classList.add('hidden');
      live.classList.remove('hidden');
    } else {
      await sleep(maxHold);
      el.classList.add('hidden');
      live.classList.remove('hidden');
    }

    // Refresh state after new innings starts
    const fresh = await api('GET', `/api/matches/${getMatchId()}`);
    if (fresh) updateLiveView(fresh);

    // Human vs Human: show handover card so device can be passed over
    if (AppState.playerMode === 'human_vs_human' && fresh?.current_innings) {
      await showHandoverCard(fresh, completedInnings, target);
    }

    // Human vs AI: if new innings is AI's turn, start auto-play
    if (AppState.playerMode === 'human_vs_ai' && fresh && _isAiTurn(fresh)) {
      _startAiAutoPlay();
    }
  } finally {
    MatchUI._transitionActive = false;
  }
}

function showHandoverCard(state, completedInnings, target) {
  return new Promise(resolve => {
    const nextInnings = state.current_innings;
    if (!nextInnings) { resolve(); return; }

    const inningsText = completedInnings
      ? `${completedInnings.batting_team_name}: ${formatScore(completedInnings.total_runs, completedInnings.total_wickets)}`
      : '';
    const targetText = target ? `Target: ${target}` : '';
    const nextTeam = nextInnings.batting_team_name || '';

    document.getElementById('handover-innings-text').textContent = inningsText;
    document.getElementById('handover-target-text').textContent  = targetText;
    document.getElementById('handover-team-name').textContent    = nextTeam.toUpperCase();
    const readyBtn = document.getElementById('btn-handover-ready');
    if (readyBtn) readyBtn.textContent = `${nextTeam} Captain Ready — Continue`;

    document.getElementById('handover-dim').classList.remove('hidden');
    // Store resolve so the button can call it
    document.getElementById('btn-handover-ready')._handoverResolve = resolve;
  });
}

function closeHandoverCard() {
  const btn = document.getElementById('btn-handover-ready');
  const resolve = btn?._handoverResolve;
  document.getElementById('handover-dim').classList.add('hidden');
  if (resolve) resolve();
}

// ── Result screen ─────────────────────────────────────────────────────────────

async function showResultScreen(matchId) {
  // Fetch full scorecard for innings data and POM selection
  const [state, sc] = await Promise.all([
    api('GET', `/api/matches/${matchId}`),
    api('GET', `/api/matches/${matchId}/scorecard`),
  ]);
  if (!state) return;
  MatchUI.lastState = state;

  const match = state.match || sc?.match || {};
  document.getElementById('match-live').classList.add('hidden');
  document.getElementById('match-result-screen').classList.remove('hidden');

  // Headline
  let headline = 'MATCH COMPLETE';
  const rt = match.result_type;
  if (rt === 'runs')         headline = `${(match.winning_team_name || '').toUpperCase()} WIN BY ${match.margin_runs} RUN${match.margin_runs !== 1 ? 'S' : ''}`;
  else if (rt === 'wickets') headline = `${(match.winning_team_name || '').toUpperCase()} WIN BY ${match.margin_wickets} WICKET${match.margin_wickets !== 1 ? 'S' : ''}`;
  else if (rt === 'tie')     headline = 'MATCH TIED';
  else if (rt === 'draw')    headline = 'MATCH DRAWN';

  const kickerEl = document.getElementById('result-kicker');
  const verdictEl = document.getElementById('result-verdict');
  document.getElementById('result-headline').textContent = headline;
  document.getElementById('result-subline').textContent =
    `${match.format} · ${match.venue_name || ''}${match.venue_city ? ', ' + match.venue_city : ''} · ${match.match_date || ''}`;
  if (kickerEl) kickerEl.textContent = 'Full Time';
  if (verdictEl) {
    verdictEl.textContent = match.result_string || (
      rt === 'runs' ? `${match.winning_team_name} defended successfully`
      : rt === 'wickets' ? `${match.winning_team_name} chased it down`
      : rt === 'draw' ? 'Neither side could force a result'
      : rt === 'tie' ? 'Nothing separated the sides'
      : ''
    );
  }

  // Compact innings summary
  const summaryEl = document.getElementById('result-innings-summary');
  if (sc && sc.innings && sc.innings.length) {
    summaryEl.innerHTML = sc.innings.map(inn => {
      const decl = inn.declared ? ' (d)' : '';
      const ov = inn.overs_completed != null ? ` (${formatOvers(inn.overs_completed)} ov)` : '';
      return `<div class="result-innings-row">
        <span class="result-innings-team">${escHtml(inn.batting_team_name)}</span>
        <span>
          <span class="result-innings-score">${formatScore(inn.total_runs, inn.total_wickets)}${decl}</span>
          <span class="result-innings-overs">${ov}</span>
        </span>
      </div>`;
    }).join('');
  } else {
    summaryEl.innerHTML = '';
  }

  const noteCards = [];
  if (sc?.innings?.length) {
    const allBatters = sc.innings.flatMap(inn => inn.batters || []);
    const allBowlers = sc.innings.flatMap(inn => inn.bowlers || []);
    const topBat = [...allBatters]
      .filter(b => b.status !== 'yet_to_bat')
      .sort((a, b) => (b.runs || 0) - (a.runs || 0))[0];
    const topBowl = [...allBowlers]
      .filter(b => (b.overs || 0) > 0 || (b.balls || 0) > 0)
      .sort((a, b) => {
        if ((b.wickets || 0) !== (a.wickets || 0)) return (b.wickets || 0) - (a.wickets || 0);
        return (a.runs_conceded || 0) - (b.runs_conceded || 0);
      })[0];
    const lastInn = sc.innings[sc.innings.length - 1];
    if (topBat) {
      noteCards.push(`<div class="result-note-card"><div class="result-note-label">Top score</div><div class="result-note-value">${escHtml(topBat.player_name || '')} ${topBat.runs || 0}${topBat.not_out ? '*' : ''} (${topBat.balls_faced || 0}b)</div></div>`);
    }
    if (topBowl) {
      noteCards.push(`<div class="result-note-card"><div class="result-note-label">Best bowling</div><div class="result-note-value">${escHtml(topBowl.player_name || '')} ${topBowl.wickets || 0}/${topBowl.runs_conceded || 0}</div></div>`);
    }
    if (lastInn && match.target) {
      const targetRuns = match.target - 1;
      const finalMargin = rt === 'wickets'
        ? `${match.winning_team_name} got there with ${match.margin_wickets} wicket${match.margin_wickets !== 1 ? 's' : ''} to spare`
        : rt === 'runs'
          ? `${match.winning_team_name} defended ${targetRuns}`
          : (match.result_string || 'Final innings complete');
      noteCards.push(`<div class="result-note-card"><div class="result-note-label">Match swing</div><div class="result-note-value">${escHtml(finalMargin)}</div></div>`);
    }
  }
  const notesEl = document.getElementById('result-match-notes');
  if (notesEl) notesEl.innerHTML = noteCards.join('');

  // Records broken this match
  const recEl = document.getElementById('result-records');
  if (recEl) {
    const recs = MatchUI.recordsBroken || [];
    if (recs.length) {
      recEl.innerHTML = `<div class="result-records-heading">📖 Records broken this match</div>` +
        recs.map(rec => {
          const typeLabel = RECORD_LABELS[rec.type] || rec.type.toUpperCase().replace(/_/g, ' ');
          const prev = rec.previous_value != null
            ? ` <span class="result-record-prev">(was ${escHtml(String(rec.previous_value))}${rec.previous_holder ? ' — ' + escHtml(rec.previous_holder) : ''})</span>`
            : ` <span class="result-record-prev">(first ever)</span>`;
          const holder = rec.player_name ? ` · ${escHtml(rec.player_name)}` : '';
          return `<div class="result-record-row">
            <span class="result-record-type">${escHtml(typeLabel)}</span>
            <span class="result-record-value">${escHtml(String(rec.new_value))}${holder}</span>
            ${prev}
          </div>`;
        }).join('');
      recEl.classList.remove('hidden');
    } else {
      recEl.innerHTML = '';
      recEl.classList.add('hidden');
    }
  }

  // Build POM candidates: players who batted (status != yet_to_bat) or bowled (overs > 0)
  const candidates = new Map(); // player_id -> {name, score, statLine}
  if (sc && sc.innings) {
    for (const inn of sc.innings) {
      for (const b of (inn.batters || [])) {
        if (b.status !== 'yet_to_bat') {
          const existing = candidates.get(b.player_id) || { name: b.player_name, score: 0, runs: 0, wkts: 0, statParts: [] };
          existing.runs  += b.runs || 0;
          existing.score += (b.runs || 0);
          existing.statParts.push(`${b.runs}${b.not_out ? '*' : ''} (${b.balls_faced}b)`);
          candidates.set(b.player_id, existing);
        }
      }
      for (const bw of (inn.bowlers || [])) {
        if ((bw.overs || 0) > 0 || (bw.balls || 0) > 0) {
          const existing = candidates.get(bw.player_id) || { name: bw.player_name, score: 0, runs: 0, wkts: 0, statParts: [] };
          existing.wkts  += bw.wickets || 0;
          existing.score += (bw.wickets || 0) * 20;
          existing.statParts.push(`${bw.wickets}/${bw.runs_conceded}`);
          candidates.set(bw.player_id, existing);
        }
      }
    }
  }

  // Sort by score descending; fallback to all players
  const pomList = candidates.size > 0
    ? [...candidates.entries()].sort((a, b) => b[1].score - a[1].score)
    : Object.entries(MatchUI.allPlayers).map(([id, p]) => [parseInt(id), { name: p.name, score: 0, statParts: [] }]);

  const pomSel = document.getElementById('result-pom');
  pomSel.innerHTML = '<option value="">— Select Player of the Match —</option>';
  let bestId = null;
  pomList.forEach(([pid, p]) => {
    const opt = document.createElement('option');
    opt.value = pid;
    opt.textContent = p.name + (p.statParts.length ? ' — ' + p.statParts.join(', ') : '');
    pomSel.appendChild(opt);
    if (bestId === null) bestId = pid; // first = highest score
  });
  if (bestId !== null) pomSel.value = bestId;

  document.getElementById('btn-save-almanack').disabled = false;
  document.getElementById('result-saved-msg').classList.add('hidden');
  document.getElementById('result-nav-btns').classList.add('hidden');
  document.getElementById('result-notes').value = '';
}

async function showHistoricalMatchView(matchId, state) {
  const sc = await api('GET', `/api/matches/${matchId}/scorecard`);
  if (!sc) return;

  MatchUI.lastState = state;
  document.getElementById('match-toss-screen').classList.add('hidden');
  document.getElementById('match-result-screen').classList.add('hidden');
  document.getElementById('match-live').classList.remove('hidden');

  const scorecardEl = document.getElementById('scorecard-content');
  if (scorecardEl) {
    scorecardEl.innerHTML = _renderFullScorecardHtml(sc);
  }

  const postWrap = document.getElementById('canvas-post-match');
  if (postWrap) {
    postWrap.classList.toggle('hidden', !(sc.innings && sc.innings.length));
  }

  if (sc.innings && sc.innings.length) {
    const deliveriesRes = await api('GET', `/api/matches/${matchId}/deliveries`);
    const deliveries = deliveriesRes?.deliveries || [];
    const inn1Del = deliveries.filter(d => d.innings_number === 1);
    const inn2Del = deliveries.filter(d => d.innings_number === 2);
    drawManhattan('canvas-manhattan', inn1Del, inn2Del);
    drawRunRateGraph('canvas-runrate', inn2Del.length ? inn2Del : inn1Del, sc.match?.target ?? null);
  }

  switchMatchTab('scorecard');
}

async function saveMatchToAlmanack() {
  const matchId = getMatchId();
  const pom   = document.getElementById('result-pom').value;
  const notes = document.getElementById('result-notes').value;

  const btn = document.getElementById('btn-save-almanack');
  btn.disabled = true;
  btn.textContent = '⏳ Saving…';

  const res = await api('POST', `/api/matches/${matchId}/complete`, {
    player_of_match_id: pom ? parseInt(pom) : null,
    match_notes: notes || null,
  });

  if (res && res.success) {
    btn.textContent = '✓ Saved';
    document.getElementById('result-saved-msg').classList.remove('hidden');
    document.getElementById('result-nav-btns').classList.remove('hidden');
    AppState.sessionStats.matches++;
    updateSessionBar();
    try { localStorage.setItem('ribi_welcomed', 'true'); } catch (_) {}
  } else {
    btn.disabled = false;
    btn.textContent = '📖 Save to The Almanack';
  }
}

async function suggestJournalPrompt() {
  const matchId = getMatchId();
  const notesEl = document.getElementById('result-notes');
  const btn = document.getElementById('btn-suggest-prompt');

  // Rotate through cached prompts, re-fetch when exhausted
  if (!MatchUI._journalPrompts || MatchUI._journalPromptIdx >= MatchUI._journalPrompts.length) {
    const res = await api('GET', `/api/matches/${matchId}/journal-prompts`);
    if (!res) return;
    MatchUI._journalPrompts = res.prompts || [];
    MatchUI._journalPromptIdx = 0;
  }
  if (!MatchUI._journalPrompts.length) return;

  const prompt = MatchUI._journalPrompts[MatchUI._journalPromptIdx++];
  notesEl.placeholder = prompt;
  notesEl.focus();
}

async function showResultScorecard() {
  document.getElementById('match-result-screen').classList.add('hidden');
  document.getElementById('match-live').classList.remove('hidden');
  switchMatchTab('scorecard');

  const matchId = getMatchId();
  if (!matchId) return;

  const res = await api('GET', `/api/matches/${matchId}/deliveries`);
  const deliveries = res?.deliveries || [];
  if (!deliveries.length) return;

  // Separate innings by innings_number (from deliveries join)
  const inn1Del = deliveries.filter(d => d.innings_number === 1);
  const inn2Del = deliveries.filter(d => d.innings_number === 2);

  const postWrap = document.getElementById('canvas-post-match');
  if (postWrap) {
    postWrap.classList.remove('hidden');
    drawManhattan('canvas-manhattan', inn1Del, inn2Del);
    // Run-rate graph: 2nd innings if it exists (chase), else 1st
    const target = MatchUI.lastState?.target ?? null;
    drawRunRateGraph('canvas-runrate', inn2Del.length ? inn2Del : inn1Del, target);
  }
}

// ── Fast Sim ──────────────────────────────────────────────────────────────────

async function fastSimMatch() {
  if (!confirm('Fast-simulate the rest of this match? All remaining overs will be rolled automatically.')) return;
  const btn = document.getElementById('btn-fast-sim');
  btn.disabled = true;

  // Graphics don't run during fast sim — clear any pending
  GraphicQueue.clear();

  const matchId = getMatchId();
  const res = await api('POST', `/api/matches/${matchId}/fast-sim`);
  if (!res) { btn.disabled = false; return; }

  // Show fast-sim summary card before result screen
  if (res.sim_digest) {
    await showFastSimSummary(res);
  }

  AppState.sessionStats.matches += 1;
  updateSessionBar();
  await showResultScreen(matchId);
  btn.disabled = false;
}

// ── Declare ───────────────────────────────────────────────────────────────────

async function declareInnings() {
  if (!confirm('Declare this innings?')) return;
  const res = await api('POST', `/api/matches/${getMatchId()}/declare`);
  if (!res) return;
  const newState = await api('GET', `/api/matches/${getMatchId()}`);
  if (newState) {
    const prevCompleted = (newState.innings || []).filter(i => i.status === 'complete');
    const justDeclared  = prevCompleted[prevCompleted.length - 1];
    await showInningsTransition(justDeclared, newState.target);
    updateLiveView(newState);
  }
}

// ── Complete match manually ───────────────────────────────────────────────────

async function completeMatchManual() {
  await showResultScreen(getMatchId());
}

// ── Tab switching ─────────────────────────────────────────────────────────────

function switchMatchTab(tabName) {
  document.querySelectorAll('.match-tabs .tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });
  ['scorecard', 'wagon-wheel', 'over-grid'].forEach(t => {
    const el = document.getElementById(`match-tab-${t}`);
    if (el) el.classList.toggle('hidden', t !== tabName);
  });

  if (tabName === 'wagon-wheel') _loadWagonWheel();
  if (tabName === 'over-grid')   _loadOverGrid();
}

async function _loadWagonWheel() {
  const matchId = getMatchId();
  if (!matchId) return;
  const res = await api('GET', `/api/matches/${matchId}/deliveries`);
  const deliveries = res?.deliveries || [];
  // Default: no batter filter so all shots are shown
  drawWagonWheel('canvas-wagon-wheel', deliveries, null);
}

async function _loadOverGrid() {
  const matchId = getMatchId();
  if (!matchId) return;
  const res = await api('GET', `/api/matches/${matchId}/deliveries`);
  const all  = res?.deliveries || [];
  // Filter to current innings only
  const innId = MatchUI.lastState?.current_innings_id;
  const dels  = innId ? all.filter(d => d.innings_id === innId) : all;
  drawOverGrid('canvas-over-grid', dels);
}

function _drawInningsArcFromState(state) {
  const inn = state?.current_innings;
  if (!inn) return;
  const legalBalls = (state.over_number || 0) * 6 + (state.ball_in_over || 0);
  drawInningsArc(
    'canvas-innings-arc',
    inn.total_wickets || 0,
    legalBalls,
    state.max_overs || 20,
    inn.total_runs
  );
}

// ── Scorecard tab ─────────────────────────────────────────────────────────────

function renderScorecardTab(state) {
  const el = document.getElementById('scorecard-content');
  if (!el) return;

  const innings = state.innings || [];
  if (!innings.length) { el.innerHTML = '<p class="text-muted">No innings yet.</p>'; return; }

  const matchId = state.id || getMatchId();
  let html = '';

  for (const inn of innings) {
    const isCurrentInnings = inn.id === state.current_innings_id;
    const ord = ['1st','2nd','3rd','4th'][inn.innings_number - 1] || `${inn.innings_number}th`;
    const decl = inn.declared ? ' (dec)' : '';

    if (!isCurrentInnings) {
      // Compact summary card for completed innings
      const extraTotal = (inn.extras_byes || 0) + (inn.extras_legbyes || 0) +
                         (inn.extras_wides || 0) + (inn.extras_noballs || 0);
      const oversDisp = formatOvers(inn.overs_completed || 0);
      // Derive true decimal overs for RR: parse the cricket-notation display string
      const [oversIntStr, ballsStr] = oversDisp.split('.');
      const oversForRR = parseInt(oversIntStr || '0', 10) + (ballsStr ? parseInt(ballsStr, 10) / 6 : 0);
      const rr = oversForRR > 0 ? (inn.total_runs / oversForRR).toFixed(2) : '—';

      html += `<div class="sc-innings-summary">
        <div class="sc-innings-summary-top">
          <span class="sc-innings-summary-team">${escHtml(inn.batting_team_name)} — ${ord} Innings</span>
          <span class="sc-innings-summary-score">${formatScore(inn.total_runs, inn.total_wickets)}${decl}</span>
        </div>
        <div class="sc-innings-summary-meta">${oversDisp} overs &nbsp;·&nbsp; RR: ${rr}</div>
        <div class="sc-innings-summary-extras">Extras: ${extraTotal} (b ${inn.extras_byes||0}, lb ${inn.extras_legbyes||0}, w ${inn.extras_wides||0}, nb ${inn.extras_noballs||0})</div>
      </div>`;
    } else {
      // Live tables for current innings
      const batters = state.batter_innings || [];
      const bowlers = state.bowler_innings || [];
      const fow     = state.fall_of_wickets || [];

      html += `<div class="sc-innings-header">${escHtml(inn.batting_team_name)} — ${ord} Innings: ${formatScore(inn.total_runs, inn.total_wickets)}${decl}</div>`;

      html += `<table class="data-table">
        <thead><tr>
          <th>Batter</th><th>How Out</th><th>Bowler</th>
          <th style="text-align:right">R</th><th style="text-align:right">B</th>
          <th style="text-align:right">4s</th><th style="text-align:right">6s</th>
          <th style="text-align:right">SR</th>
        </tr></thead><tbody>`;

      const showBatters = batters.filter(b => b.status !== 'yet_to_bat');
      if (!showBatters.length) {
        html += `<tr><td colspan="8" class="text-muted" style="font-style:italic">—</td></tr>`;
      }
      for (const b of showBatters) {
        const sr = b.balls_faced > 0 ? ((b.runs / b.balls_faced) * 100).toFixed(1) : '—';
        const howOut = b.status === 'dismissed'
          ? (b.dismissal_type || 'out')
          : b.status === 'batting' ? 'not out' : b.status;
        const bowlerName = b.bowler_id ? (MatchUI.allPlayers[b.bowler_id]?.name || '') : '';
        const notOut = b.not_out || b.status === 'batting' ? '*' : '';
        html += `<tr>
          <td><strong>${escHtml(b.player_name || '')}</strong></td>
          <td class="stat-muted">${escHtml(howOut)}</td>
          <td class="stat-muted">${escHtml(bowlerName)}</td>
          <td style="text-align:right" class="stat-highlight">${b.runs}${notOut}</td>
          <td style="text-align:right" class="stat-muted">${b.balls_faced}</td>
          <td style="text-align:right">${b.fours}</td>
          <td style="text-align:right">${b.sixes}</td>
          <td style="text-align:right" class="stat-muted">${sr}</td>
        </tr>`;
      }

      const extraTotal = (inn.extras_byes || 0) + (inn.extras_legbyes || 0) +
                         (inn.extras_wides || 0) + (inn.extras_noballs || 0);
      html += `<tr class="sc-extras-row">
        <td colspan="3">Extras (b ${inn.extras_byes||0}, lb ${inn.extras_legbyes||0}, w ${inn.extras_wides||0}, nb ${inn.extras_noballs||0})</td>
        <td style="text-align:right">${extraTotal}</td><td colspan="4"></td>
      </tr>
      <tr class="sc-total-row">
        <td colspan="3"><strong>TOTAL</strong></td>
        <td style="text-align:right" class="stat-highlight"><strong>${formatScore(inn.total_runs, inn.total_wickets)}</strong></td>
        <td colspan="4" class="stat-muted">${formatOvers(inn.overs_completed)} ov</td>
      </tr></tbody></table>`;

      if (fow.length) {
        const fowStr = fow.map(f => `${f.wicket_number}-${f.score_at_fall} (${f.batter_name})`).join(', ');
        html += `<div class="sc-fow">FoW: ${escHtml(fowStr)}</div>`;
      }

      const showBowlers = bowlers.filter(b => b.overs > 0 || b.balls > 0);
      if (showBowlers.length) {
        html += `<table class="data-table" style="margin-top:8px">
          <thead><tr><th>Bowler</th><th style="text-align:right">O</th><th style="text-align:right">M</th><th style="text-align:right">R</th><th style="text-align:right">W</th><th style="text-align:right">Econ</th></tr></thead>
          <tbody>`;
        for (const bw of showBowlers) {
          const oversF = bw.overs + bw.balls / 6;
          const econ   = oversF > 0 ? (bw.runs_conceded / oversF).toFixed(2) : '0.00';
          html += `<tr>
            <td><strong>${escHtml(bw.player_name || '')}</strong></td>
            <td style="text-align:right">${formatBowlerOvers(bw.overs, bw.balls)}</td>
            <td style="text-align:right">${bw.maidens}</td>
            <td style="text-align:right">${bw.runs_conceded}</td>
            <td style="text-align:right" class="stat-highlight">${bw.wickets}</td>
            <td style="text-align:right" class="stat-muted">${econ}</td>
          </tr>`;
        }
        html += '</tbody></table>';
      }
    }
  }

  html += `<div class="sc-view-btn-row">
    <button class="btn btn-secondary btn-sm" onclick="showScorecardPopup(${matchId})">Full Scorecard</button>
  </div>`;

  el.innerHTML = html;
}

// ── Scorecard popup ────────────────────────────────────────────────────────────

function _getScorecardModal() {
  let dim = document.getElementById('sc-modal-dim');
  if (dim) return { dim, modal: document.getElementById('sc-modal') };

  dim = document.createElement('div');
  dim.id = 'sc-modal-dim';
  dim.className = 'sc-modal-dim';
  dim.addEventListener('click', closeScorecardModal);

  const modal = document.createElement('div');
  modal.id = 'sc-modal';
  modal.className = 'sc-modal';
  modal.innerHTML = `
    <div class="sc-modal-header">
      <div>
        <div class="sc-modal-title" id="sc-modal-title">Full Scorecard</div>
        <div class="sc-modal-subtitle" id="sc-modal-subtitle"></div>
      </div>
      <button class="sc-modal-close" onclick="closeScorecardModal()" title="Close">&times;</button>
    </div>
    <div class="sc-modal-body" id="sc-modal-body"></div>`;

  document.body.appendChild(dim);
  document.body.appendChild(modal);
  return { dim, modal };
}

function closeScorecardModal() {
  const dim = document.getElementById('sc-modal-dim');
  const modal = document.getElementById('sc-modal');
  if (dim) dim.style.display = 'none';
  if (modal) modal.style.display = 'none';
}

async function showScorecardPopup(matchId) {
  const { dim, modal } = _getScorecardModal();
  const body = document.getElementById('sc-modal-body');
  const subtitle = document.getElementById('sc-modal-subtitle');

  body.innerHTML = '<p class="text-muted" style="text-align:center;padding:32px 0">Loading…</p>';
  subtitle.textContent = '';
  dim.style.display = 'block';
  modal.style.display = 'flex';

  const sc = await api('GET', `/api/matches/${matchId}/scorecard`);
  if (!sc) {
    body.innerHTML = '<p class="text-muted" style="text-align:center;padding:32px 0">Could not load scorecard.</p>';
    return;
  }

  const m = sc.match || {};
  subtitle.textContent = [m.home_team_name, m.away_team_name].filter(Boolean).join(' vs ') +
    (m.venue_name ? ` · ${m.venue_name}` : '') +
    (m.format ? ` · ${m.format}` : '');

  body.innerHTML = _renderFullScorecardHtml(sc);
}

function _renderFullScorecardHtml(sc) {
  const innings = sc.innings || [];
  if (!innings.length) {
    const m = sc.match || {};
    let notes = {};
    try { notes = JSON.parse(m.match_notes || '{}'); } catch (_) { notes = {}; }
    const t1 = escHtml(m.team1_name || 'Team 1');
    const t2 = escHtml(m.team2_name || 'Team 2');
    const t1Score = escHtml(notes.team1_score || '—');
    const t2Score = escHtml(notes.team2_score || '—');
    const topScorer = notes.top_scorer?.name
      ? `${escHtml(notes.top_scorer.name)} ${escHtml(String(notes.top_scorer.runs || 0))}`
      : null;
    const topBowler = notes.top_bowler?.name
      ? `${escHtml(notes.top_bowler.name)} ${escHtml(String(notes.top_bowler.wickets || 0))}/${escHtml(String(notes.top_bowler.runs || 0))}`
      : null;
    const pom = m.player_of_match_name ? escHtml(m.player_of_match_name) : null;
    return `
      ${sc.result_string ? `<div class="sc-innings-header" style="margin-bottom:12px">${escHtml(sc.result_string)}</div>` : ''}
      <div class="result-note-grid" style="margin-bottom:16px">
        <div class="result-note-card"><div class="result-note-label">${t1}</div><div class="result-note-value">${t1Score}</div></div>
        <div class="result-note-card"><div class="result-note-label">${t2}</div><div class="result-note-value">${t2Score}</div></div>
        ${pom ? `<div class="result-note-card"><div class="result-note-label">Player of the Match</div><div class="result-note-value">${pom}</div></div>` : ''}
        ${topScorer ? `<div class="result-note-card"><div class="result-note-label">Top score</div><div class="result-note-value">${topScorer}</div></div>` : ''}
        ${topBowler ? `<div class="result-note-card"><div class="result-note-label">Best bowling</div><div class="result-note-value">${topBowler}</div></div>` : ''}
      </div>
      <p class="text-muted">This was a simulated match, so full ball-by-ball innings tables were not stored for this result.</p>`;
  }

  let html = '';

  const canonStatus = sc.match?.canon_status;
  if (canonStatus === 'exhibition') {
    html += `<div class="exhibition-banner">Exhibition match — excluded from career statistics and records</div>`;
  } else if (canonStatus === 'deleted') {
    html += `<div class="deleted-banner">This match has been soft-deleted and is hidden from public statistics</div>`;
  }

  if (sc.result_string) {
    html += `<div class="sc-innings-header" style="margin-bottom:12px">${escHtml(sc.result_string)}</div>`;
  }

  for (const inn of innings) {
    const ord = ['1st','2nd','3rd','4th'][inn.innings_number - 1] || `${inn.innings_number}th`;
    const decl = inn.declared ? ' (dec)' : '';
    html += `<div class="sc-innings-header">${escHtml(inn.batting_team_name)} — ${ord} Innings: ${formatScore(inn.total_runs, inn.total_wickets)}${decl}</div>`;

    // Build bowler name map from this innings' bowlers array
    const bowlerMap = {};
    for (const bw of (inn.bowlers || [])) {
      if (bw.player_id) bowlerMap[bw.player_id] = bw.player_name || '';
    }

    // Batters table
    html += `<table class="data-table">
      <thead><tr>
        <th>Batter</th><th>How Out</th><th>Bowler</th>
        <th style="text-align:right">R</th><th style="text-align:right">B</th>
        <th style="text-align:right">4s</th><th style="text-align:right">6s</th>
        <th style="text-align:right">SR</th>
      </tr></thead><tbody>`;

    const batters = inn.batters || [];
    if (!batters.length) {
      html += `<tr><td colspan="8" class="text-muted" style="font-style:italic">—</td></tr>`;
    }
    for (const b of batters) {
      const sr = b.balls_faced > 0 ? ((b.runs / b.balls_faced) * 100).toFixed(1) : '—';
      const howOut = b.not_out
        ? 'not out'
        : (b.dismissal_type || (b.status === 'yet_to_bat' ? 'yet to bat' : 'out'));
      const bowlerName = b.bowler_id ? (bowlerMap[b.bowler_id] || '') : '';
      const notOut = b.not_out ? '*' : '';
      html += `<tr>
        <td><strong>${escHtml(b.player_name || '')}</strong></td>
        <td class="stat-muted">${escHtml(howOut)}</td>
        <td class="stat-muted">${escHtml(bowlerName)}</td>
        <td style="text-align:right" class="stat-highlight">${b.runs}${notOut}</td>
        <td style="text-align:right" class="stat-muted">${b.balls_faced}</td>
        <td style="text-align:right">${b.fours}</td>
        <td style="text-align:right">${b.sixes}</td>
        <td style="text-align:right" class="stat-muted">${sr}</td>
      </tr>`;
    }

    const ext = inn.extras || {};
    const extraTotal = (ext.byes || 0) + (ext.leg_byes || 0) + (ext.wides || 0) + (ext.no_balls || 0);
    html += `<tr class="sc-extras-row">
      <td colspan="3">Extras (b ${ext.byes||0}, lb ${ext.leg_byes||0}, w ${ext.wides||0}, nb ${ext.no_balls||0})</td>
      <td style="text-align:right">${extraTotal}</td><td colspan="4"></td>
    </tr>
    <tr class="sc-total-row">
      <td colspan="3"><strong>TOTAL</strong></td>
      <td style="text-align:right" class="stat-highlight"><strong>${formatScore(inn.total_runs, inn.total_wickets)}</strong></td>
      <td colspan="4" class="stat-muted">${formatOvers(inn.overs_completed)} ov</td>
    </tr></tbody></table>`;

    // Fall of wickets
    const fow = inn.fall_of_wickets || [];
    if (fow.length) {
      const fowStr = fow.map(f => `${f.wicket_number}-${f.score_at_fall} (${f.batter_name})`).join(', ');
      html += `<div class="sc-fow">FoW: ${escHtml(fowStr)}</div>`;
    }

    // Bowlers table
    const bowlers = (inn.bowlers || []).filter(b => b.overs > 0 || b.balls > 0);
    if (bowlers.length) {
      html += `<table class="data-table" style="margin-top:8px">
        <thead><tr><th>Bowler</th><th style="text-align:right">O</th><th style="text-align:right">M</th><th style="text-align:right">R</th><th style="text-align:right">W</th><th style="text-align:right">Econ</th></tr></thead>
        <tbody>`;
      for (const bw of bowlers) {
        html += `<tr>
          <td><strong>${escHtml(bw.player_name || '')}</strong></td>
          <td style="text-align:right">${formatBowlerOvers(bw.overs, bw.balls)}</td>
          <td style="text-align:right">${bw.maidens}</td>
          <td style="text-align:right">${bw.runs_conceded}</td>
          <td style="text-align:right" class="stat-highlight">${bw.wickets}</td>
          <td style="text-align:right" class="stat-muted">${bw.economy != null ? bw.economy : '—'}</td>
        </tr>`;
      }
      html += '</tbody></table>';
    }

    html += '<div style="margin-bottom:20px"></div>';
  }

  return html;
}

// ── Match screen load hook ────────────────────────────────────────────────────

async function loadMatchScreen() {
  if (!AppState.activeMatch) {
    // No active match — show play screen instead
    showScreen('play');
    return;
  }
  // If toss not yet taken, show toss
  const matchId = getMatchId();
  const state = await api('GET', `/api/matches/${matchId}`);
  if (!state) return;
  MatchUI.lastState = state;
  buildAllPlayersMap(state);

  // Restore player mode from match data (in case we navigated away and back)
  if (state.match) {
    AppState.playerMode  = state.match.player_mode  || AppState.playerMode  || 'ai_vs_ai';
    AppState.humanTeamId = state.match.human_team_id ?? AppState.humanTeamId ?? null;
    if (AppState.activeMatch) {
      AppState.activeMatch.playerMode  = AppState.playerMode;
      AppState.activeMatch.humanTeamId = AppState.humanTeamId;
    }
  }

  if (state.match?.status === 'complete') {
    if (AppState.historicalMatchView) {
      await showHistoricalMatchView(matchId, state);
    } else {
      initLiveView(state);
      await showResultScreen(matchId);
    }
  } else if (!state.current_innings && !(state.innings || []).length) {
    showMatchToss();
  } else {
    AppState.historicalMatchView = false;
    document.getElementById('match-toss-screen').classList.add('hidden');
    initLiveView(state);
  }
}

// ── Teams Screen ──────────────────────────────────────────────────────────────

async function loadTeamsScreen() {
  const container = document.getElementById('teams-list');
  const subtitleEl = document.getElementById('teams-subtitle');
  if (!container) return;
  AppState.teamsFilter = AppState.teamsFilter || 'all';
  container.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', '/api/teams');
  const teams = data && data.teams ? data.teams : [];

  if (!teams.length) {
    container.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">👕</div><h3 class="empty-state-heading">No teams yet</h3><p class="empty-state-sub">Create a team to get started.</p></div>`;
    return;
  }

  const filteredTeams = teams.filter(t => {
    const isDomestic = !!t.team_type && t.team_type !== 'international';
    if (AppState.teamsFilter === 'international') return !isDomestic;
    if (AppState.teamsFilter === 'domestic') return isDomestic;
    return true;
  });

  ['all', 'international', 'domestic'].forEach(key => {
    document.getElementById(`teams-filter-${key}`)?.classList.toggle('active', AppState.teamsFilter === key);
  });

  if (subtitleEl) {
    const label = AppState.teamsFilter === 'international'
      ? 'International teams only.'
      : AppState.teamsFilter === 'domestic'
        ? 'Domestic and franchise teams only.'
        : 'All teams.';
    subtitleEl.textContent = `${label} ${filteredTeams.length} shown.`;
  }

  if (!filteredTeams.length) {
    container.innerHTML = '<p class="text-muted">No teams match this filter.</p>';
    return;
  }

  container.innerHTML = filteredTeams.map(t => `
    <div class="team-card" onclick="loadTeamDetail(${t.id})">
      <span class="team-card-badge" style="background:${t.badge_colour || '#444'}"></span>
      <div>
        <div class="team-card-name">${t.name}</div>
        <div class="team-card-code">${t.short_code || ''}${t.team_type && t.team_type !== 'international' && t.league ? ` · ${t.league}` : ''}</div>
      </div>
    </div>
  `).join('');
}

function setTeamsFilter(filter) {
  AppState.teamsFilter = ['all', 'international', 'domestic'].includes(filter) ? filter : 'all';
  if (AppState.currentScreen === 'teams') loadTeamsScreen();
}

// ── Team Detail ───────────────────────────────────────────────────────────────

let _currentTeamId = null;

async function loadTeamDetail(id) {
  _currentTeamId = id;
  showScreen('team-detail');

  const nameEl = document.getElementById('team-detail-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const data = await api('GET', `/api/teams/${id}/profile`);
  if (!data) return;

  const team = data.team || {};
  if (nameEl) nameEl.textContent = team.name || 'Team';

  const badgeEl = document.getElementById('team-detail-badge');
  if (badgeEl) {
    badgeEl.textContent = team.short_code || team.name?.slice(0,2) || 'T';
    badgeEl.style.background = team.badge_colour || '#555';
  }

  const metaEl = document.getElementById('team-detail-meta');
  if (metaEl) {
    const parts = [team.venue_name].filter(Boolean);
    metaEl.textContent = parts.join(' · ');
  }

  // Format records
  const recEl = document.getElementById('team-format-records');
  if (recEl) {
    const recs = data.format_records || [];
    if (recs.length) {
      recEl.innerHTML = `<div class="format-records-grid">${recs.map(r => `
        <div class="card format-record-card">
          <div class="fr-format">${r.format}</div>
          <div class="fr-stats">
            <span class="fr-big">${r.matches_played}</span><span class="fr-label">P</span>
            <span class="fr-big">${r.won}</span><span class="fr-label">W</span>
            <span class="fr-big">${r.lost}</span><span class="fr-label">L</span>
            <span class="fr-big">${r.drawn || 0}</span><span class="fr-label">D</span>
          </div>
          <div class="fr-pct">${r.win_pct ?? '-'}%</div>
        </div>
      `).join('')}</div>`;
    } else {
      recEl.innerHTML = '<p class="text-muted">No matches played yet.</p>';
    }
  }

  // Head-to-head opponent dropdown
  const sel = document.getElementById('h2h-opponent-select');
  if (sel) {
    const allTeams = await api('GET', '/api/teams');
    sel.innerHTML = '<option value="">Select opponent…</option>';
    (allTeams?.teams || []).forEach(t => {
      if (t.id !== id) {
        const opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.name;
        sel.appendChild(opt);
      }
    });
  }

  // Top scorers
  const scorersEl = document.getElementById('team-top-scorers');
  if (scorersEl) {
    scorersEl.innerHTML = (data.top_scorers || []).map(p => `
      <div class="performer-row">
        <a class="alm-link" onclick="goToPlayer(${p.player_id})">${p.name}</a>
        <span>${p.runs} runs</span>
      </div>`).join('') || '<p class="text-muted">—</p>';
  }

  // Top bowlers
  const bowlersEl = document.getElementById('team-top-bowlers');
  if (bowlersEl) {
    bowlersEl.innerHTML = (data.top_bowlers || []).map(p => `
      <div class="performer-row">
        <a class="alm-link" onclick="goToPlayer(${p.player_id})">${p.name}</a>
        <span>${p.wickets} wkts</span>
      </div>`).join('') || '<p class="text-muted">—</p>';
  }

  // Squad table
  const squadEl = document.getElementById('team-squad-table');
  if (squadEl) {
    const rows = data.squad_stats || [];
    if (rows.length) {
      squadEl.innerHTML = `<table class="alm-table"><thead><tr>
        <th>#</th><th>Name</th><th>Bat ★</th><th>Bowl ★</th><th>Runs</th><th>Avg</th><th>Wkts</th>
      </tr></thead><tbody>${rows.map(p => `<tr onclick="goToPlayer(${p.player_id})" style="cursor:pointer">
        <td>${p.batting_position || '—'}</td>
        <td><a class="alm-link">${p.name}</a></td>
        <td>${'★'.repeat(p.batting_rating || 0)}${'☆'.repeat(Math.max(0, 5-(p.batting_rating||0)))}</td>
        <td>${p.bowling_rating ? '★'.repeat(p.bowling_rating)+'☆'.repeat(Math.max(0,5-p.bowling_rating)) : '—'}</td>
        <td>${p.total_runs || 0}</td>
        <td>${p.bat_innings > 0 ? (p.total_runs / Math.max(1, p.bat_innings - (p.bat_innings - p.total_runs/Math.max(1,p.total_runs/Math.max(1,p.bat_innings))))).toFixed(0) : '—'}</td>
        <td>${p.total_wickets || 0}</td>
      </tr>`).join('')}</tbody></table>`;
    } else {
      squadEl.innerHTML = '<p class="text-muted">No squad data.</p>';
    }
  }

  // Recent results
  const resultsEl = document.getElementById('team-recent-results');
  if (resultsEl) {
    resultsEl.innerHTML = (data.recent_matches || []).map(m => {
      const won = m.winning_team_id === id;
      const drew = m.result_type === 'draw' || m.result_type === 'tie';
      const badge = drew ? 'D' : (won ? 'W' : 'L');
      const cls   = drew ? 'res-draw' : (won ? 'res-win' : 'res-loss');
      const opp = m.team1_name === team.name ? m.team2_name : m.team1_name;
      return `<div class="result-row">
        <span class="result-badge ${cls}">${badge}</span>
        <span class="result-opp">${opp}</span>
        <span class="result-format text-muted">${m.format}</span>
        ${_modeBadgeHtml(m.player_mode)}
        ${_canonBadgeHtml(m.canon_status)}
        <span class="result-date text-muted">${m.match_date}</span>
        <span class="result-venue text-muted">${m.venue_name || ''}</span>
      </div>`;
    }).join('') || '<p class="text-muted">No matches played yet.</p>';
  }
}

async function loadH2H() {
  const sel = document.getElementById('h2h-opponent-select');
  const el  = document.getElementById('h2h-results');
  if (!sel || !el || !_currentTeamId) return;
  const oppId = sel.value;
  if (!oppId) { el.innerHTML = ''; return; }

  el.innerHTML = '<div class="spinner"></div>';
  const data = await api('GET', `/api/teams/${_currentTeamId}/head-to-head/${oppId}`);
  if (!data) { el.innerHTML = '<p class="text-muted">No data.</p>'; return; }

  const matches = data.matches || [];
  if (!matches.length) { el.innerHTML = '<p class="text-muted">No matches between these teams.</p>'; return; }

  const byFmt = data.by_format || {};
  const summaryHtml = Object.entries(byFmt).map(([fmt, stats]) => `
    <div class="h2h-fmt-row">
      <strong>${fmt}</strong>
      <span>${stats.team1_wins}–${stats.team2_wins}${stats.draws ? `–${stats.draws}D` : ''}</span>
    </div>`).join('');

  const rowsHtml = matches.slice(0,10).map(m => `
    <div class="result-row">
      <span class="result-format text-muted">${m.format}</span>
      <span>${m.team1_name} vs ${m.team2_name}</span>
      <span class="text-muted">${m.winning_team_name ? `${m.winning_team_name} won` : 'Draw'}</span>
      <span class="result-date text-muted">${m.match_date}</span>
    </div>`).join('');

  el.innerHTML = `<div class="h2h-summary">${summaryHtml}</div><div class="h2h-matches">${rowsHtml}</div>`;
}

// ── Venues Screen ─────────────────────────────────────────────────────────────

async function loadVenuesScreen() {
  const container = document.getElementById('venues-list');
  if (!container) return;
  container.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', '/api/venues');
  const venues = data && data.venues ? data.venues : [];

  if (!venues.length) {
    container.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">🏟️</div><h3 class="empty-state-heading">No venues yet</h3><p class="empty-state-sub">Add a venue to host your matches.</p></div>`;
    return;
  }

  container.innerHTML = venues.map(v => `
    <div class="card" style="margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;cursor:pointer"
         onclick="loadVenueDetail(${v.id})">
      <div>
        <strong>${v.name}</strong>
        <div class="text-muted" style="font-size:13px">${[v.city, v.country].filter(Boolean).join(', ')}</div>
      </div>
      <span style="color:var(--text-muted);font-size:20px">›</span>
    </div>
  `).join('');
}

async function loadVenueDetail(id) {
  showScreen('venue-detail');
  const nameEl = document.getElementById('venue-detail-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const data = await api('GET', `/api/venues/${id}`);
  if (!data) return;

  const venue = data.venue || {};
  const stats = data.stats || {};

  if (nameEl) nameEl.textContent = venue.name || 'Venue';

  const metaEl = document.getElementById('venue-detail-meta');
  if (metaEl) metaEl.textContent = [venue.city, venue.country].filter(Boolean).join(', ');

  // Stat cards
  const cardsEl = document.getElementById('venue-stat-cards');
  if (cardsEl) {
    cardsEl.innerHTML = [
      { label: 'Matches', value: stats.match_count || 0 },
    ].map(c => `<div class="stat-card"><div class="stat-card-val">${c.value}</div><div class="stat-card-lbl">${c.label}</div></div>`).join('');
  }

  // Avg first innings
  const avgEl = document.getElementById('venue-avg-first-innings');
  if (avgEl) {
    const rows = stats.avg_first_innings || [];
    if (rows.length) {
      avgEl.innerHTML = rows.map(r =>
        `<div class="avg-row"><span class="fr-format">${r.format}</span><span class="avg-val">${r.avg_runs}</span><span class="text-muted"> (${r.matches} matches)</span></div>`
      ).join('');
    } else {
      avgEl.innerHTML = '<p class="text-muted">No data yet.</p>';
    }
  }

  // Records grid
  const recEl = document.getElementById('venue-records');
  if (recEl) {
    const hs  = stats.highest_team_score;
    const hi  = stats.highest_individual_score;
    const bb  = stats.best_bowling;
    const low = stats.lowest_innings;
    recEl.innerHTML = [
      hs  ? `<div class="card"><div class="record-label">Highest Team Score</div><div class="record-value">${formatScore(hs.total_runs, hs.total_wickets)}${hs.declared?'d':''}</div><div class="text-muted">${hs.team_name} · ${hs.match_date}</div></div>` : '',
      low ? `<div class="card"><div class="record-label">Lowest Team Score</div><div class="record-value">${formatScore(low.total_runs, low.total_wickets)}</div><div class="text-muted">${low.team_name} · ${low.match_date}</div></div>` : '',
      hi  ? `<div class="card"><div class="record-label">Highest Individual Score</div><div class="record-value">${hi.runs}</div><div class="text-muted">${hi.player_name} · ${hi.match_date}</div></div>` : '',
      bb  ? `<div class="card"><div class="record-label">Best Bowling</div><div class="record-value">${bb.wickets}/${bb.runs_conceded}</div><div class="text-muted">${bb.player_name} · ${bb.match_date}</div></div>` : '',
    ].filter(Boolean).join('');
  }

  // Recent matches
  const recentEl = document.getElementById('venue-recent-matches');
  if (recentEl) {
    recentEl.innerHTML = (data.recent_matches || []).map(m => `
      <div class="result-row">
        <span class="result-format text-muted">${m.format}</span>
        ${_modeBadgeHtml(m.player_mode)}
        ${_canonBadgeHtml(m.canon_status)}
        <span>${m.team1_name} vs ${m.team2_name}</span>
        <span class="text-muted">${m.winning_team_name ? m.winning_team_name + ' won' : 'Draw'}</span>
        <span class="result-date text-muted">${m.match_date}</span>
      </div>`).join('') || '<p class="text-muted">No matches yet.</p>';
  }
}

// ── Settings Screen ────────────────────────────────────────────────────────────

async function loadSettingsScreen() {
  // Sync toggle button states from AppState
  const dmBtn = document.getElementById('settings-darkmode');
  if (dmBtn) { dmBtn.textContent = AppState.darkMode ? 'On' : 'Off'; dmBtn.classList.toggle('active', AppState.darkMode); }
  const bcBtn = document.getElementById('settings-broadcast');
  if (bcBtn) { bcBtn.textContent = AppState.broadcastMode ? 'On' : 'Off'; bcBtn.classList.toggle('active', AppState.broadcastMode); }
  const sndBtn = document.getElementById('settings-sound');
  if (sndBtn) { sndBtn.textContent = AppState.soundEnabled ? 'On' : 'Off'; sndBtn.classList.toggle('active', AppState.soundEnabled); }
  const recBtn = document.getElementById('settings-record-popups');
  if (recBtn) { recBtn.textContent = AppState.recordPopups ? 'On' : 'Off'; recBtn.classList.toggle('active', AppState.recordPopups); }

  // Sync animation speed radios
  document.querySelectorAll('input[name="anim-speed"]').forEach(r => {
    r.checked = (r.value === AppState.animationSpeed);
  });

  // Sync default format
  const fmtSel = document.getElementById('settings-default-format');
  if (fmtSel && AppState.defaultFormat) fmtSel.value = AppState.defaultFormat;
  const scoringSel = document.getElementById('settings-default-scoring');
  if (scoringSel) scoringSel.value = getDefaultScoringMode();

  // Load venues for default venue dropdown
  const venSel = document.getElementById('settings-default-venue');
  if (venSel && venSel.options.length <= 1) {
    const vdata = await api('GET', '/api/venues');
    if (vdata && vdata.venues) {
      vdata.venues.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = v.name;
        venSel.appendChild(opt);
      });
    }
  }
  if (venSel && AppState.defaultVenueId) venSel.value = AppState.defaultVenueId;

  populateSettingsLegal();
  await loadDbStats();
}

function setAnimationSpeed(speed) {
  AppState.animationSpeed = speed;
  try { localStorage.setItem('ribi_anim_speed', speed); } catch (_) {}
  // Sync radio buttons if settings screen is open
  document.querySelectorAll('input[name="anim-speed"]').forEach(r => {
    r.checked = (r.value === speed);
  });
}

function setDefaultFormat(fmt) {
  AppState.defaultFormat = fmt;
  try { localStorage.setItem('ribi_default_format', fmt || ''); } catch (_) {}
}

function setDefaultScoringMode(mode) {
  const prevMode = getDefaultScoringMode();
  const nextMode = mode === 'classic' ? 'classic' : 'modern';
  AppState.defaultScoringMode = nextMode;
  try { localStorage.setItem('ribi_default_scoring_mode', nextMode); } catch (_) {}
  const scoringSel = document.getElementById('settings-default-scoring');
  if (scoringSel) scoringSel.value = nextMode;
  if (!AppState._playScoringMode || AppState._playScoringMode === prevMode) {
    AppState._playScoringMode = nextMode;
  }
  syncWelcomeScoringMode();
  syncPlayScoringMode();
}

function setDefaultVenue(venueId) {
  AppState.defaultVenueId = venueId || null;
  try { localStorage.setItem('ribi_default_venue', venueId || ''); } catch (_) {}
}

async function loadDbStats() {
  const el = document.getElementById('db-stats');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', '/api/health');
  if (!data) { el.innerHTML = '<p class="text-muted">Could not load stats.</p>'; return; }

  const tables = data.tables || {};
  const tableRows = Object.entries(tables)
    .map(([k, v]) => `<div class="db-stat-item"><span class="db-stat-label">${k}</span><span class="text-mono">${v.toLocaleString()}</span></div>`)
    .join('');

  el.innerHTML = `
    <div class="db-stat-item">
      <span class="db-stat-label">DB size</span>
      <span class="text-mono">${(data.db_size_mb || 0).toFixed(2)} MB</span>
    </div>
    <div class="db-stat-item">
      <span class="db-stat-label">SQLite</span>
      <span class="text-mono">${data.sqlite_version || '—'}</span>
    </div>
    ${tableRows}
  `;
}

function downloadAlmanack() {
  window.location.href = '/api/export/almanack';
}

function downloadBackup() {
  window.location.href = '/api/export/full-backup';
}

async function handleRestoreFile(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const ok = confirm(`Restore from "${file.name}"?\n\nThis will REPLACE existing data with the content of the backup. This cannot be undone.`);
  if (!ok) { input.value = ''; return; }

  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    showError('Invalid JSON file'); input.value = ''; return;
  }

  // Detect backup type: full-backup has a "data" key
  let result;
  if (data.data) {
    result = await api('POST', '/api/import/full-backup', { data: data.data, confirm: true });
  } else {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/api/import/almanack', { method: 'POST', body: formData });
      result = await res.json();
      if (!res.ok) { showError(result.error || 'Restore failed'); input.value = ''; return; }
    } catch (e) { showError('Upload error: ' + e.message); input.value = ''; return; }
  }

  if (result) {
    const counts = result.restored || {};
    const summary = Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(', ');
    alert(`Restore complete!\n${summary}`);
    loadDbStats();
  }
  input.value = '';
}

async function archiveMatches() {
  const daysInput = document.getElementById('archive-days');
  const days = parseInt(daysInput?.value) || 30;
  if (days < 1) { showError('Days must be at least 1'); return; }

  const resultEl = document.getElementById('archive-result');
  if (resultEl) { resultEl.classList.add('hidden'); }

  const res = await api('POST', '/api/archive/old-matches', { older_than_days: days });
  if (!res) return;

  if (resultEl) {
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `Archived <strong>${res.archived_matches}</strong> matches, removed <strong>${res.deliveries_removed.toLocaleString()}</strong> deliveries (~${res.space_saved_estimate_mb} MB saved). DB now ${res.db_size_mb} MB.`;
  }
  loadDbStats();
}

// ── Journal Screen ─────────────────────────────────────────────────────────────

const JournalUI = {
  search:      '',
  format:      '',
  page:        1,
  totalPages:  1,
  _debounceTimer: null,
};

function loadJournalScreen() {
  JournalUI.search = '';
  JournalUI.format = '';
  JournalUI.page   = 1;
  const searchEl = document.getElementById('journal-search');
  if (searchEl) searchEl.value = '';
  document.querySelectorAll('.journal-filter-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.fmt === ''));
  _fetchJournal();
}

function journalSearchInput() {
  clearTimeout(JournalUI._debounceTimer);
  JournalUI._debounceTimer = setTimeout(() => {
    JournalUI.search = document.getElementById('journal-search')?.value || '';
    JournalUI.page = 1;
    _fetchJournal();
  }, 300);
}

function setJournalFormat(fmt, btn) {
  JournalUI.format = fmt;
  JournalUI.page   = 1;
  document.querySelectorAll('.journal-filter-btn').forEach(b =>
    b.classList.toggle('active', b === btn));
  _fetchJournal();
}

function journalGoPage(page) {
  JournalUI.page = page;
  _fetchJournal();
}

async function _fetchJournal() {
  const el = document.getElementById('journal-entries');
  const pagEl = document.getElementById('journal-pagination');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';

  const params = new URLSearchParams({ page: JournalUI.page });
  if (JournalUI.search) params.set('search', JournalUI.search);
  if (JournalUI.format) params.set('format', JournalUI.format);

  const data = await api('GET', `/api/journal?${params}`);
  if (!data) { el.innerHTML = '<p class="text-muted">Could not load journal.</p>'; return; }

  const entries = data.entries || [];
  JournalUI.totalPages = data.total_pages || 1;

  if (!entries.length) {
    const searching = JournalUI.search || JournalUI.format;
    el.innerHTML = searching
      ? `<div class="empty-state-card"><div class="empty-state-icon">🔍</div><h3 class="empty-state-heading">No journal entries found</h3><p class="empty-state-sub">Try adjusting your search or filter.</p></div>`
      : `<div class="empty-state-card"><div class="empty-state-icon">📓</div><h3 class="empty-state-heading">No journal entries yet</h3><p class="empty-state-sub">They appear automatically after each completed match.</p></div>`;
    if (pagEl) pagEl.innerHTML = '';
    return;
  }

  el.innerHTML = entries.map(e => {
    const resultStr = _journalResultStr(e);
    return `<div class="journal-entry-card">
      <div class="journal-match-header">
        <span class="journal-date">${e.match_date || '—'}</span>
        <span class="journal-teams">${e.team1_name} vs ${e.team2_name}</span>
        <span class="badge badge-format">${e.format || ''}</span>
        ${resultStr ? `<span class="journal-result">${resultStr}</span>` : ''}
        <a href="#" class="journal-view-match" onclick="goToMatch(${e.match_id});return false">View Match</a>
      </div>
      <div class="journal-text">${_escapeHtml(e.note_text || '')}</div>
    </div>`;
  }).join('');

  // Pagination
  if (pagEl) {
    if (JournalUI.totalPages <= 1) { pagEl.innerHTML = ''; return; }
    let pages = '';
    for (let p = 1; p <= JournalUI.totalPages; p++) {
      pages += `<button class="btn-page${p === JournalUI.page ? ' active' : ''}" onclick="journalGoPage(${p})">${p}</button>`;
    }
    pagEl.innerHTML = `<div class="pagination-inner">${pages}</div>`;
  }
}

function _journalResultStr(e) {
  if (!e.result_type) return '';
  if (e.result_type === 'draw') return 'Draw';
  if (e.result_type === 'tie') return 'Tie';
  const winner = e.winning_team_name || '?';
  if (e.result_type === 'runs' && e.margin_runs) return `${winner} won by ${e.margin_runs} runs`;
  if (e.result_type === 'wickets' && e.margin_wickets) return `${winner} won by ${e.margin_wickets} wkts`;
  return `${winner} won`;
}

function _escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/"/g,'&quot;').replace(/\n/g,'<br>');
}

function goToMatch(matchId) {
  openPlayedMatch(matchId);
}

function openPlayedMatch(matchId) {
  if (!matchId) return;
  // Match screen expects an object-like active match, not a raw id.
  AppState.historicalMatchView = true;
  AppState.activeMatch = { id: matchId, match_id: matchId };
  AppState.activeMatchId = matchId;
  showScreen('match');
}

// ── Keyboard Shortcuts ────────────────────────────────────────────────────────

function initKeyboard() {
  document.addEventListener('keydown', e => {
    // Ignore when typing in inputs
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    // Ignore when a blocking overlay is open
    if (document.querySelector('.milestone-toast-dim, .record-overlay-dim')) return;

    // Demo mode — arrow navigation
    if (DemoMode.active) {
      if (e.key === 'ArrowRight') { e.preventDefault(); DemoMode.next(); return; }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); DemoMode.previous(); return; }
      if (e.key === 'Escape')     { e.preventDefault(); DemoMode.end(); return; }
      // S is rebound in demo mode to not clash with Sound toggle
      return; // absorb all other keys in demo
    }

    const onMatch = AppState.currentScreen === 'match';

    switch (e.key) {
      // Space or R — primary action (Roll ball / or pass through)
      case ' ': {
        if (!onMatch) break;
        const rollBtn = document.getElementById('btn-roll');
        if (rollBtn && !rollBtn.disabled && !rollBtn.classList.contains('hidden')) {
          e.preventDefault();
          rollBtn.click();
        }
        break;
      }
      case 'r': case 'R': {
        if (!onMatch) break;
        const rollBtn2 = document.getElementById('btn-roll');
        if (rollBtn2 && !rollBtn2.disabled && !rollBtn2.classList.contains('hidden')) {
          e.preventDefault();
          rollBtn2.click();
        }
        break;
      }
      // A — Appeal (Manual mode, HOWZAT state)
      case 'a': case 'A': {
        if (!onMatch) break;
        if (MatchUI.diceState === DiceState.HOWZAT) {
          e.preventDefault();
          document.getElementById('btn-appeal')?.click();
        }
        break;
      }
      // C — Continue / NOT OUT (Manual mode, NOT_OUT state)
      case 'c': case 'C': {
        if (!onMatch) break;
        if (MatchUI.diceState === DiceState.NOT_OUT) {
          e.preventDefault();
          document.getElementById('btn-continue-notout')?.click();
        }
        break;
      }
      // D — Dismissal (Manual mode, OUT_PENDING state) or Dark Mode toggle
      case 'd': case 'D': {
        if (onMatch && MatchUI.diceState === DiceState.OUT_PENDING) {
          e.preventDefault();
          document.getElementById('btn-dismissal')?.click();
        } else {
          toggleDarkMode();
        }
        break;
      }
      // M — toggle Manual/Auto (between balls only)
      case 'm': case 'M': {
        if (!onMatch) break;
        if (MatchUI.diceState === DiceState.IDLE && AppState.playerMode !== 'ai_vs_ai') {
          const newMode = MatchUI.rollMode === 'manual' ? 'auto' : 'manual';
          setRollMode(newMode);
        }
        break;
      }
      // F — fast sim
      case 'f': case 'F': {
        if (!onMatch) break;
        const fsBtn = document.getElementById('btn-fast-sim');
        if (fsBtn && !fsBtn.disabled) fsBtn.click();
        break;
      }
      case 'b': case 'B': toggleBroadcastMode(); break;
      case 's': case 'S': toggleSound(); break;
      case 'Escape': {
        clearError();
        document.querySelectorAll('.milestone-toast-dim, .milestone-toast, .record-overlay-dim, .record-overlay-card').forEach(el => el.remove());
        break;
      }
    }
  });
}

// ── Broadcast Graphic System ──────────────────────────────────────────────────

// Team colour map for match-result headline tint
const TEAM_COLORS = {
  'England':       '#003f7f',
  'Australia':     '#c8922a',
  'India':         '#138808',
  'Pakistan':      '#01411c',
  'New Zealand':   '#1a1a1a',
  'South Africa':  '#007a4d',
  'West Indies':   '#7b0c1f',
  'Sri Lanka':     '#003087',
  'Bangladesh':    '#006a4e',
  'Afghanistan':   '#002366',
};

const GRAPHIC_TIMING = {
  normal: {
    wicket:          { hold: 3000, animIn: 300, animOut: 300 },
    duck:            { hold: 3500, animIn: 400, animOut: 300 },
    fifty:           { hold: 4000, animIn: 400, animOut: 400 },
    century:         { hold: 6000, animIn: 500, animOut: 400 },
    one_fifty:       { hold: 5000, animIn: 500, animOut: 400 },
    double_century:  { hold: 8000, animIn: 600, animOut: 400 },
    five_fer:        { hold: 5000, animIn: 400, animOut: 400 },
    ten_wicket:      { hold: 8000, animIn: 500, animOut: 400 },
    almanack_record: { hold: 5000, animIn: 400, animOut: 400 },
    world_record:    { hold: 10000, animIn: 600, animOut: 500 },
    over_complete:   { hold: 2000, animIn: 200, animOut: 200 },
    story_alert:     { hold: 2400, animIn: 220, animOut: 220 },
  },
  broadcast: {
    wicket:          { hold: 5000, animIn: 400, animOut: 400 },
    duck:            { hold: 5000, animIn: 500, animOut: 400 },
    fifty:           { hold: 6000, animIn: 500, animOut: 500 },
    century:         { hold: 8000, animIn: 600, animOut: 500 },
    one_fifty:       { hold: 7000, animIn: 600, animOut: 500 },
    double_century:  { hold: 12000, animIn: 700, animOut: 500 },
    five_fer:        { hold: 7000, animIn: 500, animOut: 500 },
    ten_wicket:      { hold: 10000, animIn: 600, animOut: 500 },
    almanack_record: { hold: 8000, animIn: 500, animOut: 500 },
    world_record:    { hold: 15000, animIn: 700, animOut: 600 },
    over_complete:   { hold: 3000, animIn: 300, animOut: 300 },
    story_alert:     { hold: 3600, animIn: 300, animOut: 300 },
  },
};

function getGraphicTiming(type) {
  const mode = AppState.broadcastMode ? 'broadcast' : 'normal';
  return GRAPHIC_TIMING[mode][type] || { hold: 3000, animIn: 300, animOut: 300 };
}

function getGraphicPriority(type) {
  const p = {
    world_record: 13, almanack_record: 12, double_century: 11,
    ten_wicket: 10, century: 9, five_fer: 8, one_fifty: 7,
    duck: 6, wicket: 5, fifty: 4,
    story_alert: 2, over_complete: 1,
  };
  return p[type] || 0;
}

const GraphicQueue = {
  queue: [],
  isPlaying: false,
  _currentEl: null,
  _clearTimer: null,

  add(graphic) {
    // Over-complete: skip if queue already has anything (lower priority)
    if (graphic.type === 'over_complete' && this.queue.length > 0) return;
    this.queue.push(graphic);
    if (!this.isPlaying) this._next();
  },

  _next() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this._hideAll();
      return;
    }
    // Skip over_complete if higher-priority items follow
    while (this.queue.length > 1 && this.queue[0].type === 'over_complete') {
      this.queue.shift();
    }
    this.isPlaying = true;
    const graphic = this.queue.shift();
    this._show(graphic);
  },

  _show(graphic) {
    // Suppress all graphics in 'instant' animation speed mode (not in demo)
    if (AppState.animationSpeed === 'instant' && !DemoMode.active) { this._next(); return; }
    // In screenshot mode, hold indefinitely (very long timer)
    if (DemoMode.screenshotMode) {
      // handled below — just don't auto-dismiss
    }

    const timing = getGraphicTiming(graphic.type);
    if (timing.hold === 0) { this._next(); return; }

    const el = this._render(graphic);
    if (!el) { this._next(); return; }

    const overlay = document.getElementById('graphic-overlay');
    if (!overlay) { this._next(); return; }
    overlay.innerHTML = '';
    overlay.appendChild(el);
    overlay.style.display = '';
    this._currentEl = el;

    // Backdrop for card-style graphics
    const needsBackdrop = [
      'fifty','century','one_fifty','double_century',
      'five_fer','ten_wicket','almanack_record','world_record'
    ].includes(graphic.type);
    const backdrop = document.getElementById('graphic-backdrop');
    if (backdrop) {
      if (needsBackdrop) backdrop.classList.add('active');
      else backdrop.classList.remove('active');
    }

    // Trigger in-animation on next paint
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('visible')));

    // Play sound
    SoundEngine.playGraphic(graphic.type);

    // Auto-dismiss after hold (not in screenshot mode — holds indefinitely)
    if (!DemoMode.screenshotMode) {
      this._clearTimer = setTimeout(() => this._dismiss(), timing.hold);
    }
  },

  _dismiss() {
    if (this._clearTimer) { clearTimeout(this._clearTimer); this._clearTimer = null; }
    const el = this._currentEl;
    if (!el) { this._afterDismiss(); return; }

    const type = el.dataset.graphicType || 'wicket';
    const timing = getGraphicTiming(type);
    el.classList.remove('visible');
    setTimeout(() => this._afterDismiss(), timing.animOut || 300);
  },

  _afterDismiss() {
    const overlay = document.getElementById('graphic-overlay');
    if (overlay) { overlay.innerHTML = ''; overlay.style.display = 'none'; }
    const backdrop = document.getElementById('graphic-backdrop');
    if (backdrop) backdrop.classList.remove('active');
    this._currentEl = null;
    this._next();
  },

  clear() {
    if (this._clearTimer) { clearTimeout(this._clearTimer); this._clearTimer = null; }
    this.queue = [];
    this.isPlaying = false;
    this._currentEl = null;
    const overlay = document.getElementById('graphic-overlay');
    if (overlay) { overlay.innerHTML = ''; overlay.style.display = 'none'; }
    const backdrop = document.getElementById('graphic-backdrop');
    if (backdrop) backdrop.classList.remove('active');
  },

  _hideAll() {
    const overlay = document.getElementById('graphic-overlay');
    if (overlay) { overlay.innerHTML = ''; overlay.style.display = 'none'; }
    const backdrop = document.getElementById('graphic-backdrop');
    if (backdrop) backdrop.classList.remove('active');
  },

  // ── Graphic renderers ─────────────────────────────────────────

  _render(graphic) {
    const el = document.createElement('div');
    el.dataset.graphicType = graphic.type;
    switch (graphic.type) {
      case 'wicket':          return this._wicket(el, graphic);
      case 'duck':            return this._duck(el, graphic);
      case 'fifty':           return this._fifty(el, graphic);
      case 'century':         return this._century(el, graphic);
      case 'one_fifty':       return this._oneFifty(el, graphic);
      case 'double_century':  return this._doubleCentury(el, graphic);
      case 'five_fer':        return this._fiveFer(el, graphic);
      case 'ten_wicket':      return this._tenWicket(el, graphic);
      case 'almanack_record': return this._almanackRecord(el, graphic);
      case 'world_record':    return this._worldRecord(el, graphic);
      case 'over_complete':   return this._overComplete(el, graphic);
      case 'story_alert':     return this._storyAlert(el, graphic);
      default: return null;
    }
  },

  _spawnConfetti(el, count = 18) {
    const container = el.querySelector('.gfx-confetti-container');
    if (!container) return;
    const colors = ['var(--almanack-gold)', '#fff', '#e74c3c', '#2ecc71', '#9b59b6'];
    for (let i = 0; i < count; i++) {
      const p = document.createElement('div');
      p.className = 'confetti-piece';
      p.style.left = `${Math.random() * 100}%`;
      p.style.animationDelay = `${(Math.random() * 1.8).toFixed(2)}s`;
      p.style.background = colors[i % colors.length];
      container.appendChild(p);
    }
  },

  _wicket(el, g) {
    el.className = 'graphic graphic-banner graphic-wicket';
    const ords = ['1st','2nd','3rd','4th','5th','6th','7th','8th','9th','10th'];
    const ord = g.wicketNum ? (ords[(g.wicketNum - 1)] || `${g.wicketNum}th`) : '';
    const fow = (g.wicketNum && g.fowScore != null) ? `FOW: ${g.wicketNum}-${g.fowScore}` : '';
    const dism = (g.dismissalType || 'out').replace(/_/g, ' ');
    const sr = g.balls > 0 ? ((g.runs / g.balls) * 100).toFixed(1) : '0.0';
    el.innerHTML = `
      <div class="gw-header">
        <span class="gw-label">WICKET</span>
        <span class="gw-dot">●</span>
        <span class="gw-bowler">${escHtml(g.bowlerName || '')}</span>
      </div>
      <div class="gw-rule"></div>
      <div class="gw-batter">${escHtml(g.batterName || 'Batter')} <span class="gw-dism">${escHtml(dism)}</span> ${g.runs} (${g.balls}b) SR: ${sr}</div>
      <div class="gw-fow">${ord ? ord + ' wicket' : ''}${fow ? ' &nbsp;•&nbsp; ' + fow : ''}</div>`;
    return el;
  },

  _duck(el, g) {
    el.className = 'graphic graphic-banner graphic-duck';
    const dism = (g.dismissalType || 'out').replace(/_/g, ' ');
    el.innerHTML = `
      <div class="gd-header">
        <span class="duck-emoji">🦆</span>
        <span class="gd-label">DUCK!</span>
      </div>
      <div class="gd-rule"></div>
      <div class="gd-batter">${escHtml(g.batterName || 'Batter')} <span class="gd-dism">${escHtml(dism)}</span> 0 (${g.balls}b)</div>
      <div class="gd-bowler">Cheap dismissal from ${escHtml(g.bowlerName || 'Bowler')}</div>`;
    return el;
  },

  _fifty(el, g) {
    el.className = 'graphic graphic-card graphic-fifty';
    const sr = g.balls > 0 ? ((g.runs / g.balls) * 100).toFixed(1) : '0.0';
    el.innerHTML = `
      <div class="gf-header"><span class="milestone-star">★</span> HALF CENTURY <span class="milestone-star">★</span></div>
      <div class="gf-player">${escHtml(g.playerName)}</div>
      <div class="gf-score">${g.runs}*</div>
      <div class="gf-detail">(${g.balls} balls) &nbsp; SR: ${sr}</div>
      <div class="gf-context">${escHtml(g.matchContext || '')}</div>`;
    return el;
  },

  _century(el, g) {
    el.className = 'graphic graphic-card graphic-century';
    const sr = g.balls > 0 ? ((g.runs / g.balls) * 100).toFixed(1) : '0.0';
    const digits = String(g.runs).split('').map((d, i) =>
      `<span class="century-digit" style="animation-delay:${i * 220}ms">${d}</span>`
    ).join('');
    el.innerHTML = `
      <div class="gfx-confetti-container"></div>
      <div class="gc-header">✦ ✦ ✦ &nbsp; CENTURY! &nbsp; ✦ ✦ ✦</div>
      <div class="gc-player">${escHtml(g.playerName)}</div>
      ${g.teamName ? `<div class="gc-team">${renderTeamLabel(g.teamName, { compact: true })}</div>` : ''}
      <div class="gc-digits">${digits}<span class="gc-star">*</span></div>
      <div class="gc-detail">(${g.balls} balls) &nbsp; SR: ${sr}</div>
      <div class="gc-context">${escHtml(g.matchContext || '')}</div>`;
    this._spawnConfetti(el, 20);
    return el;
  },

  _oneFifty(el, g) {
    el.className = 'graphic graphic-card graphic-one-fifty';
    const sr = g.balls > 0 ? ((g.runs / g.balls) * 100).toFixed(1) : '0.0';
    const digits = ['1','5','0'].map((d, i) =>
      `<span class="century-digit" style="animation-delay:${i * 220}ms">${d}</span>`
    ).join('');
    el.innerHTML = `
      <div class="go-header">⭐ &nbsp; 150! &nbsp; ⭐</div>
      <div class="go-player">${escHtml(g.playerName)}</div>
      <div class="gc-digits">${digits}<span class="gc-star">*</span></div>
      <div class="go-detail">(${g.balls} balls) &nbsp; SR: ${sr}</div>
      <div class="go-context">${escHtml(g.matchContext || '')}</div>`;
    return el;
  },

  _doubleCentury(el, g) {
    el.className = 'graphic graphic-card graphic-double-century';
    const sr = g.balls > 0 ? ((g.runs / g.balls) * 100).toFixed(1) : '0.0';
    const digits = ['2','0','0'].map((d, i) =>
      `<span class="century-digit" style="animation-delay:${i * 250}ms">${d}</span>`
    ).join('');
    el.innerHTML = `
      <div class="gfx-confetti-container"></div>
      <div class="gdc-header">🌟 &nbsp; DOUBLE CENTURY! &nbsp; 🌟</div>
      <div class="gdc-player">${escHtml(g.playerName)}</div>
      <div class="gc-digits">${digits}<span class="gc-star">*</span></div>
      <div class="gdc-detail">(${g.balls} balls) &nbsp; SR: ${sr}</div>
      <div class="gdc-context">${escHtml(g.matchContext || '')}</div>`;
    this._spawnConfetti(el, 28);
    return el;
  },

  _fiveFer(el, g) {
    el.className = 'graphic graphic-card graphic-five-fer';
    el.innerHTML = `
      <div class="gff-header"><span class="bowling-ball-emoji">🎳</span> &nbsp; FIVE WICKET HAUL! &nbsp; <span class="bowling-ball-emoji">🎳</span></div>
      <div class="gff-player">${escHtml(g.playerName)}</div>
      ${g.teamName ? `<div class="gff-team">${renderTeamLabel(g.teamName, { compact: true })}</div>` : ''}
      <div class="gff-figures">${escHtml(g.figures || '5/?')}</div>
      <div class="gff-detail">in ${escHtml(g.overs || '?')} overs &nbsp;•&nbsp; Econ: ${escHtml(g.econ || '?')}</div>`;
    return el;
  },

  _tenWicket(el, g) {
    el.className = 'graphic graphic-card graphic-ten-wicket';
    el.innerHTML = `
      <div class="gtw-header"><span class="lightning-emoji">⚡</span> &nbsp; TEN WICKETS IN THE MATCH! &nbsp; <span class="lightning-emoji">⚡</span></div>
      <div class="gtw-player">${escHtml(g.playerName)}</div>
      ${g.teamName ? `<div class="gtw-team">${renderTeamLabel(g.teamName, { compact: true })}</div>` : ''}
      <div class="gtw-figures">${escHtml(g.figures || '10 wkts')}</div>
      <div class="gtw-subtitle">A match for the history books</div>`;
    return el;
  },

  _almanackRecord(el, g) {
    el.className = 'graphic graphic-card graphic-almanack-record';
    el.innerHTML = `
      <div class="gar-label">📖 &nbsp; NEW ALMANACK RECORD</div>
      <div class="gar-type">${escHtml(g.typeLabel || '')}</div>
      <div class="gar-value">${escHtml(String(g.newValue))}</div>
      <div class="gar-holder">${escHtml(g.playerName || '')}</div>
      ${g.previousValue != null
        ? `<div class="gar-prev">Previous: ${escHtml(String(g.previousValue))}${g.previousHolder ? ' &nbsp;('+escHtml(g.previousHolder)+')' : ''}</div>`
        : '<div class="gar-prev">First ever record</div>'}`;
    return el;
  },

  _worldRecord(el, g) {
    el.className = 'graphic graphic-card graphic-world-record';
    el.innerHTML = `
      <div class="gfx-confetti-container"></div>
      <div class="gwr-header"><span class="globe-emoji">🌍</span> &nbsp; REAL WORLD RECORD BEATEN! &nbsp; <span class="globe-emoji">🌍</span></div>
      <div class="gwr-type">${escHtml(g.typeLabel || '')}</div>
      <div class="gwr-value">${escHtml(String(g.newValue))}</div>
      <div class="gwr-holder">${escHtml(g.playerName || '')}</div>
      ${g.worldRecord != null ? `
        <div class="gwr-rule"></div>
        <div class="gwr-prev-label">Previous real-world record:</div>
        <div class="gwr-prev">${escHtml(String(g.worldRecord))}${g.worldRecordHolder ? ' &nbsp;·&nbsp; '+escHtml(g.worldRecordHolder) : ''}</div>
      ` : ''}`;
    this._spawnConfetti(el, 22);
    return el;
  },

  _overComplete(el, g) {
    el.className = 'graphic graphic-lower-third graphic-over-complete';
    let line2 = g.teamScore || '';
    if (g.rr) line2 += ` &nbsp;·&nbsp; RR: ${g.rr}`;
    if (g.rrr) line2 += ` &nbsp;·&nbsp; req: ${g.rrr}`;
    el.innerHTML = `
      <span class="goc-over">End of over ${g.overNumber}</span>
      <span class="goc-sep">•</span>
      <span class="goc-bowler">${escHtml(g.bowlerName || '')}</span>
      <span class="goc-sep">•</span>
      <span class="goc-figures">${g.wickets}-${g.maidens}-${g.runs}</span>
      <span class="goc-score">${line2}</span>`;
    return el;
  },

  _storyAlert(el, g) {
    el.className = `graphic graphic-lower-third graphic-story-alert graphic-story-alert-${g.tone || 'neutral'}`;
    el.innerHTML = `
      <span class="gsa-label">${escHtml(g.label || 'Story Update')}</span>
      <span class="gsa-sep">•</span>
      <span class="gsa-text">${escHtml(g.text || '')}</span>`;
    return el;
  },
};

// ── Milestone + record → graphic detection ────────────────────────────────────

function _detectAndQueueGraphics(res, delivery, preBallState, freshState) {
  if (!res) return;
  const gfx = [];

  // ── Wicket / Duck ──────────────────────────────────────────────
  if (delivery && delivery.outcome_type === 'wicket') {
    const strikerPid = preBallState?.current_striker_id;
    const strikerInfo  = strikerPid ? MatchUI.allPlayers[strikerPid] : null;
    const strikerBI    = strikerPid
      ? (preBallState?.batter_innings || []).find(b => b.player_id === strikerPid && b.status === 'batting')
      : null;
    const bowlerPid    = preBallState?.current_bowler_id;
    const bowlerInfo   = bowlerPid ? MatchUI.allPlayers[bowlerPid] : null;

    const runs   = strikerBI?.runs        ?? 0;
    const balls  = strikerBI?.balls_faced ?? 0;
    const dism   = delivery.dismissal_type || 'out';
    // wicket count and FOW come from fresh state (after the ball)
    const freshInn     = freshState?.current_innings;
    const wicketNum    = freshInn?.total_wickets ?? null;
    const fowScore     = freshInn?.total_runs    ?? null;

    gfx.push({
      type: runs === 0 ? 'duck' : 'wicket',
      batterName:    strikerInfo?.name  || 'Batter',
      bowlerName:    bowlerInfo?.name   || 'Bowler',
      runs, balls, dismissalType: dism, wicketNum, fowScore,
    });
  }

  // ── Batting + bowling milestones from API ──────────────────────
  const matchState = freshState || MatchUI.lastState;
  const match      = matchState?.match || MatchUI.lastState?.match || {};
  const matchCtx   = [match.team1_name, match.team2_name].filter(Boolean).join(' v ')
    + (match.venue_name ? ' · ' + match.venue_name : '');

  for (const ms of (res.milestones || [])) {
    const pid        = ms.player_id;
    const playerInfo = pid ? MatchUI.allPlayers[pid] : null;
    const playerName = ms.player_name || playerInfo?.name || 'Player';
    const teamName   = playerInfo?.team_name || '';

    // Get live innings stats for this player
    const bi  = freshState ? (freshState.batter_innings  || []).find(b => b.player_id === pid) : null;
    const bwi = freshState ? (freshState.bowler_innings  || []).find(b => b.player_id === pid) : null;

    if (ms.type === 'batter_50') {
      gfx.push({
        type: 'fifty', playerName,
        runs:  bi?.runs        ?? 50,
        balls: bi?.balls_faced ?? (ms.balls || 0),
        matchContext: matchCtx,
      });
    } else if (ms.type === 'batter_100') {
      gfx.push({
        type: 'century', playerName, teamName,
        runs:  bi?.runs        ?? 100,
        balls: bi?.balls_faced ?? (ms.balls || 0),
        matchContext: matchCtx,
        format: matchState?.format || match.format || '',
      });
    } else if (ms.type === 'batter_150') {
      gfx.push({
        type: 'one_fifty', playerName,
        runs:  bi?.runs        ?? 150,
        balls: bi?.balls_faced ?? (ms.balls || 0),
        matchContext: matchCtx,
      });
    } else if (ms.type === 'batter_200') {
      gfx.push({
        type: 'double_century', playerName,
        runs:  bi?.runs        ?? 200,
        balls: bi?.balls_faced ?? (ms.balls || 0),
        matchContext: matchCtx,
      });
    } else if (ms.type === 'bowler_5fer') {
      const wkts      = bwi?.wickets       ?? 5;
      const runsConc  = bwi?.runs_conceded ?? 0;
      const ovsF      = formatBowlerOvers(bwi?.overs ?? 0, bwi?.balls ?? 0);
      const totalOvs  = (bwi?.overs ?? 0) + (bwi?.balls ?? 0) / 6;
      const econ      = totalOvs > 0 ? (runsConc / totalOvs).toFixed(2) : '0.00';
      gfx.push({
        type: 'five_fer', playerName, teamName,
        figures: `${wkts}/${runsConc}`,
        overs: ovsF,
        econ,
      });
    } else if (ms.type === 'bowler_10fer') {
      gfx.push({
        type: 'ten_wicket', playerName, teamName,
        figures: ms.figures || '10 wkts',
      });
    }
  }

  // ── Records broken ─────────────────────────────────────────────
  for (const rec of (res.records_broken || [])) {
    // Accumulate for end-of-match summary regardless of popup setting
    const existing = MatchUI.recordsBroken.findIndex(r => r.type === rec.type);
    if (existing >= 0) MatchUI.recordsBroken[existing] = rec;
    else MatchUI.recordsBroken.push(rec);

    if (AppState.recordPopups) {
      const typeLabel = RECORD_LABELS[rec.type] || rec.type.toUpperCase().replace(/_/g, ' ');
      const isWorld   = !!(rec.is_world_record);

      gfx.push({
        type: isWorld ? 'world_record' : 'almanack_record',
        typeLabel,
        newValue:          rec.new_value,
        playerName:        rec.player_name         || '',
        previousValue:     rec.previous_value      ?? null,
        previousHolder:    rec.previous_holder     || null,
        worldRecord:       rec.world_record_value  ?? null,
        worldRecordHolder: rec.world_record_holder || null,
      });
    }
  }

  // ── Over complete ──────────────────────────────────────────────
  if (!res.innings_complete && !res.match_complete && freshState && preBallState) {
    const prevOver = preBallState.over_number ?? -1;
    const newOver  = freshState.over_number   ?? -1;
    if (newOver > prevOver && newOver > 0) {
      const bowlerPid = preBallState.current_bowler_id;
      const bInfo     = bowlerPid ? MatchUI.allPlayers[bowlerPid] : null;
      const bwi       = (preBallState.bowler_innings || []).find(b => b.player_id === bowlerPid) || {};
      const freshInn  = freshState.current_innings;
      const teamScore = freshInn
        ? formatScore(freshInn.total_runs, freshInn.total_wickets)
        : '';
      const crr = freshInn?.run_rate        ?? null;
      const rrr = freshInn?.required_rate   ?? null;

      gfx.push({
        type: 'over_complete',
        overNumber: newOver,  // overs complete = the over that just finished
        bowlerName: bInfo?.name || 'Bowler',
        wickets:  bwi.wickets       ?? 0,
        maidens:  bwi.maidens       ?? 0,
        runs:     bwi.runs_conceded ?? 0,
        teamScore,
        rr:  crr != null ? Number(crr).toFixed(2)  : null,
        rrr: rrr != null ? Number(rrr).toFixed(2)  : null,
      });
    }
  }

  // Sort highest priority first and add to queue
  gfx.sort((a, b) => getGraphicPriority(b.type) - getGraphicPriority(a.type));
  gfx.forEach(g => GraphicQueue.add(g));
}

// ── Fast Sim Summary Card ─────────────────────────────────────────────────────

function showFastSimSummary(res) {
  return new Promise(resolve => {
    const digest = res?.sim_digest;
    if (!digest) { resolve(); return; }

    const trophies = [];
    for (const ev of (digest.key_events || [])) {
      if (/century|100/i.test(ev))      trophies.push('💯 ' + ev);
      else if (/five.?wic|5.?fer/i.test(ev)) trophies.push('🎳 ' + ev);
      else if (/record/i.test(ev))       trophies.push('📖 ' + ev);
      else if (/duck/i.test(ev))         trophies.push('🦆 ' + ev);
      else                               trophies.push('⭐ ' + ev);
    }

    const dim = document.createElement('div');
    dim.className = 'fast-sim-summary-dim';
    dim.innerHTML = `
      <div class="fast-sim-summary-card">
        <div class="fss-header">INNINGS COMPLETE — Fast Sim</div>
        <div class="fss-score">${escHtml(digest.end_score || '—')}</div>
        <div style="font-size:var(--fs-sm);color:var(--text-muted);margin-bottom:4px">
          ${digest.overs_completed ? formatOvers(digest.overs_completed) + ' ov' : ''}
          ${digest.runs_scored != null ? ' · +' + digest.runs_scored + ' runs' : ''}
          ${digest.wickets_fallen != null ? ' · ' + digest.wickets_fallen + ' wkt' + (digest.wickets_fallen !== 1 ? 's' : '') : ''}
        </div>
        ${trophies.length ? `
          <div class="fss-trophies">
            ${trophies.slice(0, 6).map(t => `<div class="fss-trophy">${escHtml(t)}</div>`).join('')}
          </div>` : ''}
        <div class="fss-continue">
          <button class="btn btn-primary btn-sm">Continue</button>
        </div>
      </div>`;

    dim.querySelector('.btn').addEventListener('click', () => { dim.remove(); resolve(); });
    document.body.appendChild(dim);
  });
}

// ── Sound Engine ──────────────────────────────────────────────────────────────

const SoundEngine = {
  _ctx: null,

  init() {
    if (this._ctx) return;
    try {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      this._ctx = null;
    }
  },

  _tone(freqStart, freqEnd, duration, volume, shape = 'sine') {
    if (!AppState.soundEnabled || !this._ctx) return;
    try {
      const ctx  = this._ctx;
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = shape;
      osc.frequency.setValueAtTime(freqStart, ctx.currentTime);
      if (freqEnd !== freqStart) {
        osc.frequency.linearRampToValueAtTime(freqEnd, ctx.currentTime + duration);
      }

      gain.gain.setValueAtTime(volume, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + duration);
    } catch (e) { /* audio errors are non-fatal */ }
  },

  play(type) {
    this.init();
    switch (type) {
      case 'dot':
        this._tone(220, 220, 0.10, 0.10); break;
      case 'single':
      case 'two':
        this._tone(330, 330, 0.15, 0.20); break;
      case 'three':
        this._tone(370, 370, 0.18, 0.22); break;
      case 'four':
        // Sweep up — boundary crack
        this._tone(440, 660, 0.30, 0.40); break;
      case 'six':
        // Three-note ascending: 523 → 784 → 1047
        this._tone(523, 784, 0.20, 0.50);
        setTimeout(() => this._tone(784, 1047, 0.30, 0.50), 200);
        break;
      case 'wicket':
        // Descending sweep
        this._tone(440, 110, 0.60, 0.50);
        break;
      case 'howzat':
        this._tone(330, 660, 0.40, 0.40); break;
      case 'wide':
      case 'no_ball':
        this._tone(280, 280, 0.12, 0.15); break;
      case 'leg_bye':
      case 'bye':
        this._tone(260, 260, 0.12, 0.12); break;
      case 'milestone':
        // Ascending fanfare: 523 → 659 → 784 → 1047
        this._tone(523, 659, 0.20, 0.60);
        setTimeout(() => this._tone(659, 784,  0.20, 0.60), 200);
        setTimeout(() => this._tone(784, 1047, 0.30, 0.60), 400);
        setTimeout(() => this._tone(1047, 1047, 0.40, 0.60), 700);
        break;
      case 'record':
        // milestone x2
        this._tone(523, 659, 0.20, 0.60);
        setTimeout(() => this._tone(659, 784,  0.20, 0.60), 200);
        setTimeout(() => this._tone(784, 1047, 0.30, 0.60), 400);
        setTimeout(() => this._tone(1047, 1047, 0.40, 0.60), 700);
        setTimeout(() => this._tone(523, 659, 0.20, 0.60), 1200);
        setTimeout(() => this._tone(659, 784,  0.20, 0.60), 1400);
        setTimeout(() => this._tone(784, 1047, 0.30, 0.60), 1600);
        setTimeout(() => this._tone(1047, 1047, 0.40, 0.60), 1900);
        break;
    }
  },

  // Sounds for broadcast graphic types
  playGraphic(type) {
    if (!AppState.soundEnabled) return;
    this.init();
    switch (type) {
      case 'wicket':
        this._tone(440, 220, 0.25, 0.45);
        setTimeout(() => this._tone(220, 110, 0.30, 0.40), 250);
        break;
      case 'duck':
        this._tone(300, 200, 0.20, 0.35);
        setTimeout(() => this._tone(200, 140, 0.25, 0.35), 200);
        setTimeout(() => this._tone(140, 100, 0.30, 0.30), 420);
        break;
      case 'fifty':
        this._tone(523, 659, 0.15, 0.55);
        setTimeout(() => this._tone(659, 784, 0.15, 0.55), 150);
        setTimeout(() => this._tone(784, 784, 0.25, 0.55), 300);
        break;
      case 'century':
        this._tone(523, 659, 0.12, 0.60);
        setTimeout(() => this._tone(659, 784,  0.12, 0.60), 130);
        setTimeout(() => this._tone(784, 1047, 0.15, 0.65), 260);
        setTimeout(() => this._tone(1047, 1047,0.40, 0.70), 420);
        break;
      case 'one_fifty':
        this._tone(587, 698, 0.12, 0.60);
        setTimeout(() => this._tone(698, 880,  0.12, 0.60), 130);
        setTimeout(() => this._tone(880, 1175, 0.15, 0.65), 260);
        setTimeout(() => this._tone(1175,1175, 0.40, 0.70), 420);
        break;
      case 'double_century':
        this._tone(523, 659, 0.10, 0.65);
        setTimeout(() => this._tone(659, 784,  0.10, 0.65), 110);
        setTimeout(() => this._tone(784, 1047, 0.10, 0.70), 220);
        setTimeout(() => this._tone(1047,1319, 0.12, 0.75), 330);
        setTimeout(() => this._tone(1319,1319, 0.50, 0.80), 460);
        break;
      case 'five_fer':
        this._tone(440, 550, 0.12, 0.55);
        setTimeout(() => this._tone(550, 660, 0.12, 0.55), 120);
        setTimeout(() => this._tone(660, 550, 0.12, 0.55), 240);
        setTimeout(() => this._tone(550, 440, 0.12, 0.55), 360);
        setTimeout(() => this._tone(440, 440, 0.30, 0.60), 480);
        break;
      case 'ten_wicket':
        this._tone(330, 440, 0.10, 0.60);
        setTimeout(() => this._tone(440, 550, 0.10, 0.65), 100);
        setTimeout(() => this._tone(550, 660, 0.10, 0.70), 200);
        setTimeout(() => this._tone(660, 880, 0.10, 0.75), 300);
        setTimeout(() => this._tone(880, 880, 0.60, 0.80), 400);
        break;
      case 'almanack_record':
        this._tone(659, 784, 0.15, 0.60);
        setTimeout(() => this._tone(784, 1047, 0.20, 0.65), 180);
        setTimeout(() => this._tone(1047,1047, 0.35, 0.70), 400);
        break;
      case 'world_record':
        this._tone(523, 784, 0.10, 0.70);
        setTimeout(() => this._tone(784, 1047, 0.10, 0.75), 110);
        setTimeout(() => this._tone(1047,784,  0.10, 0.75), 220);
        setTimeout(() => this._tone(784, 1047, 0.10, 0.80), 330);
        setTimeout(() => this._tone(1047,1319, 0.15, 0.85), 440);
        setTimeout(() => this._tone(1319,1319, 0.55, 0.90), 580);
        break;
      case 'over_complete':
        this._tone(440, 440, 0.08, 0.20);
        break;
    }
  },
};

// ── Series & Tournaments ──────────────────────────────────────────────────────

const SeriesUI = { activeTab: 'series', activeTournamentId: null, activeSeriesId: null };

function switchSeriesTab(tab) {
  SeriesUI.activeTab = tab;
  document.querySelectorAll('[data-stab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.stab === tab);
  });
  document.getElementById('stab-series').classList.toggle('hidden', tab !== 'series');
  document.getElementById('stab-tournaments').classList.toggle('hidden', tab !== 'tournaments');
}

async function loadSeriesScreen() {
  await Promise.all([_loadSeriesList(), _loadTournamentsList()]);
  await _populateSeriesFormDropdowns();
}

async function _loadSeriesList() {
  const el = document.getElementById('series-list');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';
  const data = await api('GET', '/api/series');
  const list = data?.series || [];
  if (!list.length) {
    el.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">🏏</div><h3 class="empty-state-heading">No active series</h3><p class="empty-state-sub">Create one to track a bilateral contest.</p><button class="btn btn-primary btn-sm" onclick="document.getElementById('series-create-form').scrollIntoView({behavior:'smooth'})">Create Series</button></div>`;
    return;
  }
  el.innerHTML = list.map(s => {
    const statusCls = s.status === 'complete' ? 'badge-complete' : 'badge-active';
    const winner = s.status === 'complete' ? ` — <strong>${s.winner_name || 'Drawn'}</strong> won` : '';
    return `
      <div class="series-card" onclick="loadSeriesDetail(${s.id})">
        <div class="series-card-header">
          <span class="series-card-name">${s.name}</span>
          <span class="badge ${statusCls}">${s.status}</span>
        </div>
        <div class="series-card-meta">
          ${s.team1_name} vs ${s.team2_name} · ${s.format}${winner}
        </div>
      </div>`;
  }).join('');
}

async function _loadTournamentsList() {
  const el = document.getElementById('tournaments-list');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';
  const data = await api('GET', '/api/tournaments');
  const list = data?.tournaments || [];
  if (!list.length) {
    el.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">🏆</div><h3 class="empty-state-heading">No tournaments running</h3><p class="empty-state-sub">Set up a World Cup!</p><button class="btn btn-primary btn-sm" onclick="document.getElementById('tournament-create-form')?.scrollIntoView({behavior:'smooth'})">Create Tournament</button></div>`;
    return;
  }
  el.innerHTML = list.map(t => {
    const statusCls = t.status === 'complete' ? 'badge-complete' : 'badge-active';
    const winner = t.status === 'complete' ? ` — <strong>${t.winner_name || '?'}</strong> won` : '';
    return `
      <div class="series-card" onclick="loadTournamentDetail(${t.id})">
        <div class="series-card-header">
          <span class="series-card-name">${t.name}</span>
          <span class="badge ${statusCls}">${t.status}</span>
        </div>
        <div class="series-card-meta">
          ${t.tournament_type.replace(/_/g, ' ')} · ${t.format}${winner}
        </div>
      </div>`;
  }).join('');
}

async function _populateSeriesFormDropdowns() {
  const [teamsData, venuesData] = await Promise.all([
    api('GET', '/api/teams'),
    api('GET', '/api/venues'),
  ]);
  const teams = teamsData?.teams || [];
  const venues = venuesData?.venues || [];

  const teamOpts = teams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
  const venueOpts = venues.map(v => `<option value="${v.id}">${v.name}</option>`).join('');

  ['sc-team1', 'sc-team2'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = teamOpts;
  });
  const scv = document.getElementById('sc-venues');
  if (scv) scv.innerHTML = venueOpts;

  const tcTeams = document.getElementById('tc-teams');
  if (tcTeams) tcTeams.innerHTML = teamOpts;
  const tcVenues = document.getElementById('tc-venues');
  if (tcVenues) tcVenues.innerHTML = venueOpts;
}

function showSeriesCreateForm() {
  document.getElementById('series-create-form').classList.remove('hidden');
}
function hideSeriesCreateForm() {
  document.getElementById('series-create-form').classList.add('hidden');
}
function showTournamentCreateForm() {
  document.getElementById('tournament-create-form').classList.remove('hidden');
}
function hideTournamentCreateForm() {
  document.getElementById('tournament-create-form').classList.add('hidden');
}

function updateTournamentTeamCount() {
  const type = document.getElementById('tc-type')?.value;
  const counts = { world_cup: 10, t20_world_cup: 8, tri_series: 3 };
  const label = document.getElementById('tc-teams-label');
  if (label) label.firstChild.textContent = `Select ${counts[type] || 10} Teams (hold Ctrl/Cmd)`;
}

async function submitCreateSeries() {
  const name = document.getElementById('sc-name')?.value.trim();
  const format = document.getElementById('sc-format')?.value;
  const team1_id = parseInt(document.getElementById('sc-team1')?.value);
  const team2_id = parseInt(document.getElementById('sc-team2')?.value);
  const num_matches = parseInt(document.getElementById('sc-num')?.value);
  const start_date = document.getElementById('sc-date')?.value || null;
  const venueSelect = document.getElementById('sc-venues');
  const venue_ids = venueSelect ? Array.from(venueSelect.selectedOptions).map(o => parseInt(o.value)) : [];

  if (!name) { alert('Enter a series name.'); return; }
  if (team1_id === team2_id) { alert('Teams must be different.'); return; }
  if (!venue_ids.length) { alert('Select at least one venue.'); return; }

  const res = await api('POST', '/api/series', { name, format, team1_id, team2_id, num_matches, start_date, venue_ids });
  if (res?.series_id) {
    hideSeriesCreateForm();
    loadSeriesDetail(res.series_id);
  }
}

async function submitCreateTournament() {
  const name = document.getElementById('tc-name')?.value.trim();
  const tournament_type = document.getElementById('tc-type')?.value;
  const format = document.getElementById('tc-format')?.value;
  const start_date = document.getElementById('tc-date')?.value || null;
  const teamsEl = document.getElementById('tc-teams');
  const team_ids = teamsEl ? Array.from(teamsEl.selectedOptions).map(o => parseInt(o.value)) : [];
  const venuesEl = document.getElementById('tc-venues');
  const venue_ids = venuesEl ? Array.from(venuesEl.selectedOptions).map(o => parseInt(o.value)) : [];

  const required = { world_cup: 10, t20_world_cup: 8, tri_series: 3 };
  if (!name) { alert('Enter a tournament name.'); return; }
  if (team_ids.length !== required[tournament_type]) {
    alert(`Select exactly ${required[tournament_type]} teams for this tournament type.`);
    return;
  }
  if (!venue_ids.length) { alert('Select at least one venue.'); return; }

  const res = await api('POST', '/api/tournaments', { name, format, tournament_type, team_ids, start_date, venue_ids });
  if (res?.tournament_id) {
    hideTournamentCreateForm();
    loadTournamentDetail(res.tournament_id);
  }
}

// ── Series Detail ─────────────────────────────────────────────────────────────

async function loadSeriesDetail(id) {
  SeriesUI.activeSeriesId = id;
  showScreen('series-detail');
  const nameEl = document.getElementById('series-detail-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const data = await api('GET', `/api/series/${id}`);
  if (!data?.series) return;

  const s = data.series;
  if (nameEl) nameEl.textContent = s.name;

  // Score banner
  const banner = document.getElementById('series-score-banner');
  if (banner) {
    const sc = data.score;
    banner.classList.remove('hidden');
    const wins = `${sc.team1_wins}–${sc.team2_wins}`;
    const lead = sc.team1_wins > sc.team2_wins ? s.team1_name
               : sc.team2_wins > sc.team1_wins ? s.team2_name : null;
    const leadStr = lead ? ` <span class="score-lead">${lead} lead</span>` : ' <span class="score-lead">Level</span>';
    banner.innerHTML = `
      <span class="score-teams">${s.team1_name}</span>
      <span class="score-wins">${wins}</span>
      <span class="score-teams">${s.team2_name}</span>
      ${leadStr}
      <span class="score-played">${sc.played}/${sc.total} played</span>
      ${s.status === 'complete' ? `<span class="badge badge-complete">Complete — ${s.winner_name || 'Drawn'}</span>` : ''}
    `;
  }

  // Fixtures
  const container = document.getElementById('series-fixtures-list');
  if (!container) return;
  const fixtures = data.fixtures || [];
  const matchMap = {};
  (data.matches || []).forEach(m => { matchMap[m.id] = m; });

  container.innerHTML = fixtures.map((f, i) => {
    const match = f.match_id ? matchMap[f.match_id] : null;
    const status = match ? match.status : f.status;
    const result = match?.result_type ? _buildShortResult(match) : '';
    const statusCls = status === 'complete' ? 'badge-complete' : 'badge-scheduled';
    return `
      <div class="fixture-card ${status === 'complete' ? 'fixture-done' : 'fixture-pending'}"
           onclick="${f.match_id ? `loadMatchDetail(${f.match_id})` : `startSeriesFixture(${f.id})`}">
        <div class="fixture-card-header">
          <span class="fixture-num">Match ${i + 1}</span>
          <span class="badge ${statusCls}">${status}</span>
        </div>
        <div class="fixture-teams">${f.team1_name} vs ${f.team2_name}</div>
        ${f.venue_name ? `<div class="fixture-venue">${f.venue_name}</div>` : ''}
        ${result ? `<div class="fixture-result">${result}</div>` : ''}
      </div>`;
  }).join('');
}

function _buildShortResult(match) {
  const rt = match.result_type;
  const wn = match.winning_team_name || '';
  if (rt === 'runs') return `${wn} won by ${match.margin_runs} run(s)`;
  if (rt === 'wickets') return `${wn} won by ${match.margin_wickets} wicket(s)`;
  if (rt === 'draw') return 'Match drawn';
  if (rt === 'tie') return 'Tie';
  return '';
}

async function loadMatchDetail(matchId) {
  openPlayedMatch(matchId);
}

async function startSeriesFixture(fixtureId) {
  // Navigate to play screen with fixture pre-selected
  AppState.pendingFixtureId = fixtureId;
  showScreen('play');
}

// ── Tournament Detail ─────────────────────────────────────────────────────────

async function loadTournamentDetail(id) {
  SeriesUI.activeTournamentId = id;
  showScreen('tournament-detail');
  const nameEl = document.getElementById('tournament-detail-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const data = await api('GET', `/api/tournaments/${id}`);
  if (!data?.tournament) return;

  const t = data.tournament;
  if (nameEl) nameEl.textContent = t.name;

  // Stage badge
  const stageBadge = document.getElementById('tournament-stage-badge');
  if (stageBadge) {
    const labels = { league: 'Group Stage', ready_to_advance: 'Ready to Advance', semi: 'Semi-Finals', final: 'Final', complete: 'Complete' };
    stageBadge.textContent = labels[data.stage] || data.stage;
    stageBadge.className = `stage-badge stage-${data.stage}`;
  }

  // Standings
  const standingsEl = document.getElementById('tournament-standings');
  if (standingsEl) {
    const groups = data.standings || {};
    standingsEl.innerHTML = Object.entries(groups).map(([grp, rows]) => `
      <div class="standings-group">
        <div class="standings-group-title">Group ${grp}</div>
        <table class="standings-table">
          <thead><tr><th>Team</th><th>P</th><th>W</th><th>L</th><th>Pts</th><th>NRR</th></tr></thead>
          <tbody>
            ${rows.map(r => `
              <tr>
                <td><span class="team-dot" style="background:${r.badge_colour||'#888'}"></span>${r.team_name}</td>
                <td>${r.played}</td><td>${r.won}</td><td>${r.lost}</td>
                <td><strong>${r.points}</strong></td>
                <td class="${r.nrr >= 0 ? 'nrr-pos' : 'nrr-neg'}">${(r.nrr >= 0 ? '+' : '') + r.nrr.toFixed(3)}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`).join('');
  }

  // Advance button
  const advWrap = document.getElementById('tournament-advance-wrap');
  if (advWrap) {
    const showAdv = data.stage === 'ready_to_advance' ||
      (data.stage === 'semi' && (data.semi_fixtures || []).every(f => f.status === 'complete')) ||
      (data.stage === 'final' && (data.final_fixtures || []).every(f => f.status === 'complete'));
    advWrap.classList.toggle('hidden', !showAdv);
  }

  // Bracket
  _renderBracket(data);

  // Fixture list
  const fixtureList = document.getElementById('tournament-fixtures-list');
  if (fixtureList) {
    const all = [...(data.league_fixtures || []), ...(data.semi_fixtures || []), ...(data.final_fixtures || [])];
    const sections = [
      { label: 'Group Stage', items: data.league_fixtures || [] },
      { label: 'Semi-Finals', items: data.semi_fixtures || [] },
      { label: 'Final', items: data.final_fixtures || [] },
    ].filter(s => s.items.length);

    fixtureList.innerHTML = sections.map(sec => `
      <div class="fixture-section-label">${sec.label}</div>
      ${sec.items.map(f => {
        const statusCls = f.status === 'complete' ? 'badge-complete' : 'badge-scheduled';
        const clickFn = f.match_id ? `loadMatchDetail(${f.match_id})` : `startTournamentFixture(${f.id})`;
        return `
          <div class="fixture-card ${f.status === 'complete' ? 'fixture-done' : 'fixture-pending'}"
               onclick="${clickFn}">
            <div class="fixture-card-header">
              <span class="fixture-type">${f.fixture_type}</span>
              <span class="badge ${statusCls}">${f.status}</span>
            </div>
            <div class="fixture-teams">${f.team1_name || '?'} vs ${f.team2_name || '?'}</div>
            ${f.venue_name ? `<div class="fixture-venue">${f.venue_name}</div>` : ''}
          </div>`;
      }).join('')}`).join('');
  }
}

function _renderBracket(data) {
  const el = document.getElementById('tournament-bracket');
  if (!el) return;
  const semis = data.semi_fixtures || [];
  const finals = data.final_fixtures || [];
  if (!semis.length && !finals.length) { el.innerHTML = ''; return; }

  const _teamStr = (f, side) => {
    const name = side === 1 ? (f.team1_name || '?') : (f.team2_name || '?');
    const won = f.status === 'complete' && f.match_id;
    return `<div class="bracket-team">${name}</div>`;
  };

  let html = '<div class="bracket-wrap">';
  if (semis.length) {
    html += '<div class="bracket-col"><div class="bracket-col-label">Semi-Finals</div>';
    semis.forEach(f => {
      html += `<div class="bracket-match">
        ${_teamStr(f, 1)}
        <div class="bracket-vs">vs</div>
        ${_teamStr(f, 2)}
      </div>`;
    });
    html += '</div>';
  }
  if (finals.length) {
    html += '<div class="bracket-col"><div class="bracket-col-label">Final</div>';
    finals.forEach(f => {
      html += `<div class="bracket-match bracket-final">
        ${_teamStr(f, 1)}
        <div class="bracket-vs">vs</div>
        ${_teamStr(f, 2)}
      </div>`;
    });
    html += '</div>';
  }
  html += '</div>';
  el.innerHTML = html;
}

async function advanceTournament() {
  const id = SeriesUI.activeTournamentId;
  if (!id) return;
  const res = await api('PUT', `/api/tournaments/${id}/advance`);
  if (res?.success) {
    loadTournamentDetail(id);
  }
}

async function startTournamentFixture(fixtureId) {
  AppState.pendingFixtureId = fixtureId;
  showScreen('play');
}

// ── Section 12: Almanack ─────────────────────────────────────────────────────

const ALM = {
  tab:     'batting',
  offset:  0,
  limit:   50,
  total:   0,
  sort:    '',
  dir:     'DESC',
  formats: new Set(['Test', 'ODI', 'T20']),
  modes:   new Set(['ai_vs_ai', 'human_vs_ai', 'human_vs_human']),
  _searchTimer: null,
};

// Keys whose columns should right-align and render in monospace
const ALMANACK_NUMERIC_KEYS = new Set([
  'matches', 'innings', 'not_outs', 'runs', 'highest_score', 'average', 'strike_rate',
  'hundreds', 'fifties', 'ducks', 'innings_bowled', 'overs', 'maidens', 'runs_conceded',
  'wickets', 'economy', 'five_fors', 'batting_average', 'bowling_average', 'ar_index',
  'matches_played', 'won', 'lost', 'drawn', 'tied', 'win_percentage',
  'wicket_number', 'balls',
]);

// Column definitions per tab
const ALM_COLS = {
  batting: [
    {k:'#',            label:'#',        nosort:true},
    {k:'name',         label:'Player'},
    {k:'team_name',    label:'Team'},
    {k:'format',       label:'Format'},
    {k:'matches',      label:'M'},
    {k:'innings',      label:'Inn'},
    {k:'not_outs',     label:'NO'},
    {k:'runs',         label:'Runs'},
    {k:'highest_score',label:'HS'},
    {k:'average',      label:'Avg'},
    {k:'strike_rate',  label:'SR'},
    {k:'hundreds',     label:'100s'},
    {k:'fifties',      label:'50s'},
    {k:'ducks',        label:'Ducks'},
  ],
  bowling: [
    {k:'#',             label:'#',        nosort:true},
    {k:'name',          label:'Player'},
    {k:'team_name',     label:'Team'},
    {k:'bowling_type',  label:'Type'},
    {k:'format',        label:'Format'},
    {k:'matches',       label:'M'},
    {k:'innings_bowled',label:'Inn'},
    {k:'overs',         label:'Overs'},
    {k:'maidens',       label:'Mdns'},
    {k:'runs_conceded', label:'Runs'},
    {k:'wickets',       label:'Wkts'},
    {k:'average',       label:'Avg'},
    {k:'economy',       label:'Econ'},
    {k:'strike_rate',   label:'SR'},
    {k:'five_fors',     label:'5W'},
  ],
  allrounders: [
    {k:'#',               label:'#',        nosort:true},
    {k:'name',            label:'Player'},
    {k:'team_name',       label:'Team'},
    {k:'format',          label:'Format'},
    {k:'matches',         label:'M'},
    {k:'innings',         label:'Inn'},
    {k:'runs',            label:'Runs'},
    {k:'batting_average', label:'Bat Avg'},
    {k:'wickets',         label:'Wkts'},
    {k:'bowling_average', label:'Bowl Avg'},
    {k:'ar_index',        label:'AR Idx'},
  ],
  teams: [
    {k:'#',            label:'#',        nosort:true},
    {k:'team_name',    label:'Team'},
    {k:'format',       label:'Format'},
    {k:'matches_played',label:'M'},
    {k:'won',          label:'W'},
    {k:'lost',         label:'L'},
    {k:'drawn',        label:'D'},
    {k:'tied',         label:'T'},
    {k:'win_percentage',label:'Win%'},
  ],
  matches: [
    {k:'#',                    label:'#',      nosort:true},
    {k:'match_date',           label:'Date'},
    {k:'format',               label:'Fmt'},
    {k:'canon_status',         label:'Status', nosort:true},
    {k:'player_mode',          label:'Mode',   nosort:true},
    {k:'team1_name',           label:'Team 1', nosort:true},
    {k:'team2_name',           label:'Team 2', nosort:true},
    {k:'venue_name',           label:'Venue',  nosort:true},
    {k:'result_string',        label:'Result', nosort:true},
    {k:'player_of_match_name', label:'PoM',    nosort:true},
  ],
  partnerships: [
    {k:'#',           label:'#',     nosort:true},
    {k:'batter1_name',label:'Batter 1',nosort:true},
    {k:'batter2_name',label:'Batter 2',nosort:true},
    {k:'wicket_number',label:'Wkt'},
    {k:'runs',         label:'Runs'},
    {k:'balls',        label:'Balls'},
    {k:'format',       label:'Format',nosort:true},
  ],
};

// Default sort per tab
const ALM_DEFAULT_SORT = {
  batting: 'runs', bowling: 'wickets', allrounders: 'ar_index',
  teams: 'win_percentage', matches: 'match_date', partnerships: 'runs',
};

async function loadAlmanackScreen() {
  ALM.tab = 'batting';
  ALM.offset = 0;
  ALM.sort = ALM_DEFAULT_SORT.batting || '';
  ALM.dir = 'DESC';

  // Inject publication masthead once (replaces plain h2 + subtitle)
  const screenInner = document.querySelector('#screen-almanack .screen-inner');
  if (screenInner && !screenInner.querySelector('.alm-masthead')) {
    const h2  = screenInner.querySelector('h2');
    const sub = h2 ? h2.nextElementSibling : null;
    const yr  = new Date().getFullYear();
    const masthead = document.createElement('div');
    masthead.className = 'alm-masthead';
    masthead.innerHTML =
      `<div class="alm-masthead-rule"><span class="alm-masthead-rule-inner">══════════════</span></div>` +
      `<h2 class="alm-masthead-title">The Dice Cricketers&#8217; Almanack</h2>` +
      `<div class="alm-masthead-rule"><span class="alm-masthead-rule-inner">══════════════</span></div>` +
      `<p class="alm-masthead-sub">The complete statistical record of every match ever played</p>` +
      `<div class="alm-masthead-footer">` +
        `<span class="alm-masthead-volume">Volume I</span>` +
        `<span class="alm-masthead-est">Est. ${yr}</span>` +
      `</div>` +
      `<p class="alm-masthead-disclaimer">Independent fan project &middot; Not affiliated with Wisden or any cricket authority</p>`;
    if (h2) {
      h2.replaceWith(masthead);
      if (sub && sub.classList.contains('screen-subtitle')) sub.remove();
    }
    // Update search placeholder
    const searchInput = document.getElementById('alm-search-input');
    if (searchInput) searchInput.placeholder = 'Search the Almanack\u2026';
    // Update Manage tab label
    const manageBtn = document.querySelector('#alm-tab-bar .alm-manage-tab');
    if (manageBtn && !manageBtn.querySelector('.alm-manage-icon')) {
      manageBtn.innerHTML = '<span class="alm-manage-icon">&#9881;</span> Manage';
    }
  }

  // Populate team dropdown once
  const teamSel = document.getElementById('alm-f-team');
  if (teamSel && teamSel.options.length <= 1) {
    const teams = await api('GET', '/api/teams');
    if (teams) {
      teams.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id; opt.textContent = t.name;
        teamSel.appendChild(opt);
      });
    }
  }

  document.querySelectorAll('#alm-tab-bar .tab-btn').forEach(btn => {
    const tab = btn.classList.contains('alm-manage-tab')
      ? 'manage'
      : btn.textContent.trim().toLowerCase().replace('-', '');
    btn.classList.toggle('active', tab === 'batting');
  });
  document.getElementById('alm-filter-panel')?.classList.remove('hidden');
  document.getElementById('alm-toolbar')?.classList.remove('hidden');
  document.getElementById('alm-table-area')?.classList.remove('hidden');
  document.getElementById('alm-manage-area')?.classList.add('hidden');

  loadAlmanackStoryDesk();
  await loadAlmTab('batting');
}

function switchAlmTab(tab, btn) {
  ALM.tab    = tab;
  ALM.offset = 0;
  ALM.sort   = ALM_DEFAULT_SORT[tab] || '';
  ALM.dir    = 'DESC';
  document.querySelectorAll('#alm-tab-bar .tab-btn').forEach(b =>
    b.classList.toggle('active', b === btn));

  const isHonours = tab === 'honours';
  const isManage  = tab === 'manage';
  document.getElementById('alm-filter-panel').classList.toggle('hidden', isHonours || isManage);
  document.getElementById('alm-toolbar').classList.toggle('hidden', isHonours || isManage);
  document.getElementById('alm-table-area').classList.toggle('hidden', isManage);
  document.getElementById('alm-manage-area').classList.toggle('hidden', !isManage);

  if (isManage) {
    loadAlmManage();
  } else {
    loadAlmTab(tab);
  }
}

function toggleAlmFilters() {
  const body    = document.getElementById('alm-filter-body');
  const chevron = document.getElementById('alm-filter-chevron');
  const open    = !body.classList.contains('hidden');
  body.classList.toggle('hidden', open);
  chevron.textContent = open ? '▸' : '▾';
}

function almToggleFmt(btn) {
  const fmt = btn.dataset.fmt;
  btn.classList.toggle('active');
  if (btn.classList.contains('active')) ALM.formats.add(fmt);
  else ALM.formats.delete(fmt);
}

function almToggleMode(btn) {
  const mode = btn.dataset.mode;
  btn.classList.toggle('active');
  if (btn.classList.contains('active')) ALM.modes.add(mode);
  else ALM.modes.delete(mode);
}

function _almParams() {
  const p = new URLSearchParams();
  p.set('limit',  ALM.limit);
  p.set('offset', ALM.offset);
  if (ALM.sort) p.set('sort', ALM.sort);
  p.set('dir', ALM.dir);

  // Format filter: only add if not all selected
  if (ALM.formats.size === 1) p.set('format', [...ALM.formats][0]);
  else if (ALM.formats.size === 0) p.set('format', 'none'); // no results

  // Mode filter: only add if exactly one mode selected
  if (ALM.modes.size === 1) p.set('player_mode', [...ALM.modes][0]);
  else if (ALM.modes.size === 0) p.set('format', 'none'); // no results (reuse format none trick)

  const team = document.getElementById('alm-f-team')?.value;
  if (team) p.set('team_id', team);
  const player = document.getElementById('alm-f-player')?.value.trim();
  if (player) p.set('player', player);
  const mi = document.getElementById('alm-f-mininnings')?.value;
  if (mi) p.set('min_innings', mi);
  const df = document.getElementById('alm-f-datefrom')?.value;
  if (df) p.set('date_from', df);
  const dt = document.getElementById('alm-f-dateto')?.value;
  if (dt) p.set('date_to', dt);

  return p.toString();
}

function applyAlmFilters() {
  ALM.offset = 0;
  loadAlmTab(ALM.tab);
}

function resetAlmFilters() {
  document.getElementById('alm-f-team').value       = '';
  document.getElementById('alm-f-player').value     = '';
  document.getElementById('alm-f-mininnings').value = '';
  document.getElementById('alm-f-datefrom').value   = '';
  document.getElementById('alm-f-dateto').value     = '';
  ALM.formats = new Set(['Test', 'ODI', 'T20']);
  document.querySelectorAll('.alm-fmt-btn').forEach(b => b.classList.add('active'));
  ALM.modes   = new Set(['ai_vs_ai', 'human_vs_ai', 'human_vs_human']);
  document.querySelectorAll('.alm-mode-btn').forEach(b => b.classList.add('active'));
  ALM.offset  = 0;
  loadAlmTab(ALM.tab);
}

function almPage(dir) {
  const next = ALM.offset + dir * ALM.limit;
  if (next < 0 || next >= ALM.total) return;
  ALM.offset = next;
  loadAlmTab(ALM.tab);
}

function almSort(col) {
  if (ALM.sort === col) ALM.dir = ALM.dir === 'DESC' ? 'ASC' : 'DESC';
  else { ALM.sort = col; ALM.dir = 'DESC'; }
  ALM.offset = 0;
  loadAlmTab(ALM.tab);
}

async function loadAlmTab(tab) {
  if (tab === 'honours') { loadAlmHonours(); return; }
  const qs   = _almParams();
  const data = await api('GET', `/api/almanack/${tab}?${qs}`);
  if (!data) return;

  ALM.total = data.total || 0;
  _updateAlmCount(data.total, data.offset, data.limit);
  _updateAlmPager(data.total, data.offset, data.limit);

  // Show exhibition fallback banner if canon data is absent
  const bannerEl = document.getElementById('alm-exhibition-banner');
  if (bannerEl) bannerEl.classList.toggle('hidden', !data.exhibition_fallback);

  const cols = ALM_COLS[tab];
  if (!cols) return;
  _renderAlmTable(cols, data.rows || [], data.offset);
}

function _updateAlmCount(total, offset, limit) {
  const el = document.getElementById('alm-count-label');
  if (!el) return;
  if (!total) { el.textContent = 'No records'; return; }
  const from = offset + 1;
  const to   = Math.min(offset + limit, total);
  el.textContent = `Showing ${from}–${to} of ${total}`;
}

function _updateAlmPager(total, offset, limit) {
  const prev = document.getElementById('alm-prev');
  const next = document.getElementById('alm-next');
  if (prev) prev.disabled = offset <= 0;
  if (next) next.disabled = offset + limit >= total;
}

function _renderAlmTable(cols, rows, offset) {
  const area = document.getElementById('alm-table-area');
  if (!area) return;

  if (!rows.length) {
    const isFiltered = ALM.formats.size < 3 || ALM.modes.size < 3 || document.getElementById('alm-f-team')?.value;
    const msg = isFiltered
      ? 'No records match your filters.'
      : (ALM.tab === 'batting'
          ? 'No batting records yet — play some matches first.'
          : ALM.tab === 'bowling'
            ? 'No bowling records yet — play some matches first.'
            : 'No records to display.');
    const sub = isFiltered
      ? ''
      : `<p class="alm-empty-state-sub">The Almanack grows with every match played.</p>`;
    const cta = isFiltered ? '' : `<button class="btn btn-primary btn-sm" style="margin-top:8px" onclick="showScreen('play')">Play a Match →</button>`;
    area.innerHTML = `<div class="alm-empty-state">
      <div class="alm-empty-state-icon">📖</div>
      <h3 class="alm-empty-state-heading">${msg}</h3>
      ${sub}${cta}
    </div>`;
    return;
  }

  const thead = cols.map(c => {
    const numCls = ALMANACK_NUMERIC_KEYS.has(c.k) ? ' numeric' : '';
    if (c.nosort) return `<th class="${numCls.trim()}">${c.label}</th>`;
    const active = ALM.sort === c.k;
    const arrow  = active ? (ALM.dir === 'DESC' ? ' ▼' : ' ▲') : '';
    return `<th class="alm-sortable${active ? ' alm-sort-active' : ''}${numCls}"
                onclick="almSort('${c.k}')">${c.label}${arrow}</th>`;
  }).join('');

  const tbody = rows.map((row, i) => {
    const cells = cols.map(c => {
      const numCls = ALMANACK_NUMERIC_KEYS.has(c.k) ? ' class="numeric"' : '';
      if (c.k === '#') return `<td>${offset + i + 1}</td>`;
      const v = row[c.k];
      if (v === null || v === undefined) return `<td${numCls}>—</td>`;
      if (c.k === 'name') return `<td><a class="alm-link" onclick="goToPlayer(${row.player_id})">${v}</a></td>`;
      if (c.k === 'team_name') return `<td><a class="alm-link" onclick="goToTeam(${row.team_id})">${v}</a></td>`;
      if (c.k === 'format') return `<td><span class="badge badge-${String(v).toLowerCase()}">${v}</span></td>`;
      if (c.k === 'player_mode')  return `<td>${_modeBadgeHtml(v)}</td>`;
      if (c.k === 'canon_status') return `<td>${v && v !== 'canon' ? _canonBadgeHtml(v) : '<span class="badge badge-canon">Canon</span>'}</td>`;
      if (c.k === 'average' || c.k === 'batting_average' || c.k === 'bowling_average')
        return `<td${numCls}>${v != null ? Number(v).toFixed(2) : '—'}</td>`;
      if (c.k === 'strike_rate' || c.k === 'economy' || c.k === 'win_percentage')
        return `<td${numCls}>${v != null ? Number(v).toFixed(1) : '—'}</td>`;
      if (c.k === 'ar_index')
        return `<td${numCls}>${v != null ? Number(v).toFixed(1) : '—'}</td>`;
      return `<td${numCls}>${v}</td>`;
    }).join('');
    return `<tr class="${i % 2 === 0 ? 'alm-row-even' : 'alm-row-odd'}">${cells}</tr>`;
  }).join('');

  area.innerHTML =
    `<div class="alm-table-wrap"><table class="alm-table almanack-table">
       <thead><tr>${thead}</tr></thead>
       <tbody>${tbody}</tbody>
     </table></div>`;
}

function _nextMilestone(value, steps) {
  for (const step of steps) {
    if (value < step) return step;
  }
  return null;
}

async function loadAlmanackStoryDesk() {
  const el = document.getElementById('alm-story-desk');
  if (!el) return;
  el.innerHTML = '';

  const [batting, bowling, honours] = await Promise.all([
    api('GET', '/api/almanack/batting?limit=8&offset=0&sort=runs&dir=DESC'),
    api('GET', '/api/almanack/bowling?limit=8&offset=0&sort=wickets&dir=DESC'),
    api('GET', '/api/almanack/honours/with-world-records'),
  ]);
  if (!batting || !bowling || !honours) {
    el.innerHTML = '<div class="story-desk-card"><div class="story-desk-empty">Story desk unavailable right now.</div></div>';
    return;
  }

  const battingRows = batting.rows || [];
  const bowlingRows = bowling.rows || [];
  const honoursRows = honours
    ? [
        ...(honours.batting || []),
        ...(honours.bowling || []),
        ...(honours.teams || []),
      ]
    : [];

  const threatRows = (Array.isArray(honoursRows) ? honoursRows : [])
    .filter(r => r?.pct_of_world_record != null && r.pct_of_world_record < 100)
    .sort((a, b) => (b.pct_of_world_record || 0) - (a.pct_of_world_record || 0))
    .slice(0, 3);

  const formBatters = battingRows.slice(0, 2);
  const formBowlers = bowlingRows.slice(0, 2);

  const milestoneItems = [];
  battingRows.slice(0, 4).forEach(r => {
    const target = _nextMilestone(r.runs || 0, [100, 250, 500, 1000, 1500, 2000, 3000, 5000]);
    if (target && target - (r.runs || 0) <= Math.max(50, target * 0.08)) {
      milestoneItems.push({
        title: `${r.name} closing on ${target} runs`,
        sub: `${target - (r.runs || 0)} away for ${r.team_name}`
      });
    }
  });
  bowlingRows.slice(0, 4).forEach(r => {
    const target = _nextMilestone(r.wickets || 0, [25, 50, 100, 150, 200, 300, 400]);
    if (target && target - (r.wickets || 0) <= 5) {
      milestoneItems.push({
        title: `${r.name} nearing ${target} wickets`,
        sub: `${target - (r.wickets || 0)} away for ${r.team_name}`
      });
    }
  });

  el.innerHTML = `
    <div class="story-desk-card">
      <div class="story-desk-kicker">Records Under Threat</div>
      ${threatRows.length ? `<div class="story-desk-list">
        ${threatRows.map(r => `
          <div class="story-desk-item">
            <div class="story-desk-title">${escHtml(getHonoursLabel(r.key || r.record_key || 'Record'))}</div>
            <div class="story-desk-sub"><span class="story-desk-stat">${(r.pct_of_world_record || 0).toFixed(1)}%</span>${escHtml(r.in_game?.player_name || r.in_game?.team_name || 'In-game record')} has closed to the real-world mark.</div>
          </div>`).join('')}
      </div>` : '<div class="story-desk-empty">No record chases flagged yet.</div>'}
    </div>
    <div class="story-desk-card">
      <div class="story-desk-kicker">Players In Form</div>
      <div class="story-desk-list">
        ${formBatters.map(r => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(r.name)} <span class="story-desk-stat">${r.runs}</span></div><div class="story-desk-sub">${escHtml(r.team_name)} · Avg ${Number(r.average || 0).toFixed(2)} · SR ${Number(r.strike_rate || 0).toFixed(1)}</div></div>`).join('')}
        ${formBowlers.map(r => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(r.name)} <span class="story-desk-stat">${r.wickets} wkts</span></div><div class="story-desk-sub">${escHtml(r.team_name)} · Avg ${Number(r.average || 0).toFixed(2)} · Econ ${Number(r.economy || 0).toFixed(2)}</div></div>`).join('')}
      </div>
    </div>
    <div class="story-desk-card">
      <div class="story-desk-kicker">Milestone Watch</div>
      ${milestoneItems.length ? `<div class="story-desk-list">
        ${milestoneItems.slice(0, 4).map(item => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(item.title)}</div><div class="story-desk-sub">${escHtml(item.sub)}</div></div>`).join('')}
      </div>` : '<div class="story-desk-empty">No major round-number milestones are close right now.</div>'}
    </div>`;
}

// ── Honours helpers ───────────────────────────────────────────────────────────

const HONOURS_LABELS = {
  'highest_score_test':        'Highest Individual Score — Test',
  'highest_score_odi':         'Highest Individual Score — ODI',
  'highest_score_t20':         'Highest Individual Score — T20',
  'most_runs_test':            'Most Career Runs — Test',
  'most_runs_odi':             'Most Career Runs — ODI',
  'most_runs_t20':             'Most Career Runs — T20',
  'best_average_test':         'Best Batting Average — Test',
  'best_average_odi':          'Best Batting Average — ODI',
  'best_average_t20':          'Best Batting Average — T20',
  'most_centuries_test':       'Most Centuries — Test',
  'most_centuries_odi':        'Most Centuries — ODI',
  'most_sixes':                'Most Sixes (Career)',
  'highest_partnership_test':  'Highest Partnership — Test',
  'highest_partnership_odi':   'Highest Partnership — ODI',
  'highest_partnership_t20':   'Highest Partnership — T20',
  'best_bowling_test':         'Best Bowling Figures — Test',
  'best_bowling_odi':          'Best Bowling Figures — ODI',
  'best_bowling_t20':          'Best Bowling Figures — T20',
  'most_wickets_test':         'Most Career Wickets — Test',
  'most_wickets_odi':          'Most Career Wickets — ODI',
  'most_wickets_t20':          'Most Career Wickets — T20',
  'best_bowling_average_test': 'Best Bowling Average — Test',
  'best_economy_t20':          'Best Economy Rate — T20',
  'best_economy_odi':          'Best Economy Rate — ODI',
  'most_five_fors_test':       'Most Five-Wicket Hauls — Test',
  'highest_team_total_test':   'Highest Team Total — Test',
  'highest_team_total_odi':    'Highest Team Total — ODI',
  'highest_team_total_t20':    'Highest Team Total — T20',
  'lowest_team_total_test':    'Lowest Team Total — Test',
  'lowest_team_total_odi':     'Lowest Team Total — ODI',
  'lowest_team_total_t20':     'Lowest Team Total — T20',
  'biggest_win_runs_test':     'Biggest Win (by runs) — Test',
  'biggest_win_runs_odi':      'Biggest Win (by runs) — ODI',
  'biggest_win_wickets_test':  'Biggest Win (by wickets) — Test',
};

function getHonoursLabel(key) {
  return HONOURS_LABELS[key.toLowerCase()] ||
    key.replace(/_/g, ' ')
       .replace(/\b(test|odi|t20)\b/gi, m => m.toUpperCase())
       .replace(/\b\w/g, c => c.toUpperCase());
}

function formatBowlingFigures(wickets, runs) {
  if (wickets === null || wickets === undefined) return '—';
  if (runs    === null || runs    === undefined) return `${wickets}/?`;
  return `${wickets}/${runs}`;
}

function formatHonoursValue(key, record) {
  const k = (key || '').toLowerCase();
  if (k.includes('best_bowling')) {
    return record.display_value ||
           formatBowlingFigures(record.wickets, record.runs_conceded);
  }
  if (k.includes('highest_score') || k.includes('highest_partnership')) {
    const notOut = record.not_out ? '*' : '';
    return `${record.value ?? record.display_value ?? '—'}${notOut}`;
  }
  if (k.includes('average') || k.includes('economy')) {
    const v = record.value ?? record.value_decimal;
    return v != null ? parseFloat(v).toFixed(2) : (record.display_value || '—');
  }
  if (k.includes('team_total')) {
    const wkts = record.wickets ?? record.value_wickets;
    const runs  = record.value ?? record.value_runs;
    if (wkts != null && runs != null)
      return wkts >= 10 ? `${runs} all out` : `${runs}/${wkts}`;
  }
  return record.value ?? record.display_value ?? '—';
}

function formatHonoursContext(record) {
  const parts = [];
  if (record.player_name)   parts.push(record.player_name);
  if (record.team_name)     parts.push(record.team_name);
  if (record.opponent_name) parts.push(`v ${record.opponent_name}`);
  if (record.venue_name)    parts.push(record.venue_name);
  if (record.match_date)    parts.push(record.match_date);
  return parts.join(' · ');
}

function _renderHonoursEnrichedSection(title, entries) {
  if (!entries || !entries.length) return '';
  let html = `<h3 class="alm-section-heading">${title}</h3>`;
  html += `<div class="alm-honours-grid">`;
  for (const entry of entries) {
    const label = getHonoursLabel(entry.key);
    const rw    = entry.real_world;
    const ig    = entry.in_game;
    const pct   = entry.pct_of_world_record;
    const beaten = pct != null && pct >= 100;

    let igHtml;
    if (ig) {
      const igVal  = formatHonoursValue(entry.key, ig);
      const igCtx  = formatHonoursContext(ig);
      igHtml = `
        <div class="honours-section-label">In-Game Record</div>
        <div class="honours-card__value">${igVal}</div>
        ${igCtx ? `<div class="honours-card__context">${igCtx}</div>` : ''}`;
    } else {
      igHtml = `<div class="honours-card__context honours-card__context--empty">No record set yet</div>`;
    }

    let rwHtml = '';
    if (rw) {
      const rwVal  = rw.display_value || formatHonoursValue(entry.key, rw);
      const rwCtx  = formatHonoursContext({
        player_name: rw.holder_name, team_name: rw.team_name,
        opponent_name: rw.opponent_name, match_date: rw.match_date,
      });
      rwHtml = `
        <div class="honours-divider"></div>
        <div class="honours-section-label honours-section-label--world">🌍 Real World Record</div>
        <div class="honours-card__value honours-card__value--world">${rwVal}</div>
        ${rwCtx ? `<div class="honours-card__context">${rwCtx}</div>` : ''}
        ${rw.notes ? `<div class="honours-card__notes">"${rw.notes}"</div>` : ''}`;
    }

    let progressHtml = '';
    if (pct != null && rw) {
      const bar = Math.min(100, pct);
      progressHtml = `
        <div class="honours-progress-wrap">
          <div class="honours-progress-bar" style="width:${bar}%"></div>
        </div>
        <div class="honours-progress-label">${beaten ? '🏆 World Record beaten!' : `${pct.toFixed(1)}% of world record`}</div>`;
    }

    html += `
      <div class="alm-honours-card${beaten ? ' alm-honours-card--beaten' : ''}">
        ${beaten ? '<div class="honours-beaten-badge">🏆 WORLD RECORD BEATEN!</div>' : ''}
        <div class="alm-honours-card-title">${label}</div>
        ${igHtml}
        ${rwHtml}
        ${progressHtml}
      </div>`;
  }
  html += '</div>';
  return html;
}

async function loadAlmHonours() {
  const area = document.getElementById('alm-table-area');
  if (!area) return;

  // Fetch both standard honours and enriched world-record comparison
  const [honData, wrData] = await Promise.all([
    api('GET', '/api/almanack/honours'),
    api('GET', '/api/almanack/honours/with-world-records'),
  ]);
  if (!honData) return;

  let html = '';

  // Series winners
  html += `<h3 class="alm-section-heading">Series Winners</h3>`;
  const series = honData.series || [];
  html += series.length
    ? `<div class="alm-table-wrap"><table class="alm-table almanack-table"><thead><tr>
         <th>Series</th><th>Format</th><th>Teams</th><th>Winner</th><th>Date</th>
       </tr></thead><tbody>
         ${series.map((r,i) => `<tr class="${i%2===0?'alm-row-even':'alm-row-odd'}">
           <td>${r.name}</td>
           <td><span class="badge badge-${(r.format||'').toLowerCase()}">${r.format||'—'}</span></td>
           <td>${r.team1_name} v ${r.team2_name}</td>
           <td><strong>${r.winner_name || '—'}</strong></td>
           <td>${r.start_date || '—'}</td>
         </tr>`).join('')}
       </tbody></table></div>`
    : `<div class="alm-empty-state" style="margin:12px 0 24px;padding:24px">
         <p class="alm-empty-state-heading">No completed series yet</p>
       </div>`;

  // Tournament winners
  html += `<h3 class="alm-section-heading">Tournament Winners</h3>`;
  const tournaments = honData.tournaments || [];
  html += tournaments.length
    ? `<div class="alm-table-wrap"><table class="alm-table almanack-table"><thead><tr>
         <th>Tournament</th><th>Format</th><th>Winner</th><th>Date</th>
       </tr></thead><tbody>
         ${tournaments.map((r,i) => `<tr class="${i%2===0?'alm-row-even':'alm-row-odd'}">
           <td>${r.name}</td>
           <td><span class="badge badge-${(r.format||'').toLowerCase()}">${r.format||'—'}</span></td>
           <td><strong>${r.winner_name || '—'}</strong></td>
           <td>${r.start_date || '—'}</td>
         </tr>`).join('')}
       </tbody></table></div>`
    : `<div class="alm-empty-state" style="margin:12px 0 24px;padding:24px">
         <p class="alm-empty-state-heading">No completed tournaments yet</p>
       </div>`;

  // Enriched records vs real world
  if (wrData) {
    html += _renderHonoursEnrichedSection('Batting Records', wrData.batting);
    html += _renderHonoursEnrichedSection('Bowling Records', wrData.bowling);
    html += _renderHonoursEnrichedSection('Team Records',    wrData.teams);
  }

  // World mode records (legacy cards)
  const worldRecs = honData.world_records || [];
  if (worldRecs.some(s => s.records.length)) {
    html += `<h3 class="alm-section-heading">World Mode Records</h3>`;
    worldRecs.forEach(section => {
      if (!section.records.length) return;
      html += `<h4 class="alm-section-subheading">${section.world.name}</h4>`;
      html += `<div class="alm-honours-grid">` +
        section.records.map(r => {
          const hasValue = r.record_value != null && r.record_value !== '';
          const label    = getHonoursLabel(r.record_key);
          return `<div class="alm-honours-card">
            <div class="alm-honours-card-title">${label}</div>
            ${hasValue
              ? `<div class="honours-card__value">${r.record_value}</div>`
              : `<div class="honours-card__context honours-card__context--empty">No record set yet</div>`}
          </div>`;
        }).join('') +
        `</div>`;
    });
  }

  area.innerHTML = html;
}

// ── Player Detail ─────────────────────────────────────────────────────────────

let _playerData       = null;
let _playerInningsOff = 0;
let _playerBowlOff    = 0;
const PLAYER_PAGE     = 20;

async function loadPlayerDetail(id) {
  showScreen('player-detail');

  const nameEl = document.getElementById('player-detail-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const data = await api('GET', `/api/players/${id}`);
  if (!data) return;
  _playerData = data;
  _playerInningsOff = 0;
  _playerBowlOff    = 0;

  const player = data.player || {};
  if (nameEl) nameEl.textContent = player.name || 'Player';

  // Badge
  const badgeEl = document.getElementById('player-badge');
  if (badgeEl) {
    badgeEl.textContent = (player.team_code || player.team_name || 'P').slice(0,2).toUpperCase();
    badgeEl.style.background = player.badge_colour || '#555';
  }

  // Back button remembers team
  const backBtn = document.getElementById('player-detail-back');
  if (backBtn && player.team_id) {
    backBtn.onclick = () => loadTeamDetail(player.team_id);
  }

  const metaEl = document.getElementById('player-detail-meta');
  if (metaEl) {
    const parts = [player.team_name, player.batting_hand ? player.batting_hand + '-hand' : null,
                   player.bowling_type && player.bowling_type !== 'none' ? player.bowling_type : null].filter(Boolean);
    metaEl.textContent = parts.join(' · ');
  }

  // Star ratings
  const ratingsEl = document.getElementById('player-detail-ratings');
  if (ratingsEl) {
    const bat = player.batting_rating || 0;
    const bowl = player.bowling_rating || 0;
    ratingsEl.innerHTML =
      `<span title="Batting">🏏 ${'★'.repeat(bat)}${'☆'.repeat(Math.max(0,5-bat))}</span>` +
      (bowl > 0 ? `<span title="Bowling" style="margin-left:12px">⚡ ${'★'.repeat(bowl)}${'☆'.repeat(Math.max(0,5-bowl))}</span>` : '');
  }

  // Career milestone cards
  const mil = data.milestones || {};
  const cardsEl = document.getElementById('player-career-cards');
  if (cardsEl) {
    const cards = [
      { label: 'Matches', value: mil.total_matches || 0 },
      { label: 'Runs',    value: mil.total_runs    || 0 },
      { label: '100s',    value: mil.hundreds      || 0 },
      { label: '50s',     value: mil.fifties       || 0 },
      { label: 'Wickets', value: mil.total_wickets || 0 },
      { label: '5-fors',  value: mil.five_fors     || 0 },
    ];
    cardsEl.innerHTML = cards.map(c =>
      `<div class="stat-card"><div class="stat-card-val">${c.value}</div><div class="stat-card-lbl">${c.label}</div></div>`
    ).join('');
  }

  // Reset format tab to 'All'
  document.querySelectorAll('#player-format-tabs .tab-btn').forEach((b,i) => b.classList.toggle('active', i===0));
  renderPlayerFormatStats('all');

  // Wagon wheel (all formats)
  loadWagonWheel(id, null);

  // Innings table
  await loadPlayerInnings(id, 0);

  // Bowling section (only if has wickets)
  const hasBowling = (mil.total_wickets || 0) > 0 ||
                     (data.bowling && data.bowling.length > 0);
  const bowlSection = document.getElementById('player-bowling-section');
  if (bowlSection) {
    if (hasBowling) {
      bowlSection.classList.remove('hidden');
      await loadPlayerBowling(id, 0);
    } else {
      bowlSection.classList.add('hidden');
    }
  }
}

function renderPlayerFormatStats(fmt) {
  const el = document.getElementById('player-format-stats');
  if (!el || !_playerData) return;

  let batRows = _playerData.batting || [];
  let bowlRows = _playerData.bowling || [];

  if (fmt !== 'all') {
    batRows  = batRows.filter(r => r.format === fmt);
    bowlRows = bowlRows.filter(r => r.format === fmt);
  }

  const batHtml = batRows.length ? `
    <h4 style="margin:8px 0 4px">Batting</h4>
    <table class="alm-table"><thead><tr>
      <th>Format</th><th>M</th><th>Inn</th><th>Runs</th><th>HS</th><th>Avg</th><th>SR</th><th>100s</th><th>50s</th>
    </tr></thead><tbody>${batRows.map(r => `<tr>
      <td>${r.format}</td>
      <td>${r.matches}</td><td>${r.innings}</td><td>${r.runs||0}</td>
      <td>${r.highest_score||0}</td>
      <td>${r.average ?? '—'}</td><td>${r.strike_rate ?? '—'}</td>
      <td>${r.hundreds||0}</td><td>${r.fifties||0}</td>
    </tr>`).join('')}</tbody></table>` : '';

  const bowlHtml = bowlRows.length ? `
    <h4 style="margin:8px 0 4px">Bowling</h4>
    <table class="alm-table"><thead><tr>
      <th>Format</th><th>M</th><th>Inn</th><th>Overs</th><th>Wkts</th><th>Avg</th><th>Econ</th><th>5W</th>
    </tr></thead><tbody>${bowlRows.map(r => `<tr>
      <td>${r.format}</td>
      <td>${r.matches}</td><td>${r.innings_bowled}</td><td>${r.overs||0}</td>
      <td>${r.wickets||0}</td>
      <td>${r.average ?? '—'}</td><td>${r.economy ?? '—'}</td>
      <td>${r.five_fors||0}</td>
    </tr>`).join('')}</tbody></table>` : '';

  el.innerHTML = batHtml + bowlHtml || '<p class="text-muted">No stats for this format.</p>';
}

function switchPlayerTab(fmt, btn) {
  document.querySelectorAll('#player-format-tabs .tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderPlayerFormatStats(fmt);
}

async function loadWagonWheel(playerId, fmt) {
  const data = await api('GET', `/api/players/${playerId}/wagon-wheel${fmt ? '?format=' + fmt : ''}`);
  drawWagonWheel('wagon-wheel-canvas', data?.deliveries || []);
}

async function loadPlayerInnings(playerId, offset) {
  _playerInningsOff = offset;
  const el = document.getElementById('player-innings-table');
  const pageEl = document.getElementById('player-innings-pages');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', `/api/players/${playerId}/innings?limit=${PLAYER_PAGE}&offset=${offset}`);
  const innings = data?.innings || [];
  const total   = data?.total  || 0;

  if (!innings.length) {
    el.innerHTML = '<p class="text-muted">No innings data.</p>';
    if (pageEl) pageEl.innerHTML = '';
    return;
  }

  el.innerHTML = `<table class="alm-table"><thead><tr>
    <th>Date</th><th>Fmt</th><th>vs</th><th>Venue</th><th>#</th>
    <th>Runs</th><th>B</th><th>4s</th><th>6s</th><th>SR</th><th>How out</th>
  </tr></thead><tbody>${innings.map(r => `<tr>
    <td>${r.match_date || ''}</td>
    <td>${r.format}</td>
    <td>${r.opponent_name || ''}</td>
    <td>${r.venue_name || ''}</td>
    <td>${r.batting_position || ''}</td>
    <td><strong>${r.runs}${r.not_out ? '*' : ''}</strong></td>
    <td>${r.balls_faced || 0}</td>
    <td>${r.fours || 0}</td>
    <td>${r.sixes || 0}</td>
    <td>${r.strike_rate ?? '—'}</td>
    <td class="text-muted">${r.not_out ? 'not out' : (r.dismissal_type || '—')}${r.bowler_name ? ' b. ' + r.bowler_name : ''}</td>
  </tr>`).join('')}</tbody></table>`;

  if (pageEl) {
    const pages = Math.ceil(total / PLAYER_PAGE);
    const cur   = Math.floor(offset / PLAYER_PAGE);
    pageEl.innerHTML = pages > 1 ? Array.from({length: pages}, (_,i) =>
      `<button class="btn-page${i===cur?' active':''}" onclick="loadPlayerInnings(${playerId},${i*PLAYER_PAGE})">${i+1}</button>`
    ).join('') : '';
  }
}

async function loadPlayerBowling(playerId, offset) {
  _playerBowlOff = offset;
  const el = document.getElementById('player-bowling-table');
  const pageEl = document.getElementById('player-bowling-pages');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', `/api/players/${playerId}/bowling?limit=${PLAYER_PAGE}&offset=${offset}`);
  const spells = data?.spells || [];
  const total  = data?.total  || 0;

  if (!spells.length) {
    el.innerHTML = '<p class="text-muted">No bowling data.</p>';
    if (pageEl) pageEl.innerHTML = '';
    return;
  }

  el.innerHTML = `<table class="alm-table"><thead><tr>
    <th>Date</th><th>Fmt</th><th>vs</th><th>Venue</th>
    <th>Overs</th><th>M</th><th>Runs</th><th>Wkts</th><th>Econ</th>
  </tr></thead><tbody>${spells.map(r => `<tr>
    <td>${r.match_date || ''}</td>
    <td>${r.format}</td>
    <td>${r.opponent_name || ''}</td>
    <td>${r.venue_name || ''}</td>
    <td>${formatBowlerOvers(r.overs, r.balls)}</td>
    <td>${r.maidens || 0}</td>
    <td>${r.runs_conceded || 0}</td>
    <td><strong>${r.wickets}</strong></td>
    <td>${r.economy ?? '—'}</td>
  </tr>`).join('')}</tbody></table>`;

  if (pageEl) {
    const pages = Math.ceil(total / PLAYER_PAGE);
    const cur   = Math.floor(offset / PLAYER_PAGE);
    pageEl.innerHTML = pages > 1 ? Array.from({length: pages}, (_,i) =>
      `<button class="btn-page${i===cur?' active':''}" onclick="loadPlayerBowling(${playerId},${i*PLAYER_PAGE})">${i+1}</button>`
    ).join('') : '';
  }
}

function goToPlayer(playerId) {
  if (!playerId) return;
  loadPlayerDetail(playerId);
}

function goToTeam(teamId) {
  if (!teamId) return;
  loadTeamDetail(teamId);
}

// ── Almanack Manage Tab ───────────────────────────────────────────────────────

let _manageRows = [];   // [{id, match_date, format, canon_status, team1_name, team2_name, ...}]

async function loadAlmManage() {
  const wrap = document.getElementById('manage-table-wrap');
  if (!wrap) return;
  wrap.innerHTML = '<div class="spinner"></div>';

  const statusFilter = document.getElementById('manage-status-filter')?.value || '';
  const fmtFilter    = document.getElementById('manage-format-filter')?.value || '';

  const qs = new URLSearchParams({
    include_deleted: '1',
    limit: 500,
    offset: 0,
    dir: 'DESC',
    sort: 'match_date',
  });
  if (statusFilter) qs.set('canon_status', statusFilter);
  if (fmtFilter)    qs.set('format', fmtFilter);

  const data = await api('GET', `/api/almanack/matches?${qs}`);
  if (!data) { wrap.innerHTML = '<p class="text-muted">Failed to load.</p>'; return; }

  _manageRows = data.rows || [];
  almManageClearSelection();
  _renderManageTable();
}

function _renderManageTable() {
  const wrap = document.getElementById('manage-table-wrap');
  if (!wrap) return;
  if (!_manageRows.length) {
    wrap.innerHTML = '<p class="text-muted" style="padding:16px 0">No matches found.</p>';
    return;
  }

  const rows = _manageRows.map((m, i) => {
    const isDeleted = m.canon_status === 'deleted';
    const statusBadge = m.canon_status === 'canon'
      ? '<span class="badge badge-canon">Canon</span>'
      : _canonBadgeHtml(m.canon_status);
    return `<tr class="${isDeleted ? 'deleted-row' : ''}" id="mrow-${m.id}">
      <td><input type="checkbox" class="manage-cb" data-id="${m.id}" onchange="_manageCheckChange()"></td>
      <td>${m.match_date || '—'}</td>
      <td><span class="badge badge-${(m.format||'').toLowerCase()}">${m.format||'—'}</span></td>
      <td>${statusBadge}</td>
      <td>${m.team1_name||'—'} <span class="text-muted">vs</span> ${m.team2_name||'—'}</td>
      <td class="text-muted" style="font-size:0.8rem">${m.venue_name||'—'}</td>
      <td class="text-muted" style="font-size:0.8rem">${m.winning_team_name ? m.winning_team_name+' won' : (m.result_type||'—')}</td>
      <td>
        <button class="manage-action-btn" onclick="openManageRowMenu(${m.id}, this)">Actions ▾</button>
      </td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `
    <div class="alm-table-wrap">
      <table class="manage-table">
        <thead><tr>
          <th><input type="checkbox" id="manage-select-all" onchange="_manageToggleAll(this.checked)"></th>
          <th>Date</th><th>Fmt</th><th>Status</th><th>Match</th>
          <th>Venue</th><th>Result</th><th>Actions</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function _manageCheckChange() {
  const checked = document.querySelectorAll('.manage-cb:checked');
  const bar     = document.getElementById('manage-bulk-bar');
  const count   = document.getElementById('manage-bulk-count');
  if (!bar) return;
  bar.classList.toggle('hidden', checked.length === 0);
  if (count) count.textContent = `${checked.length} selected`;
}

function _manageToggleAll(checked) {
  document.querySelectorAll('.manage-cb').forEach(cb => { cb.checked = checked; });
  _manageCheckChange();
}

function almManageClearSelection() {
  document.querySelectorAll('.manage-cb').forEach(cb => { cb.checked = false; });
  const all = document.getElementById('manage-select-all');
  if (all) all.checked = false;
  _manageCheckChange();
}

function _manageSelectedIds() {
  return [...document.querySelectorAll('.manage-cb:checked')].map(cb => parseInt(cb.dataset.id));
}

async function almManageBulkAction(newStatus) {
  const ids = _manageSelectedIds();
  if (!ids.length) return;

  const label = { canon: 'Canon', exhibition: 'Exhibition', deleted: 'Delete' }[newStatus] || newStatus;
  const warning = newStatus === 'deleted'
    ? `\n\nWARNING: Deleted matches will be hidden from all match lists.`
    : '';
  if (!confirm(`Set ${ids.length} match(es) to "${label}"?${warning}`)) return;

  const res = await api('POST', '/api/almanack/bulk-canon-status', {
    match_ids:    ids,
    canon_status: newStatus,
    note:         `Bulk set to ${newStatus} via Manage tab`,
  });
  if (res) {
    showError(`Updated ${res.updated} match(es) to ${label}`);
    loadAlmManage();
  }
}

function openManageRowMenu(matchId, btn) {
  // Remove any existing menu
  document.querySelectorAll('.manage-row-menu').forEach(m => m.remove());

  const match = _manageRows.find(r => r.id === matchId);
  if (!match) return;

  const menu = document.createElement('div');
  menu.className = 'manage-row-menu';
  menu.style.cssText = 'position:absolute;background:var(--surface2);border:1px solid var(--border);border-radius:6px;min-width:160px;z-index:200;box-shadow:0 4px 16px rgba(0,0,0,0.4);overflow:hidden;';

  const options = [
    { label: 'Set Canon',      action: () => _manageSetOne(matchId, 'canon') },
    { label: 'Set Exhibition', action: () => _manageSetOne(matchId, 'exhibition') },
    { label: 'Soft Delete',    action: () => _manageDeleteOne(matchId) },
    { label: '─────────',      action: null },
    { label: 'Edit Result',    action: () => openEditResultModal(matchId) },
  ];

  options.forEach(opt => {
    if (opt.action === null) {
      const div = document.createElement('div');
      div.style.cssText = 'padding:2px 12px;color:var(--border);font-size:0.75rem;user-select:none;';
      div.textContent = opt.label;
      menu.appendChild(div);
    } else {
      const btn2 = document.createElement('button');
      btn2.textContent = opt.label;
      btn2.style.cssText = 'display:block;width:100%;text-align:left;padding:8px 14px;background:transparent;border:none;color:var(--text);font-size:0.83rem;cursor:pointer;';
      btn2.onmouseenter = () => { btn2.style.background = 'var(--border)'; };
      btn2.onmouseleave = () => { btn2.style.background = 'transparent'; };
      btn2.onclick = () => { menu.remove(); opt.action(); };
      menu.appendChild(btn2);
    }
  });

  // Position near button
  const rect = btn.getBoundingClientRect();
  menu.style.top  = (rect.bottom + window.scrollY + 4) + 'px';
  menu.style.left = (rect.left  + window.scrollX)      + 'px';
  document.body.appendChild(menu);

  // Close on outside click
  const close = (e) => { if (!menu.contains(e.target)) { menu.remove(); document.removeEventListener('click', close); } };
  setTimeout(() => document.addEventListener('click', close), 0);
}

async function _manageSetOne(matchId, newStatus) {
  const res = await api('PATCH', `/api/matches/${matchId}/canon-status`, {
    canon_status: newStatus,
    note: `Set to ${newStatus} via Manage tab`,
  });
  if (res) { loadAlmManage(); }
}

async function _manageDeleteOne(matchId) {
  if (!confirm('Soft-delete this match? It will be hidden from all lists and excluded from statistics.')) return;
  const res = await api('DELETE', `/api/matches/${matchId}`, { confirm: 'DELETE', note: 'Soft deleted via Manage tab' });
  if (res) { loadAlmManage(); }
}

// ── Audit Log ─────────────────────────────────────────────────────────────────

function toggleAuditLog() {
  const body    = document.getElementById('audit-log-body');
  const chevron = document.getElementById('audit-chevron');
  if (!body) return;
  const isHidden = body.classList.contains('hidden');
  body.classList.toggle('hidden', !isHidden);
  if (chevron) chevron.textContent = isHidden ? '▾' : '▸';
  if (isHidden) loadAuditLog();
}

async function loadAuditLog() {
  const content = document.getElementById('audit-log-content');
  if (!content) return;
  content.innerHTML = '<div class="spinner"></div>';

  const data = await api('GET', '/api/almanack/audit-log');
  if (!data || !data.entries?.length) {
    content.innerHTML = '<p class="text-muted" style="padding:12px">No audit entries yet.</p>';
    return;
  }

  const rows = data.entries.map((e, i) => `
    <tr>
      <td>${e.created_at?.slice(0,16) || '—'}</td>
      <td>${e.team1_name||'?'} vs ${e.team2_name||'?'} (${e.match_date||'?'})</td>
      <td><code style="font-size:0.75rem">${e.action}</code></td>
      <td class="text-muted" style="font-size:0.78rem">${e.old_value||'—'} → ${e.new_value||'—'}</td>
      <td class="text-muted" style="font-size:0.78rem">${e.note||''}</td>
    </tr>`).join('');

  content.innerHTML = `
    <div style="overflow-x:auto;padding:8px 0">
      <table class="audit-table">
        <thead><tr><th>Time</th><th>Match</th><th>Action</th><th>Change</th><th>Note</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ── Almanack search ───────────────────────────────────────────────────────────

function almSearchDebounce(val) {
  clearTimeout(ALM._searchTimer);
  if (!val.trim() || val.trim().length < 2) {
    document.getElementById('alm-search-dropdown').classList.add('hidden');
    return;
  }
  ALM._searchTimer = setTimeout(() => almDoSearch(val.trim()), 280);
}

async function almDoSearch(q) {
  const data = await api('GET', `/api/almanack/search?q=${encodeURIComponent(q)}`);
  const dd = document.getElementById('alm-search-dropdown');
  if (!data || !data.results.length) {
    dd.classList.add('hidden');
    return;
  }
  dd.innerHTML = data.results.map(r => {
    const icon = r.type === 'player' ? '🏏' : r.type === 'team' ? '🛡' : '📋';
    return `<div class="alm-search-item" onclick="almSearchSelect('${r.type}',${r.id})">
      <span class="alm-si-icon">${icon}</span>
      <span class="alm-si-name">${r.name}</span>
      <span class="alm-si-ctx">${r.context || ''}</span>
    </div>`;
  }).join('');
  dd.classList.remove('hidden');
}

function almSearchSelect(type, id) {
  document.getElementById('alm-search-dropdown').classList.add('hidden');
  document.getElementById('alm-search-input').value = '';
  if (type === 'match') loadMatchDetail(id);
  else if (type === 'team') showScreen('teams');
}

// Close dropdown on outside click
document.addEventListener('click', e => {
  if (!e.target.closest('.alm-search-wrap')) {
    const dd = document.getElementById('alm-search-dropdown');
    if (dd) dd.classList.add('hidden');
  }
});

// ── Edit Result Modal ─────────────────────────────────────────────────────────

let _editResultMatchId = null;

async function openEditResultModal(matchId) {
  _editResultMatchId = matchId;

  const modal = document.getElementById('edit-result-modal');
  if (!modal) return;

  // Fetch the match data
  const data = await api('GET', `/api/matches/${matchId}/scorecard`);
  if (!data) return;

  const m = data.match || {};

  // Fill meta
  const meta = document.getElementById('er-match-meta');
  if (meta) meta.textContent = `${m.team1_name} vs ${m.team2_name} · ${m.match_date} · ${m.format}`;

  // Set current values
  const rtEl = document.getElementById('er-result-type');
  if (rtEl) rtEl.value = m.result_type || 'runs';

  const mrEl = document.getElementById('er-margin-runs');
  const mwEl = document.getElementById('er-margin-wickets');
  if (mrEl) mrEl.value = m.margin_runs || '';
  if (mwEl) mwEl.value = m.margin_wickets || '';

  // Populate winning team select
  const wtSel = document.getElementById('er-winning-team');
  if (wtSel) {
    wtSel.innerHTML = '<option value="">None</option>';
    [{ id: m.team1_id, name: m.team1_name }, { id: m.team2_id, name: m.team2_name }].forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.name;
      if (t.id === m.winning_team_id) opt.selected = true;
      wtSel.appendChild(opt);
    });
  }

  // Populate PoM select from innings players
  const pomSel = document.getElementById('er-pom');
  if (pomSel) {
    pomSel.innerHTML = '<option value="">None</option>';
    const players = new Map();
    (data.innings || []).forEach(inn => {
      (inn.batters || []).forEach(b => { if (b.player_id && b.player_name) players.set(b.player_id, b.player_name); });
      (inn.bowlers || []).forEach(bw => { if (bw.player_id && bw.player_name) players.set(bw.player_id, bw.player_name); });
    });
    players.forEach((name, id) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = name;
      if (id === m.player_of_match_id) opt.selected = true;
      pomSel.appendChild(opt);
    });
  }

  document.getElementById('er-note').value = '';

  modal.classList.remove('hidden');
}

function closeEditResultModal() {
  const modal = document.getElementById('edit-result-modal');
  if (modal) modal.classList.add('hidden');
  _editResultMatchId = null;
}

async function saveEditResult() {
  if (!_editResultMatchId) return;

  const result_type      = document.getElementById('er-result-type')?.value;
  const winning_team_id  = parseInt(document.getElementById('er-winning-team')?.value) || null;
  const margin_runs      = parseInt(document.getElementById('er-margin-runs')?.value)   || null;
  const margin_wickets   = parseInt(document.getElementById('er-margin-wickets')?.value) || null;
  const player_of_match_id = parseInt(document.getElementById('er-pom')?.value) || null;
  const note             = document.getElementById('er-note')?.value?.trim() || 'Manual result edit';

  const res = await api('PATCH', `/api/matches/${_editResultMatchId}/result`, {
    result_type, winning_team_id, margin_runs, margin_wickets, player_of_match_id, note,
  });

  if (res) {
    closeEditResultModal();
    showError('Result updated successfully');
    // Refresh manage table if open
    if (!document.getElementById('alm-manage-area')?.classList.contains('hidden')) {
      loadAlmManage();
    }
  }
}

// ── Export ────────────────────────────────────────────────────────────────────

function exportAlmCSV() {
  const tab    = ALM.tab;
  const params = _almParams();

  // Build a SELECT query matching what the API uses
  const queryMap = {
    batting:      `SELECT * FROM batting_averages WHERE 1=1`,
    bowling:      `SELECT * FROM bowling_averages WHERE wickets > 0`,
    allrounders:  `SELECT bat.player_id, bat.name, bat.team_name, bat.format, bat.innings, bat.runs, bat.average, bowl.wickets, bowl.average FROM batting_averages bat JOIN bowling_averages bowl ON bat.player_id=bowl.player_id AND bat.format=bowl.format WHERE bat.innings >= 3 AND bowl.wickets >= 5`,
    teams:        `SELECT team_name, format, matches_played, won, lost, drawn, tied FROM team_records_view`,
    partnerships: `SELECT batter1_name, batter2_name, wicket_number, runs, balls, format FROM partnership_records`,
    matches:      `SELECT m.match_date, m.format, t1.name, t2.name, v.name, m.result_type, m.margin_runs, m.margin_wickets FROM matches m JOIN teams t1 ON m.team1_id=t1.id JOIN teams t2 ON m.team2_id=t2.id JOIN venues v ON m.venue_id=v.id WHERE m.status='complete' ORDER BY m.match_date DESC`,
    honours:      null,
  };

  const q = queryMap[tab];
  if (!q) { alert('Export not available for this tab.'); return; }

  const url = `/api/export/table?q=${encodeURIComponent(q)}`;
  const a   = document.createElement('a');
  a.href    = url;
  a.download = `almanack_${tab}.csv`;
  a.click();
}

// ── Section 14: World Mode ────────────────────────────────────────────────────

const WorldUI = {
  activeWorldId:   null,
  wizardStep:      1,
  wizardTeamIds:   new Set(),
  wizardAllTeams:  [],
  wizardInternationalTeams: [],
  wizardDomesticTeams: [],
  wizardDomesticLeagues: new Set(),
  wizardDomesticTeamMode: 'selected',
  wizardDomesticLeagueOptions: [],
  wizardScope:     'international',
  wizardCalendarYears: 2,
  calendarFilter:  'all',
  _worldData:      null,
  _seriesData:     [],
};

// ── Worlds list ───────────────────────────────────────────────────────────────

async function loadWorldsScreen() {
  const listEl = document.getElementById('worlds-list');
  if (!listEl) return;
  listEl.innerHTML = '<div class="spinner"></div>';
  const worlds = await api('GET', '/api/worlds');
  if (!worlds || !worlds.length) {
    listEl.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">🌍</div><h3 class="empty-state-heading">No cricket worlds created yet</h3><p class="empty-state-sub">Build your universe.</p><button class="btn btn-primary btn-sm" onclick="showWorldWizard()">Create World</button></div>`;
    return;
  }
  listEl.innerHTML = worlds.map(w => {
    const played = w.matches_played || 0;
    const total  = w.fixture_count  || 0;
    const pct    = total > 0 ? Math.round(played / total * 100) : 0;
    return `
    <div class="world-card" onclick="loadWorldDetail(${w.id})">
      <div class="world-card-header">
        <div class="world-card-name">${w.name}</div>
        <button class="world-card-delete" title="Delete world" onclick="event.stopPropagation(); deleteWorld(${w.id}, '${escHtml(String(w.name || '').replace(/'/g, '&#39;'))}')">✕</button>
      </div>
      <div class="world-card-meta">
        <span class="badge">${w.calendar_density || 'moderate'}</span>
        <span class="text-muted">${w.current_date || ''}</span>
        <span class="text-muted">${played}/${total} matches</span>
      </div>
      <div class="world-progress-bar" style="margin-top:6px">
        <div class="world-progress-fill" style="width:${pct}%"></div>
      </div>
    </div>`;
  }).join('');
}

async function deleteWorld(worldId, worldName) {
  const label = worldName || 'this world';
  if (!confirm(`Delete ${label}?\n\nThis removes the world, its fixtures, rankings, records, and any world-linked matches created for it.`)) {
    return;
  }
  const res = await api('DELETE', `/api/worlds/${worldId}`, { confirm: 'DELETE' });
  if (!res?.deleted) return;
  if (WorldUI.activeWorldId === worldId) {
    WorldUI.activeWorldId = null;
    showScreen('world');
  }
  _showToast(`Deleted ${label}`, 1800);
  await loadWorldsScreen();
}

// ── World creation wizard ─────────────────────────────────────────────────────

async function showWorldWizard() {
  document.getElementById('btn-show-create-world').classList.add('hidden');
  document.getElementById('world-wizard').classList.remove('hidden');
  WorldUI.wizardStep          = 1;
  WorldUI.wizardTeamIds       = new Set();
  WorldUI.wizardDomesticLeagues = new Set();
  WorldUI.wizardDomesticTeamMode = 'selected';
  WorldUI.wizardScope         = 'international';
  WorldUI.wizardCalendarYears = 2;
  _wizardShowPage(1);
  const yearsEl = document.getElementById('wc-years');
  if (yearsEl) yearsEl.value = '2';

  // Load teams for team-selection step
  const teams = await api('GET', '/api/teams');
  const allTeams = (teams && teams.teams ? teams.teams : teams) || [];
  WorldUI.wizardInternationalTeams = allTeams.filter(t => !t.team_type || t.team_type === 'international');
  WorldUI.wizardDomesticTeams = allTeams.filter(t => t.team_type && t.team_type !== 'international');

  // Load domestic leagues
  const leagueData = await api('GET', '/api/domestic-leagues');
  WorldUI.wizardDomesticLeagueOptions = (leagueData?.leagues || []).filter(l => l.team_count > 0);
  _renderWizardDomesticLeagues();

  // Wire up cal-style radios to show/hide domestic section
  document.querySelectorAll('input[name="wc-cal-style"]').forEach(radio => {
    radio.addEventListener('change', _syncDomesticSectionVisibility);
  });
  setWorldScope('international');
}

function _syncDomesticSectionVisibility() {
  const calStyle = document.querySelector('input[name="wc-cal-style"]:checked')?.value || 'realistic';
  const section = document.getElementById('wc-domestic-section');
  if (section) section.classList.toggle('hidden', calStyle !== 'realistic' || getWorldScope() === 'international');
  const modeSection = document.getElementById('wc-domestic-team-mode-section');
  if (modeSection) modeSection.classList.toggle('hidden', calStyle !== 'realistic' || getWorldScope() !== 'domestic');
  syncWorldDomesticTeamMode();
}

function getWorldScope() {
  return ['international', 'domestic', 'combined'].includes(WorldUI.wizardScope)
    ? WorldUI.wizardScope
    : 'international';
}

function setWorldScope(scope) {
  WorldUI.wizardScope = ['international', 'domestic', 'combined'].includes(scope) ? scope : 'international';
  ['international', 'domestic', 'combined'].forEach(key => {
    document.getElementById(`wc-scope-${key}`)?.classList.toggle('active', WorldUI.wizardScope === key);
  });
  const helpEl = document.getElementById('wc-scope-help');
  if (helpEl) helpEl.textContent = WORLD_SCOPE_META[WorldUI.wizardScope];
  _syncDomesticSectionVisibility();
  _refreshWizardTeamPool();
}

function getWorldDomesticTeamMode() {
  return WorldUI.wizardDomesticTeamMode === 'full_league' ? 'full_league' : 'selected';
}

function syncWorldDomesticTeamMode() {
  const mode = getWorldDomesticTeamMode();
  document.getElementById('wc-domestic-team-mode-selected')?.classList.toggle('active', mode === 'selected');
  document.getElementById('wc-domestic-team-mode-full')?.classList.toggle('active', mode === 'full_league');
  const helpEl = document.getElementById('wc-domestic-team-mode-help');
  if (helpEl) helpEl.textContent = WORLD_DOMESTIC_TEAM_MODE_META[mode];
}

function setWorldDomesticTeamMode(mode) {
  WorldUI.wizardDomesticTeamMode = mode === 'full_league' ? 'full_league' : 'selected';
  syncWorldDomesticTeamMode();
  _refreshWizardTeamPool();
}

function _renderWizardDomesticLeagues() {
  const el = document.getElementById('wc-domestic-leagues');
  if (!el) return;
  const leagues = WorldUI.wizardDomesticLeagueOptions || [];
  if (!leagues.length) {
    el.innerHTML = '<p class="text-muted" style="font-size:var(--fs-sm)">No domestic leagues available.</p>';
    return;
  }
  const FORMAT_LABELS = { Test: '4-day', ODI: 'List-A', T20: 'T20' };
  el.innerHTML = leagues.map(l => `
    <button type="button"
      class="domestic-league-btn ${WorldUI.wizardDomesticLeagues.has(l.key) ? 'active' : ''}"
      id="dlb-${l.key}" onclick="wizardToggleDomesticLeague('${l.key}')">
      <span class="dlb-name">${l.name}</span>
      <span class="dlb-meta">${FORMAT_LABELS[l.format] || l.format} · ${l.team_count} teams</span>
    </button>`).join('');
}

function wizardToggleDomesticLeague(key) {
  if (WorldUI.wizardDomesticLeagues.has(key)) {
    WorldUI.wizardDomesticLeagues.delete(key);
  } else {
    WorldUI.wizardDomesticLeagues.add(key);
  }
  const btn = document.getElementById(`dlb-${key}`);
  if (btn) btn.classList.toggle('active', WorldUI.wizardDomesticLeagues.has(key));
  if (getWorldScope() === 'domestic') _refreshWizardTeamPool();
}

function hideWorldWizard() {
  document.getElementById('btn-show-create-world').classList.remove('hidden');
  document.getElementById('world-wizard').classList.add('hidden');
}

function _wizardShowPage(n) {
  [1,2,3,4].forEach(i => {
    document.getElementById(`wizard-page-${i}`).classList.toggle('hidden', i !== n);
    const stepEl = document.getElementById(`ws-step-${i}`);
    if (stepEl) {
      stepEl.classList.toggle('active', i === n);
      stepEl.classList.toggle('done', i < n);
    }
  });
}

function wizardNext(fromStep) {
  if (fromStep === 1) {
    const name = (document.getElementById('wc-name').value || '').trim();
    if (!name) { alert('Enter a world name.'); return; }
  }
  if (fromStep === 3) {
    const scope = getWorldScope();
    const minTeams = scope === 'domestic' ? 2 : 4;
    const calStyle = document.querySelector('input[name="wc-cal-style"]:checked')?.value || 'realistic';
    if (scope === 'domestic' && calStyle === 'realistic' && !(WorldUI.wizardDomesticLeagues || new Set()).size) {
      alert('Choose at least one domestic league for a realistic domestic world.'); return;
    }
    if (WorldUI.wizardTeamIds.size < minTeams) {
      alert(`Select at least ${minTeams} teams.`); return;
    }
    _wizardBuildSummary();
  }
  WorldUI.wizardStep = fromStep + 1;
  _wizardShowPage(WorldUI.wizardStep);
}

function wizardBack(fromStep) {
  WorldUI.wizardStep = fromStep - 1;
  _wizardShowPage(WorldUI.wizardStep);
}

function _renderWizardTeamBadges() {
  const el = document.getElementById('wizard-team-badges');
  if (!el) return;
  el.innerHTML = WorldUI.wizardAllTeams.map(t => `
    <div class="wizard-team-badge ${WorldUI.wizardTeamIds.has(t.id) ? 'selected' : ''}"
         id="wtb-${t.id}" onclick="wizardToggleTeam(${t.id})" title="${t.name}">
      <div class="wtb-circle" style="background:${t.badge_colour || '#555'}">${(t.short_code || t.name).slice(0,3)}</div>
      <div class="wtb-name">${t.name}</div>
    </div>`).join('');
  _wizardUpdateCount();
}

function _refreshWizardTeamPool() {
  const scope = getWorldScope();
  const domesticMode = getWorldDomesticTeamMode();
  let pool = [];
  if (scope === 'domestic') {
    const selectedLeagueNames = new Set(
      Array.from(WorldUI.wizardDomesticLeagues || [])
        .map(k => (WorldUI.wizardDomesticLeagueOptions || []).find(l => l.key === k)?.league)
        .filter(Boolean)
    );
    pool = (WorldUI.wizardDomesticTeams || []).filter(t =>
      !selectedLeagueNames.size || (t.league && selectedLeagueNames.has(t.league))
    );
  } else {
    pool = WorldUI.wizardInternationalTeams || [];
  }
  WorldUI.wizardAllTeams = pool;
  if (scope === 'domestic' && domesticMode === 'full_league') {
    WorldUI.wizardTeamIds = new Set(pool.map(t => t.id));
  } else {
    WorldUI.wizardTeamIds = new Set(Array.from(WorldUI.wizardTeamIds).filter(id => pool.some(t => t.id === id)));
  }
  _renderWizardTeamBadges();
  _refreshWizardMyTeamOptions();
  const selectAllBtn = document.getElementById('wizard-select-all-btn');
  if (selectAllBtn) {
    const lockTeamSelection = scope === 'domestic' && domesticMode === 'full_league';
    selectAllBtn.classList.toggle('hidden', lockTeamSelection);
  }
  const titleEl = document.getElementById('wizard-team-step-title');
  if (titleEl) {
    if (scope === 'domestic' && domesticMode === 'full_league') {
      titleEl.innerHTML = 'Step 3 — Review League Clubs <span class="text-muted">(all included)</span>';
    } else if (scope === 'domestic') {
      titleEl.innerHTML = 'Step 3 — Select Domestic Teams <span class="text-muted">(min 2)</span>';
    } else if (scope === 'combined') {
      titleEl.innerHTML = 'Step 3 — Select International Teams <span class="text-muted">(min 4)</span>';
    } else {
      titleEl.innerHTML = 'Step 3 — Select Teams <span class="text-muted">(min 4)</span>';
    }
  }
}

function _refreshWizardMyTeamOptions() {
  const myTeamSel = document.getElementById('wc-my-team');
  if (!myTeamSel) return;
  const current = parseInt(myTeamSel.value) || null;
  myTeamSel.innerHTML = '<option value="">None — AI only</option>' +
    (WorldUI.wizardAllTeams || []).map(t => `<option value="${t.id}">${t.name}</option>`).join('');
  if (current && (WorldUI.wizardAllTeams || []).some(t => t.id === current)) {
    myTeamSel.value = String(current);
  }
}

function wizardToggleTeam(id) {
  if (getWorldScope() === 'domestic' && getWorldDomesticTeamMode() === 'full_league') return;
  if (WorldUI.wizardTeamIds.has(id)) WorldUI.wizardTeamIds.delete(id);
  else WorldUI.wizardTeamIds.add(id);
  const el = document.getElementById(`wtb-${id}`);
  if (el) el.classList.toggle('selected', WorldUI.wizardTeamIds.has(id));
  _wizardUpdateCount();
}

function wizardSelectAllTeams() {
  if (getWorldScope() === 'domestic' && getWorldDomesticTeamMode() === 'full_league') return;
  const allSelected = WorldUI.wizardAllTeams.every(t => WorldUI.wizardTeamIds.has(t.id));
  if (allSelected) {
    WorldUI.wizardTeamIds.clear();
  } else {
    WorldUI.wizardAllTeams.forEach(t => WorldUI.wizardTeamIds.add(t.id));
  }
  _renderWizardTeamBadges();
}

function _wizardUpdateCount() {
  const el = document.getElementById('wizard-team-count');
  if (!el) return;
  if (getWorldScope() === 'domestic' && getWorldDomesticTeamMode() === 'full_league') {
    el.textContent = `All ${WorldUI.wizardAllTeams.length} clubs included`;
  } else {
    el.textContent = `${WorldUI.wizardTeamIds.size} selected`;
  }
}

function _wizardBuildSummary() {
  const el = document.getElementById('wizard-summary');
  if (!el) return;
  const name      = document.getElementById('wc-name').value.trim();
  const start     = document.getElementById('wc-start').value;
  const density   = document.querySelector('input[name="wc-density"]:checked')?.value || 'moderate';
  const calStyle  = document.querySelector('input[name="wc-cal-style"]:checked')?.value || 'realistic';
  const calYears  = Math.max(1, Math.min(10, parseInt(document.getElementById('wc-years')?.value, 10) || 2));
  const worldScope = getWorldScope();
  const domesticTeamMode = getWorldDomesticTeamMode();
  const myTeamId  = parseInt(document.getElementById('wc-my-team').value) || null;
  const myTeam    = myTeamId ? WorldUI.wizardAllTeams.find(t => t.id === myTeamId) : null;
  const teamList  = WorldUI.wizardAllTeams.filter(t => WorldUI.wizardTeamIds.has(t.id));
  const styleLabel = calStyle === 'realistic' ? 'Realistic (FTP)' : 'Random';
  const domLeagues = Array.from(WorldUI.wizardDomesticLeagues || []);
  const domLeagueNames = domLeagues.map(k => {
    const opt = (WorldUI.wizardDomesticLeagueOptions || []).find(l => l.key === k);
    return opt ? opt.name : k;
  });

  el.innerHTML = `
    <div class="summary-row"><span>World Name</span><strong>${name}</strong></div>
    <div class="summary-row"><span>World Type</span><strong>${_titleCaseWords(worldScope)}</strong></div>
    <div class="summary-row"><span>Start Date</span><strong>${start}</strong></div>
    <div class="summary-row"><span>Density</span><strong>${density}</strong></div>
    <div class="summary-row"><span>Calendar Style</span><strong>${styleLabel}</strong></div>
    <div class="summary-row"><span>Fixture Horizon</span><strong>${calYears} year${calYears !== 1 ? 's' : ''}</strong></div>
    ${worldScope === 'domestic' && calStyle === 'realistic' ? `<div class="summary-row"><span>Domestic Coverage</span><strong>${domesticTeamMode === 'full_league' ? 'Full League' : 'Selected Clubs'}</strong></div>` : ''}
    <div class="summary-row"><span>Your Team</span><strong>${myTeam ? myTeam.name : 'None (AI only)'}</strong></div>
    <div class="summary-row"><span>Teams (${teamList.length})</span>
      <span>${worldScope === 'domestic' && domesticTeamMode === 'full_league'
        ? `All clubs from the selected league set (${teamList.length})`
        : teamList.map(t => t.short_code || t.name.slice(0,3)).join(', ')}</span>
    </div>
    ${domLeagueNames.length ? `<div class="summary-row"><span>Domestic Leagues</span><span>${domLeagueNames.join(', ')}</span></div>` : ''}`;
}

async function submitWorldWizard() {
  const name      = document.getElementById('wc-name').value.trim();
  const start     = document.getElementById('wc-start').value;
  const density   = document.querySelector('input[name="wc-density"]:checked')?.value || 'moderate';
  const calStyle  = document.querySelector('input[name="wc-cal-style"]:checked')?.value || 'realistic';
  const calYears  = Math.max(1, Math.min(10, parseInt(document.getElementById('wc-years')?.value, 10) || 2));
  const worldScope = getWorldScope();
  const domesticTeamMode = getWorldDomesticTeamMode();
  const myTeamId  = parseInt(document.getElementById('wc-my-team').value) || null;
  const team_ids  = Array.from(WorldUI.wizardTeamIds);

  const btn = document.getElementById('wizard-create-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Creating…'; }

  const domestic_leagues = calStyle === 'realistic'
    ? Array.from(WorldUI.wizardDomesticLeagues || [])
    : [];

  const res = await api('POST', '/api/worlds', {
    name, start_date: start, calendar_density: density,
    calendar_style: calStyle, team_ids, my_team_id: myTeamId,
    domestic_leagues, world_scope: worldScope, domestic_team_mode: domesticTeamMode,
    calendar_years: calYears,
  });

  if (btn) { btn.disabled = false; btn.textContent = 'Create World'; }

  if (res?.world_id) {
    if (calStyle === 'realistic') {
      await _showCalendarPreview(res.world_id);
    } else {
      hideWorldWizard();
      loadWorldDetail(res.world_id);
    }
  }
}

async function _showCalendarPreview(worldId) {
  // Replace wizard content with a calendar preview before navigating
  const panel = document.getElementById('wizard-pages');
  if (!panel) { hideWorldWizard(); loadWorldDetail(worldId); return; }

  panel.innerHTML = `<div style="padding:8px 0">
    <h3 style="margin:0 0 6px">Calendar Preview</h3>
    <p class="text-muted" style="font-size:var(--fs-sm);margin:0 0 12px">
      Next 12 months of generated fixtures</p>
    <div id="cal-preview-loading" class="text-muted">Loading…</div>
    <div id="cal-preview-content" class="hidden"></div>
    <div class="wizard-nav" style="margin-top:16px">
      <button class="btn btn-primary" onclick="hideWorldWizard();loadWorldDetail(${worldId})">
        Open World →</button>
    </div>
  </div>`;

  const data = await api('GET', `/api/worlds/${worldId}/calendar/upcoming?days=365`);
  const loadingEl  = document.getElementById('cal-preview-loading');
  const contentEl  = document.getElementById('cal-preview-content');
  if (loadingEl)  loadingEl.classList.add('hidden');
  if (!contentEl) return;
  contentEl.classList.remove('hidden');

  const fixtures   = data?.fixtures || [];
  const seriesSet  = new Set(fixtures.map(f => f.series_name).filter(Boolean));
  const iccCount   = fixtures.filter(f => f.is_icc_event).length;

  const statHtml = `
    <div class="cal-preview-panel">
      <h4>Calendar Preview — Next 12 months</h4>
      <div class="cal-preview-stats">
        <div class="cal-preview-stat"><strong>${fixtures.length}</strong><small>Fixtures</small></div>
        <div class="cal-preview-stat"><strong>${seriesSet.size}</strong><small>Series</small></div>
        <div class="cal-preview-stat"><strong>${iccCount}</strong><small>ICC Event matches</small></div>
      </div>
      <ul class="cal-preview-list">
        ${fixtures.slice(0, 30).map(f => {
          const d = f.scheduled_date || '';
          const t1 = f.team1_name || `Team ${f.team1_id}`;
          const t2 = f.team2_name || `Team ${f.team2_id}`;
          const iccBadge = f.is_icc_event
            ? `<span class="cal-preview-icc">ICC</span>` : '';
          const series = f.series_name
            ? `<span class="cal-preview-series">${f.series_name}</span>` : '';
          return `<li>
            <span class="cal-preview-date">${d}</span>
            <span><span class="badge badge-${(f.format||'').toLowerCase()}">${f.format||''}</span></span>
            <span>${t1} v ${t2}</span>
            ${series}${iccBadge}
          </li>`;
        }).join('')}
        ${fixtures.length > 30 ? `<li style="color:var(--text-muted);padding:6px 0">…and ${fixtures.length - 30} more</li>` : ''}
      </ul>
    </div>`;

  contentEl.innerHTML = statHtml;
}

// ── World Dashboard ───────────────────────────────────────────────────────────

async function loadWorldDetail(worldId) {
  WorldUI.activeWorldId = worldId;
  showScreen('world-detail');

  const nameEl = document.getElementById('wd-name');
  if (nameEl) nameEl.textContent = 'Loading…';

  const [data, seriesRes] = await Promise.all([
    api('GET', `/api/worlds/${worldId}`),
    api('GET', `/api/worlds/${worldId}/calendar/series`),
  ]);
  if (!data) return;
  WorldUI._worldData = data;
  WorldUI._seriesData = seriesRes?.series || [];

  const w = data.world || {};
  const settings = (() => {
    try { return JSON.parse(w.settings_json || '{}'); }
    catch (_) { return {}; }
  })();
  const worldScope = ['international', 'domestic', 'combined'].includes(settings.world_scope)
    ? settings.world_scope
    : 'international';
  if (nameEl) nameEl.textContent = w.name || 'World';
  document.getElementById('wd-date-badge').textContent  = `📅 ${w.current_date || '?'}`;
  document.getElementById('wd-density-badge').textContent = w.calendar_density || 'moderate';
  document.getElementById('wd-scope-badge').textContent = _titleCaseWords(worldScope);

  const done  = data.completed_count || 0;
  const left  = data.upcoming_count  || 0;
  const total = done + left;
  document.getElementById('wd-done').textContent  = `${done} played`;
  document.getElementById('wd-left').textContent  = `${left} remaining`;
  const pct = total > 0 ? Math.round(done / total * 100) : 0;
  document.getElementById('wd-progress-fill').style.width = `${pct}%`;

  // Reset tabs to overview
  switchWorldTab('overview', document.querySelector('#screen-world-detail .tab-btn'));

  _renderWorldOverview(data);
}

const _LEAGUE_DISPLAY = {
  county_championship: 'County Championship',
  t20_blast:           'T20 Blast',
  royal_london_cup:    'Royal London Cup',
  sheffield_shield:    'Sheffield Shield',
  marsh_cup:           'Marsh Cup',
  bbl:                 'Big Bash League',
  ipl:                 'IPL',
  cpl:                 'CPL',
  psl:                 'PSL',
};

function _renderWorldRules(data, settings) {
  const el = document.getElementById('wd-world-rules');
  if (!el) return;

  const worldScope      = ['international', 'domestic', 'combined'].includes(settings.world_scope)
    ? settings.world_scope : 'international';
  const calStyle        = data.world?.calendar_style === 'realistic' ? 'Realistic FTP' : 'Random Calendar';
  const domesticMode    = settings.domestic_team_mode === 'full_league' ? 'Full League' : 'Selected Clubs';
  const leagues         = Array.isArray(settings.domestic_leagues) ? settings.domestic_leagues : [];
  const myTeamId        = settings.my_team_id || null;
  const calendarYears   = Math.max(1, Math.min(10, parseInt(settings.calendar_years, 10) || 2));
  const generatedThrough = data.generated_through || '';

  // Resolve team name from any available fixture data
  let myTeamName = null;
  if (myTeamId) {
    const allFixtures = [...(data.next_fixtures || []), ...(data.upcoming_fixtures || [])];
    for (const f of allFixtures) {
      if (f.team1_id === myTeamId) { myTeamName = f.team1_name; break; }
      if (f.team2_id === myTeamId) { myTeamName = f.team2_name; break; }
    }
  }

  const scopeIcon  = { international: '🌐', domestic: '🏟', combined: '🔀' }[worldScope] || '🌐';
  const scopeLabel = { international: 'International', domestic: 'Domestic', combined: 'Combined' }[worldScope] || worldScope;

  const pills = [];
  pills.push(`<span class="wrs-pill wrs-pill-scope">${scopeIcon} ${escHtml(scopeLabel)}</span>`);
  pills.push(`<span class="wrs-pill wrs-pill-calendar">📅 ${escHtml(calStyle)}</span>`);
  pills.push(`<span class="wrs-pill wrs-pill-horizon">⏳ ${calendarYears}-year block</span>`);
  if (generatedThrough) pills.push(`<span class="wrs-pill wrs-pill-generated">→ ${escHtml(generatedThrough)}</span>`);

  if (worldScope !== 'international') {
    pills.push(`<span class="wrs-pill wrs-pill-coverage">🗂 ${escHtml(domesticMode)}</span>`);
    if (leagues.length) {
      leagues.forEach(key => {
        const name = _LEAGUE_DISPLAY[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        pills.push(`<span class="wrs-pill wrs-pill-league">${escHtml(name)}</span>`);
      });
    }
  }

  if (myTeamId) {
    const label = myTeamName ? escHtml(myTeamName) : 'User Controlled';
    pills.push(`<span class="wrs-pill wrs-pill-team-set">👤 ${label}</span>`);
  } else {
    pills.push(`<span class="wrs-pill wrs-pill-team-ai">🤖 AI Only</span>`);
  }

  el.innerHTML = `<span class="wrs-label">World Rules</span>${pills.join('')}`;
}

function _renderWorldOverview(data) {
  const settings = (() => {
    try { return JSON.parse(data.world?.settings_json || '{}'); }
    catch (_) { return {}; }
  })();
  _renderWorldRules(data, settings);
  const style = data.world?.calendar_style === 'realistic' ? 'Realistic FTP' : 'Random Calendar';
  const worldScope = ['international', 'domestic', 'combined'].includes(settings.world_scope)
    ? settings.world_scope
    : 'international';
  const domesticTeamMode = settings.domestic_team_mode === 'full_league' ? 'full_league' : 'selected';
  const calendarYears = Math.max(1, Math.min(10, parseInt(settings.calendar_years, 10) || 2));
  const upcoming = data.upcoming_fixtures || [];
  const myNext = (data.next_fixtures || []).find(f => f.is_user_match) || null;
  const hasTrackedTeam = !!settings.my_team_id;
  const nextFix = (data.next_fixtures || [])[0] || null;
  const generatedThrough = data.generated_through || '';
  const iccUpcoming = upcoming.filter(f => f.is_icc_event).length;
  const activeSeries = (WorldUI._seriesData || [])
    .filter(s => (s.matches_remaining || 0) > 0)
    .slice(0, 5);

  const deskEl = document.getElementById('wd-world-desk');
  if (deskEl) {
    deskEl.innerHTML = `
      <div class="world-desk-card">
        <div class="world-desk-label">World Type</div>
        <div class="world-desk-value">${escHtml(_titleCaseWords(worldScope))}</div>
        <div class="world-desk-sub">${worldScope === 'combined'
          ? 'International calendar plus domestic leagues'
          : worldScope === 'domestic'
            ? `Domestic and franchise cricket focus · ${domesticTeamMode === 'full_league' ? 'Full league' : 'Selected clubs'}`
            : 'National teams and international fixtures only'}</div>
      </div>
      <div class="world-desk-card">
        <div class="world-desk-label">Calendar</div>
        <div class="world-desk-value">${escHtml(style)}</div>
        <div class="world-desk-sub">${upcoming.length
          ? `${iccUpcoming} ICC fixture${iccUpcoming !== 1 ? 's' : ''} in the next 2 weeks`
          : nextFix
            ? `Quiet short horizon. Next fixture is ${escHtml(nextFix.scheduled_date || '')}`
            : generatedThrough
              ? `Current block runs through ${escHtml(generatedThrough)}`
              : 'No upcoming fixtures generated yet'}</div>
      </div>
      <div class="world-desk-card">
        <div class="world-desk-label">Active Series</div>
        <div class="world-desk-value">${activeSeries.length}</div>
        <div class="world-desk-sub">${upcoming.length} fixture${upcoming.length !== 1 ? 's' : ''} on the short horizon · ${calendarYears}-year generation block</div>
      </div>
      <div class="world-desk-card">
        <div class="world-desk-label">Your Team</div>
        <div class="world-desk-value">${myNext ? 'User Controlled' : (hasTrackedTeam ? 'Tracking Enabled' : 'AI Only')}</div>
        <div class="world-desk-sub">${myNext ? `Next playable fixture: ${escHtml(myNext.scheduled_date || '')}` : (hasTrackedTeam ? 'No flagged fixture on the short horizon' : 'No user-controlled side selected')}</div>
      </div>`;
  }

  const nextMyMatchBtn = document.getElementById('btn-world-next-my-match');
  if (nextMyMatchBtn) {
    nextMyMatchBtn.disabled = !hasTrackedTeam;
    nextMyMatchBtn.title = hasTrackedTeam
      ? 'Simulate until your next user-controlled fixture'
      : 'Set a user-controlled team in this world to use My Next Match';
  }
  const extendYearsEl = document.getElementById('wd-extend-years');
  if (extendYearsEl) extendYearsEl.value = String(calendarYears);
  const extendNoteEl = document.getElementById('wd-extend-note');
  if (extendNoteEl) {
    extendNoteEl.textContent = generatedThrough
      ? `Currently generated through ${generatedThrough}`
      : 'Use this when you reach the end of the current schedule block.';
  }

  // Next fixture card
  const nfEl = document.getElementById('wd-next-fixture');
  if (nfEl) {
    if (nextFix) {
      const fmtBadge = `<span class="badge badge-${(nextFix.format||'').toLowerCase()}">${nextFix.format || ''}</span>`;
      const storyLine = nextFix.is_icc_event
        ? `<span class="badge badge-upcoming">${escHtml(nextFix.icc_event_name || 'ICC Event')}</span>`
        : (nextFix.series_name ? `<span class="nf-series">${escHtml(nextFix.series_name)}</span>` : '');
      nfEl.innerHTML = `
        <div class="nf-label">Next Fixture</div>
        <div class="nf-teams">${nextFix.team1_name || '?'} <span class="nf-vs">vs</span> ${nextFix.team2_name || '?'}</div>
        <div class="nf-meta">${fmtBadge} <span class="text-muted">${nextFix.scheduled_date || ''}</span>
          <span class="text-muted">${nextFix.venue_name ? '@ ' + nextFix.venue_name : ''}</span> ${storyLine}
        </div>
        <div class="nf-actions">
          <button class="btn btn-primary btn-sm" onclick="simulateWorld('next_match')">▶ Simulate</button>
          ${nextFix.is_user_match ? `<button class="btn btn-accent btn-sm" onclick="playWorldFixture(${nextFix.id})">🏏 Play Now</button>` : ''}
        </div>`;
    } else {
      nfEl.innerHTML = `<p class="text-muted">No upcoming fixtures.${generatedThrough ? ` Current block runs through ${escHtml(generatedThrough)}.` : ''}</p>
        <div class="nf-actions" style="margin-top:10px">
          <button class="btn btn-secondary btn-sm" onclick="extendWorldCalendar()">+ Generate More Fixtures</button>
        </div>`;
    }
  }

  loadWorldStoryDesk(data);

  const seriesEl = document.getElementById('wd-series-list');
  if (seriesEl) {
    seriesEl.innerHTML = activeSeries.length
      ? activeSeries.map(s => _seriesSummaryHtml(s)).join('')
      : '<p class="text-muted">No active series or event blocks right now.</p>';
  }

  // Upcoming 2-week list
  const upEl = document.getElementById('wd-upcoming-list');
  if (upEl) {
    const fixtures = data.upcoming_fixtures || [];
    upEl.innerHTML = fixtures.length
      ? fixtures.map(f => _fixtureRowHtml(f)).join('')
      : (nextFix
          ? `<div class="empty-state-card">
              <div class="empty-state-icon">📅</div>
              <h3 class="empty-state-heading">No fixtures in the next 2 weeks</h3>
              <p class="empty-state-sub">This realistic calendar is between blocks right now. The next scheduled fixture is <strong>${escHtml(nextFix.scheduled_date || '')}</strong>: ${escHtml(nextFix.team1_name || '?')} vs ${escHtml(nextFix.team2_name || '?')}.</p>
            </div>`
          : `<div class="empty-state-card">
              <div class="empty-state-icon">🗓️</div>
              <h3 class="empty-state-heading">No fixtures left in the current block</h3>
              <p class="empty-state-sub">${generatedThrough
                ? `This world is currently generated through ${escHtml(generatedThrough)}. Extend the calendar to keep the save moving.`
                : 'Extend the calendar to generate the next block of fixtures.'}</p>
              <button class="btn btn-secondary btn-sm" onclick="extendWorldCalendar()">+ Generate More Fixtures</button>
            </div>`);
  }

  // Mini rankings — top 3 per format
  const rankEl = document.getElementById('wd-mini-rankings');
  if (rankEl) {
    const byFmt = data.rankings || {};
    rankEl.innerHTML = ['Test','ODI','T20'].map(fmt => {
      const rows = (byFmt[fmt] || []).slice(0, 3);
      if (!rows.length) return '';
      const maxPts = Math.max(...rows.map(r => r.points || 0), 1);
      return `<div class="mini-rank-group">
        <div class="mini-rank-fmt">${fmt}</div>
        ${rows.map(r => {
          const pct = Math.round((r.points || 0) / maxPts * 100);
          return `<div class="mini-rank-row">
            <span class="mr-pos">${r.position || '-'}</span>
            <span class="mr-team">${r.team_name}</span>
            <span class="mr-pts">${Math.round(r.points || 0)}</span>
            <div class="mr-bar-wrap"><div class="mr-bar" style="width:${pct}%"></div></div>
          </div>`;
        }).join('')}
      </div>`;
    }).join('');
  }

  // Recent results
  const resEl = document.getElementById('wd-recent-results');
  if (resEl) {
    const results = (data.recent_results || []).slice(0, 5);
    resEl.innerHTML = results.length
      ? results.map(m => {
          const rt = m.result_type;
          let desc = '';
          if (rt === 'runs')     desc = `${m.winning_team_name} won by ${m.margin_runs} runs`;
          else if (rt === 'wickets') desc = `${m.winning_team_name} won by ${m.margin_wickets} wkts`;
          else if (rt === 'draw') desc = 'Match drawn';
          else if (rt === 'tie')  desc = 'Match tied';
          return `<div class="result-row result-row-clickable" onclick="openPlayedMatch(${m.id || m.match_id})" title="View scorecard">
            <span class="result-format text-muted">${m.format}</span>
            <span>${m.team1_name} vs ${m.team2_name}</span>
            <span class="text-muted">${desc}</span>
            <span class="result-date text-muted">${m.match_date || ''}</span>
          </div>`;
        }).join('')
      : '<p class="text-muted">No matches played yet.</p>';
  }

  // World records
  _renderRecordsSection('wd-records-overview', data.world_records || []);
}

async function loadWorldStoryDesk(data) {
  const el = document.getElementById('wd-story-desk');
  if (!el) return;
  el.innerHTML = '';

  const [batting, bowling] = await Promise.all([
    api('GET', '/api/almanack/batting?limit=6&offset=0&sort=runs&dir=DESC'),
    api('GET', '/api/almanack/bowling?limit=6&offset=0&sort=wickets&dir=DESC'),
  ]);
  const battingRows = batting?.rows || [];
  const bowlingRows = bowling?.rows || [];
  const worldRecords = data.world_records || [];
  const nextFixtures = data.next_fixtures || [];

  const recordThreats = worldRecords
    .filter(r => r && r.value != null)
    .slice(0, 3)
    .map(r => ({
      title: r.record_name || r.label || r.category || 'World record',
      sub: r.holder_name
        ? `${r.holder_name} leads with ${r.display_value || r.value}`
        : `${r.display_value || r.value} is the current world mark`
    }));

  const inForm = [
    ...battingRows.slice(0, 2).map(r => ({
      title: `${r.name} ${r.runs} runs`,
      sub: `${r.team_name} · Avg ${Number(r.average || 0).toFixed(2)} · SR ${Number(r.strike_rate || 0).toFixed(1)}`
    })),
    ...bowlingRows.slice(0, 2).map(r => ({
      title: `${r.name} ${r.wickets} wickets`,
      sub: `${r.team_name} · Avg ${Number(r.average || 0).toFixed(2)} · Econ ${Number(r.economy || 0).toFixed(2)}`
    })),
  ].slice(0, 4);

  const milestoneWatch = [];
  battingRows.slice(0, 4).forEach(r => {
    const target = _nextMilestone(r.runs || 0, [100, 250, 500, 1000, 1500, 2000, 3000, 5000]);
    if (target && target - (r.runs || 0) <= Math.max(50, target * 0.08)) {
      milestoneWatch.push({
        title: `${r.name} tracking ${target} runs`,
        sub: `${target - (r.runs || 0)} away before the next landmark`
      });
    }
  });
  bowlingRows.slice(0, 4).forEach(r => {
    const target = _nextMilestone(r.wickets || 0, [25, 50, 100, 150, 200, 300, 400]);
    if (target && target - (r.wickets || 0) <= 5) {
      milestoneWatch.push({
        title: `${r.name} tracking ${target} wickets`,
        sub: `${target - (r.wickets || 0)} away from the next landmark`
      });
    }
  });
  if (!milestoneWatch.length && nextFixtures.length) {
    nextFixtures.slice(0, 2).forEach(f => {
      milestoneWatch.push({
        title: `${f.team1_name} vs ${f.team2_name}`,
        sub: `${f.scheduled_date || ''}${f.series_name ? ' · ' + f.series_name : ''}`
      });
    });
  }

  el.innerHTML = `
    <div class="story-desk-card">
      <div class="story-desk-kicker">World Records</div>
      ${recordThreats.length ? `<div class="story-desk-list">
        ${recordThreats.map(item => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(item.title)}</div><div class="story-desk-sub">${escHtml(item.sub)}</div></div>`).join('')}
      </div>` : '<div class="story-desk-empty">World records will appear here once the world develops more history.</div>'}
    </div>
    <div class="story-desk-card">
      <div class="story-desk-kicker">Players In Form</div>
      ${inForm.length ? `<div class="story-desk-list">
        ${inForm.map(item => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(item.title)}</div><div class="story-desk-sub">${escHtml(item.sub)}</div></div>`).join('')}
      </div>` : '<div class="story-desk-empty">Not enough played cricket yet to call out form players.</div>'}
    </div>
    <div class="story-desk-card">
      <div class="story-desk-kicker">Milestone Chances</div>
      ${milestoneWatch.length ? `<div class="story-desk-list">
        ${milestoneWatch.slice(0, 4).map(item => `<div class="story-desk-item"><div class="story-desk-title">${escHtml(item.title)}</div><div class="story-desk-sub">${escHtml(item.sub)}</div></div>`).join('')}
      </div>` : '<div class="story-desk-empty">No milestone pushes stand out yet.</div>'}
    </div>`;
}

function _fixtureRowHtml(f) {
  const fmtBadge = `<span class="badge badge-${(f.format||'').toLowerCase()}">${f.format || ''}</span>`;
  const userMark = f.is_user_match ? '<span class="badge badge-play">▶ Play</span>' : '';
  const storyMark = f.is_icc_event
    ? `<span class="badge badge-upcoming">${escHtml(f.icc_event_name || 'ICC')}</span>`
    : (f.series_name ? `<span class="wf-series">${escHtml(f.series_name)}</span>` : '');
  return `<div class="world-fixture-row ${f.is_user_match ? 'wf-play' : ''}">
    <span class="wf-date">${f.scheduled_date || ''}</span>
    ${fmtBadge}
    <span class="wf-teams">${f.team1_name || '?'} vs ${f.team2_name || '?'}</span>
    ${storyMark}
    ${userMark}
  </div>`;
}

function _seriesSummaryHtml(series) {
  const isIcc = !!series.is_icc_event;
  const label = isIcc ? (series.icc_event_name || 'ICC Event') : (series.format || 'Series');
  const progress = `${series.matches_played || 0}/${series.total_matches || 0}`;
  const teams = series.team2_name
    ? `${series.team1_name || '?'} vs ${series.team2_name || '?'}`
    : (series.series_name || 'Series');
  return `<div class="world-series-row ${isIcc ? 'world-series-icc' : ''}">
    <div class="world-series-main">
      <div class="world-series-name">${escHtml(series.series_name || teams)}</div>
      <div class="world-series-meta">
        <span class="badge badge-${String(series.format || 'odi').toLowerCase()}">${escHtml(label)}</span>
        <span class="text-muted">${escHtml(teams)}</span>
        <span class="text-muted">${escHtml(series.start_date || '')}${series.end_date ? ' → ' + escHtml(series.end_date) : ''}</span>
      </div>
    </div>
    <div class="world-series-progress">${progress}</div>
  </div>`;
}

function _renderRecordsSection(elId, records) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!records.length) { el.innerHTML = '<p class="text-muted">No records yet.</p>'; return; }

  const keyLabels = {
    highest_score:      'Highest Individual Score',
    best_bowling:       'Best Bowling',
    highest_team_total: 'Highest Team Total',
    lowest_team_total:  'Lowest Team Total',
  };
  const grouped = {};
  records.forEach(r => { grouped[r.record_key] = r; });

  el.innerHTML = `<div class="records-grid">${
    Object.entries(grouped).map(([key, r]) => {
      let ctx = {};
      try { ctx = JSON.parse(r.context_json || '{}'); } catch(e) {}
      const label = keyLabels[key] || key;
      const who   = ctx.player_name || ctx.team_name || '';
      const opp   = ctx.opponent_name ? ` vs ${ctx.opponent_name}` : '';
      return `<div class="record-card card">
        <div class="record-label">${label}${r.format ? ' (' + r.format + ')' : ''}</div>
        <div class="record-value">${r.record_value}</div>
        <div class="text-muted" style="font-size:var(--fs-xs)">${who}${opp} · ${ctx.match_date || ''}</div>
      </div>`;
    }).join('')
  }</div>`;
}

function switchWorldTab(tab, btn) {
  ['overview','rankings','records'].forEach(t => {
    const el = document.getElementById(`wd-tab-${t}`);
    if (el) el.classList.toggle('hidden', t !== tab);
  });
  document.querySelectorAll('#screen-world-detail .tab-btn').forEach(b =>
    b.classList.toggle('active', b === btn));

  if (tab === 'rankings') loadWorldRankings();
  if (tab === 'records')  loadWorldRecords();
}

async function loadWorldRankings() {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  const data = await api('GET', `/api/worlds/${id}/rankings`);
  const el = document.getElementById('wd-rankings-content');
  if (!el || !data) return;
  const by_fmt = data.rankings || {};

  el.innerHTML = ['Test','ODI','T20'].map(fmt => {
    const rows = (by_fmt[fmt] || []);
    if (!rows.length) return '';
    const maxPts = Math.max(...rows.map(r => r.points || 0), 1);

    return `<div class="standings-group" style="margin-bottom:24px">
      <h4 style="margin:0 0 8px">${fmt}</h4>
      <table class="standings-table rankings-table">
        <thead><tr><th>Pos</th><th>Team</th><th>Points</th><th>Chg</th><th>M</th></tr></thead>
        <tbody>${rows.map(r => {
          const pts  = Math.round(r.points || 0);
          const pct  = Math.round(pts / maxPts * 100);
          const hist = r.history || [];
          const prev = hist.length >= 2 ? (hist[1].position || 0) : (r.position || 0);
          const cur  = r.position || 0;
          const chg  = prev && cur ? prev - cur : 0;
          const chgHtml = chg > 0
            ? `<span class="rank-up">↑${chg}</span>`
            : chg < 0
              ? `<span class="rank-down">↓${Math.abs(chg)}</span>`
              : '<span class="rank-same">—</span>';
          return `<tr>
            <td>${r.position || '-'}</td>
            <td>${r.team_name}</td>
            <td>
              <div class="pts-bar-wrap">
                <span class="pts-num">${pts}</span>
                <div class="pts-bar"><div class="pts-bar-fill" style="width:${pct}%"></div></div>
              </div>
            </td>
            <td>${chgHtml}</td>
            <td>${r.matches_counted || 0}</td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>
    </div>`;
  }).join('');
}

async function loadWorldRecords() {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  const data = await api('GET', `/api/worlds/${id}/records`);
  const el = document.getElementById('wd-records-content');
  if (!el || !data) return;
  _renderRecordsSection('wd-records-content', data.records || []);
}

// ── World Calendar ────────────────────────────────────────────────────────────

let _calendarData = null;

function openWorldCalendar() {
  if (!WorldUI.activeWorldId) return;
  showScreen('world-calendar');
  const titleEl = document.getElementById('wcal-title');
  const worldName = WorldUI._worldData?.world?.name || 'World';
  if (titleEl) titleEl.textContent = `${worldName} — Calendar`;
  loadWorldCalendar();
}

async function loadWorldCalendar(filter) {
  if (filter !== undefined) WorldUI.calendarFilter = filter;
  const id = WorldUI.activeWorldId;
  if (!id) return;

  const el = document.getElementById('wcal-months');
  if (!el) return;
  el.innerHTML = '<div class="spinner"></div>';

  const statusParam = WorldUI.calendarFilter === 'all' ? '' : `&status=${WorldUI.calendarFilter}`;
  const data = await api('GET', `/api/worlds/${id}/calendar?${statusParam}`);
  if (!data) { el.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">📅</div><h3 class="empty-state-heading">Could not load calendar</h3></div>`; return; }

  _calendarData = data;
  const byMonth = data.by_month || {};
  const months  = Object.keys(byMonth).sort();

  if (!months.length) {
    el.innerHTML = `<div class="empty-state-card"><div class="empty-state-icon">📅</div><h3 class="empty-state-heading">No fixtures scheduled</h3><p class="empty-state-sub">Create a world to generate a fixture calendar.</p><button class="btn btn-primary btn-sm" style="margin-top:14px" onclick="showScreen('world')">Create World</button></div>`;
    return;
  }

  el.innerHTML = months.map(m => {
    const [yr, mo] = m.split('-');
    const monthName = new Date(parseInt(yr), parseInt(mo)-1).toLocaleString('default', {month:'long', year:'numeric'});
    const fixtures  = byMonth[m] || [];
    return `
    <div class="cal-month-section" id="calmonth-${m}">
      <div class="cal-month-header" onclick="toggleCalMonth('${m}')">
        <span class="cal-month-name">${monthName}</span>
        <span class="cal-month-count text-muted">${fixtures.length} fixture${fixtures.length !== 1 ? 's' : ''}</span>
        <span class="cal-month-toggle">▼</span>
      </div>
      <div class="cal-month-body" id="calmonth-body-${m}">
        ${fixtures.map(f => _calFixtureRowHtml(f)).join('')}
      </div>
    </div>`;
  }).join('');
}

function switchCalFilter(filter, btn) {
  document.querySelectorAll('.wcal-filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadWorldCalendar(filter);
}

function toggleCalMonth(monthKey) {
  const body = document.getElementById(`calmonth-body-${monthKey}`);
  const sec  = document.getElementById(`calmonth-${monthKey}`);
  if (body && sec) {
    body.classList.toggle('collapsed');
    sec.classList.toggle('month-collapsed');
  }
}

function _calFixtureRowHtml(f) {
  const status    = f.status || 'scheduled';
  const skipped   = status === 'skipped';
  const completed = status === 'complete';
  const fmtBadge  = `<span class="badge badge-${(f.format||'').toLowerCase()}">${f.format||''}</span>`;
  const statusBadge = completed
    ? `<span class="badge badge-complete">✓</span>`
    : skipped
      ? `<span class="badge badge-skipped">Skip</span>`
      : `<span class="badge badge-upcoming">Upcoming</span>`;

  const result = f.result_string ? `<span class="cal-result text-muted">${f.result_string}</span>` : '';

  const actions = !completed && !skipped ? `
    <button class="btn-cal-action btn-cal-play ${f.is_user_match ? 'active' : ''}"
            onclick="toggleWorldFixturePlay(${f.id})" title="Toggle play"
            >▶</button>
    <button class="btn-cal-action btn-cal-skip"
            onclick="skipCalFixture(${f.id},this)" title="Skip">✕</button>` : '';

  const openFn = completed && f.match_id ? ` onclick="openPlayedMatch(${f.match_id})" title="View scorecard"` : '';

  return `<div class="cal-fixture-row${skipped ? ' cal-skipped' : ''}${completed ? ' cal-complete cal-clickable' : ''}" id="calfx-${f.id}"${openFn}>
    <span class="cal-date">${(f.scheduled_date||'').slice(5)}</span>
    ${fmtBadge}
    <span class="cal-teams">${f.team1_name||'?'} vs ${f.team2_name||'?'}</span>
    ${statusBadge}
    ${result}
    <span class="cal-actions">${actions}</span>
  </div>`;
}

async function skipCalFixture(fixtureId, btn) {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  await api('POST', `/api/worlds/${id}/skip-fixture/${fixtureId}`);
  // Update row in place
  const row = document.getElementById(`calfx-${fixtureId}`);
  if (row) row.outerHTML = _calFixtureRowHtml({
    ...(_calendarData?.fixtures || []).find(f => f.id === fixtureId) || {},
    id: fixtureId, status: 'skipped'
  });
}

async function toggleWorldFixturePlay(fixtureId) {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  await api('POST', `/api/worlds/${id}/fixtures/${fixtureId}/toggle-play`);
  // Reload calendar or dashboard
  if (document.getElementById('screen-world-calendar').classList.contains('active') ||
      !document.getElementById('screen-world-detail').classList.contains('active')) {
    loadWorldCalendar();
  } else {
    loadWorldDetail(id);
  }
}

async function playWorldFixture(fixtureId) {
  // Navigate to match creation for this fixture
  const row = (WorldUI._worldData?.next_fixtures || []).find(f => f.id === fixtureId)
           || (WorldUI._worldData?.upcoming_fixtures || []).find(f => f.id === fixtureId);
  if (row) {
    // Load match creation pre-filled — show play screen
    showScreen('play');
  }
}

async function simulateWorld(target) {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  const settings = (() => {
    try { return JSON.parse(WorldUI._worldData?.world?.settings_json || '{}'); }
    catch (_) { return {}; }
  })();

  if (target === 'next_my_match' && !settings.my_team_id) {
    alert('Set a user-controlled team for this world before using My Next Match.');
    return;
  }

  const body = { target };
  if (target === 'date') {
    const d = document.getElementById('wd-sim-date').value;
    if (!d) { alert('Select a date first.'); return; }
    body.target_date = d;
  }

  // 500-match guard: count scheduled fixtures
  const calData = await api('GET', `/api/worlds/${id}/calendar?status=scheduled&limit=1`);
  const total = (calData || {}).total || 0;
  if (total > 500) {
    if (!confirm(`This could simulate up to ${total} matches. Continue?`)) return;
  }

  // Disable sim buttons
  document.querySelectorAll('#screen-world-detail .btn-sim').forEach(b => b.disabled = true);

  const res = await api('POST', `/api/worlds/${id}/simulate`, body);

  document.querySelectorAll('#screen-world-detail .btn-sim').forEach(b => b.disabled = false);

  if (!res) return;

  if (res.matches_simulated === 0) {
    alert(res.message || 'Nothing to simulate. You may need to generate more fixtures.');
    return;
  }

  // Stash paused fixture onto the report so _renderSimReport can use it
  if (res.sim_report) res.sim_report._pausedFixture = res.paused_at_fixture || null;
  _renderSimReport(res.sim_report);
  showScreen('world-sim-report');
}

async function extendWorldCalendar() {
  const id = WorldUI.activeWorldId;
  if (!id) return;
  const years = Math.max(1, Math.min(10, parseInt(document.getElementById('wd-extend-years')?.value, 10) || 2));
  const btn = document.getElementById('btn-world-extend');
  if (btn) { btn.disabled = true; btn.textContent = 'Extending…'; }
  const res = await api('POST', `/api/worlds/${id}/extend-calendar`, { years });
  if (btn) { btn.disabled = false; btn.textContent = '+ Extend Calendar'; }
  if (!res?.success) return;
  _showToast(`Generated ${res.new_fixture_count || 0} more fixtures`, 2200);
  await loadWorldDetail(id);
}

function _renderSimReport(report) {
  const recap = document.getElementById('wsim-recap');
  if (!recap || !report) return;

  const n        = report.matches_simulated || 0;
  const from     = report.date_from || '';
  const to       = report.date_to   || '';
  const trunc    = report.truncated;
  const matchWord = n === 1 ? 'match' : 'matches';

  // ── Header ────────────────────────────────────────────────────────────────
  const metaParts = [];
  if (from) metaParts.push(`${from}${to && to !== from ? ` → ${to}` : ''}`);
  if (trunc) metaParts.push('truncated at 500');

  // ── Biggest Result ────────────────────────────────────────────────────────
  function _biggestResultHtml() {
    const br = report.biggest_by_runs;
    const bw = report.biggest_by_wickets;
    if (!br && !bw) return '<p class="wsim-rank-empty">No decisive results this round.</p>';

    function _resultCard(r) {
      if (!r) return '';
      const fmtBadge = `<span class="badge badge-${(r.format||'').toLowerCase()}">${r.format||''}</span>`;
      const ts = r.top_scorer;
      const tb = r.top_bowler;
      const performer = [
        ts ? `🏏 ${escHtml(ts.name)} — ${ts.runs} runs` : '',
        tb ? `🎳 ${escHtml(tb.name)} — ${tb.wickets} wkts` : '',
      ].filter(Boolean).join(' &nbsp;·&nbsp; ');
      return `
        <div class="wsim-big-result">
          <div class="wsim-big-result-summary">${escHtml(r.summary || '')}</div>
          <div class="wsim-big-result-detail">
            ${fmtBadge}
            <span>${escHtml(r.team1_name||'')} v ${escHtml(r.team2_name||'')}</span>
            <span>${escHtml(r.scheduled_date||'')}</span>
          </div>
          <div class="wsim-big-result-scores">${escHtml(r.team1_score||'')} &nbsp;/&nbsp; ${escHtml(r.team2_score||'')}</div>
          ${performer ? `<div class="wsim-big-result-performer">${performer}</div>` : ''}
        </div>`;
    }

    // Show the single most decisive result (prefer run wins as they feel bigger)
    const best = br || bw;
    return _resultCard(best);
  }

  // ── Notable Performances ──────────────────────────────────────────────────
  function _performancesHtml() {
    const batters = report.top_batting_perfs || [];
    const bowlers = report.top_bowling_perfs || [];
    if (!batters.length && !bowlers.length) {
      return '<p class="wsim-rank-empty">No individual performances recorded.</p>';
    }

    function _perfRows(perfs, statKey) {
      if (!perfs.length) return '<p class="wsim-rank-empty" style="font-size:var(--fs-xs)">—</p>';
      return perfs.map(p => `
        <div class="wsim-perf-row">
          <div class="wsim-perf-stat">${p[statKey] ?? '–'}</div>
          <div>
            <div class="wsim-perf-name">${escHtml(p.name)}</div>
            <div class="wsim-perf-ctx">${escHtml(p.match)} · ${escHtml(p.format)} · ${escHtml(p.date)}</div>
          </div>
        </div>`).join('');
    }

    return `
      <div class="wsim-perf-grid">
        <div>
          <div class="wsim-perf-col-title">🏏 Batting</div>
          ${_perfRows(batters, 'runs')}
        </div>
        <div>
          <div class="wsim-perf-col-title">🎳 Bowling</div>
          ${_perfRows(bowlers, 'wickets')}
        </div>
      </div>`;
  }

  // ── Ranking Impact ────────────────────────────────────────────────────────
  function _rankingImpactHtml() {
    const changes = report.ranking_changes || {};
    const allMoves = [];
    for (const [fmt, movers] of Object.entries(changes)) {
      movers.forEach(m => allMoves.push({ ...m, format: fmt }));
    }
    allMoves.sort((a, b) => Math.abs(b.pos_change) - Math.abs(a.pos_change));

    if (!allMoves.length) {
      return '<p class="wsim-rank-empty">No position changes — rankings updated but order held.</p>';
    }

    return `<div class="wsim-rank-grid">${allMoves.map(m => {
      const up    = m.pos_change > 0;
      const arrow = up ? '▲' : '▼';
      const delta = Math.abs(m.pos_change);
      const fmtBadge = `<span class="badge badge-${m.format.toLowerCase()}">${m.format}</span>`;
      return `
        <div class="wsim-rank-mover">
          <span class="wsim-rank-arrow ${up ? 'up' : 'down'}">${arrow}</span>
          <span class="wsim-rank-name">${escHtml(m.team_name)}</span>
          <span class="wsim-rank-change">${m.old_position} → ${m.new_position} &nbsp;(${up ? '+' : ''}${up ? delta : -delta} place${delta !== 1 ? 's' : ''})</span>
          <span class="wsim-rank-fmt">${fmtBadge}</span>
        </div>`;
    }).join('')}</div>`;
  }

  // ── What's Next ───────────────────────────────────────────────────────────
  function _whatsNextHtml(pausedFixture) {
    const fixtures = report.next_fixtures_preview || [];
    const rows = [];

    // Paused fixture (user match) always goes first if present
    if (pausedFixture) {
      const t1 = escHtml(pausedFixture.team1_name || '?');
      const t2 = escHtml(pausedFixture.team2_name || '?');
      const fmtBadge = `<span class="badge badge-${(pausedFixture.format||'').toLowerCase()}">${pausedFixture.format||''}</span>`;
      rows.push(`
        <div class="wsim-next-row">
          <span class="wsim-next-date">${escHtml(pausedFixture.scheduled_date||'')}</span>
          ${fmtBadge}
          <span class="wsim-next-teams">${t1} v ${t2}</span>
          <span class="wsim-next-user">▶ Your match</span>
        </div>`);
    }

    for (const f of fixtures) {
      // Skip the paused fixture if it appears in the list too
      if (pausedFixture && f.id === pausedFixture.id) continue;
      if (rows.length >= 4) break;
      const t1 = escHtml(f.team1_name || '?');
      const t2 = escHtml(f.team2_name || '?');
      const fmtBadge = `<span class="badge badge-${(f.format||'').toLowerCase()}">${f.format||''}</span>`;
      rows.push(`
        <div class="wsim-next-row">
          <span class="wsim-next-date">${escHtml(f.scheduled_date||'')}</span>
          ${fmtBadge}
          <span class="wsim-next-teams">${t1} v ${t2}</span>
        </div>`);
    }

    if (!rows.length) return '<p class="wsim-rank-empty">No further fixtures scheduled.</p>';
    return `<div class="wsim-next-list">${rows.join('')}</div>`;
  }

  // ── All Results (disclosure) ──────────────────────────────────────────────
  function _allResultsHtml() {
    return (report.results || []).map(r => {
      const fmtBadge = `<span class="badge badge-${(r.format||'').toLowerCase()}">${r.format || ''}</span>`;
      const ts = r.top_scorer;
      const tb = r.top_bowler;
      return `
        <div class="wsim-result-row">
          <div class="wsim-result-header">
            <span class="wf-date">${escHtml(r.scheduled_date||'')}</span>
            ${fmtBadge}
          </div>
          <div class="wsim-result-summary">${escHtml(r.summary||'')}</div>
          <div class="wsim-scores">${escHtml(r.team1_score||'')} &nbsp;/&nbsp; ${escHtml(r.team2_score||'')}</div>
          ${ts ? `<div class="wsim-performer">🏏 ${escHtml(ts.name)} — ${ts.runs} runs</div>` : ''}
          ${tb ? `<div class="wsim-performer">🎳 ${escHtml(tb.name)} — ${tb.wickets} wickets</div>` : ''}
        </div>`;
    }).join('');
  }

  // ── Rankings table (disclosure) ───────────────────────────────────────────
  function _rankingsTableHtml() {
    const by_fmt = report.updated_rankings || {};
    return `<div class="wsim-rankings-wrap">${['Test','ODI','T20'].map(fmt => {
      const rows = (by_fmt[fmt] || []).sort((a,b) => (a.position||99)-(b.position||99));
      if (!rows.length) return '';
      return `<div class="standings-group">
        <h4>${fmt}</h4>
        <table class="standings-table">
          <thead><tr><th>#</th><th>Team</th><th>Pts</th><th>M</th></tr></thead>
          <tbody>${rows.map(r => `
            <tr><td>${r.position||'–'}</td><td>${escHtml(r.team_name)}</td>
                <td>${Math.round(r.points||0)}</td><td>${r.matches_counted||0}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
    }).join('')}</div>`;
  }

  function _section(icon, title, body) {
    return `
      <div class="wsim-section">
        <div class="wsim-section-title">${icon} ${title}</div>
        ${body}
      </div>`;
  }

  function _disclosure(label, body) {
    return `
      <div class="wsim-disclosure wsim-section">
        <button class="wsim-disclosure-btn" onclick="
          const b=this.nextElementSibling;
          const open=b.style.display!=='none';
          b.style.display=open?'none':'';
          this.querySelector('.wsim-disc-arrow').textContent=open?'▸':'▾';
        ">
          ${escHtml(label)} <span class="wsim-disc-arrow">▸</span>
        </button>
        <div class="wsim-disclosure-body" style="display:none">${body}</div>
      </div>`;
  }

  // Store paused fixture for use in _whatsNextHtml — it's on the response,
  // not on report itself, so we stash it on the report object when we call this.
  const pausedFixture = report._pausedFixture || null;

  recap.innerHTML = `
    <div class="wsim-recap-header">
      <span class="wsim-recap-headline">${n} ${matchWord} simulated</span>
      ${metaParts.length ? `<span class="wsim-recap-meta">${escHtml(metaParts.join(' · '))}</span>` : ''}
    </div>
    ${_section('🏆', 'Biggest Result',          _biggestResultHtml())}
    ${_section('⭐', 'Notable Performances',    _performancesHtml())}
    ${_section('📊', 'Ranking Impact',          _rankingImpactHtml())}
    ${_section('📅', "What's Next",             _whatsNextHtml(pausedFixture))}
    ${_disclosure(`All ${n} results`,           _allResultsHtml())}
    ${_disclosure('Full rankings table',        _rankingsTableHtml())}
  `;
}

// switchSimTab kept as no-op for any lingering calls
function switchSimTab() {}

// ── Welcome screen toggle ─────────────────────────────────────────────────────

function toggleWelcomeInfo(btn) {
  const body = btn.nextElementSibling;
  const open = body.classList.contains('hidden');
  body.classList.toggle('hidden', !open);
  btn.textContent = open ? '▾ What is this?' : '▸ What is this?';
}

// ── Disclaimer Modal ──────────────────────────────────────────────────────────

function showDisclaimerModal(dismissible) {
  const modal = document.getElementById('disclaimer-modal');
  const closeBtn = document.getElementById('disclaimer-modal-close');
  const acceptBtn = document.getElementById('disclaimer-modal-accept');
  const body = document.getElementById('disclaimer-modal-body');
  if (!modal) return;

  if (body) body.textContent = DISCLAIMER_TEXT.full;

  if (closeBtn) closeBtn.classList.toggle('hidden', !dismissible);
  if (acceptBtn) acceptBtn.classList.toggle('hidden', dismissible);

  modal.classList.remove('hidden');
}

function closeDisclaimerModal() {
  const modal = document.getElementById('disclaimer-modal');
  if (modal) modal.classList.add('hidden');
}

function acceptDisclaimer() {
  try { localStorage.setItem('ribi_disclaimer_accepted', 'true'); } catch (_) {}
  closeDisclaimerModal();
}

function openFullDisclaimer() {
  showDisclaimerModal(true);
}

function populateSettingsLegal() {
  const shortEl = document.getElementById('settings-legal-short');
  if (shortEl) shortEl.textContent = DISCLAIMER_TEXT.short;
}

// ── Demo Mode ─────────────────────────────────────────────────────────────────

const DEMO_SCENES = [
  // 0
  { id: 'intro', title: 'Welcome to Roll It & Bowl It', type: 'title_card', duration: 3000,
    data: { headline: 'Roll It & Bowl It', subtitle: 'Dice Cricket Done Digitally', tagline: 'Powered by the HOWZAT! Engine' } },
  // 1
  { id: 'match_screen', title: 'The Live Match Screen', type: 'match_state', duration: 4000, screenshot_worthy: true, screenshot_label: 'Live Match Screen',
    data: { team1: 'England', team2: 'Australia', format: 'Test', venue: "Lord's, London", series: 'The Ashes — 2nd Test',
      score: '247/4', overs: '67.3', rr: '3.66',
      batters: [
        { name: 'J. Root',   runs: 97, balls: 134, fours: 11, sixes: 1, sr: 72.4, batting: true },
        { name: 'B. Stokes', runs: 43, balls: 61,  fours: 4,  sixes: 2, sr: 70.5, batting: false }
      ],
      bowler: { name: 'P. Cummins', overs: '14.3', maidens: 2, runs: 58, wickets: 2, econ: 3.97 },
      commentary: [
        '67.3 • Cummins to Root — pushed back firmly. No run.',
        '67.2 • Root drives imperiously through the covers. FOUR!',
        '67.1 • Short of a length, Root rocks back and pulls for TWO.',
        '66.6 • Stokes clips it off his pads to square leg. Single.',
      ] } },
  // 2
  { id: 'die_normal', title: 'Stage 1 — The Ball', type: 'dice_demo', duration: 2500,
    data: { label: 'The Ball', result: 5, flash: 'green', outcome_text: 'FOUR! Root drives through the covers!' } },
  // 3
  { id: 'die_howzat', title: 'Stage 1 — HOWZAT!', type: 'dice_demo', duration: 2000,
    data: { label: 'The Ball', result: 1, flash: 'red', outcome_text: 'HOWZAT! Australia appeal as one!' } },
  // 4
  { id: 'die_appeal', title: 'Stage 2 — The Umpire Considers', type: 'dice_demo', duration: 2000,
    data: { label: 'Appeal!', result: 2, flash: 'blue', outcome_text: 'NOT OUT — the finger stays down. Root survives!' } },
  // 5
  { id: 'die_extras', title: 'Stage 3 — What Happened?', type: 'dice_demo', duration: 2000,
    data: { label: 'Extras', result: 3, flash: 'teal', outcome_text: 'Leg bye — clips the pad and rolls away. One extra.' } },
  // 6
  { id: 'die_out', title: 'Stage 2 — OUT!', type: 'dice_demo', duration: 2000,
    data: { label: 'Appeal!', result: 6, flash: 'red', outcome_text: 'OUT! The finger goes up — Root has to go!' } },
  // 7
  { id: 'die_dismissal', title: 'Stage 4 — The Dismissal', type: 'dice_demo', duration: 2000,
    data: { label: 'Dismissal', result: 3, flash: 'purple', outcome_text: 'CAUGHT — taken at slip! Root walks for 97.' } },
  // 8
  { id: 'graphic_wicket', title: 'Broadcast Graphic — Wicket', type: 'graphic', duration: 4000,
    data: { graphic_type: 'wicket', batterName: 'J. Root', bowlerName: 'P. Cummins',
      runs: 97, balls: 134, dismissalType: 'caught', wicketNumber: 5, fowScore: 247 } },
  // 9
  { id: 'graphic_duck', title: 'Broadcast Graphic — Duck', type: 'graphic', duration: 4500,
    data: { graphic_type: 'duck', batterName: 'M. Wood', bowlerName: 'M. Starc', balls: 1, dismissalType: 'bowled' } },
  // 10
  { id: 'graphic_fifty', title: 'Broadcast Graphic — Half Century', type: 'graphic', duration: 5000,
    data: { graphic_type: 'fifty', playerName: 'B. Stokes', teamName: 'England',
      runs: 50, balls: 67, strikeRate: 74.6, matchContext: "England v Australia · The Ashes · Lord's" } },
  // 11
  { id: 'graphic_century', title: 'Broadcast Graphic — Century', type: 'graphic', duration: 7000, screenshot_worthy: true, screenshot_label: 'Century Graphic',
    data: { graphic_type: 'century', playerName: 'J. Root', teamName: 'England',
      runs: 100, balls: 142, strikeRate: 70.4, matchContext: "England v Australia · The Ashes · Lord's" } },
  // 12
  { id: 'graphic_double_century', title: 'Broadcast Graphic — Double Century', type: 'graphic', duration: 8000,
    data: { graphic_type: 'double_century', playerName: 'J. Root', teamName: 'England',
      runs: 200, balls: 287, strikeRate: 69.7, matchContext: "England v Australia · The Ashes · Lord's" } },
  // 13
  { id: 'graphic_fivefer', title: 'Broadcast Graphic — Five Wicket Haul', type: 'graphic', duration: 6000,
    data: { graphic_type: 'five_fer', playerName: 'J.M. Anderson', teamName: 'England',
      wickets: 5, runs: 32, overs: '14.3', economy: 2.21 } },
  // 14
  { id: 'graphic_ten_wicket', title: 'Broadcast Graphic — Ten Wickets in the Match', type: 'graphic', duration: 8000,
    data: { graphic_type: 'ten_wicket_haul', playerName: 'J.M. Anderson', teamName: 'England',
      inn1Figures: '5/32', inn2Figures: '5/41', totalFigures: '10/73' } },
  // 15
  { id: 'graphic_almanack_record', title: 'Broadcast Graphic — New Almanack Record', type: 'graphic', duration: 6000,
    data: { graphic_type: 'almanack_record', recordLabel: 'Highest Individual Score — Test',
      newValue: '203*', holderName: 'J. Root', teamName: 'England',
      previousValue: '187*', previousHolder: 'B. Stokes' } },
  // 16
  { id: 'graphic_world_record', title: 'Broadcast Graphic — Real World Record Beaten!', type: 'graphic', duration: 10000, screenshot_worthy: true, screenshot_label: 'World Record Beaten',
    data: { graphic_type: 'world_record', recordLabel: 'Highest Individual Score — Test',
      newValue: '412*', holderName: 'J. Root', teamName: 'England',
      realWorldValue: '400*', realWorldHolder: 'B.C. Lara',
      realWorldContext: 'West Indies v England · Antigua · 2004' } },
  // 17
  { id: 'graphic_over', title: 'Over Complete Lower-Third', type: 'graphic', duration: 3000,
    data: { graphic_type: 'over_complete', overNumber: 14, bowlerName: 'P. Cummins',
      figures: '0-0-8-0', teamScore: '187/3', currentRR: '3.97', requiredRR: null } },
  // 18
  { id: 'graphic_innings_break', title: 'Innings Break Graphic', type: 'graphic', duration: 6000,
    data: { graphic_type: 'innings_break', battingTeam: 'Australia', score: '247 all out',
      overs: '68.3', target: 248, requiredRR: '3.62', oversAvailable: '90',
      topScorer: 'S. Smith  89 (167b)', bestBowling: 'J.M. Anderson  4/52' } },
  // 19
  { id: 'graphic_result', title: 'Match Result Graphic', type: 'graphic', duration: 6000,
    data: { graphic_type: 'match_result', winnerName: 'England', resultText: 'by 6 wickets',
      score1: 'Australia  247 all out', score2: 'England  248/4',
      playerOfMatch: 'J. Root', pomDetail: '203* (287b) & 0/22' } },
  // 20
  { id: 'almanack_preview', title: "The Dice Cricketers' Almanack", type: 'almanack_preview', duration: 5000, screenshot_worthy: true, screenshot_label: 'The Almanack',
    data: { headline: "The Dice Cricketers' Almanack",
      subtitle: 'Every match. Every run. Every wicket. Forever.',
      stats: [
        { label: 'Matches Recorded', value: '247' },
        { label: 'Runs Scored', value: '312,847' },
        { label: 'Wickets Taken', value: '8,934' },
        { label: 'Centuries', value: '312' },
        { label: 'World Records Broken', value: '3' },
      ] } },
  // 21
  { id: 'rolling_modes', title: 'Auto-Roll and Manual Roll', type: 'feature_card', duration: 5000,
    data: { headline: 'Two Ways to Play',
      features: [
        { icon: '⚡', title: 'Auto-Roll', description: 'Sit back and watch. Perfect for recording and AI vs AI spectator mode.' },
        { icon: '🎲', title: 'Manual Roll', description: 'Press each die separately. Feel every appeal. Switch to Manual for a tight finish.' },
      ] } },
  // 22
  { id: 'world_mode', title: 'Cricket World Mode', type: 'feature_card', duration: 5000,
    data: { headline: 'Cricket World Mode',
      features: [
        { icon: '🌍', title: 'A Living Cricket World', description: 'Real calendar, realistic tours, ICC tournaments. Designed to run forever.' },
        { icon: '📅', title: 'Real Scheduling Logic', description: "England don't tour Australia in July. India rest during monsoon season. The Ashes every two years." },
      ] } },
  // 23
  { id: 'outro', title: 'Get Started', type: 'title_card', duration: 4000,
    data: { headline: 'Roll It & Bowl It', subtitle: 'Start playing in under 60 seconds', cta: 'Play Now →' } },
];

// Auto-timer for demo
let _demoAutoTimer = null;
function _clearDemoTimer() {
  if (_demoAutoTimer) { clearTimeout(_demoAutoTimer); _demoAutoTimer = null; }
}

const DemoMode = {
  active:         false,
  currentScene:   0,
  autoPlay:       false,
  screenshotMode: false,
  _prevScreen:    'home',
  _ssIndices:     [],   // screenshot-worthy scene indices

  start(autoPlay = false) {
    this.active       = true;
    this.screenshotMode = false;
    this.currentScene = 0;
    this.autoPlay     = autoPlay;
    this._prevScreen  = AppState.currentScreen || 'home';
    GraphicQueue.clear();
    showScreen('demo');
    this._buildDots();
    this._updateAutoBtn();
    document.getElementById('demo-watermark')?.classList.add('hidden');
    document.getElementById('demo-screenshot-bar')?.classList.add('hidden');
    document.querySelector('.demo-shell')?.classList.remove('screenshot-mode');
    document.getElementById('demo-btn-screenshot')?.classList.remove('hidden');
    this.renderScene(0);
    this._fetchRealData();
  },

  startScreenshotMode() {
    this._ssIndices = DEMO_SCENES.reduce((acc, s, i) => { if (s.screenshot_worthy) acc.push(i); return acc; }, []);
    this.screenshotMode = true;
    this.active         = true;
    this.autoPlay       = false;
    this.currentScene   = this._ssIndices[0] || 0;
    this._prevScreen    = AppState.currentScreen || 'home';
    GraphicQueue.clear();
    showScreen('demo');
    this._buildDots();
    this._updateAutoBtn();
    document.getElementById('demo-watermark')?.classList.remove('hidden');
    document.getElementById('demo-screenshot-bar')?.classList.remove('hidden');
    document.getElementById('demo-btn-screenshot')?.classList.add('hidden');
    document.querySelector('.demo-shell')?.classList.add('screenshot-mode');
    this.renderScene(this.currentScene);
  },

  next() {
    _clearDemoTimer();
    if (this.screenshotMode) {
      const pos = this._ssIndices.indexOf(this.currentScene);
      const next = this._ssIndices[pos + 1];
      if (next !== undefined) { this.renderScene(next); } else { this.end(); }
      return;
    }
    if (this.currentScene < DEMO_SCENES.length - 1) {
      this.renderScene(this.currentScene + 1);
    } else {
      this.end();
    }
  },

  previous() {
    _clearDemoTimer();
    if (this.screenshotMode) {
      const pos = this._ssIndices.indexOf(this.currentScene);
      const prev = this._ssIndices[pos - 1];
      if (prev !== undefined) this.renderScene(prev);
      return;
    }
    if (this.currentScene > 0) this.renderScene(this.currentScene - 1);
  },

  jumpTo(index) {
    _clearDemoTimer();
    this.renderScene(index);
  },

  renderScene(index) {
    _clearDemoTimer();
    GraphicQueue.clear();
    this.currentScene = index;
    const scene = DEMO_SCENES[index];
    if (!scene) return;

    document.getElementById('demo-scene-title').textContent   = scene.title;
    document.getElementById('demo-scene-counter').textContent = `${index + 1} of ${DEMO_SCENES.length}`;

    this._updateProgress();

    // Render scene content
    switch (scene.type) {
      case 'title_card':       renderDemoTitleCard(scene.data);     break;
      case 'match_state':      renderDemoMatchScreen(scene.data);   break;
      case 'dice_demo':        renderDemoDice(scene.data);          break;
      case 'graphic':          renderDemoGraphic(scene.data);       break;
      case 'almanack_preview': renderDemoAlmanack(scene.data);      break;
      case 'feature_card':     renderDemoFeatureCard(scene.data);   break;
    }

    // Auto-advance
    if (this.autoPlay && !this.screenshotMode && scene.duration < 99999) {
      _demoAutoTimer = setTimeout(() => this.next(), scene.duration);
    }
  },

  _updateProgress() {
    const pct = (this.currentScene / (DEMO_SCENES.length - 1)) * 100;
    const bar = document.getElementById('demo-progress-bar');
    if (bar) bar.style.width = `${pct}%`;
    document.querySelectorAll('.demo-dot').forEach((dot, i) => {
      dot.classList.toggle('active',  i === this.currentScene);
      dot.classList.toggle('visited', i < this.currentScene);
    });
  },

  end() {
    this.active         = false;
    this.screenshotMode = false;
    _clearDemoTimer();
    GraphicQueue.clear();
    history.replaceState(null, '', location.pathname);
    showScreen(this._prevScreen || 'home');
  },

  toggleAutoPlay() {
    this.autoPlay = !this.autoPlay;
    this._updateAutoBtn();
    if (this.autoPlay) {
      const scene = DEMO_SCENES[this.currentScene];
      if (scene && scene.duration < 99999) {
        _demoAutoTimer = setTimeout(() => this.next(), scene.duration);
      }
    } else {
      _clearDemoTimer();
    }
  },

  _updateAutoBtn() {
    const btn = document.getElementById('demo-auto-btn');
    if (!btn) return;
    btn.textContent = this.autoPlay ? '⏸ Pause' : '▶ Auto';
    btn.classList.toggle('active', this.autoPlay);
  },

  _buildDots() {
    const container = document.getElementById('demo-dots');
    if (!container) return;
    container.innerHTML = '';
    DEMO_SCENES.forEach((scene, i) => {
      const dot = document.createElement('button');
      dot.className   = 'demo-dot';
      dot.title       = scene.title;
      dot.onclick     = () => this.jumpTo(i);
      container.appendChild(dot);
    });
  },

  async _fetchRealData() {
    try {
      const data = await api('GET', '/api/demo/data');
      if (!data || !data.has_real_data) return;
      // Update almanack preview scene (index 20) with real stats
      const almScene = DEMO_SCENES[20];
      if (almScene && almScene.data && almScene.data.stats) {
        almScene.data.stats = [
          { label: 'Matches Recorded', value: data.match_count.toLocaleString() },
          { label: 'Runs Scored',      value: data.total_runs.toLocaleString() },
          { label: 'Wickets Taken',    value: data.total_wickets.toLocaleString() },
          { label: 'Centuries',        value: (data.centuries || '—').toLocaleString() },
          { label: 'Top Score', value: data.top_score ? `${data.top_score.runs} (${data.top_score.name})` : '—' },
        ];
        // If currently showing the almanack scene, re-render it
        if (this.currentScene === 20) this.renderScene(20);
      }
    } catch (_) {}
  },
};

// ── Demo scene renderers ──────────────────────────────────────────────────────

function renderDemoTitleCard(data) {
  const content = document.getElementById('demo-content');
  if (!content) return;
  content.innerHTML = `
    <div class="demo-title-card">
      <span class="demo-tc-logo">🏏</span>
      <h2 class="demo-tc-headline">${escHtml(data.headline)}</h2>
      ${data.subtitle ? `<p class="demo-tc-subtitle">${escHtml(data.subtitle)}</p>` : ''}
      ${data.tagline  ? `<p class="demo-tc-tagline">${escHtml(data.tagline)}</p>`  : ''}
      ${data.cta      ? `<button class="demo-tc-cta" onclick="DemoMode.end()">${escHtml(data.cta)}</button>` : ''}
    </div>`;
}

function renderDemoMatchScreen(data) {
  const content = document.getElementById('demo-content');
  if (!content) return;

  const battersHtml = (data.batters || []).map(b => `
    <div class="batter-row">
      <div class="batter-name${b.batting ? ' on-strike' : ''}">${escHtml(b.name)}</div>
      <div class="batter-stats">${b.runs} (${b.balls}b) ${b.fours}x4 ${b.sixes}x6 SR:${b.sr}</div>
    </div>`).join('');

  const bwl = data.bowler || {};
  const commentHtml = (data.commentary || []).map(c =>
    `<div class="commentary-line">${escHtml(c)}</div>`).join('');

  // Render die pips for face 5 statically
  const pips5 = '<div class="die-pips" style="display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr)">' + DIE_PIPS[5] + '</div>';

  content.innerHTML = `
    <div class="demo-match-mockup">
      <div class="match-topbar">
        <span class="match-title">${escHtml(data.team1)} vs ${escHtml(data.team2)} · ${escHtml(data.format)} · ${escHtml(data.venue)}</span>
        <span class="match-context">${escHtml(data.series)}</span>
      </div>
      <div class="match-scoreboard">
        <div class="scoreboard-main">
          <span class="sb-team">${escHtml(data.team1)}</span>
          <span class="sb-score">${escHtml(data.score)}</span>
          <span class="sb-overs">${escHtml(data.overs)} ov</span>
          <span class="sb-rr">RR: ${escHtml(data.rr)}</span>
        </div>
      </div>
      <div class="match-play-area">
        <div class="match-players-panel">
          <div class="players-label">BATTING</div>
          ${battersHtml}
          <div class="players-label mt-16">BOWLING</div>
          <div class="bowler-row">
            <div class="bowler-name">${escHtml(bwl.name || '')}</div>
            <div class="bowler-stats">${escHtml(bwl.overs||'')}-${bwl.maidens||0}-${bwl.runs||0}-${bwl.wickets||0} Econ:${bwl.econ||0}</div>
          </div>
        </div>
        <div class="match-dice-panel">
          <div id="demo-match-die" class="die-face demo-static-die" data-face="5">${pips5}</div>
          <div class="die-stage-label"></div>
          <div class="dice-btns">
            <button class="btn btn-primary btn-large" disabled>🎲 Roll Ball</button>
          </div>
        </div>
        <div class="match-commentary-panel">
          <div class="commentary-header">COMMENTARY</div>
          <div class="commentary-feed">${commentHtml}</div>
        </div>
      </div>
    </div>`;
}

function renderDemoDice(data) {
  const content = document.getElementById('demo-content');
  if (!content) return;

  const pipsQ = '<span style="font-size:28px;color:var(--text-muted)">?</span>';
  content.innerHTML = `
    <div class="demo-dice-scene">
      <div class="demo-dice-label">${escHtml(data.label)}</div>
      <div class="demo-die-wrap">
        <div id="demo-die-el" class="demo-die-el" data-face="0">
          <div class="demo-die-pips" style="display:flex;align-items:center;justify-content:center;width:100%;height:100%">${pipsQ}</div>
        </div>
        <div id="demo-die-stage" class="demo-die-stage">ROLLING…</div>
      </div>
      <div id="demo-dice-outcome" class="demo-dice-outcome" style="opacity:0">${escHtml(data.outcome_text)}</div>
    </div>`;

  _animateDemoDie(data.result, data.flash, data.outcome_text);
}

async function _animateDemoDie(targetFace, flashColor, outcomeText) {
  const dieEl     = document.getElementById('demo-die-el');
  const stageEl   = document.getElementById('demo-die-stage');
  const outcomeEl = document.getElementById('demo-dice-outcome');
  if (!dieEl) return;

  const totalMs  = 900;
  const flickers = 12;
  const interval = totalMs / flickers;

  function _setPips(el, face) {
    const pipsEl = el.querySelector('.demo-die-pips');
    if (!pipsEl) return;
    if (face === 0) {
      pipsEl.style.cssText = 'display:flex;align-items:center;justify-content:center;width:100%;height:100%;box-sizing:border-box';
      pipsEl.innerHTML = '<span style="font-size:28px;color:var(--text-muted)">?</span>';
    } else {
      pipsEl.style.cssText = 'display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);width:100%;height:100%;padding:12px;gap:6px;box-sizing:border-box';
      pipsEl.innerHTML = DIE_PIPS[face] || '';
    }
    el.dataset.face = face;
  }

  // In screenshot mode: skip animation, jump to result
  if (DemoMode.screenshotMode) {
    _setPips(dieEl, targetFace);
    if (stageEl) stageEl.textContent = '';
    if (outcomeEl) { outcomeEl.textContent = outcomeText; outcomeEl.style.opacity = '1'; }
    return;
  }

  for (let i = 0; i < flickers; i++) {
    _setPips(dieEl, Math.ceil(Math.random() * 6));
    await sleep(interval);
    // Stop if demo changed scenes
    if (!DemoMode.active || document.getElementById('demo-die-el') !== dieEl) return;
  }

  _setPips(dieEl, targetFace);
  if (stageEl) stageEl.textContent = '';

  // Colour flash
  const flashMap = { green: '#2ecc71', red: '#e74c3c', blue: '#3498db', teal: '#1abc9c', purple: '#9b59b6' };
  if (flashColor && flashMap[flashColor]) {
    dieEl.style.boxShadow = `0 0 28px ${flashMap[flashColor]}, 0 0 8px ${flashMap[flashColor]}`;
    dieEl.style.borderColor = flashMap[flashColor];
    setTimeout(() => {
      if (dieEl.isConnected) { dieEl.style.boxShadow = ''; dieEl.style.borderColor = ''; }
    }, 900);
  }

  await sleep(250);
  if (!DemoMode.active || document.getElementById('demo-dice-outcome') !== outcomeEl) return;
  if (outcomeEl) { outcomeEl.textContent = outcomeText; outcomeEl.style.opacity = '1'; }
}

function renderDemoGraphic(data) {
  const { graphic_type } = data;
  const content = document.getElementById('demo-content');
  if (!content) return;

  // Special cases — rendered inline (not via GraphicQueue overlay)
  if (graphic_type === 'innings_break') {
    _renderDemoInningsBreak(data, content);
    return;
  }
  if (graphic_type === 'match_result') {
    _renderDemoMatchResult(data, content);
    return;
  }

  // All other types go through the real GraphicQueue (identical to in-game rendering)
  // Show background context in demo content while overlay plays
  const typeLabels = {
    wicket: 'Wicket', duck: 'Duck', fifty: 'Half Century', century: 'CENTURY!',
    one_fifty: '150', double_century: 'Double Century', five_fer: 'Five Wicket Haul',
    ten_wicket_haul: 'Ten Wickets in the Match', almanack_record: 'Almanack Record',
    world_record: 'Real World Record Beaten', over_complete: 'Over Complete',
  };
  const displayLabel = typeLabels[graphic_type] || graphic_type;

  content.innerHTML = `
    <div class="demo-graphic-stage">
      <div class="demo-graphic-stage-title">${escHtml(displayLabel)}</div>
      <div class="demo-graphic-stage-sub">Broadcast graphic</div>
      <div class="demo-graphic-stage-hint">▲ Playing above — same code as a real match</div>
    </div>`;

  // Map demo scene data to GraphicQueue format and enqueue
  const gfx = _mapDemoDataToGraphic(graphic_type, data);
  if (gfx) {
    GraphicQueue.clear();
    GraphicQueue.add(gfx);
  }
}

function _mapDemoDataToGraphic(type, d) {
  switch (type) {
    case 'wicket':
      return { type: 'wicket', batterName: d.batterName, bowlerName: d.bowlerName,
        runs: d.runs, balls: d.balls, dismissalType: d.dismissalType,
        wicketNum: d.wicketNumber, fowScore: d.fowScore };
    case 'duck':
      return { type: 'duck', batterName: d.batterName, bowlerName: d.bowlerName,
        balls: d.balls, dismissalType: d.dismissalType };
    case 'fifty':
      return { type: 'fifty', playerName: d.playerName, teamName: d.teamName,
        runs: d.runs, balls: d.balls, matchContext: d.matchContext };
    case 'century':
      return { type: 'century', playerName: d.playerName, teamName: d.teamName,
        runs: d.runs, balls: d.balls, matchContext: d.matchContext };
    case 'double_century':
      return { type: 'double_century', playerName: d.playerName, teamName: d.teamName,
        runs: d.runs, balls: d.balls, matchContext: d.matchContext };
    case 'five_fer':
      return { type: 'five_fer', playerName: d.playerName, teamName: d.teamName,
        figures: `${d.wickets}/${d.runs}`, overs: d.overs, econ: String(d.economy) };
    case 'ten_wicket_haul':
      return { type: 'ten_wicket', playerName: d.playerName, teamName: d.teamName,
        figures: d.totalFigures };
    case 'almanack_record':
      return { type: 'almanack_record', typeLabel: d.recordLabel, newValue: d.newValue,
        playerName: d.holderName, previousValue: d.previousValue, previousHolder: d.previousHolder };
    case 'world_record':
      return { type: 'world_record', typeLabel: d.recordLabel, newValue: d.newValue,
        playerName: d.holderName, worldRecord: d.realWorldValue, worldRecordHolder: d.realWorldHolder };
    case 'over_complete': {
      const parts = (d.figures || '0-0-0-0').split('-');
      return { type: 'over_complete', overNumber: d.overNumber, bowlerName: d.bowlerName,
        wickets: parseInt(parts[3]||0), maidens: parseInt(parts[1]||0), runs: parseInt(parts[2]||0),
        teamScore: d.teamScore, rr: d.currentRR, rrr: d.requiredRR };
    }
    default: return null;
  }
}

function _renderDemoInningsBreak(d, content) {
  content.innerHTML = `
    <div class="demo-innings-card">
      <div class="ibg-batting-team">${renderTeamLabel(d.battingTeam, { compact: true })}</div>
      <div class="ibg-score">${escHtml(d.score)}</div>
      <div class="ibg-overs">${escHtml(d.overs)} overs</div>
      <div class="ibg-target-row">
        <div class="ibg-target">Target: <strong>${d.target}</strong></div>
        <div class="ibg-rrr">Required RR: ${escHtml(d.requiredRR)} from ${escHtml(d.oversAvailable)} overs</div>
      </div>
      <div class="ibg-stat-row">
        <div>Top Scorer: <span>${escHtml(d.topScorer)}</span></div>
        <div>Best Bowling: <span>${escHtml(d.bestBowling)}</span></div>
      </div>
    </div>`;
}

function _renderDemoMatchResult(d, content) {
  content.innerHTML = `
    <div class="demo-result-card">
      <div class="result-header">
        <div class="result-winner">${renderTeamLabel(d.winnerName, { compact: true })} WIN</div>
        <div class="result-margin">${escHtml(d.resultText)}</div>
      </div>
      <div class="result-scores">
        <div class="result-score-line">${escHtml(d.score1)}</div>
        <div class="result-score-line">${escHtml(d.score2)}</div>
      </div>
      <div class="result-pom">Player of the Match: <strong>${escHtml(d.playerOfMatch)}</strong> — ${escHtml(d.pomDetail)}</div>
    </div>`;
}

function renderDemoAlmanack(data) {
  const content = document.getElementById('demo-content');
  if (!content) return;

  const statsHtml = (data.stats || []).map(s => `
    <div class="demo-alm-stat">
      <div class="demo-alm-stat-value">${escHtml(s.value)}</div>
      <div class="demo-alm-stat-label">${escHtml(s.label)}</div>
    </div>`).join('');

  const yr = new Date().getFullYear();
  content.innerHTML = `
    <div class="demo-almanack-preview">
      <div class="alm-masthead">
        <div class="alm-masthead-rule"><span class="alm-masthead-rule-inner">══════════════</span></div>
        <h2 class="alm-masthead-title">The Dice Cricketers&#8217; Almanack</h2>
        <div class="alm-masthead-rule"><span class="alm-masthead-rule-inner">══════════════</span></div>
        <p class="alm-masthead-sub">${escHtml(data.subtitle)}</p>
        <div class="alm-masthead-footer">
          <span class="alm-masthead-volume">Volume I</span>
          <span class="alm-masthead-est">Est. ${yr}</span>
        </div>
      </div>
      <div class="demo-alm-stats">${statsHtml}</div>
    </div>`;
}

function renderDemoFeatureCard(data) {
  const content = document.getElementById('demo-content');
  if (!content) return;

  const featuresHtml = (data.features || []).map(f => `
    <div class="demo-fc-item">
      <span class="demo-fc-icon">${f.icon}</span>
      <div class="demo-fc-title">${escHtml(f.title)}</div>
      <div class="demo-fc-desc">${escHtml(f.description)}</div>
    </div>`).join('');

  content.innerHTML = `
    <div class="demo-feature-card">
      <h2 class="demo-fc-headline">${escHtml(data.headline)}</h2>
      <div class="demo-fc-grid">${featuresHtml}</div>
    </div>`;
}

// ── DOMContentLoaded ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  initNav();
  initKeyboard();
  SoundEngine.init();
  updateSessionBar();

  // Restore animation speed from localStorage
  try {
    const saved = localStorage.getItem('ribi_anim_speed');
    if (saved && ['normal', 'fast', 'instant'].includes(saved)) {
      AppState.animationSpeed = saved;
    }
  } catch (_) {}

  // Restore user preferences from localStorage
  try {
    const darkSaved = localStorage.getItem('ribi_dark_mode');
    if (darkSaved !== null) {
      AppState.darkMode = darkSaved !== '0';
      document.body.classList.toggle('light-mode', !AppState.darkMode);
    }
    const soundSaved = localStorage.getItem('ribi_sound');
    if (soundSaved !== null) {
      AppState.soundEnabled = soundSaved !== '0';
    }
    const broadcastSaved = localStorage.getItem('ribi_broadcast');
    if (broadcastSaved === '1') {
      AppState.broadcastMode = true;
      document.body.classList.add('broadcast-mode');
    }
    const fmtSaved = localStorage.getItem('ribi_default_format');
    if (fmtSaved && ['Test', 'ODI', 'T20'].includes(fmtSaved)) {
      AppState.defaultFormat = fmtSaved;
    }
    const scoringSaved = localStorage.getItem('ribi_default_scoring_mode');
    if (scoringSaved && ['classic', 'modern'].includes(scoringSaved)) {
      AppState.defaultScoringMode = scoringSaved;
    }
    const venueSaved = localStorage.getItem('ribi_default_venue');
    if (venueSaved) {
      AppState.defaultVenueId = parseInt(venueSaved) || null;
    }
    const recPopupSaved = localStorage.getItem('ribi_record_popups');
    if (recPopupSaved !== null) {
      AppState.recordPopups = recPopupSaved === '1';
    }
  } catch (_) {}

  // First-launch disclaimer check
  try {
    const accepted = localStorage.getItem('ribi_disclaimer_accepted');
    if (!accepted) {
      showDisclaimerModal(false);
    }
  } catch (_) {}

  // First-run welcome check
  let showWelcome = false;
  try {
    const welcomed = localStorage.getItem('ribi_welcomed');
    if (!welcomed) {
      const health = await fetch('/api/health').then(r => r.json()).catch(() => null);
      if (health && health.tables && health.tables.matches === 0) {
        showWelcome = true;
      }
    }
  } catch (_) {}

  // Hash routing for demo modes
  if (location.hash === '#demo') {
    history.replaceState(null, '', location.pathname);
    showScreen(showWelcome ? 'welcome' : 'home');
    DemoMode.start(true);
  } else if (location.hash === '#demo-screenshot') {
    history.replaceState(null, '', location.pathname);
    showScreen(showWelcome ? 'welcome' : 'home');
    DemoMode.startScreenshotMode();
  } else {
    showScreen(showWelcome ? 'welcome' : 'home');
  }

  // hashchange for demo (e.g. shared link opened while app already loaded)
  window.addEventListener('hashchange', () => {
    if (location.hash === '#demo') {
      history.replaceState(null, '', location.pathname);
      DemoMode.start(true);
    } else if (location.hash === '#demo-screenshot') {
      history.replaceState(null, '', location.pathname);
      DemoMode.startScreenshotMode();
    }
  });
});
