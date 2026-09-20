export const startDetectionWindow = (
  expectedObject: string, 
  timeoutSeconds: number = 6,
  ignoreDeviation: boolean = false
): Promise<string> => {
  return new Promise((resolve) => {
    let isResolved = false;

    // 1. Tell backend to start detecting this object
    fetch(`http://localhost:8000/api/fsm/set_target?object=${expectedObject}`, { method: "POST" })
      .catch(console.error);

    // 2. Strict Timeout
    const timer = setTimeout(() => {
      if (!isResolved) {
        isResolved = true;
        fetch(`http://localhost:8000/api/fsm/set_target?object=pause`, { method: "POST" }).catch(console.error);
        resolve("timeout"); 
      }
    }, timeoutSeconds * 1000);

    let backendCaughtUp = false;
    
    // 3. Listen to the WebSocket
    const ws = new WebSocket("ws://localhost:8000/ws/telemetry/demo-session");
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        // Success condition (step advanced)
        if (payload.fsm) {
            if (payload.fsm.expected_object === expectedObject) {
                backendCaughtUp = true;
            }
            if (backendCaughtUp && payload.fsm.expected_object !== expectedObject && payload.fsm.current_state !== "IDLE") {
               if (!isResolved) {
                  isResolved = true;
                  clearTimeout(timer);
                  ws.close();
                  fetch(`http://localhost:8000/api/fsm/set_target?object=pause`, { method: "POST" }).catch(console.error);
                  resolve("success");
               }
            }
        }
        
        // Deviation condition
        if (backendCaughtUp && !ignoreDeviation && payload.fsm && payload.fsm.current_state === "DEVIATION") {
           if (!isResolved) {
              isResolved = true;
              clearTimeout(timer);
              ws.close();
              fetch(`http://localhost:8000/api/fsm/set_target?object=pause`, { method: "POST" }).catch(console.error);
              resolve("wrong_object:" + (payload.fsm.deviation_details || "another object"));
           }
        }
        
      } catch (e) {
      }
    };
    
    ws.onerror = () => {
      if (!isResolved) {
         isResolved = true;
         clearTimeout(timer);
         resolve("timeout");
      }
    };
  });
};
