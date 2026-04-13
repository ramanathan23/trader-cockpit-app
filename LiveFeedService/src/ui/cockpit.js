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
    // Robin-style ascending triple chirp — confident breakout
    chirp(900, 1700, 0.07);
    setTimeout(() => chirp(1100, 1900, 0.07), 110);
    setTimeout(() => chirp(1300, 2100, 0.07), 220);
  } else if (t === 'SPIKE_BREAKOUT') {
    // Sharp single ascending tweet
    chirp(700, 1500, 0.09);
    setTimeout(() => chirp(1000, 1700, 0.06), 130);
  } else if (t === 'ABSORPTION') {
    // Gentle warble — descending then settling
    chirp(1300, 900, 0.10);
    setTimeout(() => chirp(950, 1100, 0.08), 140);
  } else if (t === 'EXHAUSTION_REVERSAL') {
    // Rising double chirp — reversal alert
    chirp(650, 1250, 0.09);
    setTimeout(() => chirp(850, 1500, 0.09), 140);
    setTimeout(() => chirp(1050, 1700, 0.07), 280);
  } else if (t === 'DRIVE_FAILED') {
    // Descending drooping chirp — warning
    chirp(1400, 600, 0.14);
    setTimeout(() => chirp(1000, 500, 0.10), 180);
  } else if (t === 'EXIT') {
    // Single falling note
    chirp(1100, 650, 0.12);
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
      };
      return this.signals.filter(s => {
        if (this.filter !== 'ALL' && !(typeMap[this.filter] || []).includes(s.signal_type)) return false;
        if (this.minValue > 0) {
          const m = this.metricsCache[s.symbol];
          if (m && m.adv_20_cr < this.minValue) return false;
        }
        return true;
      });
    },

    get filteredHistory() {
      const typeMap = {
        DRIVE:   ['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT', 'TRAIL_UPDATE'],
        SPIKE:   ['SPIKE_BREAKOUT'],
        ABS:     ['ABSORPTION'],
        EXHAUST: ['EXHAUSTION_REVERSAL'],
      };
      // History is chronological (oldest first); reverse for newest-first display.
      return [...this.historySignals].reverse().filter(s => {
        if (this.filter !== 'ALL' && !(typeMap[this.filter] || []).includes(s.signal_type)) return false;
        if (this.minValue > 0) {
          const m = this.metricsCache[s.symbol];
          if (m && m.adv_20_cr < this.minValue) return false;
        }
        return true;
      });
    },

    // ── Lifecycle ────────────────────────────────────────────────────────────

    init() {
      this.startClock();
      this.pollStatus();
      setInterval(() => this.pollStatus(), 10_000);
      this.connect();
      this.loadHistoryDates();
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

      // Catch-up signals: historical context — no dedup, no sound, no blink.
      // Server sends oldest-first; unshift each so newest ends at index 0.
      if (isCatchup) {
        if (!this.signals.some(x => x.id === s.id)) {
          s._count = 1;
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
          existing._count       = (existing._count || 1) + 1;
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
      }[t] || t;
    },

    pct(value, reference) {
      if (!reference) return '';
      return ((value - reference) / reference * 100).toFixed(1) + '%';
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
