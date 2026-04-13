// ── Bird-chirp audio (Web Audio API, no external files) ──────────────────────
const AudioCtx = window.AudioContext || window.webkitAudioContext;
let _audioCtx = null;

/**
 * chirp(startHz, endHz, dur, vol)
 * Single frequency-sweep oscillator — sounds like a bird syllable.
 */
function chirp(startHz, endHz, dur = 0.08, vol = 0.28) {
  try {
    if (!_audioCtx) _audioCtx = new AudioCtx();
    const osc  = _audioCtx.createOscillator();
    const gain = _audioCtx.createGain();
    osc.connect(gain);
    gain.connect(_audioCtx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(startHz, _audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(endHz, _audioCtx.currentTime + dur);
    gain.gain.setValueAtTime(vol, _audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, _audioCtx.currentTime + dur);
    osc.start(_audioCtx.currentTime);
    osc.stop(_audioCtx.currentTime + dur + 0.01);
  } catch (_) {}
}

function alertSound(t) {
  if (t === 'OPEN_DRIVE_ENTRY') {
    chirp(1100, 2000, 0.09);
  } else if (t === 'SPIKE_BREAKOUT') {
    chirp(750, 1600, 0.09);
  } else if (t === 'ABSORPTION') {
    chirp(1300, 800, 0.10);
  } else if (t === 'EXHAUSTION_REVERSAL') {
    chirp(650, 1450, 0.10);
  } else if (t === 'DRIVE_FAILED') {
    chirp(1400, 500, 0.14);
  } else if (t === 'EXIT') {
    chirp(1000, 600, 0.12);
  } else if (t === 'FADE_ALERT') {
    chirp(1100, 750, 0.09);
  } else if (t === 'ORB_BREAKOUT' || t === 'RANGE_BREAKOUT' || t === 'WEEK52_BREAKOUT'
             || t === 'PDH_BREAKOUT' || t === 'VWAP_BREAKOUT') {
    chirp(900, 1800, 0.09);           // ascending sweep — upside breakout
  } else if (t === 'ORB_BREAKDOWN' || t === 'RANGE_BREAKDOWN' || t === 'WEEK52_BREAKDOWN'
             || t === 'PDL_BREAKDOWN' || t === 'VWAP_BREAKDOWN') {
    chirp(1700, 700, 0.09);           // descending sweep — downside breakdown
  } else if (t === 'CAM_H3_REVERSAL' || t === 'CAM_L3_REVERSAL') {
    chirp(1000, 1300, 0.07);          // short uptick — reversal watch
  } else if (t === 'CAM_H4_BREAKOUT') {
    chirp(850, 1700, 0.09);
  } else if (t === 'CAM_L4_BREAKDOWN') {
    chirp(1600, 650, 0.09);
  }
}

// Unlock audio context on first user interaction (browser autoplay policy).
document.addEventListener('click', () => {
  if (!_audioCtx) _audioCtx = new AudioCtx();
  _audioCtx.resume();
}, { once: true });

// ── Alpine component ──────────────────────────────────────────────────────────
function cockpit() {
  return {
    // ── Live feed state ─────────────────────────────────────────────────────
    signals:      [],
    pending:      [],
    paused:       false,
    filter:       'ALL',
    minValue:     0,
    clock:        '--:--:--',
    phase:        '--',
    connState:    'connecting',
    bias:         { nifty: 'NEUTRAL', banknifty: 'NEUTRAL', sensex: 'NEUTRAL' },
    metricsCache: {},

    // ── History review state ─────────────────────────────────────────────────
    historyMode:    false,
    historyDate:    new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }),
    historySignals: [],
    historyDates:   [],
    historyLoading: false,

    // ── Notes (persisted in localStorage, keyed by signal.id) ────────────────
    notes:       {},   // id → saved text
    noteDrafts:  {},   // id → in-progress edit
    noteEditing: {},   // id → bool

    valueTiers: [
      { label: 'All',    cr: 0   },
      { label: '5Cr+',   cr: 5   },
      { label: '25Cr+',  cr: 25  },
      { label: '100Cr+', cr: 100 },
      { label: '500Cr+', cr: 500 },
    ],

    tabs: [
      { key: 'ALL',     label: 'ALL',        activeClass: 'bg-subtle border-[#58a6ff] text-[#e6edf3]' },
      { key: 'DRIVE',   label: 'DRIVE',      activeClass: 'bg-[#1a2d1a] border-[#3fb950] text-[#3fb950]' },
      { key: 'SPIKE',   label: 'SPIKE',      activeClass: 'bg-[#2d2118] border-[#d29922] text-[#d29922]' },
      { key: 'ABS',     label: 'ABSORPTION', activeClass: 'bg-[#1a2233] border-[#58a6ff] text-[#58a6ff]' },
      { key: 'EXHAUST', label: 'EXHAUST',    activeClass: 'bg-[#211a2d] border-[#a371f7] text-[#a371f7]' },
      { key: 'FADE',    label: 'FADE',       activeClass: 'bg-[#2d2800] border-[#e3b341] text-[#e3b341]' },
      { key: 'BREAK',   label: 'BREAKOUT',   activeClass: 'bg-[#1a2d20] border-[#39d353] text-[#39d353]' },
      { key: 'VWAP',    label: 'VWAP',       activeClass: 'bg-[#1a2533] border-[#79c0ff] text-[#79c0ff]' },
      { key: 'CAM',     label: 'CAMARILLA',  activeClass: 'bg-[#2d1f2f] border-[#d2a8ff] text-[#d2a8ff]' },
    ],

    PHASE_COLORS: {
      DRIVE_WINDOW:   { bg: '#1f2d1f', color: '#3fb950' },
      EXECUTION:      { bg: '#1a2d1a', color: '#2ea043' },
      CLOSE_MOMENTUM: { bg: '#1e2840', color: '#58a6ff' },
      SESSION_END:    { bg: '#2d1818', color: '#f85149' },
      DEAD_ZONE:      { bg: '#2d2118', color: '#d29922' },
    },

    get filteredSignals() {
      const typeMap = {
        DRIVE:   ['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT', 'TRAIL_UPDATE'],
        SPIKE:   ['SPIKE_BREAKOUT'],
        ABS:     ['ABSORPTION'],
        EXHAUST: ['EXHAUSTION_REVERSAL'],
        FADE:    ['FADE_ALERT'],
        BREAK:   ['ORB_BREAKOUT', 'ORB_BREAKDOWN', 'RANGE_BREAKOUT', 'RANGE_BREAKDOWN',
                  'WEEK52_BREAKOUT', 'WEEK52_BREAKDOWN', 'PDH_BREAKOUT', 'PDL_BREAKDOWN'],
        VWAP:    ['VWAP_BREAKOUT', 'VWAP_BREAKDOWN'],
        CAM:     ['CAM_H3_REVERSAL', 'CAM_H4_BREAKOUT', 'CAM_L3_REVERSAL', 'CAM_L4_BREAKDOWN'],
      };
      return this.signals.filter(s => {
        if (this.filter !== 'ALL' && !(typeMap[this.filter] || []).includes(s.signal_type)) return false;
        if (this.minValue > 0) {
          const m = this.metricsCache[s.symbol];
          if (m && m.adv_20_cr < this.minValue) return false;
        }
        return true;
      }).sort((a, b) => (b.score || 0) - (a.score || 0));
    },

    get filteredHistory() {
      const typeMap = {
        DRIVE:   ['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT', 'TRAIL_UPDATE'],
        SPIKE:   ['SPIKE_BREAKOUT'],
        ABS:     ['ABSORPTION'],
        EXHAUST: ['EXHAUSTION_REVERSAL'],
        FADE:    ['FADE_ALERT'],
        BREAK:   ['ORB_BREAKOUT', 'ORB_BREAKDOWN', 'RANGE_BREAKOUT', 'RANGE_BREAKDOWN',
                  'WEEK52_BREAKOUT', 'WEEK52_BREAKDOWN', 'PDH_BREAKOUT', 'PDL_BREAKDOWN'],
        VWAP:    ['VWAP_BREAKOUT', 'VWAP_BREAKDOWN'],
        CAM:     ['CAM_H3_REVERSAL', 'CAM_H4_BREAKOUT', 'CAM_L3_REVERSAL', 'CAM_L4_BREAKDOWN'],
      };
      // History is chronological (oldest first); sort by score descending.
      return [...this.historySignals].filter(s => {
        if (this.filter !== 'ALL' && !(typeMap[this.filter] || []).includes(s.signal_type)) return false;
        if (this.minValue > 0) {
          const m = this.metricsCache[s.symbol];
          if (m && m.adv_20_cr < this.minValue) return false;
        }
        return true;
      }).sort((a, b) => (b.score || 0) - (a.score || 0));
    },

    // ── Lifecycle ────────────────────────────────────────────────────────────

    init() {
      this.startClock();
      this.pollStatus();
      setInterval(() => this.pollStatus(), 10_000);
      this.connect();
      this.loadHistoryDates();
      this._loadNotes();
    },

    startClock() {
      const tick = () => {
        const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
        this.clock = ist.toTimeString().slice(0, 8);
      };
      tick();
      setInterval(tick, 1000);
    },

    async pollStatus() {
      try {
        const r = await fetch('/api/v1/status');
        if (!r.ok) return;
        const d = await r.json();
        if (d.session_phase) this.phase = d.session_phase;
        if (d.index_bias) {
          this.bias.nifty     = d.index_bias.nifty     || 'NEUTRAL';
          this.bias.banknifty = d.index_bias.banknifty || 'NEUTRAL';
          this.bias.sensex    = d.index_bias.sensex     || 'NEUTRAL';
        }
      } catch (_) {}
    },

    connect() {
      const src = new EventSource('/api/v1/signals/stream');
      src.onopen    = () => { this.connState = 'connected'; };
      src.onmessage = (e) => {
        try { this.addSignal(JSON.parse(e.data)); } catch (_) {}
      };
      src.onerror   = () => {
        this.connState = 'disconnected';
        src.close();
        setTimeout(() => { this.connState = 'connecting'; this.connect(); }, 3000);
      };
    },

    // ── History ──────────────────────────────────────────────────────────────

    async loadHistoryDates() {
      try {
        const r = await fetch('/api/v1/signals/history/dates');
        if (r.ok) {
          const d = await r.json();
          this.historyDates = d.dates;
        }
      } catch (_) {}
    },

    async loadHistory() {
      this.historyLoading = true;
      this.historySignals = [];
      try {
        const r = await fetch(`/api/v1/signals/history?date=${this.historyDate}`);
        if (r.ok) {
          const d = await r.json();
          this.historySignals = d.signals;
          this.historyDates   = d.available_dates;
          // Prefetch metrics for all distinct symbols in history.
          const syms = [...new Set(d.signals.map(s => s.symbol))];
          syms.forEach(sym => { if (!this.metricsCache[sym]) this.fetchMetrics(sym); });
        }
      } catch (_) {}
      this.historyLoading = false;
    },

    toggleHistory() {
      this.historyMode = !this.historyMode;
      if (this.historyMode && this.historySignals.length === 0) this.loadHistory();
    },

    // ── Signal ingestion ─────────────────────────────────────────────────────

    addSignal(s) {
      if (this.paused) { this.pending.push(s); return; }
      this.pushSignal(s);
    },

    pushSignal(s) {
      if (!s.id) s.id = `${s.symbol}-${s.signal_type}-${s.timestamp}`;

      const isCatchup = !!s._catchup;

      // Catch-up signals: historical context — no sound, no blink.
      // Use the same _dedupKey logic as live so that:
      //   a) multiple catch-up events for the same symbol:type collapse into one card,
      //   b) the first live signal for that type correctly finds and updates it.
      if (isCatchup) {
        const ALWAYS_NEW_CU = new Set(['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT']);

        if (!ALWAYS_NEW_CU.has(s.signal_type)) {
          const key = `${s.symbol}:${s.signal_type}`;
          const idx = this.signals.findIndex(x => x._dedupKey === key);
          if (idx !== -1) {
            // Update existing card with fresher data; do not increment count.
            const existing = this.signals[idx];
            existing.timestamp    = s.timestamp;
            existing.price        = s.price;
            existing.message      = s.message;
            existing.volume_ratio = s.volume_ratio;
            existing.trail_stop   = s.trail_stop;
            this.signals = [existing, ...this.signals.filter((_, i) => i !== idx)];
            return;
          }
          s._dedupKey = key;
        }

        if (!this.signals.some(x => x.id === s.id)) {
          s._count       = 1;
          s._fromCatchup = true;   // first live dedup will promote without incrementing
          this.signals.unshift(s);
          if (this.signals.length > 200) this.signals.pop();
          if (!this.metricsCache[s.symbol]) this.fetchMetrics(s.symbol);
        }
        return;
      }

      // Live signal: dedup by symbol:type, alert, move to top.
      const ALWAYS_NEW = new Set(['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT']);

      if (!ALWAYS_NEW.has(s.signal_type)) {
        const key = `${s.symbol}:${s.signal_type}`;
        const idx = this.signals.findIndex(x => x._dedupKey === key);
        if (idx !== -1) {
          const existing = this.signals[idx];
          existing.timestamp    = s.timestamp;
          existing.price        = s.price;
          existing.message      = s.message;
          existing.volume_ratio = s.volume_ratio;
          existing.trail_stop   = s.trail_stop;
          if (existing._fromCatchup) {
            // First live signal for this type — promote the catch-up card, don't count yet.
            existing._fromCatchup = false;
          } else {
            existing._count = existing._count + 1;
          }
          this.signals = [existing, ...this.signals.filter((_, i) => i !== idx)];
          alertSound(s.signal_type);
          if (document.hidden) this.blinkTab(s.symbol);
          return;
        }
        s._dedupKey = key;
      }

      s._count = 1;
      this.signals.unshift(s);
      if (this.signals.length > 200) this.signals.pop();
      alertSound(s.signal_type);
      if (document.hidden) this.blinkTab(s.symbol);
      if (!this.metricsCache[s.symbol]) this.fetchMetrics(s.symbol);
    },

    async fetchMetrics(symbol) {
      this.metricsCache[symbol] = null;   // sentinel: loading
      try {
        const r = await fetch(`/api/v1/instrument/${encodeURIComponent(symbol)}/metrics`);
        if (r.ok) this.metricsCache[symbol] = await r.json();
      } catch (_) {}
    },

    togglePause() {
      this.paused = !this.paused;
      if (!this.paused && this.pending.length > 0) {
        this.pending.forEach(s => this.pushSignal(s));
        this.pending = [];
      }
    },

    setFilter(f) { this.filter = f; },

    // ── Notes ────────────────────────────────────────────────────────────────

    _loadNotes() {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith('cockpit:note:')) {
          const id = k.slice('cockpit:note:'.length);
          this.notes = { ...this.notes, [id]: localStorage.getItem(k) };
        }
      }
    },

    startEditNote(id) {
      this.noteDrafts  = { ...this.noteDrafts,  [id]: this.notes[id] || '' };
      this.noteEditing = { ...this.noteEditing, [id]: true };
    },

    commitNote(id) {
      const text = (this.noteDrafts[id] || '').trim();
      if (text) {
        this.notes = { ...this.notes, [id]: text };
        localStorage.setItem(`cockpit:note:${id}`, text);
      } else {
        const n = { ...this.notes };
        delete n[id];
        this.notes = n;
        localStorage.removeItem(`cockpit:note:${id}`);
      }
      this.noteEditing = { ...this.noteEditing, [id]: false };
    },

    cancelNote(id) {
      this.noteEditing = { ...this.noteEditing, [id]: false };
    },

    blinkTab(symbol) {
      const orig = document.title;
      let n = 0;
      const iv = setInterval(() => {
        document.title = n++ % 2 === 0 ? `⚡ ${symbol}` : orig;
        if (n > 8) { clearInterval(iv); document.title = orig; }
      }, 600);
    },

    // ── Template helpers ─────────────────────────────────────────────────────

    fmt(v) { return v != null ? Number(v).toFixed(2) : ''; },

    timeStr(iso) {
      if (!iso) return '';
      const aware = /Z$|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + 'Z';
      const d = new Date(aware);
      if (isNaN(d)) return '??:??';
      return d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
    },

    shortType(t) {
      return {
        OPEN_DRIVE_ENTRY:    'DRIVE',
        SPIKE_BREAKOUT:      'SPIKE',
        ABSORPTION:          'ABS',
        EXHAUSTION_REVERSAL: 'EXHAUST',
        TRAIL_UPDATE:        'TRAIL',
        DRIVE_FAILED:        'FAILED',
        EXIT:                'EXIT',
        FADE_ALERT:          'FADE',
        ORB_BREAKOUT:        'ORB↑',
        ORB_BREAKDOWN:       'ORB↓',
        RANGE_BREAKOUT:      'RNG↑',
        RANGE_BREAKDOWN:     'RNG↓',
        WEEK52_BREAKOUT:     '52W↑',
        WEEK52_BREAKDOWN:    '52W↓',
        PDH_BREAKOUT:        'PDH↑',
        PDL_BREAKDOWN:       'PDL↓',
        VWAP_BREAKOUT:       'VWAP↑',
        VWAP_BREAKDOWN:      'VWAP↓',
        CAM_H3_REVERSAL:     'CAM H3',
        CAM_H4_BREAKOUT:     'CAM H4↑',
        CAM_L3_REVERSAL:     'CAM L3',
        CAM_L4_BREAKDOWN:    'CAM L4↓',
      }[t] || t;
    },

    pct(value, reference) {
      if (!reference) return '';
      return ((value - reference) / reference * 100).toFixed(1) + '%';
    },

    // Signed percent with explicit + sign and color helper
    spct(value, reference) {
      if (!reference) return '';
      const p = (value - reference) / reference * 100;
      return (p >= 0 ? '+' : '') + p.toFixed(1) + '%';
    },

    pctColor(value, reference) {
      if (!reference) return '#8b949e';
      const p = (value - reference) / reference * 100;
      return p > 0 ? '#3fb950' : p < 0 ? '#f85149' : '#8b949e';
    },

    // ── Colour palette ───────────────────────────────────────────────────────

    signalColor(t) {
      return {
        OPEN_DRIVE_ENTRY:    '#3fb950',
        SPIKE_BREAKOUT:      '#d29922',
        ABSORPTION:          '#58a6ff',
        EXHAUSTION_REVERSAL: '#a371f7',
        TRAIL_UPDATE:        '#8b949e',
        DRIVE_FAILED:        '#f85149',
        EXIT:                '#f85149',
        FADE_ALERT:          '#e3b341',
        ORB_BREAKOUT:        '#39d353',
        ORB_BREAKDOWN:       '#ff7b72',
        RANGE_BREAKOUT:      '#56d364',
        RANGE_BREAKDOWN:     '#ff7b72',
        WEEK52_BREAKOUT:     '#2ea043',
        WEEK52_BREAKDOWN:    '#da3633',
        PDH_BREAKOUT:        '#4ac26b',
        PDL_BREAKDOWN:       '#f85149',
        VWAP_BREAKOUT:       '#79c0ff',
        VWAP_BREAKDOWN:      '#ff9bce',
        CAM_H3_REVERSAL:     '#d2a8ff',
        CAM_H4_BREAKOUT:     '#bc8cff',
        CAM_L3_REVERSAL:     '#d2a8ff',
        CAM_L4_BREAKDOWN:    '#bc8cff',
      }[t] || '#30363d';
    },

    dirColor(dir) {
      return { BULLISH: '#3fb950', BEARISH: '#f85149', NEUTRAL: '#8b949e' }[dir] || '#8b949e';
    },

    cardStyle(t) {
      const tint = {
        OPEN_DRIVE_ENTRY:    'rgba(63,185,80,0.06)',
        SPIKE_BREAKOUT:      'rgba(210,153,34,0.06)',
        ABSORPTION:          'rgba(88,166,255,0.06)',
        EXHAUSTION_REVERSAL: 'rgba(163,113,247,0.06)',
        DRIVE_FAILED:        'rgba(248,81,73,0.06)',
        EXIT:                'rgba(248,81,73,0.06)',
        FADE_ALERT:          'rgba(227,179,65,0.06)',
        ORB_BREAKOUT:        'rgba(57,211,83,0.06)',
        ORB_BREAKDOWN:       'rgba(255,123,114,0.06)',
        RANGE_BREAKOUT:      'rgba(86,211,100,0.06)',
        RANGE_BREAKDOWN:     'rgba(255,123,114,0.06)',
        WEEK52_BREAKOUT:     'rgba(46,160,67,0.08)',
        WEEK52_BREAKDOWN:    'rgba(218,54,51,0.08)',
        PDH_BREAKOUT:        'rgba(74,194,107,0.06)',
        PDL_BREAKDOWN:       'rgba(248,81,73,0.06)',
        VWAP_BREAKOUT:       'rgba(121,192,255,0.06)',
        VWAP_BREAKDOWN:      'rgba(255,155,206,0.06)',
        CAM_H3_REVERSAL:     'rgba(210,168,255,0.06)',
        CAM_H4_BREAKOUT:     'rgba(188,140,255,0.06)',
        CAM_L3_REVERSAL:     'rgba(210,168,255,0.06)',
        CAM_L4_BREAKDOWN:    'rgba(188,140,255,0.06)',
      }[t] || 'transparent';
      return `background:${tint}`;
    },

    typeStyle(t) {
      const c = this.signalColor(t);
      return `color:${c};background:${c}18;`;
    },

    signalDesc(t) {
      return {
        OPEN_DRIVE_ENTRY:    'Strong open drive — ride the momentum',
        SPIKE_BREAKOUT:      'Volume shock breakout — watch for follow-through',
        ABSORPTION:          'Big vol, flat price — supply/demand absorbing',
        EXHAUSTION_REVERSAL: 'Downtrend climax held — bounce reversal setup',
        TRAIL_UPDATE:        'Trailing stop moved up',
        DRIVE_FAILED:        'Drive failed — price back through open',
        EXIT:                'Position exited',
        FADE_ALERT:          'Big move, no volume — likely to fade/reverse',
        ORB_BREAKOUT:        'Closed above opening range high on volume',
        ORB_BREAKDOWN:       'Closed below opening range low on volume',
        RANGE_BREAKOUT:      '5-candle consolidation broken upward on volume',
        RANGE_BREAKDOWN:     '5-candle consolidation broken downward on volume',
        WEEK52_BREAKOUT:     '52-week high breakout on 2× volume',
        WEEK52_BREAKDOWN:    '52-week low breakdown on 2× volume',
        PDH_BREAKOUT:        'Closed above previous day high on volume',
        PDL_BREAKDOWN:       'Closed below previous day low on volume',
        VWAP_BREAKOUT:       'Price crossed above VWAP on volume — intraday bull',
        VWAP_BREAKDOWN:      'Price crossed below VWAP on volume — intraday bear',
        CAM_H3_REVERSAL:     'Rejected at Camarilla H3 — fade short setup',
        CAM_H4_BREAKOUT:     'Broke above Camarilla H4 — momentum long',
        CAM_L3_REVERSAL:     'Bounced off Camarilla L3 — fade long setup',
        CAM_L4_BREAKDOWN:    'Broke below Camarilla L4 — momentum short',
      }[t] || '';
    },

    phaseBadgeStyle() {
      const c = this.PHASE_COLORS[this.phase];
      return c
        ? `background:${c.bg};color:${c.color}`
        : 'background:#21262d;color:#8b949e';
    },
  };
}
