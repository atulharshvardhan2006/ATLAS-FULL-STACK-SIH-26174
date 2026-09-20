import React, { useEffect, useState, memo } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';

// ─── Types ───────────────────────────────────────────────────────────────────

interface SensorState {
  altitude: number;       // km
  velocity: number;       // km/s
  tiltBeta: number;       // front-back degrees
  tiltGamma: number;      // left-right degrees
  o2Level: number;        // percentage
  waterLevel: number;     // percentage
  foodSupply: number;     // days remaining
  sensorsAvailable: boolean;
}

// ─── Telemetry Card (memoized) ───────────────────────────────────────────────

const TelemetryCard = memo(({ 
  label, 
  sublabel, 
  value, 
  unit, 
  status, 
  barPercent,
  barColor
}: { 
  label: string; 
  sublabel: string; 
  value: string; 
  unit: string; 
  status: 'nominal' | 'warning' | 'critical';
  barPercent?: number;
  barColor?: string;
}) => {
  const statusColor = status === 'nominal' ? 'text-status-green' 
    : status === 'warning' ? 'text-status-amber' 
    : 'text-status-red';
  
  const statusLabel = status === 'nominal' ? 'NOMINAL' 
    : status === 'warning' ? 'WARNING' 
    : 'CRITICAL';

  const statusDot = status === 'nominal' ? 'bg-status-green' 
    : status === 'warning' ? 'bg-status-amber' 
    : 'bg-status-red';

  return (
    <Card title={label} className="p-3">
      <div className="text-sm space-y-3 lowercase">
        <div className="text-xs text-brand-textMuted uppercase tracking-widest">{sublabel}</div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-brand-text font-mono tabular-nums transition-all duration-300">
            {value}
          </span>
          <span className="text-xs text-brand-textMuted">{unit}</span>
        </div>
        
        {barPercent !== undefined && (
          <div className="w-full h-1.5 bg-brand-border rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{ 
                width: `${Math.min(100, Math.max(0, barPercent))}%`,
                backgroundColor: barColor || (status === 'nominal' ? '#548749' : status === 'warning' ? '#A09653' : '#873B3B')
              }}
            />
          </div>
        )}

        <div className="flex justify-between items-center text-xs pt-2 border-t border-brand-border/30">
          <span className="text-brand-textLight">status</span>
          <span className={`flex items-center gap-1.5 ${statusColor}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusDot} ${status !== 'nominal' ? 'animate-pulse' : ''}`} />
            {statusLabel}
          </span>
        </div>
      </div>
    </Card>
  );
});

// ─── Main Station Component ──────────────────────────────────────────────────

