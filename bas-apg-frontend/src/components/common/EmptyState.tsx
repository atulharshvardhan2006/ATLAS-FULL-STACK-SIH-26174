import React from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description }) => {
  return (
    <div className="flex flex-col items-start justify-center py-10 px-8 text-brand-text bg-brand-bg font-mono">
      <h3 className="text-base font-semibold text-brand-text lowercase tracking-wide">{title}</h3>
      {description && <p className="mt-2 text-base font-medium">{description}</p>}
    </div>
  );
};
