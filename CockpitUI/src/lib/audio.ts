// Web Audio API — alert sounds for signal events.
// Browser autoplay policy requires user interaction before audio works.
// Call unlockAudio() on first user click to satisfy browser policy.

let ctx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!ctx) {
    ctx = new (
      window.AudioContext ||
      (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    )!();
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function chirp(startHz: number, endHz: number, dur = 0.08, vol = 0.28): void {
  try {
    const c = getCtx();
    const osc  = c.createOscillator();
    const gain = c.createGain();
    osc.connect(gain);
    gain.connect(c.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(startHz, c.currentTime);
    osc.frequency.linearRampToValueAtTime(endHz, c.currentTime + dur);
    gain.gain.setValueAtTime(vol, c.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur);
    osc.start(c.currentTime);
    osc.stop(c.currentTime + dur + 0.01);
  } catch { /* intentionally silent — never crash on audio */ }
}

export function alertSound(type: string): void {
  if (typeof window === 'undefined') return;
  switch (type) {
    case 'RANGE_BREAKOUT':      return chirp(900,  1800, 0.09);
    case 'RANGE_BREAKDOWN':     return chirp(1700, 700,  0.09);
    case 'CAM_H3_REVERSAL':
    case 'CAM_L3_REVERSAL':     return chirp(1000, 1300, 0.07);
    case 'CAM_H4_BREAKOUT':     return chirp(850,  1700, 0.09);
    case 'CAM_L4_BREAKDOWN':    return chirp(1600, 650,  0.09);
    case 'CAM_H4_REVERSAL':     return chirp(950,  600,  0.09);
    case 'CAM_L4_REVERSAL':     return chirp(650,  1100, 0.09);
  }
}

export function unlockAudio(): void {
  if (typeof window === 'undefined') return;
  try { getCtx(); } catch { /* ignore */ }
}
