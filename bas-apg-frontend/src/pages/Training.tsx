import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';

export const Training: React.FC = () => {
  const [objectName, setObjectName] = useState('');
  const [description, setDescription] = useState('');
  const [audioPrompt, setAudioPrompt] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [captureCount, setCaptureCount] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'info' | 'error' | 'success'>('info');

  const [experimentName, setExperimentName] = useState('');
  const [experimentSteps, setExperimentSteps] = useState<any[]>([]);

  const slugify = (text: string) => text.toLowerCase().replace(/\s+/g, '_').replace(/-+/g, '_');
  const currentSlug = slugify(objectName);

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
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ok') {
        // Automatically add this object as a step in the background!
        setExperimentSteps(prev => [
          ...prev, 
          { 
            action: "DETECT", 
            object: currentSlug, 
            description: description.trim() || `Detect ${objectName}`,
            audio_prompt: audioPrompt.trim() || `Please detect the ${objectName}.`
          }
        ]);

        setStatusMsg(`Successfully registered '${objectName}'. It is now part of the experiment.`);
        setStatusType('success');
        setCaptureCount(0);
        setObjectName('');
        setDescription('');
        setAudioPrompt('');
      }
    })
    .catch(err => {
      console.error(err);
      setStatusMsg("Failed to extract features.");
      setStatusType('error');
    });
  };

  const handleDeployExperiment = () => {
    if (!experimentName.trim()) {
      alert("Please name your experiment first.");
      return;
    }
    if (experimentSteps.length === 0) {
      alert("You need to capture and register at least one object before deploying.");
      return;
    }

    fetch('http://localhost:8000/api/procedures/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: experimentName,
        steps: experimentSteps
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ok') {
        alert("Experiment Deployed successfully! You can now close this window and select it in the Setup page.");
        setExperimentName('');
        setExperimentSteps([]);
        setStatusMsg('');
      }
    });
  };

  return (
    <div className="min-h-screen bg-brand-bg font-mono text-brand-text p-6">
      <div className="max-w-7xl mx-auto">
        <PageHeader title="A.T.L.A.S TRAINING SUITE" subtitle="OBJECT REGISTRATION & DEPLOYMENT" />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-6">
          
          {/* LEFT SIDE: CAMERA AND CAPTURE */}
          <div className="flex flex-col gap-6">
            
            {/* BOX 1: CAMERA FEED */}
            <Card title="1. LIVE CAMERA FEED" className="p-4">
              <div className="relative aspect-video bg-black border border-brand-border/50 overflow-hidden">
                <img 
                  src="http://localhost:8000/video_feed" 
                  alt="Live Camera Feed" 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    setTimeout(() => {
                      (e.target as HTMLImageElement).src = "http://localhost:8000/video_feed?retry=" + new Date().getTime();
                    }, 2000);
                  }}
                />
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 border-2 border-brand-accent/30 rounded-lg pointer-events-none">
                  <div className="absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 border-brand-accent"></div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 border-t-2 border-r-2 border-brand-accent"></div>
                  <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-2 border-l-2 border-brand-accent"></div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-2 border-r-2 border-brand-accent"></div>
                </div>
              </div>
            </Card>

            {/* BOX 2: OBJECT CAPTURE CONTROLS */}
            <Card title="2. OBJECT CAPTURE" className="p-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-brand-textMuted uppercase mb-1">New Object Name</label>
                  <input 
                    type="text" 
                    value={objectName}
                    onChange={(e) => setObjectName(e.target.value)}
                    placeholder="e.g. PHONE"
                    className="w-full bg-brand-panel border border-brand-border text-brand-text p-3 text-sm focus:outline-none focus:border-brand-accent uppercase"
                  />
                </div>

                <div>
                  <label className="block text-xs text-brand-textMuted uppercase mb-1">Checklist Text (Mission Dashboard)</label>
                  <input 
                    type="text" 
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. Scan the astronaut's mobile phone"
                    className="w-full bg-brand-panel border border-brand-border text-brand-text p-3 text-sm focus:outline-none focus:border-brand-accent"
                  />
                </div>

                <div>
                  <label className="block text-xs text-brand-textMuted uppercase mb-1">AI Audio Prompt (What it says)</label>
                  <input 
                    type="text" 
                    value={audioPrompt}
                    onChange={(e) => setAudioPrompt(e.target.value)}
                    placeholder="e.g. Please present your mobile device for scanning."
                    className="w-full bg-brand-panel border border-brand-border text-brand-text p-3 text-sm focus:outline-none focus:border-brand-accent"
                  />
                </div>
                
                <div className="flex gap-4">
                  <button 
                    onClick={handleCapture}
                    disabled={capturing || !objectName.trim()}
                    className="flex-1 py-3 border border-brand-accent text-brand-accent hover:bg-brand-accent/10 text-sm font-bold uppercase disabled:opacity-50"
                  >
                    {capturing ? 'CAPTURING...' : 'CAPTURE IMAGE'}
                  </button>
                  <button 
                    onClick={handleRegister}
                    disabled={captureCount < 5}
                    className="flex-1 py-3 bg-brand-accent text-brand-bg hover:bg-brand-accent/90 text-sm font-bold uppercase disabled:opacity-50"
                  >
                    FINISH & ADD TO EXPERIMENT
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
                
                <div className="flex justify-between items-center text-xs text-brand-textMuted uppercase">
                  <span>Images Captured: {captureCount}</span>
                  <span>Minimum Required: 5</span>
                </div>
              </div>
            </Card>
          </div>

          {/* RIGHT SIDE: EXPERIMENT DEPLOYMENT */}
          <div className="flex flex-col gap-6">
            
            {/* BOX 3: DEPLOY EXPERIMENT */}
            <Card title="3. DEPLOY EXPERIMENT" className="p-4 flex flex-col justify-center min-h-[250px]">
              <div className="space-y-6">
                <div>
                  <label className="block text-xs text-brand-textMuted uppercase mb-2">Experiment Name</label>
                  <input 
                    type="text" 
                    value={experimentName}
                    onChange={(e) => setExperimentName(e.target.value)}
                    placeholder="e.g. MY CUSTOM EXPERIMENT"
                    className="w-full bg-brand-panel border border-brand-border text-brand-text p-4 text-lg focus:outline-none focus:border-brand-accent uppercase"
                  />
                </div>

                <button 
                  onClick={handleDeployExperiment}
                  className="w-full py-5 bg-status-green text-brand-bg hover:bg-status-green/90 text-lg font-bold uppercase tracking-widest"
                >
                  DEPLOY TO LIFTOFF
                </button>
                
                <div className="text-xs text-brand-textMuted text-center leading-relaxed">
                  When deployed, the captured objects will be saved as a new mission protocol. You can select it in the Setup dropdown in Liftoff.
                </div>
              </div>
            </Card>

          </div>
        </div>
      </div>
    </div>
  );
};
