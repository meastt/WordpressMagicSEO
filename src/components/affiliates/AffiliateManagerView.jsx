/**
 * AffiliateManagerView Component
 * Manage affiliate IDs for different networks
 */
import React, { useState, useEffect } from 'react';
import { NetworkCard } from './NetworkCard';
import { AddNetworkModal } from './AddNetworkModal';
import './AffiliateManagerView.css';

// Pre-configured affiliate networks
const DEFAULT_NETWORKS = [
    {
        id: 'amazon',
        name: 'Amazon Associates',
        icon: '📦',
        urlPattern: 'amazon.com',
        paramName: 'tag',
        placeholder: 'yoursite-20',
        helpUrl: 'https://affiliate-program.amazon.com/'
    },
    {
        id: 'shareasale',
        name: 'ShareASale',
        icon: '🤝',
        urlPattern: 'shareasale.com',
        paramName: 'afftrack',
        placeholder: '12345',
        helpUrl: 'https://www.shareasale.com/'
    },
    {
        id: 'cj',
        name: 'CJ Affiliate',
        icon: '🔗',
        urlPattern: 'cj.com|anrdoezrs|dpbolvw',
        paramName: 'sid',
        placeholder: 'your-cj-id',
        helpUrl: 'https://www.cj.com/'
    },
    {
        id: 'impact',
        name: 'Impact',
        icon: '💥',
        urlPattern: 'goto.|imp.i',
        paramName: 'subId1',
        placeholder: 'tracking-id',
        helpUrl: 'https://impact.com/'
    },
    {
        id: 'awin',
        name: 'Awin',
        icon: '🌐',
        urlPattern: 'awin1.com',
        paramName: 'awinaffid',
        placeholder: '123456',
        helpUrl: 'https://www.awin.com/'
    },
    {
        id: 'rakuten',
        name: 'Rakuten Advertising',
        icon: '🎯',
        urlPattern: 'linksynergy|click.linksynergy',
        paramName: 'id',
        placeholder: 'your-rakuten-id',
        helpUrl: 'https://rakutenadvertising.com/'
    }
];

export const AffiliateManagerView = () => {
    const [networks, setNetworks] = useState([]);
    const [showAddModal, setShowAddModal] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Load on mount
    useEffect(() => {
        loadNetworks();
    }, []);

    const loadNetworks = () => {
        const saved = localStorage.getItem('magic_seo_affiliates');
        if (saved) {
            setNetworks(JSON.parse(saved));
        } else {
            // Initialize with default networks (empty IDs)
            setNetworks(DEFAULT_NETWORKS.map(n => ({
                ...n,
                affiliateId: '',
                enabled: false
            })));
        }
    };

    const updateNetwork = (id, updates) => {
        setNetworks(networks.map(n =>
            n.id === id ? { ...n, ...updates } : n
        ));
    };

    const addCustomNetwork = (network) => {
        const newNetwork = {
            ...network,
            id: `custom_${Date.now()}`,
            isCustom: true,
            enabled: true
        };
        setNetworks([...networks, newNetwork]);
        setShowAddModal(false);
    };

    const removeNetwork = (id) => {
        setNetworks(networks.filter(n => n.id !== id));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            localStorage.setItem('magic_seo_affiliates', JSON.stringify(networks));
            // TODO: Save to WordPress options via REST API
        } finally {
            setIsSaving(false);
        }
    };

    const enabledCount = networks.filter(n => n.enabled && n.affiliateId).length;

    return (
        <div className="affiliate-manager">
            <div className="affiliate-header">
                <div>
                    <h1 className="section-title">
                        <span className="section-title__icon">💰</span>
                        Affiliate Link Manager
                    </h1>
                    <p className="affiliate-subtitle">
                        Add your affiliate IDs so Magic SEO can automatically insert proper tracking links.
                    </p>
                </div>

                <div className="affiliate-stats glass-card">
                    <div className="metric-value">{enabledCount}</div>
                    <div className="metric-label">Networks Active</div>
                </div>
            </div>

            <div className="affiliate-grid">
                {networks.map(network => (
                    <NetworkCard
                        key={network.id}
                        network={network}
                        onUpdate={(updates) => updateNetwork(network.id, updates)}
                        onRemove={network.isCustom ? () => removeNetwork(network.id) : null}
                    />
                ))}

                {/* Add Custom Network Card */}
                <button
                    className="add-network-card"
                    onClick={() => setShowAddModal(true)}
                >
                    <span className="add-network-icon">+</span>
                    <span className="add-network-label">Add Custom Network</span>
                </button>
            </div>

            <div className="affiliate-actions">
                <button
                    className="btn-transformative"
                    onClick={handleSave}
                    disabled={isSaving}
                >
                    {isSaving ? '💾 Saving...' : '💾 Save Affiliate Settings'}
                </button>
            </div>

            {showAddModal && (
                <AddNetworkModal
                    onAdd={addCustomNetwork}
                    onClose={() => setShowAddModal(false)}
                />
            )}
        </div>
    );
};

export default AffiliateManagerView;
