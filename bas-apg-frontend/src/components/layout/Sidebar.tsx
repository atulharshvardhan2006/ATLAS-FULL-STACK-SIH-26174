import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'motion/react';
import { Settings, Target, FileText, Lock, Gauge, Camera } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useMissionContext } from '../../context/MissionContext';

export const Sidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true);

  const { isMissionUnlocked } = useMissionContext();

  const navItems = [
    { path: '/setup', label: 'Setup', icon: <Settings size={20} /> },
    { 
      path: isMissionUnlocked ? '/mission' : '#', 
      label: 'Mission', 
      icon: isMissionUnlocked ? <Target size={20} /> : <Lock size={20} className="text-status-red" />,
      locked: !isMissionUnlocked
    },
    { path: '/audit', label: 'Audit Log', icon: <FileText size={20} /> },
    { path: '/station', label: 'Station', icon: <Gauge size={20} /> },
  ];

  const sidebarVariants = {
    open: { width: '256px' }, // 256px matches w-64
    closed: { width: '80px' } // 80px matches w-20
  };

  return (
    <motion.nav
      initial="open"
      animate={isOpen ? 'open' : 'closed'}
      variants={sidebarVariants}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="bg-brand-bg border-r border-brand-border flex flex-col shrink-0 h-full font-mono text-brand-text overflow-hidden"
    >
      <div className="px-5 border-b border-brand-border flex items-center h-16 shrink-0">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center cursor-pointer hover:opacity-80 transition-opacity"
        >
          <div className="w-10 h-10 flex items-center justify-center shrink-0 rounded-lg hover:bg-brand-border transition-colors">
            <img src="/logo.png" alt="A" className="w-6 h-6 filter invert" />
          </div>
          
          <motion.div
            initial={false}
            animate={{ 
              opacity: isOpen ? 1 : 0,
              width: isOpen ? 'auto' : 0,
              marginLeft: isOpen ? '-6px' : '0px'
            }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden flex items-center"
          >
            <span className="font-logo font-bold text-xl tracking-widest uppercase whitespace-nowrap">
              TLAS
            </span>
          </motion.div>
        </button>
      </div>
      
      <div className="flex-1 py-6 flex flex-col gap-2 px-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              twMerge(
                clsx(
                  'group flex items-center h-12 rounded-lg transition-colors px-3',
                  {
                    'cursor-not-allowed opacity-50': item.locked,
                    'cursor-pointer': !item.locked,
                    'text-brand-accent': isActive && !item.locked,
                    'text-brand-text hover:text-brand-text hover:bg-brand-border/50': !isActive && !item.locked,
                  }
                )
              )
            }
            onClick={(e) => {
              if (item.locked) {
                e.preventDefault();
              }
            }}
          >
            <div className="shrink-0 w-8 flex items-center justify-center">
              {item.icon}
            </div>
            <motion.div
              initial={false}
              animate={{
                opacity: isOpen ? 1 : 0,
                width: isOpen ? 'auto' : 0,
                marginLeft: isOpen ? '12px' : '0px'
              }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="overflow-hidden whitespace-nowrap text-[15px] font-medium lowercase tracking-wide"
            >
              {item.label}
            </motion.div>
          </NavLink>
        ))}
      </div>
    </motion.nav>
  );
};
