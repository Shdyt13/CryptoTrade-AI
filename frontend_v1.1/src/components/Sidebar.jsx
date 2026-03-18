import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, LineChart, Terminal } from 'lucide-react';

const Sidebar = () => {
  const location = useLocation();

  const menuItems = [
    { path: '/', name: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { path: '/analytics', name: 'Akurasi & Evaluasi', icon: <LineChart size={20} /> },
  ];

  return (
    <div className="w-64 bg-slate-900 border-r border-slate-800 min-h-screen p-4 flex flex-col fixed left-0 top-0 hidden md:flex">
      {/* Logo Area */}
      <div className="flex items-center gap-2 mb-10 px-2">
        <div className="bg-blue-600 p-2 rounded-lg">
          <Terminal size={24} className="text-white"/>
        </div>
        <div>
          <h1 className="font-bold text-white text-lg">ETH Predictor</h1>
          <p className="text-xs text-slate-500">v1.1 Enterprise</p>
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 space-y-2">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive 
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {item.icon}
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Kecil */}
      <div className="text-xs text-slate-600 px-2 mt-auto">
        &copy; 2025 Sapar Hidayat
      </div>
    </div>
  );
};

export default Sidebar;