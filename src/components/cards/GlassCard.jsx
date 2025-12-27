/**
 * GlassCard Component
 * Glassmorphic metric card with frosted glass effect, organic borders, and hover glow
 */
import React from 'react';

export const GlassCard = ({
    value,
    label,
    icon,
    trend = null,
    trendDirection = 'up', // 'up' | 'down' | 'neutral'
    className = '',
    onClick = null
}) => {
    return (
        <div
            className={`glass-card ${onClick ? 'glass-card--clickable' : ''} ${className}`}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            <div className="glass-card__content">
                {icon && (
                    <div className="glass-card__icon">
                        {icon}
                    </div>
                )}

                <div className="metric-value">
                    {value}
                </div>

                <div className="metric-label">
                    {label}
                </div>

                {trend !== null && (
                    <div className={`glass-card__trend glass-card__trend--${trendDirection}`}>
                        <TrendIndicator value={trend} direction={trendDirection} />
                    </div>
                )}
            </div>
        </div>
    );
};

const TrendIndicator = ({ value, direction }) => {
    const arrow = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
    const color = direction === 'up' ? 'var(--mint)' : direction === 'down' ? 'var(--coral)' : 'var(--warm-gray-500)';

    return (
        <span style={{ color, fontWeight: 600, fontSize: 'var(--text-sm)' }}>
            {arrow} {value}
        </span>
    );
};

export default GlassCard;
