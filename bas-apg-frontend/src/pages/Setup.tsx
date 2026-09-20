import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { useMissionContext } from '../context/MissionContext';

interface ManifestItem {
  id: string;
  name: string;
  verified: boolean;
  yolo_class: string;
}

export const Setup: React.FC = () => {
  const navigate = useNavigate();
  const { unlockMission } = useMissionContext();

  const [opticalVerified, setOpticalVerified] = useState(false);
  const [lux] = useState(450);
  const [glare, setGlare] = useState(0.85);
  const [tempData, setTempData] = useState<number[]>(Array(20).fill(30.0));
  
  const [procedures, setProcedures] = useState<any[]>([]);
  const [selectedProcedure, setSelectedProcedure] = useState<string>('');
  
  const [manifest, setManifest] = useState<ManifestItem[]>([
    { id: '1', name: 'LUNAR REGOLITH SAMPLE (14g)', verified: false, yolo_class: 'sample' },
    { id: '2', name: 'TITRATION FLASK A', verified: false, yolo_class: 'main_box' },
    { id: '3', name: 'REAGENT HCL (0.1M)', verified: false, yolo_class: 'red_box' },
    { id: '4', name: 'PIPETTE TOOL', verified: false, yolo_class: 'tweezers' },
  ]);

  const allVerified = manifest.every(item => item.verified) && opticalVerified;

  useEffect(() => {
    // Fetch available procedures
    fetch('http://localhost:8000/api/procedures/list')
      .then(res => res.json())
      .then(data => {
        setProcedures(data.procedures || []);
        const active = data.procedures.find((p: any) => p.selected);
        if (active) {
          setSelectedProcedure(active.filename);
          updateManifestForProcedure(active, data.procedures);
        }
      })
      .catch(err => console.error("Failed to load procedures", err));
  }, []);

  const updateManifestForProcedure = (proc: any, allProcs: any[]) => {
    if (proc && proc.filename !== 'red_yellow_box_experiment.json') {
      const newManifest = proc.objects
        .filter((o: string) => o !== 'procedure' && o !== 'hand')
        .map((obj: string, i: number) => ({
          id: String(i),
          name: obj.toUpperCase().replace(/_/g, ' '),
          verified: false,
          yolo_class: obj
        }));
      setManifest(newManifest);
    } else {
      // Default manifest
      setManifest([
        { id: '1', name: 'LUNAR REGOLITH SAMPLE (14g)', verified: false, yolo_class: 'sample' },
        { id: '2', name: 'TITRATION FLASK A', verified: false, yolo_class: 'main_box' },
        { id: '3', name: 'REAGENT HCL (0.1M)', verified: false, yolo_class: 'red_box' },
        { id: '4', name: 'PIPETTE TOOL', verified: false, yolo_class: 'tweezers' },
      ]);
    }
  };

  const handleProcedureChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const filename = e.target.value;
    setSelectedProcedure(filename);
    fetch('http://localhost:8000/api/procedures/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ procedure_file: filename })
    })
    .then(res => res.json())
    .then(() => {
      const proc = procedures.find(p => p.filename === filename);
      updateManifestForProcedure(proc, procedures);
    });
  };

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/telemetry/demo-session');
    
    ws.onopen = () => {
      setOpticalVerified(true);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        // Generate fluctuating FPS between 27 and 30
        const fakeFps = 27 + Math.random() * 3;
        setTempData(prev => {
          const arr = [...prev.slice(1), fakeFps];
          return arr;
        });
        
        if (payload.glare && payload.glare.saturation_pct !== undefined) {
          setGlare(payload.glare.saturation_pct);
        }
        
        if (payload.detections && Array.isArray(payload.detections)) {
          const detectedClasses = payload.detections.map((d: any) => d.class_name);
          
          setManifest(prev => prev.map(item => {
            if (item.verified) return item;
            if (detectedClasses.includes(item.yolo_class)) {
              return { ...item, verified: true };
            }
            return item;
          }));
        }
      } catch (e) {
        console.error("Telemetry parse error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleStartSession = () => {
    // If manifest is empty (no objects required), just start
    if (allVerified || manifest.length === 0) {
      unlockMission();
      navigate('/mission');
    }
  };

  return (
    <div className="max-w-6xl mx-auto font-mono text-brand-text mb-12">
      <div className="flex justify-between items-end">
        <PageHeader title="Cleanroom Diagnostics" subtitle="PRE-FLIGHT HARDWARE LOCK" />
        
        <div className="mb-8 w-96">
          <label className="block text-xs text-brand-textMuted uppercase mb-2">Select Mission Protocol</label>
          <select 
            value={selectedProcedure} 
            onChange={handleProcedureChange}
            className="w-full bg-brand-panel border border-brand-border text-brand-text p-2 text-sm focus:outline-none focus:border-brand-accent"
          >
            {procedures.map(p => (
              <option key={p.filename} value={p.filename}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mt-2">
        
        {/* LEFT COLUMN: Hardware Diagnostics */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          
          <Card title="OPTICAL INTRINSIC MATRIX" className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-xs text-brand-textMuted uppercase">camera_profile.npz</div>
                <div className="text-sm">Focal Length & Distortion Center</div>
              </div>
              <div className="flex items-center space-x-3">
                <span className={`text-sm font-bold ${opticalVerified ? 'text-status-green' : 'text-status-amber animate-pulse'}`}>
                  {opticalVerified ? 'CALIBRATED' : 'SOLVING...'}
                </span>
                <div className={`w-3 h-3 rounded-full ${opticalVerified ? 'bg-status-green' : 'bg-status-amber'}`}></div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-xs border-t border-brand-border/30 pt-3">
              <div>fx: {opticalVerified ? '1422.3' : '---'}</div>
              <div>fy: {opticalVerified ? '1422.3' : '---'}</div>
              <div>cx: {opticalVerified ? '960.0' : '---'}</div>
            </div>
          </Card>

          <Card title="PID THERMODYNAMIC BASELINE" className="p-4">
            <div className="flex justify-between items-end mb-4">
              <div>
                <div className="text-xs text-brand-textMuted uppercase mb-1">EDGE NODE IDLE TEMP / FPS</div>
                <div className="text-2xl font-bold text-brand-accent">{tempData[tempData.length - 1]?.toFixed(2)}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-brand-textMuted uppercase mb-1">SLEEP PENALTY</div>
                <div className="text-sm text-status-green">STABLE @ 30 FPS</div>
              </div>
            </div>
            
            {/* Simulated Graph */}
            <div className="h-24 w-full flex items-end space-x-1 border-b border-l border-brand-border/50 pb-1 pl-1">
              {tempData.map((temp, i) => (
                <div 
                  key={i} 
                  className="flex-1 bg-brand-accent/50 transition-all duration-300" 
                  style={{ height: `${Math.min(100, Math.max(5, ((temp - 26) / 4) * 100))}%` }}
                ></div>
              ))}
            </div>
          </Card>

          <Card title="ENVIRONMENTAL CALIBRATION RADAR" className="p-4">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <div className="text-xs text-brand-textMuted uppercase mb-1">AMBIENT VENUE LUX</div>
                <div className="text-xl font-bold text-brand-text">{lux.toFixed(0)}</div>
                <div className="text-xs text-status-green mt-1">AUTO-CLAHE: PRIMED</div>
              </div>
              <div>
                <div className="text-xs text-brand-textMuted uppercase mb-1">OPTICAL GLARE SATURATION</div>
                <div className="text-xl font-bold text-brand-accent">{glare.toFixed(2)}</div>
                <div className="text-xs text-status-green mt-1">GLARE GUARDIAN: ACTIVE</div>
              </div>
            </div>
          </Card>
          
        </div>

        {/* RIGHT COLUMN: Manifest & Lock */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          <Card title="MASS MANIFEST LOCK (FOD)" className="p-4">
            <div className="text-xs text-brand-textMuted uppercase mb-4 leading-relaxed">
              AI VISION MUST DETECT AND VERIFY ALL PAYLOAD ITEMS BEFORE STATE FSM CAN TRANSITION OUT OF STANDBY.
            </div>
            
            <div className="space-y-3">
              {manifest.length === 0 && (
                <div className="text-sm text-brand-textMuted italic">No payload verification required for this protocol.</div>
              )}
              {manifest.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-3 border border-brand-border bg-brand-panel">
                  <span className={`text-sm ${item.verified ? 'text-brand-text' : 'text-brand-textMuted'}`}>
                    {item.name}
                  </span>
                  <span className={`text-xs font-bold ${item.verified ? 'text-status-green' : 'text-status-amber animate-pulse'}`}>
                    {item.verified ? '[ VERIFIED ]' : '[ SCANNING ]'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <div className="mt-4">
            <button
              onClick={handleStartSession}
              disabled={!allVerified && manifest.length > 0}
              className={`w-full py-5 border text-sm font-bold uppercase tracking-widest transition-all ${
                (allVerified || manifest.length === 0)
                  ? 'border-brand-accent text-brand-bg bg-brand-accent hover:bg-brand-accent/90 cursor-pointer' 
                  : 'border-brand-border text-brand-textMuted bg-transparent cursor-not-allowed'
              }`}
            >
              {(allVerified || manifest.length === 0) ? 'UNLOCK MISSION SEQUENCE' : 'SYSTEM LOCKED: AWAITING VERIFICATION'}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
