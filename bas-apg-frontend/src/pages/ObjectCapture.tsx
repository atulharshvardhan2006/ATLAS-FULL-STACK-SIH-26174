import React, { useState, useEffect, useRef } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';

export const ObjectCapture: React.FC = () => {
  const [objects, setObjects] = useState<any[]>([]);
  const [objectName, setObjectName] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [captureCount, setCaptureCount] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'info' | 'error' | 'success'>('info');

  const slugify = (text: string) => text.toLowerCase().replace(/\s+/g, '_').replace(/-+/g, '_');
  const currentSlug = slugify(objectName);

  const fetchObjects = () => {
    fetch('http://localhost:8000/api/objects/list')
      .then(res => res.json())
      .then(data => setObjects(data.objects || []))
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchObjects();
  }, []);

  const handleCapture = () => {
    if (!objectName.trim()) {
      setStatusMsg("Enter an object name first.");
      setStatusType('error');
      return;
    }
    
    setCapturing(true);
    fetch('http://localhost:8000/api/objects/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ object_slug: currentSlug })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ok') {
        setCaptureCount(data.count);
        setStatusMsg(`Captured image ${data.count}. Move the object slightly and capture more.`);
        setStatusType('info');
      } else {
        setStatusMsg("Failed to capture image.");
        setStatusType('error');
      }
    })
    .catch(err => {
      console.error(err);
      setStatusMsg("Error communicating with backend.");
      setStatusType('error');
    })
    .finally(() => {
      setCapturing(false);
    });
  };

  const handleRegister = () => {
    if (captureCount < 5) {
      setStatusMsg(`Need at least 5 images. You only have ${captureCount}.`);
      setStatusType('error');
      return;
    }

    setStatusMsg("Extracting ORB features... Please wait.");
    setStatusType('info');

    fetch('http://localhost:8000/api/objects/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ object_slug: currentSlug, display_name: objectName })
    })
    .then(res => {
      if (!res.ok) throw new Error("Registration failed");
      return res.json();
    })
    .then(data => {
      if (data.status === 'ok') {
        setStatusMsg(`Successfully registered '${objectName}' with ${data.refs_loaded} valid reference frames.`);
        setStatusType('success');
        setCaptureCount(0);
        setObjectName('');
        fetchObjects();
      }
    })
    .catch(err => {
      console.error(err);
      setStatusMsg("Failed to extract features. Ensure the images have good contrast.");
      setStatusType('error');
    });
  };

  const handleDelete = (slug: string) => {
    if (!window.confirm("Are you sure you want to delete this object?")) return;
    
    fetch(`http://localhost:8000/api/objects/delete/${slug}`, { method: 'DELETE' })
      .then(res => res.json())
      .then(() => fetchObjects())
      .catch(err => console.error(err));
  };

  return (
    <div className="max-w-6xl mx-auto font-mono text-brand-text mb-12">
      <PageHeader title="Dynamic Object Registration" subtitle="ORB FEATURE EXTRACTION PIPELINE" />
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
        
        {/* Left Column - Live Feed & Capture Control */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <Card title="LIVE OPTICAL FEED" className="p-4">
            <div className="relative aspect-video bg-black border border-brand-border/50 overflow-hidden mb-4">
              <img 
                src="http://localhost:8000/video_feed" 
                alt="Live Camera Feed" 
                className="w-full h-full object-cover"
              />
              {/* Overlays */}
              <div className="absolute top-4 left-4 flex space-x-2">
                <div className="px-2 py-1 bg-black/60 border border-brand-accent/50 text-[10px] text-brand-accent backdrop-blur-sm">
                  MJPEG STREAM
                </div>
              </div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 border-2 border-brand-accent/30 rounded-lg pointer-events-none">
                <div className="absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 border-brand-accent"></div>
                <div className="absolute -top-1 -right-1 w-4 h-4 border-t-2 border-r-2 border-brand-accent"></div>
                <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-2 border-l-2 border-brand-accent"></div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-2 border-r-2 border-brand-accent"></div>
                <div className="absolute -top-6 left-0 w-full text-center text-xs text-brand-accent/70">
                  CENTER OBJECT HERE
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-brand-textMuted uppercase mb-1">Object Name</label>
                <input 
                  type="text" 
                  value={objectName}
                  onChange={(e) => setObjectName(e.target.value)}
                  placeholder="e.g. Water Bottle"
                  className="w-full bg-brand-panel border border-brand-border text-brand-text p-3 text-sm focus:outline-none focus:border-brand-accent uppercase"
                />
              </div>
              
              <div className="flex gap-4">
                <button 
                  onClick={handleCapture}
                  disabled={capturing || !objectName.trim()}
                  className="flex-1 py-3 border border-brand-accent text-brand-accent hover:bg-brand-accent/10 text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider"
                >
                  {capturing ? 'CAPTURING...' : 'CAPTURE FRAME'}
                </button>
                <button 
                  onClick={handleRegister}
                  disabled={captureCount < 5}
                  className="flex-1 py-3 bg-brand-accent text-brand-bg hover:bg-brand-accent/90 text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider"
                >
                  REGISTER OBJECT
                </button>
              </div>

              {statusMsg && (
                <div className={`text-xs p-3 border ${
                  statusType === 'error' ? 'border-status-red text-status-red bg-status-red/10' :
                  statusType === 'success' ? 'border-status-green text-status-green bg-status-green/10' :
                  'border-brand-accent text-brand-accent bg-brand-accent/10'
                }`}>
                  {statusMsg}
                </div>
              )}
              
              <div className="flex justify-between items-center pt-2 border-t border-brand-border/30">
                <span className="text-xs text-brand-textMuted uppercase">Images Captured</span>
                <span className={`text-lg font-bold ${captureCount >= 20 ? 'text-status-green' : captureCount >= 5 ? 'text-brand-accent' : 'text-brand-textMuted'}`}>
                  {captureCount} <span className="text-sm font-normal">/ 20</span>
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column - Registered Objects */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <Card title="REGISTERED ORB PROFILES" className="p-4 h-full max-h-[800px] overflow-y-auto">
            {objects.length === 0 ? (
              <div className="text-sm text-brand-textMuted italic p-4 text-center border border-brand-border border-dashed">
                No objects registered yet.
              </div>
            ) : (
              <div className="space-y-3">
                {objects.map((obj, i) => (
                  <div key={i} className="border border-brand-border bg-brand-panel p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-bold text-sm uppercase">{obj.name}</div>
                      <button 
                        onClick={() => handleDelete(obj.slug)}
                        className="text-xs text-status-red hover:text-red-400 uppercase tracking-wider"
                      >
                        [ DEL ]
                      </button>
                    </div>
                    <div className="flex justify-between text-xs text-brand-textMuted uppercase">
                      <span>SLUG: {obj.slug}</span>
                      <span className="text-brand-accent">{obj.orb_refs_loaded || obj.image_count} FRAMES</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

      </div>
    </div>
  );
};
