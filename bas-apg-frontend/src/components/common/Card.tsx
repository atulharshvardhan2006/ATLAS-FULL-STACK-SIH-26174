import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ title, children, className = '' }) => {
  return (
    <div className={`mb-6 border border-brand-border bg-brand-panel ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-brand-border">
          <h3 className="font-mono text-sm font-semibold text-brand-text tracking-widest lowercase">{title}</h3>
        </div>
      )}
      <div className="p-6">
        {children}
      </div>
    </div>
  );
};
