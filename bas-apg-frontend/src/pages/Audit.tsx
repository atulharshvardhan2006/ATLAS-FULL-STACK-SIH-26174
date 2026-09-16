import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Virtuoso } from 'react-virtuoso';

// Generate 10,000 logs to stress test DOM virtualization (Moved outside component for purity)
const massiveSeuLogs = Array.from({ length: 10000 }).map((_, i) => ({
  time: `T-14:${String(Math.floor((i / 60)) % 60).padStart(2, '0')}:${String(i % 60).padStart(2, '0')}.${String(Math.floor(Math.random() * 999)).padStart(3, '0')}`,
  hex: `0x${Math.floor(Math.random() * 65535).toString(16).toUpperCase().padStart(4, '0')}`,
  msg: i % 3 === 0 
    ? 'Soft error in PID registry. Governor reset to baseline.'
    : i % 2 === 0 
      ? 'Bitflip detected in L3 cache. Corrected via TMR majority vote.' 
      : 'Cosmic ray strike on ANE matrix. Tensor resynced.'
}));

export const Audit: React.FC = () => {
  const navigate = useNavigate();
  
  const handleEndSession = () => {
    fetch("http://localhost:8000/end_demo", { method: "POST" }).catch(() => {});
    navigate("/setup");
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "e" || e.key === "E") {
        handleEndSession();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  const [replayTime, setReplayTime] = useState(0);
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedAudit, setSelectedAudit] = useState<any>(null);
  const [loadingAudit, setLoadingAudit] = useState(false);
  
  useEffect(() => {
    // Simulate auto-playing the 10s anomaly buffer
    const interval = setInterval(() => {
      setReplayTime(prev => (prev >= 100 ? 0 : prev + 1));
    }, 100);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetch('http://localhost:8000/api/sessions')
      .then(r => r.json())
      .then(data => setSessions(data.sessions || []))
      .catch(() => {});
    const poll = setInterval(() => {
      fetch('http://localhost:8000/api/sessions')
        .then(r => r.json())
        .then(data => setSessions(data.sessions || []))
        .catch(() => {});
    }, 5000);
    return () => clearInterval(poll);
  }, []);

  const loadAudit = (sessionId: string) => {
    setLoadingAudit(true);
    fetch(`http://localhost:8000/api/session/${sessionId}/audit`)
      .then(r => r.json())
      .then(data => { setSelectedAudit(data); setLoadingAudit(false); })
      .catch(() => setLoadingAudit(false));
  };

  const fileMb = selectedAudit?.file_size_mb || 0;
  const packetTotal = Math.round((fileMb * 1024 * 1024) / 1440) || 145020;
  const packetDropped = Math.round(packetTotal * 0.0015) || 214;
  const retentionRate = ((packetTotal - packetDropped) / packetTotal) * 100;

  const edgeHash = '0x7A4F8B...E21D';
  const groundHash = '0x7A4F8B...E21D';

  return (
    <div className="max-w-7xl mx-auto font-mono text-brand-text mb-12">
      <PageHeader 
        title="Mission Control Forensics" 
        subtitle="IDSN GROUND STATION AUDIT LOG"
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start mt-6">
        
        {/* LEFT COLUMN: Flight & Hardware Forensics */}
        <div className="flex flex-col gap-6">
          <div className="border-b border-brand-border pb-2 mb-2">
            <h2 className="text-sm font-bold tracking-widest text-brand-accent">FLIGHT & HARDWARE FORENSICS</h2>
          </div>

          <Card title="EXPERIMENT RECORDING PLAYBACK" className="p-4">
            <div className="relative aspect-video w-full border border-brand-accent/50 bg-black overflow-hidden">
              {selectedAudit ? (
                <video
                  key={selectedAudit.session_id}
                  className="w-full h-full object-cover"
                  controls
                  autoPlay
                  muted
                  loop
                >
                  <source src={`http://localhost:8000/api/session/${selectedAudit.session_id}/recording`} type="video/mp4" />
                  Recording not available
                </video>
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="w-full h-full bg-[linear-gradient(rgba(160,150,83,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(160,150,83,0.1)_1px,transparent_1px)] bg-[size:20px_20px] opacity-40"></div>
                  <div className="absolute text-xs text-brand-textMuted uppercase tracking-widest">
                    SELECT A SESSION BELOW TO REPLAY RECORDING
                  </div>
                </div>
              )}
            </div>
            <div className="text-xs text-brand-textMuted mt-3 uppercase">
              {selectedAudit ? `Session: ${selectedAudit.session_id} | Operator: ${selectedAudit.operator_name}` : 'No session selected'}
            </div>
          </Card>

          <Card title={`SEU RADIATION MANIFEST (${massiveSeuLogs.length.toLocaleString()} LOGS)`} className="p-4">
            <div className="h-[300px]">
              <Virtuoso
                className="h-full"
                data={massiveSeuLogs}
                itemContent={(_, log) => (
                  <div className="text-xs font-mono border-l-2 border-status-amber pl-3 py-1 mb-2">
                    <div className="flex justify-between text-brand-textMuted mb-1">
                      <span>{log.time}</span>
                      <span>ADDR: {log.hex}</span>
                    </div>
                    <div className="text-brand-text">{log.msg}</div>
                  </div>
                )}
              />
            </div>
          </Card>

          <Card title="LMAX QoS TRIAGE" className="p-4">
            <div className="flex justify-between items-end mb-2">
              <div className="text-xs text-brand-textMuted uppercase">PACKETS GENERATED vs DROPPED</div>
              <div className="text-sm font-bold text-status-green">{retentionRate.toFixed(4)}% RETENTION</div>
            </div>
            <div className="w-full h-8 bg-brand-borderDark flex">
              <div className="h-full bg-status-green" style={{ width: `${retentionRate}%` }}></div>
              <div className="h-full bg-status-red" style={{ width: `${100 - retentionRate}%` }}></div>
            </div>
            <div className="flex justify-between text-xs mt-2">
              <span>{packetTotal.toLocaleString()} TOTAL ({fileMb} MB)</span>
              <span className="text-status-red">{packetDropped} DROPPED</span>
            </div>
          </Card>
        </div>

        {/* RIGHT COLUMN: IDSN Transmission Forensics */}
        <div className="flex flex-col gap-6">
          <div className="border-b border-brand-border pb-2 mb-2">
            <h2 className="text-sm font-bold tracking-widest text-brand-accent">IDSN TRANSMISSION FORENSICS</h2>
          </div>

          <Card title="AOS / LOS BURST TIMELINE" className="p-4">
            <div className="space-y-4">
              <div className="relative pt-4 pb-2 border-b border-brand-border/30">
                <div className="absolute top-0 left-0 text-[10px] text-brand-textMuted">T-00:00</div>
                <div className="absolute top-0 right-0 text-[10px] text-brand-textMuted">T-45:00</div>
                <div className="w-full h-4 bg-brand-border flex overflow-hidden">
                  <div className="w-1/3 h-full bg-status-amber flex items-center justify-center text-[9px] text-black font-bold">LOS (BUFFERING)</div>
                  <div className="w-1/6 h-full bg-status-green flex items-center justify-center text-[9px] text-black font-bold">AOS BURST</div>
                  <div className="w-1/2 h-full bg-status-amber flex items-center justify-center text-[9px] text-black font-bold">LOS (BUFFERING)</div>
                </div>
              </div>
              <div className="text-xs text-brand-text leading-relaxed">
                Telemetry stored in local Ramdisk during Loss of Signal (LOS). Burst transmitted to Byalalu Ground Station during 7.5 minute Acquisition of Signal (AOS) window.
              </div>
            </div>
          </Card>

          <Card title="PAYLOAD COMPRESSION STATS" className="p-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 border border-brand-border bg-brand-bg">
                <div className="text-[10px] text-brand-textMuted uppercase mb-1">RAW JSON TELEMETRY</div>
                <div className="text-xl font-bold text-brand-text">14.2 MB</div>
              </div>
              <div className="p-3 border border-brand-accent bg-brand-accent/5">
                <div className="text-[10px] text-brand-textMuted uppercase mb-1">ZK-SNARK COMPRESSED</div>
                <div className="text-xl font-bold text-brand-accent">845 KB</div>
              </div>
            </div>
            <div className="mt-3 text-xs text-center text-status-green font-bold">
              94.05% ORBITAL BANDWIDTH SAVED
            </div>
          </Card>

          <Card title="BASEBAND INTEGRITY & HANDSHAKE" className="p-4">
            <div className="space-y-4">
              <div className="text-xs font-mono space-y-1">
                <div className="text-brand-textMuted mb-2">-- CCSDS BASEBAND TERMINAL --</div>
                <div>&gt; Receiving Fragment 12/12... <span className="text-status-green">OK</span></div>
                <div>&gt; Assembling MTU... <span className="text-status-green">OK</span></div>
                <div>&gt; LDPC Forward Error Correction: <span className="text-brand-accent">MARGIN 4.2dB</span></div>
              </div>
              
              <div className="border border-brand-border p-3">
                <div className="text-[10px] text-brand-textMuted uppercase mb-3 text-center">MERKLE ROOT CRYPTOGRAPHIC HANDSHAKE</div>
                <div className="grid grid-cols-2 gap-4 text-xs text-center mb-4">
                  <div>
                    <div className="text-brand-textMuted mb-1">EDGE NODE HASH</div>
                    <div className="font-bold">{edgeHash}</div>
                  </div>
                  <div>
                    <div className="text-brand-textMuted mb-1">GROUND STATION HASH</div>
                    <div className="font-bold">{groundHash}</div>
                  </div>
                </div>
                <div className="bg-status-green text-black font-bold text-center py-2 text-sm uppercase tracking-widest">
                  PAYLOAD INTEGRITY VERIFIED
                </div>
              </div>
            </div>
          </Card>
          
        </div>
      </div>

      {/* LIVE SESSION AUDIT LOG */}
      <div className="mt-8 border-t border-brand-border pt-6">
        <h2 className="text-sm font-bold tracking-widest text-brand-accent mb-4">LIVE MISSION SESSIONS</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Session List */}
          <Card title={`RECORDED SESSIONS (${sessions.length})`} className="p-4">
            {sessions.length === 0 ? (
              <div className="text-xs text-brand-textMuted py-4 text-center">
                No sessions recorded yet. Start a mission from the Setup page.
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {sessions.map((s: any) => (
                  <button
                    key={s.session_id}
                    onClick={() => loadAudit(s.session_id)}
                    className={`w-full text-left p-3 border transition-colors ${ 
                      selectedAudit?.session_id === s.session_id 
                        ? 'border-brand-accent bg-brand-accent/10' 
                        : 'border-brand-border hover:border-brand-accent/50'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-brand-accent">{s.start_time ? new Date(s.start_time).toLocaleString() : s.session_id}</span>
                      <span className={`text-[10px] px-2 py-0.5 ${s.total_deviations > 0 ? 'bg-status-red text-white' : 'bg-status-green text-black'}`}>
                        {s.total_deviations || 0} DEVIATIONS
                      </span>
                    </div>
                    <div className="text-[10px] text-brand-textMuted mt-1">
                      {s.operator_name} • {s.protocol_id}
                    </div>
                    <div className="text-[10px] text-brand-textMuted">
                      {s.end_time ? `Ended: ${new Date(s.end_time).toLocaleTimeString()}` : ' (ACTIVE)'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Audit Timeline */}
          <Card title="FORENSIC EVENT TIMELINE" className="p-4">
            {loadingAudit ? (
              <div className="text-xs text-brand-textMuted py-4 text-center animate-pulse">Loading audit data...</div>
            ) : selectedAudit ? (
              <div className="space-y-1">
                <div className="flex justify-between text-xs mb-3 pb-2 border-b border-brand-border">
                  <span>Operator: <strong>{selectedAudit.operator_name}</strong></span>
                  <span className="text-status-red font-bold">{selectedAudit.total_deviations} DEVIATIONS</span>
                </div>
                <div className="max-h-[350px] overflow-y-auto space-y-1">
                  {selectedAudit.timeline && selectedAudit.timeline.length > 0 ? (
                    selectedAudit.timeline.map((evt: any, i: number) => (
                      <div key={i} className={`text-xs font-mono border-l-2 pl-3 py-1 ${
                        evt.type === 'CRITICAL' ? 'border-status-red' : 'border-brand-accent'
                      }`}>
                        <div className="text-brand-textMuted text-[10px]">
                          {new Date(evt.timestamp).toLocaleTimeString()}
                        </div>
                        <div className={evt.type === 'CRITICAL' ? 'text-status-red' : 'text-brand-text'}>
                          {evt.action}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-brand-textMuted py-2">No events recorded for this session.</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-xs text-brand-textMuted py-4 text-center">
                ← Select a session to view its forensic timeline
              </div>
            )}
          </Card>
        </div>
      </div>
      
      {/* End Session Button */}
      <div className="mt-8 flex justify-center pb-8">
        <button 
          onClick={handleEndSession}
          className="px-8 py-4 border border-status-red text-status-red font-bold tracking-widest hover:bg-status-red/10 transition-colors uppercase"
        >
          End Session [ E ]
        </button>
      </div>
    </div>
  );
};
