import React, { createContext, useContext, useState } from 'react';

interface MissionContextType {
  isMissionUnlocked: boolean;
  unlockMission: () => void;
}

const MissionContext = createContext<MissionContextType | undefined>(undefined);

export const MissionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isMissionUnlocked, setIsMissionUnlocked] = useState(true);

  const unlockMission = () => setIsMissionUnlocked(true);

  return (
    <MissionContext.Provider value={{ isMissionUnlocked, unlockMission }}>
      {children}
    </MissionContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useMissionContext = () => {
  const context = useContext(MissionContext);
  if (context === undefined) {
    throw new Error('useMissionContext must be used within a MissionProvider');
  }
  return context;
};
