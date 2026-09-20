import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Setup } from './pages/Setup';
import { Mission } from './pages/Mission';
import { Audit } from './pages/Audit';
import { Station } from './pages/Station';
import { Training } from './pages/Training';
import { MissionProvider, useMissionContext } from './context/MissionContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isMissionUnlocked } = useMissionContext();
  if (!isMissionUnlocked) {
    return <Navigate to="/setup" replace />;
  }
  return <>{children}</>;
};

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen bg-brand-bg text-brand-text font-sans font-bold overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto bg-brand-bg p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

function App() {
  useEffect(() => {
    let wakeLock: any = null;
    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator) {
          wakeLock = await (navigator as any).wakeLock.request('screen');
        }
      } catch (err) {
        console.error(`${(err as Error).name}, ${(err as Error).message}`);
      }
    };

    requestWakeLock();

    const handleVisibilityChange = () => {
      if (wakeLock !== null && document.visibilityState === 'visible') {
        requestWakeLock();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (wakeLock !== null) {
        wakeLock.release();
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return (
    <MissionProvider>
      <BrowserRouter>
          <Routes>
            <Route path="/training" element={<Training />} />
            <Route path="*" element={
              <AppLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/setup" replace />} />
                  <Route path="/setup" element={<Setup />} />
                  <Route path="/mission" element={<ProtectedRoute><Mission /></ProtectedRoute>} />
                  <Route path="/audit" element={<Audit />} />
                  <Route path="/station" element={<Station />} />
                </Routes>
              </AppLayout>
            } />
          </Routes>
      </BrowserRouter>
    </MissionProvider>
  );
}

export default App;
