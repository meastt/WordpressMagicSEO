/**
 * Magic SEO Dashboard - Main App Component
 * Redesigned UX: Onboarding → Audit → Score → Issues → Fixes
 */
import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { CircularScore } from './components/score/CircularScore';
import { AuditRunner } from './components/audit/AuditRunner';
import { IssueTabs } from './components/issues/IssueTabs';
import { IssueTable } from './components/issues/IssueTable';
import { BulkActions } from './components/issues/BulkActions';
import { SettingsView } from './components/settings/SettingsView';
import { AffiliateManagerView } from './components/affiliates/AffiliateManagerView';
import { calculateHealthScore } from './utils/auditDataTransformer';
import './styles/global.css';

// App states
const STATES = {
    LOADING: 'loading',
    ONBOARDING: 'onboarding',
    AUDITING: 'auditing',
    DASHBOARD: 'dashboard'
};

const App = () => {
    const [appState, setAppState] = useState(STATES.LOADING);
    const [activeTab, setActiveTab] = useState('audit');
    const [config, setConfig] = useState(null);
    const [auditResults, setAuditResults] = useState(null);
    const [activeIssueTab, setActiveIssueTab] = useState('h1_presence');
    const [selectedUrls, setSelectedUrls] = useState(new Set());
    const [isFixing, setIsFixing] = useState(false);

    // Check if onboarded on mount
    useEffect(() => {
        const savedConfig = localStorage.getItem('magic_seo_config');
        const savedAudit = localStorage.getItem('magic_seo_audit');

        if (savedConfig) {
            setConfig(JSON.parse(savedConfig));
            if (savedAudit) {
                setAuditResults(JSON.parse(savedAudit));
                setAppState(STATES.DASHBOARD);
            } else {
                setAppState(STATES.AUDITING);
            }
        } else {
            setAppState(STATES.ONBOARDING);
        }
    }, []);

    // Onboarding complete
    const handleOnboardingComplete = (newConfig) => {
        setConfig(newConfig);
        setAppState(STATES.AUDITING);
    };

    // Audit complete
    const handleAuditComplete = (results) => {
        setAuditResults(results);
        localStorage.setItem('magic_seo_audit', JSON.stringify(results));
        setAppState(STATES.DASHBOARD);
    };

    // Calculate health score using proper formula
    const calculateScore = () => {
        return calculateHealthScore(auditResults?.summary);
    };

    // Get issue counts per tab
    const getIssueCounts = () => {
        if (!auditResults?.issues_by_type) return {};
        const counts = {};
        Object.entries(auditResults.issues_by_type).forEach(([type, issues]) => {
            counts[type] = issues.length;
        });
        return counts;
    };

    // Get current issues
    const getCurrentIssues = () => {
        if (!auditResults?.issues_by_type) return [];
        return auditResults.issues_by_type[activeIssueTab] || [];
    };

    // Selection handlers
    const toggleSelect = (url) => {
        const newSelected = new Set(selectedUrls);
        if (newSelected.has(url)) {
            newSelected.delete(url);
        } else {
            newSelected.add(url);
        }
        setSelectedUrls(newSelected);
    };

    const selectAll = (select) => {
        if (select) {
            setSelectedUrls(new Set(getCurrentIssues().map(i => i.url)));
        } else {
            setSelectedUrls(new Set());
        }
    };

    // API helpers
    const getApiUrl = () => {
        if (typeof window !== 'undefined' && window.magicSeoData?.apiUrl) {
            return window.magicSeoData.apiUrl;
        }
        return '/wp-json/magic-seo/v1/';
    };

    const getNonce = () => window.magicSeoData?.nonce || '';

    // Fix handlers
    const callFixApi = async (issueType, urls) => {
        const response = await fetch(`${getApiUrl()}fix/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-WP-Nonce': getNonce()
            },
            body: JSON.stringify({
                issue_type: issueType,
                urls: urls
            })
        });

        if (!response.ok) {
            throw new Error('Fix request failed');
        }

        return response.json();
    };

    const fixSingle = async (url) => {
        setIsFixing(true);
        try {
            // Add initial delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 1000));
            await callFixApi(activeIssueTab, [url]);
            removeFixedUrls([url]);
        } catch (error) {
            console.error('Fix failed:', error);
            alert('Fix failed: ' + error.message);
        }
        setIsFixing(false);
    };

    const fixSelected = async () => {
        setIsFixing(true);
        const urls = [...selectedUrls];
        try {
            // Add initial delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 1000));
            await callFixApi(activeIssueTab, urls);
            removeFixedUrls(urls);
            setSelectedUrls(new Set());
        } catch (error) {
            console.error('Batch fix failed:', error);
            alert('Batch fix failed: ' + error.message);
        }
        setIsFixing(false);
    };

    const fixAll = async () => {
        setIsFixing(true);
        const urls = getCurrentIssues().map(i => i.url);
        try {
            // Add initial delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 1000));
            await callFixApi(activeIssueTab, urls);
            removeFixedUrls(urls);
            setSelectedUrls(new Set());
        } catch (error) {
            console.error('Fix all failed:', error);
            alert('Fix all failed: ' + error.message);
        }
        setIsFixing(false);
    };

    const removeFixedUrls = (urls) => {
        const urlSet = new Set(urls);
        const updated = { ...auditResults };
        updated.issues_by_type[activeIssueTab] = updated.issues_by_type[activeIssueTab]
            .filter(i => !urlSet.has(i.url));

        // Balanced adjustment: move from critical to passed to keep total same
        updated.summary.critical_issues = Math.max(0, updated.summary.critical_issues - urls.length);
        updated.summary.passed = (updated.summary.passed || 0) + urls.length;

        setAuditResults(updated);
        localStorage.setItem('magic_seo_audit', JSON.stringify(updated));
    };

    // Re-run audit
    const handleReAudit = () => {
        localStorage.removeItem('magic_seo_audit');
        setAuditResults(null);
        setAppState(STATES.AUDITING);
    };

    // Loading state
    if (appState === STATES.LOADING) {
        return (
            <div className="magic-seo-app magic-seo-app--full-width loading-screen">
                <div className="liquid-spinner" style={{ width: 48, height: 48 }}></div>
            </div>
        );
    }

    // Onboarding state
    if (appState === STATES.ONBOARDING) {
        return (
            <div className="magic-seo-app magic-seo-app--full-width onboarding-screen">
                <OnboardingWizard onComplete={handleOnboardingComplete} />
            </div>
        );
    }

    // Auditing state
    if (appState === STATES.AUDITING) {
        return (
            <div className="magic-seo-app magic-seo-app--full-width">
                <AuditRunner
                    siteUrl={config.siteUrl}
                    onComplete={handleAuditComplete}
                    onError={(err) => console.error(err)}
                />
            </div>
        );
    }

    // Dashboard state
    return (
        <div className="magic-seo-app">
            <Sidebar
                activeTab={activeTab}
                onTabChange={setActiveTab}
            />

            <main className="magic-seo-main">
                {activeTab === 'audit' && (
                    <div className="view-audit">
                        {/* Header with Score */}
                        <div className="audit-header">
                            <div className="audit-header__info">
                                <h1 className="section-title">
                                    <span className="section-title__icon">🔍</span>
                                    Technical SEO Audit
                                </h1>
                                <p className="audit-site">{config.siteUrl}</p>
                            </div>

                            <CircularScore score={calculateScore()} />

                            <div className="audit-header__actions">
                                <button
                                    className="btn-secondary"
                                    onClick={handleReAudit}
                                >
                                    🔄 Re-run Audit
                                </button>
                            </div>
                        </div>

                        {/* Summary Stats */}
                        <div className="audit-stats">
                            <div className="stat-card glass-card">
                                <span className="stat-value">{(auditResults?.summary?.critical_issues || 0) + (auditResults?.summary?.warnings || 0) + (auditResults?.summary?.passed || 0)}</span>
                                <span className="stat-label">Total Checks</span>
                                <span className="stat-sublabel">{auditResults?.total_urls_checked || 0} pages</span>
                            </div>
                            <div className="stat-card glass-card stat-card--critical">
                                <span className="stat-value">{auditResults?.summary?.critical_issues || 0}</span>
                                <span className="stat-label">Critical</span>
                            </div>
                            <div className="stat-card glass-card stat-card--warning">
                                <span className="stat-value">{auditResults?.summary?.warnings || 0}</span>
                                <span className="stat-label">Warnings</span>
                            </div>
                            <div className="stat-card glass-card stat-card--success">
                                <span className="stat-value">{auditResults?.summary?.passed || 0}</span>
                                <span className="stat-label">Passed</span>
                            </div>
                        </div>

                        {/* Issue Tabs */}
                        <IssueTabs
                            activeTab={activeIssueTab}
                            onTabChange={(tab) => {
                                setActiveIssueTab(tab);
                                setSelectedUrls(new Set());
                            }}
                            issueCounts={getIssueCounts()}
                        />

                        {/* Issue Table */}
                        <IssueTable
                            issues={getCurrentIssues()}
                            selectedUrls={selectedUrls}
                            onToggleSelect={toggleSelect}
                            onSelectAll={selectAll}
                            onFixSingle={fixSingle}
                            isFixing={isFixing}
                            pluginManager={auditResults?.urls?.[0]?.metadata?.plugin_manager}
                        />

                        {/* Bulk Actions */}
                        <BulkActions
                            selectedCount={selectedUrls.size}
                            totalCount={getCurrentIssues().length}
                            onFixSelected={fixSelected}
                            onFixAll={fixAll}
                            isFixing={isFixing}
                        />
                    </div>
                )}

                {activeTab === 'content' && (
                    <div className="view-content">
                        <h1 className="section-title">
                            <span className="section-title__icon">📈</span>
                            Content Intelligence
                        </h1>
                        <div className="glass-panel">
                            <p style={{ color: 'var(--warm-gray-500)', marginBottom: 16 }}>
                                Upload your Google Search Console export (CSV) to get AI-powered content recommendations.
                            </p>
                            <p className="handwritten">Coming soon! ✨</p>
                        </div>
                    </div>
                )}

                {activeTab === 'affiliates' && <AffiliateManagerView />}
                {activeTab === 'settings' && <SettingsView />}
            </main>
        </div>
    );
};

export default App;
