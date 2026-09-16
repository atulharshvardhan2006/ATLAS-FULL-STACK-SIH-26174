export interface Detection {
  id: string;
  label: string;
  confidence: number;
  timestamp: string;
}

export interface FSMState {
  currentState: string;
  previousState: string;
  currentStep: number;
  totalSteps: number;
  deviationFlag: boolean;
}

export interface Interaction {
  id: string;
  type: string;
  description: string;
  timestamp: string;
}

export interface SystemStatus {
  cameraConnected: boolean;
  aiEngineConnected: boolean;
  telemetryConnected: boolean;
  localStorageConnected: boolean;
  fps?: number;
  inferenceTime?: number;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  type: string;
  action: string;
}

export interface Session {
  id: string;
  operatorName: string;
  procedureId: string;
  startTime: string;
  status: 'active' | 'completed' | 'aborted';
}
