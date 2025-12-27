/**
 * AuditRunner Component
 * Runs full site audit with progress indicator
 * Connects to PHP backend via WordPress REST API
 */
import React, { useState, useEffect, useRef } from 'react';
import { transformAuditData } from '../../utils/auditDataTransformer';
import './AuditRunner.css';

export const AuditRunner = ({
    siteUrl,
    onComplete,
    onError
}) => {
    const [status, setStatus] = useState('starting'); // starting, crawling, analyzing, complete, error
    const [progress, setProgress] = useState({
        urlsScanned: 0,
        totalUrls: 0,
        issuesFound: 0,
        currentUrl: '',
        percent: 0
    });
    const [errorMessage, setErrorMessage] = useState('');
    const pollInterval = useRef(null);

    useEffect(() => {
        startAudit();

        return () => {
            // Cleanup polling on unmount
            if (pollInterval.current) {
                clearInterval(pollInterval.current);
            }
        };
    }, []);

    const getApiUrl = () => {
        // In WordPress context, use the localized data
        if (typeof window !== 'undefined' && window.magicSeoData?.apiUrl) {
            console.log('[Magic SEO] Using API URL:', window.magicSeoData.apiUrl);
            return window.magicSeoData.apiUrl;
        }
        // Fallback for dev
        console.log('[Magic SEO] Using fallback API URL');
        return '/wp-json/magic-seo/v1/';
    };

    const getNonce = () => {
        const nonce = window.magicSeoData?.nonce || '';
        console.log('[Magic SEO] Nonce:', nonce ? 'present' : 'MISSING');
        return nonce;
    };

    const startAudit = async () => {
        console.log('[Magic SEO] Starting audit for:', siteUrl);

        try {
            setStatus('crawling');

            const apiUrl = getApiUrl();
            const auditUrl = `${apiUrl}audit/start`;

            console.log('[Magic SEO] Calling:', auditUrl);
            console.log('[Magic SEO] Request body:', { site_url: siteUrl });

            // Start the audit
            const response = await fetch(auditUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-WP-Nonce': getNonce()
                },
                credentials: 'same-origin', // Important for WP cookies
                body: JSON.stringify({
                    site_url: siteUrl
                })
            });

            console.log('[Magic SEO] Response status:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Magic SEO] Response error:', errorText);
                throw new Error(`Audit failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('[Magic SEO] Audit result:', result);

            if (result.success) {
                // Audit complete - fetch results
                console.log('[Magic SEO] Audit successful, fetching results...');
                await fetchResults();
            } else if (result.error) {
                // Handle error from API
                throw new Error(result.error);
            } else {
                throw new Error(result.message || 'Audit failed - unknown error');
            }

        } catch (error) {
            console.error('[Magic SEO] Audit error:', error);
            setStatus('error');
            setErrorMessage(error.message);
            onError(error.message);
        }
    };

    const fetchResults = async () => {
        try {
            setStatus('analyzing');

            const apiUrl = getApiUrl();

            const response = await fetch(`${apiUrl}audit/results`, {
                headers: {
                    'X-WP-Nonce': getNonce()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch audit results');
            }

            const rawData = await response.json();

            if (rawData.error) {
                throw new Error(rawData.error);
            }

            // Transform to frontend format
            const results = transformAuditData(rawData);

            setProgress({
                urlsScanned: results.total_urls_checked,
                totalUrls: results.total_urls_checked,
                issuesFound: (results.summary?.critical_issues || 0) + (results.summary?.warnings || 0),
                currentUrl: '',
                percent: 100
            });

            setStatus('complete');

            // Brief delay to show completion
            setTimeout(() => {
                onComplete(results);
            }, 500);

        } catch (error) {
            console.error('Error fetching results:', error);
            setStatus('error');
            setErrorMessage(error.message);
            onError(error.message);
        }
    };

    const getPercentage = () => {
        return progress.percent;
    };

    return (
        <div className="audit-runner">
            <div className="audit-runner__card glass-panel">
                <div className="audit-runner__header">
                    {status !== 'error' && (
                        <div className="audit-runner__spinner liquid-spinner"></div>
                    )}
                    {status === 'error' && (
                        <div className="audit-runner__error-icon">⚠️</div>
                    )}
                    <div className="audit-runner__info">
                        <h2 className="audit-runner__title">
                            {status === 'starting' && 'Initializing...'}
                            {status === 'crawling' && 'Auditing Site'}
                            {status === 'analyzing' && 'Analyzing Results'}
                            {status === 'complete' && 'Audit Complete!'}
                            {status === 'error' && 'Audit Failed'}
                        </h2>
                        <p className="audit-runner__url">
                            {siteUrl}
                        </p>
                    </div>
                </div>

                {/* Progress Bar */}
                {status !== 'error' && (
                    <div className="audit-runner__progress">
                        <div className="progress-bar">
                            <div
                                className="progress-bar__fill"
                                style={{ width: `${getPercentage()}%` }}
                            ></div>
                        </div>
                        <span className="progress-percentage">{getPercentage()}%</span>
                    </div>
                )}

                {/* Error Message */}
                {status === 'error' && (
                    <div className="audit-runner__error-message">
                        <p>{errorMessage}</p>
                        <div className="audit-runner__error-actions">
                            <button
                                className="btn-primary"
                                onClick={() => {
                                    setErrorMessage('');
                                    startAudit();
                                }}
                            >
                                🔄 Retry Audit
                            </button>
                            <button
                                className="btn-secondary"
                                onClick={() => {
                                    // Clear local storage and notify parent
                                    localStorage.removeItem('magic_seo_config');
                                    localStorage.removeItem('magic_seo_audit');
                                    window.location.reload();
                                }}
                            >
                                ↩ Start Over
                            </button>
                        </div>
                    </div>
                )}

                {/* Stats */}
                {status !== 'error' && (
                    <div className="audit-runner__stats">
                        <div className="stat">
                            <span className="stat__value">{progress.urlsScanned}</span>
                            <span className="stat__label">URLs Scanned</span>
                        </div>
                        <div className="stat">
                            <span className="stat__value">{progress.totalUrls || '—'}</span>
                            <span className="stat__label">Total URLs</span>
                        </div>
                        <div className="stat">
                            <span className="stat__value stat__value--issues">{progress.issuesFound}</span>
                            <span className="stat__label">Issues Found</span>
                        </div>
                    </div>
                )}

                {/* Current URL - show during crawling */}
                {status === 'crawling' && progress.currentUrl && (
                    <div className="audit-runner__current">
                        <span className="current-label">Scanning:</span>
                        <code className="current-url">{progress.currentUrl}</code>
                    </div>
                )}

                {/* Info message */}
                {status === 'crawling' && (
                    <div className="audit-runner__info-message">
                        <p>🕐 This may take a few minutes for large sites. Please keep this page open.</p>
                    </div>
                )}

                {/* Cancel / Start Over link - always visible */}
                <div className="audit-runner__reset-link">
                    <button
                        className="btn-link"
                        onClick={() => {
                            if (confirm('Cancel audit and start over? This will clear all settings.')) {
                                localStorage.removeItem('magic_seo_config');
                                localStorage.removeItem('magic_seo_audit');
                                window.location.reload();
                            }
                        }}
                    >
                        ✕ Cancel & Start Over
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AuditRunner;
