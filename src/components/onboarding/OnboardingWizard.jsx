/**
 * OnboardingWizard Component
 * First-run setup flow for new users
 */
import React, { useState } from 'react';
import './OnboardingWizard.css';

export const OnboardingWizard = ({ onComplete }) => {
    const [step, setStep] = useState(1);
    const [config, setConfig] = useState({
        siteUrl: '',
        username: '',
        appPassword: ''
    });
    const [isValidating, setIsValidating] = useState(false);
    const [error, setError] = useState(null);

    const handleNext = async () => {
        if (step === 1) {
            // Validate site URL
            if (!config.siteUrl || !config.siteUrl.startsWith('http')) {
                setError('Please enter a valid site URL starting with http:// or https://');
                return;
            }
            setStep(2);
            setError(null);
        } else if (step === 2) {
            // Credentials are optional, proceed
            setStep(3);
        } else if (step === 3) {
            // Complete onboarding
            setIsValidating(true);
            try {
                // Save to localStorage
                localStorage.setItem('magic_seo_config', JSON.stringify(config));
                localStorage.setItem('magic_seo_onboarded', 'true');

                // Notify parent
                onComplete(config);
            } catch (err) {
                setError('Failed to save configuration');
            } finally {
                setIsValidating(false);
            }
        }
    };

    const handleBack = () => {
        setStep(step - 1);
        setError(null);
    };

    return (
        <div className="onboarding-overlay">
            <div className="onboarding-wizard glass-floating">
                <div className="onboarding-header">
                    <span className="onboarding-logo">🪄</span>
                    <h1 className="onboarding-title">Welcome to Magic SEO</h1>
                    <p className="onboarding-subtitle">
                        Let's set up your technical SEO audit
                    </p>
                </div>

                {/* Progress Dots */}
                <div className="onboarding-progress">
                    {[1, 2, 3].map(n => (
                        <div
                            key={n}
                            className={`progress-dot ${step >= n ? 'progress-dot--active' : ''}`}
                        />
                    ))}
                </div>

                <div className="onboarding-body">
                    {/* Step 1: Site URL */}
                    {step === 1 && (
                        <div className="onboarding-step fade-in">
                            <h2 className="step-title">What site do you want to audit?</h2>
                            <p className="step-desc">
                                Enter your WordPress site URL. We'll crawl it to find SEO issues.
                            </p>
                            <div className="step-input">
                                <label>Site URL</label>
                                <input
                                    type="url"
                                    className="glass-input__field"
                                    placeholder="https://yoursite.com"
                                    value={config.siteUrl}
                                    onChange={(e) => setConfig({ ...config, siteUrl: e.target.value })}
                                    autoFocus
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Credentials (Optional) */}
                    {step === 2 && (
                        <div className="onboarding-step fade-in">
                            <h2 className="step-title">WordPress Credentials</h2>
                            <p className="step-desc">
                                Optional: Add credentials to enable automatic fixes.
                                <br />
                                <span className="step-hint">You can skip this and add later.</span>
                            </p>
                            <div className="step-input">
                                <label>Username</label>
                                <input
                                    type="text"
                                    className="glass-input__field"
                                    placeholder="admin"
                                    value={config.username}
                                    onChange={(e) => setConfig({ ...config, username: e.target.value })}
                                />
                            </div>
                            <div className="step-input">
                                <label>Application Password</label>
                                <input
                                    type="password"
                                    className="glass-input__field"
                                    placeholder="xxxx xxxx xxxx xxxx"
                                    value={config.appPassword}
                                    onChange={(e) => setConfig({ ...config, appPassword: e.target.value })}
                                />
                                <small className="step-help">
                                    Generate in WordPress: Users → Profile → Application Passwords
                                </small>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Ready */}
                    {step === 3 && (
                        <div className="onboarding-step fade-in">
                            <div className="step-ready">
                                <span className="step-ready-icon">🚀</span>
                                <h2 className="step-title">Ready to Audit!</h2>
                                <p className="step-desc">
                                    We'll crawl <strong>{config.siteUrl}</strong> and analyze every page for SEO issues.
                                </p>
                                <div className="step-summary">
                                    <div className="summary-item">
                                        <span className="summary-icon">🔍</span>
                                        <span>Full site crawl</span>
                                    </div>
                                    <div className="summary-item">
                                        <span className="summary-icon">📊</span>
                                        <span>Health score (0-100)</span>
                                    </div>
                                    <div className="summary-item">
                                        <span className="summary-icon">🔧</span>
                                        <span>One-click fixes</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="onboarding-error">
                            ⚠️ {error}
                        </div>
                    )}
                </div>

                <div className="onboarding-footer">
                    {step > 1 && (
                        <button
                            className="btn-secondary"
                            onClick={handleBack}
                        >
                            ← Back
                        </button>
                    )}

                    {step === 2 && (
                        <button
                            className="btn-text"
                            onClick={() => setStep(3)}
                        >
                            Skip for now
                        </button>
                    )}

                    <button
                        className="btn-transformative"
                        onClick={handleNext}
                        disabled={isValidating}
                    >
                        {isValidating ? (
                            'Saving...'
                        ) : step === 3 ? (
                            '🔍 Start Audit'
                        ) : (
                            'Continue →'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default OnboardingWizard;
