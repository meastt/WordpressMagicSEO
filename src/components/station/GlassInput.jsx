/**
 * GlassInput Component
 * Glassmorphic input field with icon and label
 */
import React from 'react';

export const GlassInput = ({
    type = 'text',
    placeholder = '',
    value,
    onChange,
    icon = null,
    label = null,
    disabled = false,
    id = null
}) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    return (
        <div className="glass-input">
            {label && (
                <label className="glass-input__label" htmlFor={inputId}>
                    {label}
                </label>
            )}
            <div className="glass-input__wrapper">
                <input
                    type={type}
                    id={inputId}
                    className="glass-input__field"
                    placeholder={placeholder}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    disabled={disabled}
                />
                {icon && (
                    <span className="glass-input__icon">{icon}</span>
                )}
            </div>
        </div>
    );
};

export default GlassInput;
