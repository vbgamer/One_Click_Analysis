import React from 'react';
import { Menu, Bell, User, Settings } from 'lucide-react';
import '../styles/Header.css';

interface HeaderProps {
  onMenuClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  return (
    <header className="header">
      <div className="header-left">
        <button className="menu-btn" onClick={onMenuClick}>
          <Menu size={24} />
        </button>
        <div className="logo-section">
          <div className="logo">OCA</div>
          <h1>One Click Analysis</h1>
        </div>
      </div>
      
      <div className="header-right">
        <button className="icon-btn" title="Notifications">
          <Bell size={20} />
          <span className="notification-badge">3</span>
        </button>
        <button className="icon-btn" title="Settings">
          <Settings size={20} />
        </button>
        <div className="user-profile">
          <img 
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=vbgamer" 
            alt="User" 
            className="user-avatar"
          />
          <span className="user-name">vbgamer</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
