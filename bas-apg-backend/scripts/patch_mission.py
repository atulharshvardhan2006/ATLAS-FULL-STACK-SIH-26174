import os
import re

filepath = "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-frontend/src/pages/Mission.tsx"

with open(filepath, 'r') as f:
    content = f.read()

new_useEffect = """  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/telemetry/demo-session');
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        setTelemetry(prev => ({
          ...prev,
          pidDelay: payload.inference_ms !== undefined ? payload.inference_ms * 1000 : prev.pidDelay,
          packetFragCurrent: payload.fsm && payload.fsm.procedure_step !== undefined ? payload.fsm.procedure_step : prev.packetFragCurrent,
          packetFragTotal: payload.fsm && payload.fsm.total_steps !== undefined ? payload.fsm.total_steps : prev.packetFragTotal,
          cognitiveLoad: (payload.fsm && payload.fsm.deviation_flag) ? 'WARNING: TASK UNCERTAINTY' : 'NOMINAL',
          crewSyncState: (payload.fsm && payload.fsm.current_state) ? payload.fsm.current_state : prev.crewSyncState,
          ttfSeconds: payload.fps !== undefined ? payload.fps : prev.ttfSeconds,
        }));
      } catch (e) {
        console.error("Telemetry parse error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);"""

# The regex replaces the specific useEffect block at the end of the file.
# The Mission component's useEffect is the only one left at the bottom that isn't wrapped in memo/requestAnimationFrame.
# Let's find it safely.
# It starts with "  useEffect(() => {" right after the useState for telemetry.

pattern = r'  useEffect\(\(\) => \{\n    // Only updating SLOW telemetry via React State now.*?return \(\) => clearInterval\(interval\);\n  \}, \[\]\);'

new_content, count = re.subn(pattern, new_useEffect, content, flags=re.DOTALL)

if count == 0:
    print("FAILED TO FIND TARGET STRING")
else:
    with open(filepath, 'w') as f:
        f.write(new_content)
    print("SUCCESSFULLY PATCHED MISSION.TSX")
