/**
 * LiquidToggle Component
 * Toggle switch with liquid fill animation, spring easing, and squish effect
 */
import React from 'react';
import './LiquidToggle.css';

export const LiquidToggle = ({
    checked,
    onChange,
    label,
    disabled = false,
    id = null
}) => {
    const toggleId = id || `toggle-${Math.random().toString(36).substr(2, 9)}`;

    return (
        <label className={`liquid-toggle ${disabled ? 'liquid-toggle--disabled' : ''}`} htmlFor={toggleId}>
            <input
                type="checkbox"
                id={toggleId}
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                disabled={disabled}
                className="liquid-toggle__input"
            />
            <div className="liquid-toggle__track">
                <div className="liquid-toggle__thumb">
                    <div className="liquid-toggle__liquid"></div>
                </div>
            </div>
            <span className="liquid-toggle__label">{label}</span>
        </label>
    );
};

export default LiquidToggle;
