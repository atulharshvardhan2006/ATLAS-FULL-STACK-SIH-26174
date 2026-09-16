import React from 'react';

type StatusType = 'neutral' | 'green' | 'amber' | 'red';

interface StatusIndicatorProps {
  status: StatusType;
  label: string;
}

const statusColors: Record<StatusType, string> = {
  neutral: 'bg-brand-textLight',
  green: 'bg-status-green',
  amber: 'bg-brand-accent', // use gold for amber
  red: 'bg-status-red',
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, label }) => {
  return (
    <div className="flex items-center space-x-2 font-mono">
      <div className={`w-1.5 h-1.5 rounded-full ${statusColors[status]}`} />
      <span className="text-sm font-semibold tracking-wide text-brand-text lowercase">{label}</span>
    </div>
  );
};
