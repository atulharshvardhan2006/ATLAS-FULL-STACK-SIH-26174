import React from 'react';
import { useLocation } from 'react-router-dom';

export const Header: React.FC = () => {
  const location = useLocation();
  
  const getPageTitle = (pathname: string) => {
    switch (pathname) {
      case '/setup':
      case '/':
        return 'Setup';
      case '/mission':
        return 'Mission';
      case '/audit':
        return 'Audit';
      case '/station':
        return 'Station';
      default:
        return 'Overview';
    }
  };

  return (
    <header className="flex items-center justify-between h-16 px-8 bg-brand-bg border-b border-brand-border shrink-0 sticky top-0 z-10 font-mono">
      <div className="flex items-baseline space-x-6">
        <div className="text-sm font-semibold text-brand-text lowercase tracking-wide">
          {getPageTitle(location.pathname)}
        </div>
      </div>
      

    </header>
  );
};
