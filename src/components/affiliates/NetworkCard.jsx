/**
 * NetworkCard Component
 * Card for configuring a single affiliate network
 */
import React from 'react';
import { LiquidToggle } from '../station/LiquidToggle';
import './NetworkCard.css';

export const NetworkCard = ({ network, onUpdate, onRemove }) => {
    const hasId = network.affiliateId && network.affiliateId.length > 0;

    // Generate preview URL
    const getPreviewUrl = () => {
        if (!hasId) return null;

        const baseUrl = `https://${network.urlPattern.split('|')[0]}/.../product`;
        return `${baseUrl}?${network.paramName}=${network.affiliateId}`;
    };

    return (
        <div className={`network-card glass-card ${network.enabled ? 'network-card--active' : ''}`}>
            <div className="network-card__header">
                <div className="network-card__icon">{network.icon}</div>
                <div className="network-card__info">
                    <h3 className="network-card__name">{network.name}</h3>
                    {network.isCustom && (
                        <span className="network-card__badge">Custom</span>
                    )}
                </div>
                <LiquidToggle
                    checked={network.enabled}
                    onChange={(enabled) => onUpdate({ enabled })}
                    disabled={!hasId}
                />
            </div>

            <div className="network-card__body">
                <label className="network-card__label">
                    Affiliate ID / Tracking Tag
                </label>
                <input
                    type="text"
                    className="glass-input__field"
                    value={network.affiliateId || ''}
                    onChange={(e) => onUpdate({ affiliateId: e.target.value })}
                    placeholder={network.placeholder}
                />

                {hasId && (
                    <div className="network-card__preview">
                        <span className="network-card__preview-label">Preview:</span>
                        <code className="network-card__preview-url">
                            {getPreviewUrl()}
                        </code>
                    </div>
                )}

                <div className="network-card__footer">
                    <a
                        href={network.helpUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="network-card__link"
                    >
                        Learn more →
                    </a>

                    {onRemove && (
                        <button
                            className="network-card__remove"
                            onClick={onRemove}
                        >
                            🗑️
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default NetworkCard;
