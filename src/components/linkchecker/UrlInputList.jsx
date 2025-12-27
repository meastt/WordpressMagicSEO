/**
 * UrlInputList Component
 * Dynamic list of URL inputs with add/remove functionality
 */
import React from 'react';
import './UrlInputList.css';

export const UrlInputList = ({ urls, onChange, disabled }) => {
    const addUrl = () => {
        onChange([...urls, '']);
    };

    const removeUrl = (index) => {
        if (urls.length <= 1) return;
        onChange(urls.filter((_, i) => i !== index));
    };

    const updateUrl = (index, value) => {
        onChange(urls.map((url, i) => i === index ? value : url));
    };

    return (
        <div className="url-input-list">
            <label className="url-input-list__label">
                Post URLs to Scan
            </label>

            <div className="url-input-list__items">
                {urls.map((url, index) => (
                    <div key={index} className="url-input-item">
                        <span className="url-input-item__icon">🔗</span>
                        <input
                            type="url"
                            className="glass-input__field"
                            value={url}
                            onChange={(e) => updateUrl(index, e.target.value)}
                            placeholder="https://yoursite.com/post-to-scan..."
                            disabled={disabled}
                        />
                        {urls.length > 1 && (
                            <button
                                type="button"
                                className="url-input-item__remove"
                                onClick={() => removeUrl(index)}
                                disabled={disabled}
                                title="Remove"
                            >
                                −
                            </button>
                        )}
                    </div>
                ))}
            </div>

            <button
                type="button"
                className="url-input-list__add"
                onClick={addUrl}
                disabled={disabled}
            >
                + Add Another URL
            </button>
        </div>
    );
};

export default UrlInputList;
