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
        openai_key: '',
        python_engine_url: 'http://localhost:5000',
        use_ai_fixes: true
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
        try {
            const response = await fetch(`${window.magicSeoData.apiUrl}settings`, {
                headers: {
                    'X-WP-Nonce': window.magicSeoData.nonce
                }
            });
            if (response.ok) {
                const data = await response.json();
                setCredentials({
                    anthropic_key: data.anthropic_key || '',
                    gemini_key: data.gemini_key || '',
                    openai_key: data.openai_key || '',
                    python_engine_url: data.python_engine_url || 'http://localhost:5000',
                    use_ai_fixes: data.use_ai_fixes !== undefined ? data.use_ai_fixes : true
                });
                setSites(data.sites || []);
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    };

    const testConnection = async (type) => {
        setConnectionStatus(prev => ({ ...prev, [type]: 'testing' }));

        try {
            let success = false;

            if (type === 'anthropic_key' && credentials.anthropic_key) {
                // Test Anthropic API
                const resp = await fetch('https://api.anthropic.com/v1/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': credentials.anthropic_key,
                        'anthropic-version': '2023-06-01'
                    },
                    body: JSON.stringify({
                        model: 'claude-3-haiku-20240307',
                        max_tokens: 10,
                        messages: [{ role: 'user', content: 'Hi' }]
                    })
                });
                success = resp.ok || resp.status === 429; // 429 = rate limited but key is valid
            } else if (type === 'gemini_key' && credentials.gemini_key) {
                // Test Gemini API
                const resp = await fetch(`https://generativelanguage.googleapis.com/v1/models?key=${credentials.gemini_key}`);
                success = resp.ok;
            } else if (type === 'openai_key' && credentials.openai_key) {
                // Test OpenAI API
                const resp = await fetch('https://api.openai.com/v1/models', {
                    headers: { 'Authorization': `Bearer ${credentials.openai_key}` }
                });
                success = resp.ok;
            } else if (type.startsWith('site_')) {
                // Test WordPress site credentials via Magic SEO API (avoids CORS issues)
                const siteId = type.replace('site_', '');
                const site = sites.find(s => s.id === siteId);
                if (site && site.site_url && site.username && site.app_password) {
                    const resp = await fetch(`${window.magicSeoData.apiUrl}test-credentials`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-WP-Nonce': window.magicSeoData.nonce
                        },
                        body: JSON.stringify({
                            site_url: site.site_url,
                            username: site.username,
                            app_password: site.app_password
                        })
                    });
                    const data = await resp.json();
                    success = data.success === true;
                }
            }

            setConnectionStatus(prev => ({
                ...prev,
                [type]: success ? 'success' : 'error'
            }));
        } catch (error) {
            console.error('Connection test failed:', error);
            setConnectionStatus(prev => ({ ...prev, [type]: 'error' }));
        }

        // Reset after 3 seconds
        setTimeout(() => {
            setConnectionStatus(prev => ({ ...prev, [type]: 'idle' }));
        }, 3000);
    };

    const handleSave = async () => {
        setIsSaving(true);
        setSaveMessage(null);

        try {
            const response = await fetch(`${window.magicSeoData.apiUrl}settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-WP-Nonce': window.magicSeoData.nonce
                },
                body: JSON.stringify({
                    ...credentials,
                    sites: sites
                })
            });

            if (!response.ok) throw new Error('Failed to save');

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

            {/* AI Engine Configuration */}
            <section className="settings-section glass-panel">
                <h2 className="settings-section__title">
                    ⚡ Optimization Engine (Python Bridge)
                </h2>
                <p className="settings-section__desc">
                    Configure the AI Engine that performs advanced SEO optimizations.
                    The engine must be running locally or on a remote server.
                </p>

                <div className="settings-grid">
                    <div className="input-field">
                        <label className="input-label">AI Engine URL</label>
                        <input
                            type="text"
                            className="text-input"
                            value={credentials.python_engine_url}
                            onChange={(e) => setCredentials({ ...credentials, python_engine_url: e.target.value })}
                            placeholder="http://localhost:5000"
                        />
                        <p className="input-help">The URL of your running Flask/Python SEO API</p>
                    </div>

                    <div className="toggle-field" style={{ marginTop: '1rem' }}>
                        <label className="toggle-label" style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={credentials.use_ai_fixes}
                                onChange={(e) => setCredentials({ ...credentials, use_ai_fixes: e.target.checked })}
                                style={{ width: '20px', height: '20px' }}
                            />
                            <span style={{ fontWeight: 500 }}>Use AI Engine for Fixes (Recommended)</span>
                        </label>
                        <p className="input-help" style={{ marginTop: '4px' }}>
                            When enabled, the dashboard will use the AI Engine for high-quality rewrites.
                            Otherwise, it uses basic truncation.
                        </p>
                    </div>
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
