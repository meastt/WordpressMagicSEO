/**
 * AddNetworkModal Component
 * Modal for adding a custom affiliate network
 */
import React, { useState } from 'react';
import './AddNetworkModal.css';

export const AddNetworkModal = ({ onAdd, onClose }) => {
    const [network, setNetwork] = useState({
        name: '',
        icon: '🔗',
        urlPattern: '',
        paramName: '',
        affiliateId: '',
        helpUrl: ''
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!network.name || !network.urlPattern || !network.paramName) return;
        onAdd(network);
    };

    const emojiOptions = ['🔗', '💰', '🛒', '🏪', '📦', '🎁', '💳', '🌟', '🚀', '⚡'];

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content glass-floating" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">Add Custom Network</h2>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="modal-field">
                        <label>Network Name</label>
                        <input
                            type="text"
                            className="glass-input__field"
                            value={network.name}
                            onChange={e => setNetwork({ ...network, name: e.target.value })}
                            placeholder="e.g., ClickBank"
                            required
                        />
                    </div>

                    <div className="modal-field">
                        <label>Icon</label>
                        <div className="emoji-picker">
                            {emojiOptions.map(emoji => (
                                <button
                                    key={emoji}
                                    type="button"
                                    className={`emoji-option ${network.icon === emoji ? 'emoji-option--selected' : ''}`}
                                    onClick={() => setNetwork({ ...network, icon: emoji })}
                                >
                                    {emoji}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="modal-field">
                        <label>URL Pattern (domain match)</label>
                        <input
                            type="text"
                            className="glass-input__field"
                            value={network.urlPattern}
                            onChange={e => setNetwork({ ...network, urlPattern: e.target.value })}
                            placeholder="e.g., clickbank.com|hop.clickbank"
                            required
                        />
                        <small>Use | to separate multiple patterns</small>
                    </div>

                    <div className="modal-field">
                        <label>Affiliate Parameter Name</label>
                        <input
                            type="text"
                            className="glass-input__field"
                            value={network.paramName}
                            onChange={e => setNetwork({ ...network, paramName: e.target.value })}
                            placeholder="e.g., affid, tag, ref"
                            required
                        />
                    </div>

                    <div className="modal-field">
                        <label>Your Affiliate ID</label>
                        <input
                            type="text"
                            className="glass-input__field"
                            value={network.affiliateId}
                            onChange={e => setNetwork({ ...network, affiliateId: e.target.value })}
                            placeholder="Your ID for this network"
                        />
                    </div>

                    <div className="modal-field">
                        <label>Help URL (optional)</label>
                        <input
                            type="url"
                            className="glass-input__field"
                            value={network.helpUrl}
                            onChange={e => setNetwork({ ...network, helpUrl: e.target.value })}
                            placeholder="https://..."
                        />
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="btn-transformative">
                            Add Network
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddNetworkModal;
