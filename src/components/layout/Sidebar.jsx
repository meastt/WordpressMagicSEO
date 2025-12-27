/**
 * Sidebar Component
 * Navigation sidebar with glassmorphic styling
 */
import React from 'react';
import './Sidebar.css';

export const Sidebar = ({ activeTab, onTabChange }) => {
    const tabs = [
        { id: 'audit', label: 'SEO Audit', icon: '🔍' },
        { id: 'content', label: 'Content Intel', icon: '📈' },
        { id: 'affiliates', label: 'Affiliates', icon: '💰' },
        { id: 'settings', label: 'Settings', icon: '⚙️' }
    ];

    return (
        <aside className="sidebar">
            <div className="sidebar__header">
                <div className="sidebar__logo">
                    <span className="logo-icon">🪄</span>
                    <span className="logo-text">Magic SEO</span>
                </div>
                <span className="sidebar__badge">Pro</span>
            </div>

            <nav className="sidebar__nav">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        className={`sidebar__item ${activeTab === tab.id ? 'sidebar__item--active' : ''}`}
                        onClick={() => onTabChange(tab.id)}
                    >
                        <span className="sidebar__icon">{tab.icon}</span>
                        <span className="sidebar__label">{tab.label}</span>
                        {activeTab === tab.id && (
                            <div className="sidebar__indicator"></div>
                        )}
                    </button>
                ))}
            </nav>

            <div className="sidebar__footer">
                <div className="sidebar__status">
                    <span className="status-dot status-dot--online"></span>
                    <span className="sidebar__status-text">All Systems Online</span>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
