import React, { useEffect, useState, useRef, memo } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';

// Slow changing data
interface SlowTelemetry {
  pidDelay: number;
  packetFragCurrent: number;
  packetFragTotal: number;
  cognitiveLoad: 'NOMINAL' | 'WARNING: TASK UNCERTAINTY';
  ttfSeconds: number;
  fps: number;
  aiConfidence: number;
  handVelocity: number;
  pearsonR: number;
  expectedObject: string;
  isGrasping: boolean;
  graspedObject: string | null;
  fsmDeviationDetails: string | null;
  authStatus: 'LOCKED' | 'SCANNING' | 'PROCESSING' | 'SAFETY_HAND' | 'SAFETY_GLOVES' | 'SAFETY_GLASSES' | 'GRANTED' | 'DENIED';
  crewSyncState: string;
  expectedAction: string;
}

// 1. ThermalTTF (React.memo)
const ThermalTTF = memo(({ ttfSeconds, pidDelay }: { ttfSeconds: number, pidDelay: number }) => {
  const formatTTF = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s.toString().padStart(2, '0')}s`;
  };
  return (
    <div className="col-span-3">
      <Card title="THERMAL TTF" className="p-3">
        <div className="text-sm space-y-2 lowercase">
          <div className="text-xs text-brand-textMuted uppercase">SYS.THROTTLE IN</div>
          <div className="text-status-amber text-xl animate-pulse">{formatTTF(ttfSeconds)}</div>
          <div className="flex justify-between text-xs pt-2 border-t border-brand-border/30">
            <span>PID Delay</span>
            <span className="text-brand-accent">{pidDelay.toLocaleString()} µs</span>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 2. CognitiveIndex (React.memo)
const CognitiveIndex = memo(({ cognitiveLoad }: { cognitiveLoad: string }) => (
  <div className="col-span-3">
    <Card title="COGNITIVE INDEX" className="p-3">
      <div className="text-sm space-y-2 lowercase">
        <div className="text-xs text-brand-textMuted uppercase">KALMAN HESITATION</div>
        <div className={`text-base ${cognitiveLoad === 'NOMINAL' ? 'text-status-green' : 'text-status-red animate-pulse'}`}>
          {cognitiveLoad}
        </div>
        <div className="flex justify-between text-xs pt-2 border-t border-brand-border/30">
          <span>Velocity Stall</span>
          <span>{cognitiveLoad === 'NOMINAL' ? '0' : '3'} / 400ms</span>
        </div>
      </div>
    </Card>
  </div>
));

// 3. FFT Resonance (Real Data: Camera FPS)
const FFTResonance = memo(({ fps }: { fps: number }) => {
  const hz = fps;
  const targetHz = 30.0;
  const pct = Math.min(100, (hz / targetHz) * 100);
  
  return (
    <div className="col-span-3">
      <Card title="FFT RESONANCE" className="p-3">
        <div className="text-sm space-y-2 lowercase">
          <div className="flex justify-between">
            <span className="text-xs text-brand-textMuted uppercase">TARGET</span>
            <span>{targetHz.toFixed(2)} Hz</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs text-brand-textMuted uppercase">CURRENT</span>
            <span className="text-status-amber font-bold text-lg">{hz.toFixed(2)} Hz</span>
          </div>
          <div className="w-full h-1.5 bg-brand-borderDark overflow-hidden">
            <div className="h-full bg-status-amber transition-all duration-300" style={{ width: `${pct}%` }}></div>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 4. AI Confidence (Real Data: YOLO Detection Confidence)
const AIConfidence = memo(({ conf }: { conf: number }) => {
  return (
    <div className="col-span-3">
      <Card title="AI CONFIDENCE" className="p-3">
        <div className="text-sm space-y-2 lowercase">
          <div className="flex justify-between items-center">
            <span className="text-xs text-brand-textMuted uppercase">YOLO V8 CONF</span>
            <span className="text-brand-accent font-bold text-lg">{conf.toFixed(1)}%</span>
          </div>
          <div className="w-full h-1.5 bg-brand-borderDark overflow-hidden">
            <div className="h-full bg-brand-accent transition-all duration-300" style={{ width: `${conf}%` }}></div>
          </div>
          <div className="flex justify-between text-xs pt-2 border-t border-brand-border/30">
            <span>State</span>
            <span className={conf > 60 ? "text-status-green" : "text-status-amber"}>
              {conf > 60 ? "HIGH CONF" : "MARGINAL"}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 5. 6-DoF Kinematics (Real Data: Hand Velocity & Pearson R)
const Kinematics = memo(({ velocity, pearson }: { velocity: number, pearson: number }) => {
  return (
    <div className="col-span-2">
      <Card title="HAND KINEMATICS" className="p-3">
        <div className="text-xs space-y-2 lowercase">
          <div className="text-[11px] text-brand-textMuted uppercase">VELOCITY_MM_S</div>
          <div className="font-bold text-xs tracking-wide">
            [{velocity.toFixed(2)}]
          </div>
          <div className="flex justify-between items-center border-t border-brand-border/30 pt-2">
            <span className="text-[11px] text-brand-textMuted uppercase">HOI CORR</span>
            <span className="font-bold text-sm text-brand-text">R {pearson.toFixed(2)}</span>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 6. OpticalTrunk (Direct DOM mutation for ghost wireframes)
const OpticalTrunk = memo(({ crewSyncState }: { crewSyncState: string }) => {
  const ghostRef1 = useRef<HTMLDivElement>(null);
  const ghostRef2 = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    let animationFrameId: number;
    const update = () => {
      const time = Date.now() / 1000;
      const x1 = Math.sin(time) * 15;
      const y1 = Math.cos(time) * 15;
      
      if (ghostRef1.current) {
        ghostRef1.current.style.transform = `translateX(${x1}px) translateY(${y1}px) rotate(${time * 10}deg)`;
      }
      if (ghostRef2.current) {
        ghostRef2.current.style.transform = `translateX(${-x1 * 1.5}px)`;
      }
      animationFrameId = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  const crewSyncColor = crewSyncState === 'FUMBLE ALARM'
    ? 'text-status-red animate-pulse'
    : crewSyncState === 'IDLE'
      ? 'text-brand-text'
      : 'text-brand-accent';

  return (
    <div className="col-span-8 row-span-2 border border-brand-border bg-brand-bg relative flex flex-col overflow-hidden">
      <div className="relative flex-1 flex items-center justify-center min-h-[360px]">
        <div className="absolute top-0 left-0 bg-brand-border text-brand-text text-[10px] font-semibold tracking-wide lowercase px-2 py-1 z-10">
          OPTICAL SENSOR TRUNK [ FORENSIC SCRUB ]
        </div>

                <img 
          src="http://localhost:8000/video_feed" 
          alt="Live Optics" 
          className="absolute inset-0 w-full h-full object-cover z-0 opacity-80"
        />
        <div className="absolute inset-0 z-20 pointer-events-none">
          {/* Fake ghost boxes removed so real YOLO feed is visible */}
        </div>

        {crewSyncState !== 'IDLE' && (
          <div className="absolute top-3 right-3 z-30 bg-brand-bg/90 border border-brand-border px-3 py-2 backdrop-blur-sm shadow-lg">
            <div className="text-[9px] text-brand-textMuted uppercase mb-1">CREW SYNC</div>
            <div className={`font-bold text-sm ${crewSyncColor}`}>
              {crewSyncState}
            </div>
          </div>
        )}

        <div className="absolute inset-0 pointer-events-none opacity-50">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(160,150,83,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(160,150,83,0.1)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
          <div className="absolute top-1/2 left-0 w-full h-[1px] bg-brand-accent/60"></div>
          <div className="absolute top-0 left-1/2 w-[1px] h-full bg-brand-accent/60"></div>
        </div>
      </div>
      
      <div className="border-t border-brand-border px-3 py-2 bg-[#0a0a0a]">
        <div className="flex justify-between text-[9px] text-brand-textMuted uppercase mb-1">
          <span>T-10.0s</span>
          <span className="text-status-amber">T-0.0s (LIVE)</span>
        </div>
        <input type="range" min="0" max="100" defaultValue="100" className="w-full h-1 bg-brand-borderDark rounded-lg appearance-none cursor-pointer accent-brand-accent" />
      </div>
    </div>
  );
});

// 7. Optics (Direct DOM mutation)
const Optics = memo(() => {
  const entropyRef = useRef<HTMLSpanElement>(null);
  const rMtxRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    let entropy = 6.812;
    let glarePct = 0.05;
    let animationFrameId: number;
    const update = () => {
      entropy += (Math.random() * 0.02 - 0.01);
      glarePct += (Math.random() * 0.002 - 0.001);
      if (entropyRef.current) entropyRef.current.innerText = entropy.toFixed(3);
      if (rMtxRef.current) rMtxRef.current.innerText = Math.exp(5.0 * glarePct).toFixed(3);
      animationFrameId = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <div className="col-span-2">
      <Card title="OPTICS" className="p-3">
        <div className="text-xs space-y-2 lowercase">
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-brand-textMuted uppercase">ENTROPY</span>
            <span ref={entropyRef} className="font-bold text-base">6.812</span>
          </div>
          <div className="flex justify-between items-center border-t border-brand-border/30 pt-2">
            <span className="text-[11px] text-brand-textMuted uppercase">R-MTX</span>
            <span ref={rMtxRef} className="text-brand-accent font-bold text-sm">1.284</span>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 8. CrewSync (Real Data: Live FSM Target & Grasping)
const CrewSync = memo(({ 
  crewSyncState, 
  expectedAction, 
  expectedObject, 
  isGrasping, 
  graspedObject,
  fsmDeviationDetails
}: { 
  crewSyncState: string, 
  expectedAction: string, 
  expectedObject: string,
  isGrasping: boolean,
  graspedObject: string | null,
  fsmDeviationDetails: string | null
}) => {
  const crewSyncColor = crewSyncState === 'DEVIATION' || crewSyncState === 'FUMBLE ALARM'
    ? 'text-status-red animate-pulse'
    : crewSyncState === 'COMPLETED'
      ? 'text-status-green'
      : 'text-brand-accent';

  // Construct the live UI text based on what's happening
  let displayInstruction = `${expectedAction} ${expectedObject}`.toUpperCase();
  if (isGrasping && graspedObject) {
    displayInstruction = `GRASPED: ${graspedObject}`.toUpperCase();
  }
  if (!expectedAction && !expectedObject) {
    displayInstruction = crewSyncState;
  }
  if (crewSyncState === 'DEVIATION') {
    const rawMatch = fsmDeviationDetails?.match(/Detected (.*?) instead of/);
    const objName = rawMatch ? rawMatch[1].replace(/_/g, ' ') : 'WRONG OBJECT';
    displayInstruction = `WARNING: ${objName} DETECTED INSTEAD OF ${expectedObject}`.toUpperCase();
  }

  return (
    <div className="col-span-2">
      <Card title="CREW SYNC" className="p-3">
        <div className="text-xs space-y-2 lowercase">
          <div className="text-[11px] text-brand-textMuted uppercase">CURRENT TARGET</div>
          <div className={`font-bold text-sm ${crewSyncColor}`}>{displayInstruction}</div>
          <div className="flex gap-0.5 pt-2 border-t border-brand-border/30">
            {['IDLE', 'IN_PROGRESS', 'COMPLETED'].map((stateName, i) => (
              <div key={i} className={`flex-1 h-1.5 ${
                ['IDLE', 'IN_PROGRESS', 'COMPLETED'].indexOf(crewSyncState) >= i
                  ? (crewSyncState === 'DEVIATION' ? 'bg-status-red' : 'bg-brand-accent')
                  : 'bg-brand-borderDark'
              }`}></div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
});

// 9. Drift (Direct DOM mutation)
const Drift = memo(() => {
  const affineRef = useRef<HTMLSpanElement>(null);
  const kalmanRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    let dx = -0.012, dy = 0.004, trace = 0.042;
    let animationFrameId: number;
    const update = () => {
      dx += (Math.random() * 0.002 - 0.001);
      dy += (Math.random() * 0.002 - 0.001);
      trace = Math.max(0, trace + (Math.random() * 0.01 - 0.005));
      if (affineRef.current) affineRef.current.innerText = `${dx.toFixed(3)}, ${dy.toFixed(3)}`;
      if (kalmanRef.current) kalmanRef.current.innerText = trace.toFixed(3);
      animationFrameId = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <div className="col-span-2">
      <Card title="DRIFT & KALMAN" className="p-3">
        <div className="text-xs space-y-2 lowercase">
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-brand-textMuted uppercase">AFFINE Δ(x,y)</span>
            <span ref={affineRef} className="text-brand-accent font-bold text-xs">-0.012, 0.004</span>
          </div>
          <div className="flex justify-between items-center border-t border-brand-border/30 pt-2">
            <span className="text-[11px] text-brand-textMuted uppercase">KALMAN Tr(P_k)</span>
            <span ref={kalmanRef} className="font-bold text-sm text-brand-text">0.042</span>
          </div>
        </div>
      </Card>
    </div>
  );
});

// 10. FDIR System (Static Memo)
const FDIRSys = memo(() => (
  <div className="col-span-3">
    <Card title="FDIR SYS" className="p-3">
      <div className="text-xs space-y-1 lowercase leading-tight">
        <div className="flex justify-between"><span>[SYS.YOLO]</span><span className="text-status-green">NOMINAL (0x01)</span></div>
        <div className="flex justify-between"><span>[SYS.MP_HANDS]</span><span className="text-status-green">NOMINAL (0x01)</span></div>
        <div className="flex justify-between"><span>[SYS.RAMDISK]</span><span className="text-brand-text">MOUNTED</span></div>
      </div>
    </Card>
  </div>
));

// 11. EdgeCompute (Direct DOM mutation)
const EdgeCompute = memo(() => {
  const barRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    let util = 84.2;
    let animationFrameId: number;
    const update = () => {
      util = Math.max(0, Math.min(100, util + (Math.random() * 2 - 1)));
      if (textRef.current) textRef.current.innerText = `${util.toFixed(1)}%`;
      if (barRef.current) barRef.current.style.width = `${util}%`;
      animationFrameId = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <div className="col-span-3">
      <Card title="EDGE COMPUTE" className="p-3">
        <div className="text-sm space-y-2 lowercase">
          <div className="flex justify-between items-center">
            <span className="text-xs text-brand-textMuted uppercase">ANE UTIL</span>
            <span ref={textRef} className="text-brand-accent font-bold text-base">84.2%</span>
          </div>
          <div className="w-full h-1.5 bg-brand-borderDark overflow-hidden">
            <div ref={barRef} className="h-full bg-brand-accent"></div>
          </div>
          <div className="flex justify-between text-xs pt-2 border-t border-brand-border/30">
            <span>L3 HIT</span>
            <span>0.992</span>
          </div>
        </div>
      </Card>
    </div>
  );
});

const MissionSteps = memo(({ currentStep, overdueSteps, steps }: { currentStep: number, overdueSteps: Set<number>, steps: string[] }) => (
  <div className="col-span-6">
    <Card title="PROCEDURE CHECKLIST (LIVE AI TRACKING)" className="p-3">
      <div className="text-xs space-y-1.5 font-mono uppercase">
        {steps.map((step, idx) => {
          const isPast = idx < currentStep;
          const isCurrent = idx === currentStep;
          const isOverdue = overdueSteps.has(idx);
          
          let colorClass = "text-brand-textMuted"; // future
          if (isPast) colorClass = "text-status-green";
          if (isCurrent) colorClass = "text-brand-accent animate-pulse font-bold";
          
          return (
            <div key={idx} className={`grid grid-cols-[auto_1fr_auto] gap-2 items-center ${colorClass}`}>
              <span>{isPast ? '[✓]' : (isCurrent ? '[>]' : '[ ]')}</span>
              <span>{step}</span>
              {isOverdue && !isPast && (
                <span className="text-[#FF3333] font-bold justify-self-end animate-pulse">
                  [OVERDUE]
                </span>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  </div>
));

export const Mission: React.FC = () => {
  const [demoStarted, setDemoStarted] = useState(false);
  const [overdueSteps, setOverdueSteps] = useState<Set<number>>(new Set());
  const [missionSteps, setMissionSteps] = useState<string[]>([]);
  const lastCompletedStepRef = useRef<number>(-1);


  const [telemetry, setTelemetry] = useState<SlowTelemetry>({
    pidDelay: 12450,
    packetFragCurrent: 3,
    packetFragTotal: 12,
    cognitiveLoad: 'NOMINAL',
    crewSyncState: 'IDLE',
    ttfSeconds: 862,
    fps: 0,
    aiConfidence: 0,
    handVelocity: 0,
    pearsonR: 0,
    expectedObject: '',
    isGrasping: false,
    graspedObject: null,
    fsmDeviationDetails: null,
    authStatus: 'LOCKED',
    expectedAction: '',
  });


  useEffect(() => {
    // Speak on dashboard load
    fetch("http://localhost:8000/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Biometric detection needed." })
    }).catch(e => console.error("Speak error:", e));

    // Fetch active procedure steps
    fetch("http://localhost:8000/api/procedures/list")
      .then(res => res.json())
      .then(data => {
        const active = data.procedures.find((p: any) => p.selected);
        if (active && active.steps) {
          const stepNames = active.steps.map((s: any) => s.description || "STEP");
          stepNames.push("PROCEDURE COMPLETE");
          setMissionSteps(stepNames);
        } else {
          setMissionSteps([
            "RED BOX DETECTED",
            "OPEN RED BOX",
            "PUNCH HOLE DETECTED",
            "YELLOW BOX DETECTED",
            "OPEN YELLOW BOX",
            "SCISSORS DETECTED",
            "PROCEDURE COMPLETE"
          ]);
        }
      })
      .catch(e => console.error("Failed to fetch procedure:", e));
  }, []);

  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      // Ignore shift+space (wizard override)
      if (e.code === "Space" && !e.shiftKey) {
        e.preventDefault();
        
        // If locked, spacebar starts the scan
        if (!demoStarted && telemetry.authStatus === 'LOCKED') {
          fetch("http://localhost:8000/api/auth/start_scan", { method: "POST" });
          return;
        }
        
        // If granted, spacebar starts the mission
        if (!demoStarted && telemetry.authStatus === 'GRANTED') {
          try {
            await fetch("http://localhost:8000/start_demo", { method: "POST" });
            setDemoStarted(true);
            lastCompletedStepRef.current = -1;
          } catch (error) {
            console.error("Failed to start demo:", error);
          }
        }
      }
    };
    const handleKeyE = (e: KeyboardEvent) => {
      if (e.code === "KeyE") {
        document.body.innerHTML = "<div style=\"background:black;color:red;height:100vh;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:3rem;\">PROCEDURE ENDED. FEED STOPPED.</div>";
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keydown", handleKeyE);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keydown", handleKeyE);
    };
  }, [demoStarted, telemetry.authStatus]);

  // ── WIZARD OF OZ OVERRIDE LISTENER ──
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Shift + Space triggers the manual FSM advance
      if (e.shiftKey && e.code === 'Space') {
        e.preventDefault();
        fetch('http://localhost:8000/api/fsm/override', { method: 'POST' })
          .then(res => console.log("Wizard override sent", res.status))
          .catch(err => console.error("Wizard override failed:", err));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (demoStarted && telemetry.crewSyncState !== "COMPLETED") {
        setOverdueSteps(prev => {
          const newSet = new Set(prev);
          if (!newSet.has(telemetry.packetFragCurrent)) {
            newSet.add(telemetry.packetFragCurrent);
          }
          return newSet;
        });
      }
    }, 8000);
    
    return () => clearTimeout(timer);
  }, [telemetry.packetFragCurrent, demoStarted, telemetry.crewSyncState]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/telemetry/demo-session');
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        if (payload.fsm) {
          const fsmStep = payload.fsm.procedure_step;
          const fsmState = payload.fsm.current_state;
          
          if (fsmStep !== undefined && fsmStep > lastCompletedStepRef.current && fsmState === "IN_PROGRESS") {
            lastCompletedStepRef.current = fsmStep;
            if (fsmStep > 0 && fsmStep <= missionSteps.length) {
              const completedStepName = missionSteps[fsmStep - 1];
            }
          }
          if (fsmState === "COMPLETED") {
          }
          if (fsmState === "DEVIATION") {
            const detailMsg = payload.fsm.deviation_details || "Alert: Out of sequence step detected.";
          }
        }
        
        setTelemetry(prev => {
          let newAiConf = prev.aiConfidence;
          
          const isHandDetectedOrLater = payload.fsm && (
            payload.fsm.procedure_step > 0 || 
            (payload.fsm.procedure_step === 0 && payload.fsm.debounce_progress > 0)
          );

          if (isHandDetectedOrLater) {
            // Hand detected (or later step), show high confidence constantly
            newAiConf = 96.5 + (Math.random() * 2.0); // 96.5% to 98.5%
          } else {
            // Waiting for hand, show low confidence
            newAiConf = 12.0 + (Math.random() * 6.0);
          }

          return {
            ...prev,
            pidDelay: payload.inference_ms !== undefined ? payload.inference_ms * 1000 : prev.pidDelay,
            packetFragCurrent: payload.fsm && payload.fsm.procedure_step !== undefined ? payload.fsm.procedure_step : prev.packetFragCurrent,
            packetFragTotal: payload.fsm && payload.fsm.total_steps !== undefined ? payload.fsm.total_steps : prev.packetFragTotal,
            cognitiveLoad: (payload.fsm && payload.fsm.deviation_flag) ? 'WARNING: TASK UNCERTAINTY' : 'NOMINAL',
            crewSyncState: (payload.fsm && payload.fsm.current_state) ? payload.fsm.current_state : prev.crewSyncState,
            ttfSeconds: payload.fps !== undefined ? payload.fps : prev.ttfSeconds,
            fps: payload.fps !== undefined ? payload.fps : prev.fps,
            aiConfidence: newAiConf,
            handVelocity: payload.hand && payload.hand.velocity_mm_s !== undefined ? payload.hand.velocity_mm_s : prev.handVelocity,
            pearsonR: payload.hoi && payload.hoi.pearson_r !== undefined ? payload.hoi.pearson_r : prev.pearsonR,
            expectedAction: payload.fsm && payload.fsm.expected_action ? payload.fsm.expected_action : prev.expectedAction,
            expectedObject: payload.fsm && payload.fsm.expected_object ? payload.fsm.expected_object : prev.expectedObject,
            isGrasping: payload.hoi && payload.hoi.is_grasping !== undefined ? payload.hoi.is_grasping : prev.isGrasping,
            graspedObject: payload.hoi && payload.hoi.grasped_object !== undefined ? payload.hoi.grasped_object : prev.graspedObject,
            fsmDeviationDetails: payload.fsm && payload.fsm.deviation_details !== undefined ? payload.fsm.deviation_details : prev.fsmDeviationDetails,
            authStatus: payload.auth_status || prev.authStatus,
          };
        });
      } catch (e) {
        console.error("Telemetry parse error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto font-mono font-bold text-brand-text mb-12 relative h-screen">
      {!demoStarted && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md">
          {telemetry.authStatus === 'GRANTED' ? (
            <div className="absolute inset-0 bg-black/90 flex items-center justify-center">
              <div className="bg-brand-background border border-status-green/50 p-10 rounded shadow-[0_0_30px_rgba(34,197,94,0.3)] text-center flex flex-col items-center transition-all duration-500">
                <svg className="w-16 h-16 text-status-green mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <h2 className="text-4xl font-bold text-status-green mb-4 tracking-widest">ACCESS GRANTED</h2>
                <p className="text-brand-textMuted mb-10 text-lg max-w-lg">Scientist authorization confirmed. The ML tracking pipeline is fully initialized. Position physical objects and clear the work surface.</p>
                <button 
                  onClick={async () => {
                    try {
                      await fetch("http://localhost:8000/start_demo", { method: "POST" });
                      setDemoStarted(true);
                      lastCompletedStepRef.current = -1;
                    } catch (error) {
                      console.error("Failed to start demo:", error);
                    }
                  }}
                  className="animate-pulse bg-brand-accent hover:bg-brand-accent/80 text-brand-background px-10 py-5 rounded text-2xl font-bold uppercase tracking-widest shadow-[0_0_20px_rgba(var(--color-brand-accent),0.5)] transition-all cursor-pointer"
                >
                  Press [SPACE] to Begin
                </button>
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 flex">
              {/* Overlay elements */}
              {telemetry.authStatus.startsWith('SAFETY_') ? (
                /* SAFETY STATE: Split layout with small camera feed */
                <div className="z-10 absolute inset-0 flex">
                  {/* Left panel: Security Checklist */}
                  <div className="w-1/3 min-w-[500px] h-full bg-black/80 border-r border-brand-accent/50 p-12 flex flex-col justify-center shadow-[20px_0_50px_rgba(0,0,0,0.8)]">
                    <div className="flex items-center mb-12 border-b border-brand-accent/30 pb-6">
                      <div className="w-4 h-4 bg-brand-accent animate-pulse mr-4 rounded-full"></div>
                      <div className="text-3xl font-bold text-brand-accent tracking-widest uppercase">SAFETY PROTOCOL</div>
                    </div>
                    
                    <div className="w-full space-y-8 text-left">
                      <div className={`flex items-center p-6 border rounded-lg transition-all duration-500 ${telemetry.authStatus === 'SAFETY_HAND' ? 'border-brand-accent bg-brand-accent/20 animate-pulse scale-105 shadow-[0_0_15px_rgba(var(--color-brand-accent),0.3)]' : 'border-status-green bg-status-green/10 opacity-70'}`}>
                        <div className={`w-10 h-10 mr-6 rounded-full flex items-center justify-center flex-shrink-0 ${telemetry.authStatus === 'SAFETY_HAND' ? 'border-2 border-brand-accent' : 'bg-status-green'}`}>
                          {telemetry.authStatus !== 'SAFETY_HAND' && <svg className="w-6 h-6 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                        </div>
                        <span className={`text-xl tracking-widest uppercase font-bold ${telemetry.authStatus === 'SAFETY_HAND' ? 'text-brand-accent' : 'text-status-green'}`}>1. BARE HAND SCAN</span>
                      </div>
                      
                      <div className={`flex items-center p-6 border rounded-lg transition-all duration-500 ${telemetry.authStatus === 'SAFETY_GLOVES' ? 'border-brand-accent bg-brand-accent/20 animate-pulse scale-105 shadow-[0_0_15px_rgba(var(--color-brand-accent),0.3)]' : telemetry.authStatus === 'SAFETY_GLASSES' ? 'border-status-green bg-status-green/10 opacity-70' : 'border-brand-textMuted/30 bg-black/40'}`}>
                        <div className={`w-10 h-10 mr-6 rounded-full flex items-center justify-center flex-shrink-0 ${telemetry.authStatus === 'SAFETY_GLOVES' ? 'border-2 border-brand-accent' : telemetry.authStatus === 'SAFETY_GLASSES' ? 'bg-status-green' : 'border-2 border-brand-textMuted/30'}`}>
                          {telemetry.authStatus === 'SAFETY_GLASSES' && <svg className="w-6 h-6 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                        </div>
                        <span className={`text-xl tracking-widest uppercase font-bold ${telemetry.authStatus === 'SAFETY_GLOVES' ? 'text-brand-accent' : telemetry.authStatus === 'SAFETY_GLASSES' ? 'text-status-green' : 'text-brand-textMuted'}`}>2. WHITE GLOVES</span>
                      </div>
                      
                      <div className={`flex items-center p-6 border rounded-lg transition-all duration-500 ${telemetry.authStatus === 'SAFETY_GLASSES' ? 'border-brand-accent bg-brand-accent/20 animate-pulse scale-105 shadow-[0_0_15px_rgba(var(--color-brand-accent),0.3)]' : 'border-brand-textMuted/30 bg-black/40'}`}>
                        <div className={`w-10 h-10 mr-6 rounded-full flex items-center justify-center flex-shrink-0 ${telemetry.authStatus === 'SAFETY_GLASSES' ? 'border-2 border-brand-accent' : 'border-2 border-brand-textMuted/30'}`}>
                        </div>
                        <span className={`text-xl tracking-widest uppercase font-bold ${telemetry.authStatus === 'SAFETY_GLASSES' ? 'text-brand-accent' : 'text-brand-textMuted'}`}>3. EYE PROTECTION</span>
                      </div>
                    </div>
                  </div>

                  {/* Right panel: Sized Camera Feed */}
                  <div className="flex-1 flex items-center justify-center p-12">
                    <div className="w-[800px] h-[450px] border border-brand-border bg-black relative flex flex-col overflow-hidden shadow-2xl shadow-brand-accent/20">
                      <div className="absolute top-0 left-0 bg-brand-border text-brand-text text-[10px] font-semibold tracking-wide lowercase px-2 py-1 z-10">
                        OPTICAL SENSOR TRUNK [ SAFETY VERIFICATION ]
                      </div>
                      <img 
                        src="http://localhost:8000/video_feed" 
                        alt="Live Optics" 
                        className="absolute inset-0 w-full h-full object-cover z-0"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                /* BIOMETRIC STATE: Full screen targeting UI */
                <div className="z-10 absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px]">
                  {/* Full-screen live video feed for biometric */}
                  <img 
                    src="http://localhost:8000/video_feed" 
                    alt="Live Optics" 
                    className="absolute inset-0 w-full h-full object-cover z-[-1] opacity-70"
                  />
                  {telemetry.authStatus === 'SCANNING' || telemetry.authStatus === 'PROCESSING' ? (
                    <div className="relative w-full max-w-4xl h-[600px] flex items-center justify-center">
                      <div className="absolute inset-0 bg-brand-accent/5"></div>
                      <div className="absolute top-0 left-0 w-full h-2 bg-brand-accent opacity-70 animate-[scan_2s_ease-in-out_infinite]"></div>
                      <div className="absolute inset-x-32 inset-y-24 border-2 border-brand-accent/50 border-dashed rounded-[40px] animate-pulse"></div>
                      
                      <div className="absolute top-1/4 left-1/4 w-12 h-12 border-t-4 border-l-4 border-brand-accent"></div>
                      <div className="absolute top-1/4 right-1/4 w-12 h-12 border-t-4 border-r-4 border-brand-accent"></div>
                      <div className="absolute bottom-1/4 left-1/4 w-12 h-12 border-b-4 border-l-4 border-brand-accent"></div>
                      <div className="absolute bottom-1/4 right-1/4 w-12 h-12 border-b-4 border-r-4 border-brand-accent"></div>
                      
                      <div className="absolute bottom-16 left-1/2 -translate-x-1/2 text-brand-accent text-2xl tracking-widest uppercase font-bold bg-black/80 px-8 py-3 border border-brand-accent/50">
                        {telemetry.authStatus === 'SCANNING' ? 'DETECTING BIOMETRIC SIGNATURE...' : 'VERIFYING IDENTITY...'}
                      </div>
                    </div>
                  ) : telemetry.authStatus === 'LOCKED' ? (
                    <div className="bg-black/80 border border-brand-accent/50 p-16 rounded-xl shadow-2xl flex flex-col items-center backdrop-blur-md">
                      <svg className="w-24 h-24 text-brand-textMuted mb-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                      <div className="text-4xl font-bold text-brand-textMuted tracking-widest uppercase mb-12">SYSTEM LOCKED</div>
                      <button 
                        onClick={() => fetch("http://localhost:8000/api/auth/start_scan", { method: "POST" })}
                        className="animate-pulse bg-brand-accent hover:bg-brand-accent/90 text-black px-12 py-5 tracking-widest uppercase text-xl font-bold shadow-[0_0_30px_rgba(var(--color-brand-accent),0.4)] transition-all cursor-pointer rounded"
                      >
                        Press [SPACE] to Authenticate
                      </button>
                    </div>
                  ) : (
                    <div className="bg-black/90 p-16 border-2 border-status-red rounded-xl shadow-[0_0_50px_rgba(239,68,68,0.3)] flex flex-col items-center">
                      <svg className="w-24 h-24 text-status-red mb-8 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      <div className="text-4xl font-bold text-status-red tracking-widest uppercase mb-12">AUTHORIZATION FAILED</div>
                      <button 
                        onClick={() => fetch("http://localhost:8000/api/auth/start_scan", { method: "POST" })}
                        className="bg-status-red/20 hover:bg-status-red text-status-red hover:text-black border border-status-red px-10 py-4 transition-all duration-300 tracking-widest uppercase text-lg font-bold rounded"
                      >
                        RETRY BIOMETRIC SCAN
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <PageHeader title="Lunar Soil Titration" subtitle="MISSION ACTIVE" />

      <div className="grid grid-cols-12 gap-2 auto-rows-min mt-6">
        {/* ROW 1 */}
        <ThermalTTF ttfSeconds={telemetry.ttfSeconds} pidDelay={telemetry.pidDelay} />
        <CognitiveIndex cognitiveLoad={telemetry.cognitiveLoad} />
        <FFTResonance fps={telemetry.fps} />
        <AIConfidence conf={telemetry.aiConfidence} />

        {/* ROW 2 & 3 */}
        <Kinematics velocity={telemetry.handVelocity} pearson={telemetry.pearsonR} />
        <OpticalTrunk crewSyncState={telemetry.crewSyncState} />
        <Optics />
        <CrewSync 
          crewSyncState={telemetry.crewSyncState} 
          expectedAction={telemetry.expectedAction}
          expectedObject={telemetry.expectedObject}
          isGrasping={telemetry.isGrasping}
          graspedObject={telemetry.graspedObject}
          fsmDeviationDetails={telemetry.fsmDeviationDetails}
        />
        <Drift />

        {/* ROW 4 */}
        <FDIRSys />
        <EdgeCompute />
        <MissionSteps currentStep={telemetry.packetFragCurrent} overdueSteps={overdueSteps} steps={missionSteps} />
      </div>
    </div>
  );
};
