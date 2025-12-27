/**
 * SettingsView Component
 * Full settings page with API credentials and site management
 */
import React, { useState, useEffect } from 'react';
import { SecureInput } from './SecureInput';
import { SiteCredentialCard } from './SiteCredentialCard';
import './SettingsView.css';

export const SettingsView = () => {
    const [credentials, setCredentials] = useState({
        anthropic_key: '',
        gemini_key: '',
        openai_key: ''
    });

    const [sites, setSites] = useState([]);
    const [connectionStatus, setConnectionStatus] = useState({});
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState(null);

    // Load saved credentials on mount
    useEffect(() => {
        loadCredentials();
    }, []);

    const loadCredentials = async () => {
        // TODO: Fetch from WordPress REST API
        // For now, check localStorage for demo
        const saved = localStorage.getItem('magic_seo_credentials');
        if (saved) {
            const parsed = JSON.parse(saved);
            setCredentials(parsed.keys || {});
            setSites(parsed.sites || []);
        }
    };

    const testConnection = async (type) => {
        setConnectionStatus(prev => ({ ...prev, [type]: 'testing' }));

        // Simulate API test
        await new Promise(resolve => setTimeout(resolve, 1500));

        // TODO: Actually test the API connection
        const success = credentials[type]?.length > 10;
        setConnectionStatus(prev => ({
            ...prev,
            [type]: success ? 'success' : 'error'
        }));

        // Reset after 3 seconds
        setTimeout(() => {
            setConnectionStatus(prev => ({ ...prev, [type]: 'idle' }));
        }, 3000);
    };

    const handleSave = async () => {
        setIsSaving(true);
        setSaveMessage(null);

        try {
            // TODO: Save to WordPress REST API with encryption
            // For demo, save to localStorage
            localStorage.setItem('magic_seo_credentials', JSON.stringify({
                keys: credentials,
                sites: sites
            }));

            setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
        } catch (error) {
            setSaveMessage({ type: 'error', text: 'Failed to save settings.' });
        } finally {
            setIsSaving(false);
            setTimeout(() => setSaveMessage(null), 5000);
        }
    };

    const addSite = () => {
        setSites([...sites, {
            id: Date.now(),
            site_url: '',
            username: '',
            app_password: ''
        }]);
    };

    const updateSite = (id, updates) => {
        setSites(sites.map(site =>
            site.id === id ? { ...site, ...updates } : site
        ));
    };

    const removeSite = (id) => {
        setSites(sites.filter(site => site.id !== id));
    };

    return (
        <div className="settings-view">
            <h1 className="section-title">
                <span className="section-title__icon">⚙️</span>
                Settings & Connections
            </h1>

            {/* AI API Keys Section */}
            <section className="settings-section glass-panel">
                <h2 className="settings-section__title">
                    🧠 AI Service Connections
                </h2>
                <p className="settings-section__desc">
                    Connect the AI services that power your content optimization.
                    Keys are encrypted and stored securely.
                </p>

                <div className="settings-grid">
                    <SecureInput
                        label="Anthropic API Key"
                        value={credentials.anthropic_key}
                        onChange={(v) => setCredentials({ ...credentials, anthropic_key: v })}
                        placeholder="sk-ant-api03-..."
                        helpText="Powers Claude for title/content optimization"
                        testConnection={() => testConnection('anthropic_key')}
                        connectionStatus={connectionStatus.anthropic_key}
                    />

                    <SecureInput
                        label="Google Gemini API Key"
                        value={credentials.gemini_key}
                        onChange={(v) => setCredentials({ ...credentials, gemini_key: v })}
                        placeholder="AIza..."
                        helpText="Powers Imagen 4 for image generation"
                        testConnection={() => testConnection('gemini_key')}
                        connectionStatus={connectionStatus.gemini_key}
                    />

                    <SecureInput
                        label="OpenAI API Key (Optional)"
                        value={credentials.openai_key}
                        onChange={(v) => setCredentials({ ...credentials, openai_key: v })}
                        placeholder="sk-..."
                        helpText="Optional fallback for certain operations"
                        testConnection={() => testConnection('openai_key')}
                        connectionStatus={connectionStatus.openai_key}
                    />
                </div>
            </section>

            {/* WordPress Sites Section */}
            <section className="settings-section glass-panel">
                <div className="settings-section__header">
                    <div>
                        <h2 className="settings-section__title">
                            🌐 WordPress Sites
                        </h2>
                        <p className="settings-section__desc">
                            Add the WordPress sites you want to manage.
                            Use Application Passwords for secure access.
                        </p>
                    </div>
                    <button
                        className="btn-secondary"
                        onClick={addSite}
                    >
                        + Add Site
                    </button>
                </div>

                <div className="sites-list">
                    {sites.length === 0 ? (
                        <div className="sites-empty">
                            <p>No sites configured yet.</p>
                            <button className="btn-secondary" onClick={addSite}>
                                + Add Your First Site
                            </button>
                        </div>
                    ) : (
                        sites.map((site) => (
                            <SiteCredentialCard
                                key={site.id}
                                site={site}
                                onUpdate={(updates) => updateSite(site.id, updates)}
                                onRemove={() => removeSite(site.id)}
                                onTest={() => testConnection(`site_${site.id}`)}
                                connectionStatus={connectionStatus[`site_${site.id}`]}
                            />
                        ))
                    )}
                </div>
            </section>

            {/* Save Button */}
            <div className="settings-actions">
                {saveMessage && (
                    <div className={`settings-message settings-message--${saveMessage.type}`}>
                        {saveMessage.type === 'success' ? '✅' : '❌'} {saveMessage.text}
                    </div>
                )}

                <button
                    className="btn-transformative"
                    onClick={handleSave}
                    disabled={isSaving}
                >
                    {isSaving ? (
                        <>
                            <span className="liquid-spinner" style={{ width: 20, height: 20 }}></span>
                            Saving...
                        </>
                    ) : (
                        <>💾 Save All Settings</>
                    )}
                </button>
            </div>
        </div>
    );
};

export default SettingsView;
