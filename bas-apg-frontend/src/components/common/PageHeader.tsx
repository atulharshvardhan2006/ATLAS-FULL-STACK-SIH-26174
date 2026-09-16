import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  rightContent?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, rightContent }) => {
  return (
    <div className="flex justify-between items-end pb-8 mb-10 border-b border-brand-border font-mono">
      <div>
        {subtitle && <p className="text-brand-text mb-2 lowercase tracking-widest text-sm">{subtitle}</p>}
        <h1 className="text-3xl font-semibold text-brand-text tracking-wide lowercase">{title}</h1>
      </div>
      {rightContent && <div className="text-sm">{rightContent}</div>}
    </div>
  );
};
