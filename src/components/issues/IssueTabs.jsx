/**
 * IssueTabs Component
 * Tabbed navigation for issue categories - dynamically generated from actual audit data
 */
import React from 'react';
import { getIssueTypeName, getIssueWeight } from '../../utils/auditDataTransformer';
import './IssueTabs.css';

export const IssueTabs = ({
    activeTab,
    onTabChange,
    issueCounts = {}
}) => {
    // Build tabs dynamically from actual data
    // Sort by issue weight (most impactful first), then by count
    const tabs = Object.entries(issueCounts)
        .filter(([_, count]) => count > 0)
        .map(([id, count]) => ({
            id,
            label: getIssueTypeName(id),
            count,
            weight: getIssueWeight(id)
        }))
        .sort((a, b) => {
            // Sort by weight descending, then by count descending
            if (b.weight !== a.weight) return b.weight - a.weight;
            return b.count - a.count;
        });

    if (tabs.length === 0) {
        return (
            <div className="issue-tabs issue-tabs--empty">
                <p>No issues found! 🎉</p>
            </div>
        );
    }

    // If active tab is not in current tabs, select first one
    const currentActiveTab = tabs.find(t => t.id === activeTab)
        ? activeTab
        : tabs[0]?.id;

    // Notify parent if we changed the tab
    React.useEffect(() => {
        if (currentActiveTab && currentActiveTab !== activeTab) {
            onTabChange(currentActiveTab);
        }
    }, [currentActiveTab, activeTab, onTabChange]);

    return (
        <div className="issue-tabs">
            <div className="issue-tabs__scroll">
                {tabs.map(tab => {
                    const isActive = currentActiveTab === tab.id;

                    return (
                        <button
                            key={tab.id}
                            className={`issue-tab ${isActive ? 'issue-tab--active' : ''}`}
                            onClick={() => onTabChange(tab.id)}
                        >
                            <span className="issue-tab__label">{tab.label}</span>
                            <span className={`issue-tab__count ${tab.weight >= 8 ? 'issue-tab__count--critical' : ''}`}>
                                {tab.count}
                            </span>
                            {isActive && <div className="issue-tab__indicator"></div>}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default IssueTabs;
