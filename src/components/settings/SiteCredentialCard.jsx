/**
 * SiteCredentialCard Component
 * Card for managing a single WordPress site's credentials
 */
import React, { useState } from 'react';
import { SecureInput } from './SecureInput';
import './SiteCredentialCard.css';

export const SiteCredentialCard = ({
    site,
    onUpdate,
    onRemove,
    onTest,
    connectionStatus
}) => {
    const [isExpanded, setIsExpanded] = useState(!site.site_url);

    return (
        <div className={`site-card ${isExpanded ? 'site-card--expanded' : ''}`}>
            <div className="site-card__header" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="site-card__info">
                    <span className="site-card__icon">🌐</span>
                    <div>
                        <h3 className="site-card__url">
                            {site.site_url || 'New Site'}
                        </h3>
                        {site.username && (
                            <span className="site-card__user">@{site.username}</span>
                        )}
                    </div>
                </div>

                <div className="site-card__actions">
                    {connectionStatus === 'success' && (
                        <span className="site-card__status site-card__status--connected">
                            ✅ Connected
                        </span>
                    )}
                    {connectionStatus === 'error' && (
                        <span className="site-card__status site-card__status--error">
                            ❌ Failed
                        </span>
                    )}
                    <button className="site-card__expand">
                        {isExpanded ? '▲' : '▼'}
                    </button>
                </div>
            </div>

            {isExpanded && (
                <div className="site-card__body">
                    <div className="site-card__field">
                        <label className="site-card__label">Site URL</label>
                        <input
                            type="url"
                            className="glass-input__field"
                            value={site.site_url}
                            onChange={(e) => onUpdate({ site_url: e.target.value })}
                            placeholder="https://yoursite.com"
                        />
                    </div>

                    <div className="site-card__field">
                        <label className="site-card__label">Username</label>
                        <input
                            type="text"
                            className="glass-input__field"
                            value={site.username}
                            onChange={(e) => onUpdate({ username: e.target.value })}
                            placeholder="admin"
                        />
                    </div>

                    <SecureInput
                        label="Application Password"
                        value={site.app_password}
                        onChange={(v) => onUpdate({ app_password: v })}
                        placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                        helpText={
                            <>
                                Generate in WordPress: Users → Profile → Application Passwords
                                <a
                                    href="https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ marginLeft: 8, color: 'var(--teal-500)' }}
                                >
                                    Learn more →
                                </a>
                            </>
                        }
                        testConnection={onTest}
                        connectionStatus={connectionStatus}
                    />

                    <div className="site-card__footer">
                        <button
                            className="btn-danger"
                            onClick={onRemove}
                        >
                            🗑️ Remove Site
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SiteCredentialCard;
