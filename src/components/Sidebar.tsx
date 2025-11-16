import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, FolderOpen, Plus, BarChart3, Clock, History, Settings, LogOut } from 'lucide-react';
import '../styles/Sidebar.css';

interface SidebarProps {
  isOpen: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen }) => {
  const navigate = useNavigate();

  const menuItems = [
    { icon: Home, label: 'Dashboard', path: '/' },
    { icon: Plus, label: 'New Project', path: '/new-project' },
    { icon: FolderOpen, label: 'Project List', path: '/projects' },
    { icon: Clock, label: 'Recent Work', path: '/recent' },
    { icon: History, label: 'History', path: '/history' },
    { icon: BarChart3, label: 'Analytics', path: '/analytics' },
  ];

  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <button
            key={item.path}
            className="sidebar-item"
            onClick={() => navigate(item.path)}
            title={item.label}
          >
            <item.icon size={20} />
            {isOpen && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-item" title="Settings">
          <Settings size={20} />
          {isOpen && <span>Settings</span>}
        </button>
        <button className="sidebar-item logout" title="Logout">
          <LogOut size={20} />
          {isOpen && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
