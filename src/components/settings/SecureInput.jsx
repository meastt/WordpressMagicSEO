/**
 * SecureInput Component
 * Masked input for sensitive values like API keys and passwords
 */
import React, { useState } from 'react';
import './SecureInput.css';

export const SecureInput = ({
    label,
    value,
    onChange,
    placeholder = '••••••••••••••••',
    helpText = null,
    testConnection = null,
    connectionStatus = null, // 'idle' | 'testing' | 'success' | 'error'
    disabled = false
}) => {
    const [isVisible, setIsVisible] = useState(false);
    const [isFocused, setIsFocused] = useState(false);

    const hasValue = value && value.length > 0;
    const maskedValue = hasValue && !isVisible
        ? '•'.repeat(Math.min(value.length, 32))
        : value;

    return (
        <div className={`secure-input ${isFocused ? 'secure-input--focused' : ''}`}>
            <label className="secure-input__label">
                {label}
                {hasValue && (
                    <span className="secure-input__saved-badge">Saved</span>
                )}
            </label>

            <div className="secure-input__wrapper">
                <input
                    type={isVisible ? 'text' : 'password'}
                    className="secure-input__field"
                    value={isVisible ? value : maskedValue}
                    onChange={(e) => onChange(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder={placeholder}
                    disabled={disabled}
                    autoComplete="off"
                    spellCheck="false"
                />

                <div className="secure-input__actions">
                    <button
                        type="button"
                        className="secure-input__toggle"
                        onClick={() => setIsVisible(!isVisible)}
                        title={isVisible ? 'Hide' : 'Show'}
                    >
                        {isVisible ? '🙈' : '👁️'}
                    </button>

                    {testConnection && (
                        <button
                            type="button"
                            className={`secure-input__test ${connectionStatus ? `secure-input__test--${connectionStatus}` : ''}`}
                            onClick={testConnection}
                            disabled={!hasValue || connectionStatus === 'testing'}
                        >
                            {connectionStatus === 'testing' && '⏳'}
                            {connectionStatus === 'success' && '✅'}
                            {connectionStatus === 'error' && '❌'}
                            {(!connectionStatus || connectionStatus === 'idle') && 'Test'}
                        </button>
                    )}
                </div>
            </div>

            {helpText && (
                <p className="secure-input__help">{helpText}</p>
            )}
        </div>
    );
};

export default SecureInput;