export const Station: React.FC = () => {
  const [state, setState] = useState<SensorState>({
    altitude: 0,
    velocity: 0,
    tiltBeta: 0,
    tiltGamma: 0,
    o2Level: 100.0,
    waterLevel: 100.0,
    foodSupply: 180,
    sensorsAvailable: true,
  });

  // ─── Launch → Orbit Telemetry Simulation (60Hz physics) ───────────────────
  // Starts from ground (0 km, 0 km/s) and gradually ramps to ISS orbit.
  // Simulates a realistic launch-to-orbit profile for demo purposes.
  useEffect(() => {
    const startTime = performance.now();
    let frameId: number;

    // Smooth noise generator (multi-harmonic sine approximation of Perlin noise)
    const smoothNoise = (t: number, seed: number) => {
      return Math.sin(t * 0.7 + seed) * 0.4 
           + Math.sin(t * 1.3 + seed * 2.1) * 0.25
           + Math.sin(t * 2.9 + seed * 0.7) * 0.15
           + Math.sin(t * 5.1 + seed * 3.3) * 0.1
           + Math.sin(t * 11.7 + seed * 1.9) * 0.05
           + Math.sin(t * 23.3 + seed * 4.1) * 0.03;
    };

    // Smooth easing function (ease-out cubic)
    const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

    const LAUNCH_DURATION = 520; // ~8.5 minutes to reach orbit (realistic Soyuz/Falcon profile)

    const tick = () => {
      const elapsed = (performance.now() - startTime) / 1000;
      const t = elapsed;

      // Launch progress (0 → 1 over LAUNCH_DURATION seconds)
      const launchProgress = Math.min(1, t / LAUNCH_DURATION);
      const smoothProgress = easeOut(launchProgress);

      // ── Altitude: 0 → 408 km during launch, then orbital oscillation ──
      const targetAlt = 408.0;
      let altitude: number;
      if (launchProgress < 1) {
        altitude = smoothProgress * targetAlt + smoothNoise(t * 0.05, 1.0) * smoothProgress * 0.8;
      } else {
        const orbitTime = t - LAUNCH_DURATION;
        const orbitalPeriod = 92 * 60;
        const orbitPhase = (orbitTime % orbitalPeriod) / orbitalPeriod * Math.PI * 2;
        altitude = targetAlt + Math.sin(orbitPhase) * 1.8 + smoothNoise(orbitTime * 0.01, 1.0) * 0.4;
      }

      // ── Velocity: 0 → 7.66 km/s during launch, then micro-variations ──
      const targetVel = 7.66;
      let velocity: number;
      if (launchProgress < 1) {
        velocity = smoothProgress * targetVel + smoothNoise(t * 0.08, 2.0) * smoothProgress * 0.02;
      } else {
        const orbitTime = t - LAUNCH_DURATION;
        velocity = targetVel + smoothNoise(orbitTime * 0.05, 2.0) * 0.012 + smoothNoise(orbitTime * 0.2, 5.0) * 0.003;
      }

      // ── Tilt: starts at 0° (vertical), pitches during gravity turn, stabilizes in orbit ──
      let tiltBeta: number;
      let tiltGamma: number;
      if (launchProgress < 1) {
        // Gravity turn: pitch increases during ascent
        tiltBeta = smoothProgress * 90 * Math.sin(launchProgress * Math.PI) * 0.02 + smoothNoise(t * 0.1, 3.0) * smoothProgress * 0.8;
        tiltGamma = smoothNoise(t * 0.08, 4.0) * smoothProgress * 0.5;
      } else {
        const orbitTime = t - LAUNCH_DURATION;
        tiltBeta = smoothNoise(orbitTime * 0.08, 3.0) * 1.2 + smoothNoise(orbitTime * 0.4, 7.0) * 0.3;
        tiltGamma = smoothNoise(orbitTime * 0.06, 4.0) * 0.9 + smoothNoise(orbitTime * 0.35, 8.0) * 0.2;
      }

      // ── Life support: starts at 100% and slowly decreases ──
      const o2 = Math.max(18.0, 100.0 - t * 0.015 + smoothNoise(t * 0.003, 5.0) * 0.3);
      const water = Math.max(40, 100.0 - t * 0.005 + smoothNoise(t * 0.002, 6.0) * 0.5);
      const food = Math.max(30, 180 - t * 0.008 + smoothNoise(t * 0.001, 9.0) * 1.0);

      setState({
        altitude: parseFloat(Math.max(0, altitude).toFixed(3)),
        velocity: parseFloat(Math.max(0, velocity).toFixed(4)),
        tiltBeta: parseFloat(tiltBeta.toFixed(2)),
        tiltGamma: parseFloat(tiltGamma.toFixed(2)),
        o2Level: parseFloat(o2.toFixed(2)),
        waterLevel: parseFloat(water.toFixed(1)),
        foodSupply: parseFloat(food.toFixed(0)),
        sensorsAvailable: true,
      });

      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, []);

  // ─── Status Helpers ──────────────────────────────────────────────────────
  const getO2Status = (val: number): 'nominal' | 'warning' | 'critical' => {
    if (val >= 19.5 && val <= 100.0) return 'nominal';
    if (val >= 18.0 && val < 19.5) return 'warning';
    return 'critical';
  };

  const getWaterStatus = (val: number): 'nominal' | 'warning' | 'critical' => {
    if (val >= 60) return 'nominal';
    if (val >= 40) return 'warning';
    return 'critical';
  };

  const getFoodStatus = (val: number): 'nominal' | 'warning' | 'critical' => {
    if (val >= 90) return 'nominal';
    if (val >= 45) return 'warning';
    return 'critical';
  };

  // ─── UTC Clock ───────────────────────────────────────────────────────────
  const [utcTime, setUtcTime] = useState(new Date().toUTCString().slice(17, 25));
  const [utcDate, setUtcDate] = useState(new Date().toISOString().slice(0, 10));
  
  useEffect(() => {
    const clockInterval = setInterval(() => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25));
      setUtcDate(now.toISOString().slice(0, 10));
    }, 1000);
    return () => clearInterval(clockInterval);
  }, []);

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      <PageHeader
        title="station telemetry"
        subtitle="offline monitoring"
        rightContent={
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${state.sensorsAvailable ? 'bg-status-green' : 'bg-status-amber animate-pulse'}`} />
              <span className="text-brand-textMuted uppercase tracking-widest">
                TELEMETRY ACTIVE
              </span>
            </div>
            <div className="text-brand-accent tabular-nums">{utcTime} UTC</div>
          </div>
        }
      />

      {/* Mission Elapsed / UTC Date bar */}
      <div className="flex items-center justify-between mb-8 px-1">
        <div className="flex items-center gap-6 text-xs font-mono text-brand-textMuted uppercase tracking-widest">
          <span>date: <span className="text-brand-text">{utcDate}</span></span>
          <span>source: <span className="text-brand-text">station ics</span></span>
          <span>refresh: <span className="text-brand-text">60 hz</span></span>
        </div>
      </div>

      {/* ─── Telemetry Grid ─── */}
      <div className="grid grid-cols-6 gap-4">

        {/* Row 1: Orbital dynamics */}
        <div className="col-span-2">
          <TelemetryCard
            label="ALTITUDE"
            sublabel="ORBITAL HEIGHT (MEAN SEA LEVEL)"
            value={state.altitude.toFixed(3)}
            unit="km"
            status="nominal"
          />
        </div>

        <div className="col-span-2">
          <TelemetryCard
            label="VELOCITY"
            sublabel="ORBITAL SPEED"
            value={state.velocity.toFixed(4)}
            unit="km/s"
            status={state.velocity > 7.8 ? 'warning' : 'nominal'}
          />
        </div>

        <div className="col-span-2">
          <TelemetryCard
            label="ORIENTATION"
            sublabel="ATTITUDE CONTROL (β PITCH / γ ROLL)"
            value={`β ${state.tiltBeta.toFixed(2)}°  γ ${state.tiltGamma.toFixed(2)}°`}
            unit="deg"
            status={Math.abs(state.tiltBeta) > 90.0 || Math.abs(state.tiltGamma) > 30.0 ? 'warning' : 'nominal'}
          />
        </div>

        {/* Row 2: Life support */}
        <div className="col-span-2">
          <TelemetryCard
            label="O₂ LEVEL"
            sublabel="ATMOSPHERIC PARTIAL PRESSURE"
            value={state.o2Level.toFixed(2)}
            unit="%"
            status={getO2Status(state.o2Level)}
            barPercent={(state.o2Level / 100) * 100}
          />
        </div>

        <div className="col-span-2">
          <TelemetryCard
            label="WATER RESERVES"
            sublabel="POTABLE SUPPLY REMAINING"
            value={state.waterLevel.toFixed(1)}
            unit="%"
            status={getWaterStatus(state.waterLevel)}
            barPercent={state.waterLevel}
          />
        </div>

        <div className="col-span-2">
          <TelemetryCard
            label="FOOD SUPPLY"
            sublabel="CALORIC RESERVES"
            value={Math.floor(state.foodSupply).toString()}
            unit="days"
            status={getFoodStatus(state.foodSupply)}
            barPercent={(state.foodSupply / 180) * 100}
          />
        </div>

      </div>

      {/* ─── Bottom Status Bar ─── */}
      <div className="mt-8 border border-brand-border bg-brand-panel p-4">
        <div className="flex items-center justify-between text-xs font-mono text-brand-textMuted uppercase tracking-widest">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-status-green" />
            <span>all systems operational</span>
          </div>
          <span>a.t.l.a.s station monitor v1.0</span>
          <span>zero ml overhead • offline</span>
        </div>
      </div>
    </div>
  );
};
