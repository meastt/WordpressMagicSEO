/**
 * LinkCheckerView Component
 * AI-powered link checker that scans URLs, validates links, and fixes broken/missing affiliate links
 */
import React, { useState } from 'react';
import { UrlInputList } from './UrlInputList';
import { ScanProgress } from './ScanProgress';
import { LinkResultsTable } from './LinkResultsTable';
import './LinkCheckerView.css';

export const LinkCheckerView = () => {
    const [urls, setUrls] = useState(['']);
    const [isScanning, setIsScanning] = useState(false);
    const [scanProgress, setScanProgress] = useState({ current: 0, total: 0, status: '' });
    const [results, setResults] = useState(null);
    const [selectedFixes, setSelectedFixes] = useState(new Set());

    const handleScan = async () => {
        const validUrls = urls.filter(u => u.trim().length > 0);
        if (validUrls.length === 0) return;

        setIsScanning(true);
        setResults(null);
        setScanProgress({ current: 0, total: validUrls.length, status: 'Starting scan...' });

        // Simulate scanning process
        const allResults = {
            summary: {
                totalLinks: 0,
                brokenLinks: 0,
                missingAffiliate: 0,
                validLinks: 0
            },
            links: []
        };

        for (let i = 0; i < validUrls.length; i++) {
            setScanProgress({
                current: i + 1,
                total: validUrls.length,
                status: `Scanning: ${validUrls[i]}`
            });

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Mock results
            const mockLinks = generateMockLinks(validUrls[i]);
            allResults.links.push(...mockLinks);
            allResults.summary.totalLinks += mockLinks.length;
            allResults.summary.brokenLinks += mockLinks.filter(l => l.status === 'broken').length;
            allResults.summary.missingAffiliate += mockLinks.filter(l => l.status === 'missing_affiliate').length;
            allResults.summary.validLinks += mockLinks.filter(l => l.status === 'valid').length;
        }

        setResults(allResults);
        setIsScanning(false);
    };

    const handleApplyFixes = async (linkIds) => {
        // TODO: Call backend to apply fixes
        console.log('Applying fixes for:', linkIds);

        // Update results to show fixed status
        setResults(prev => ({
            ...prev,
            links: prev.links.map(link =>
                linkIds.includes(link.id)
                    ? { ...link, status: 'fixed', applied: true }
                    : link
            )
        }));

        setSelectedFixes(new Set());
    };

    const handleApplyAll = () => {
        const fixableIds = results.links
            .filter(l => l.status === 'broken' || l.status === 'missing_affiliate')
            .map(l => l.id);
        handleApplyFixes(fixableIds);
    };

    return (
        <div className="link-checker">
            <h1 className="section-title">
                <span className="section-title__icon">🔗</span>
                AI Link Checker
            </h1>

            <p className="link-checker__desc">
                Enter post URLs to scan. I'll find broken links, missing affiliate tags,
                and suggest AI-powered fixes.
            </p>

            {/* URL Input Section */}
            <section className="link-checker__input glass-panel">
                <UrlInputList
                    urls={urls}
                    onChange={setUrls}
                    disabled={isScanning}
                />

                <button
                    className="btn-transformative"
                    onClick={handleScan}
                    disabled={isScanning || urls.filter(u => u.trim()).length === 0}
                >
                    {isScanning ? (
                        <>
                            <span className="liquid-spinner" style={{ width: 20, height: 20 }}></span>
                            Scanning...
                        </>
                    ) : (
                        <>🔍 Scan Links</>
                    )}
                </button>
            </section>

            {/* Progress */}
            {isScanning && (
                <ScanProgress progress={scanProgress} />
            )}

            {/* Results */}
            {results && (
                <section className="link-checker__results">
                    {/* Summary Cards */}
                    <div className="results-summary">
                        <div className="summary-card glass-card">
                            <div className="metric-value">{results.summary.totalLinks}</div>
                            <div className="metric-label">Links Found</div>
                        </div>
                        <div className="summary-card glass-card summary-card--error">
                            <div className="metric-value" style={{ color: 'var(--coral)' }}>
                                {results.summary.brokenLinks}
                            </div>
                            <div className="metric-label">Broken Links</div>
                        </div>
                        <div className="summary-card glass-card summary-card--warning">
                            <div className="metric-value" style={{ color: 'var(--amber)' }}>
                                {results.summary.missingAffiliate}
                            </div>
                            <div className="metric-label">Missing Affiliate</div>
                        </div>
                        <div className="summary-card glass-card summary-card--success">
                            <div className="metric-value" style={{ color: 'var(--mint)' }}>
                                {results.summary.validLinks}
                            </div>
                            <div className="metric-label">Valid Links</div>
                        </div>
                    </div>

                    {/* Results Table */}
                    <LinkResultsTable
                        links={results.links}
                        selectedFixes={selectedFixes}
                        onToggleFix={(id) => {
                            const newSelected = new Set(selectedFixes);
                            if (newSelected.has(id)) {
                                newSelected.delete(id);
                            } else {
                                newSelected.add(id);
                            }
                            setSelectedFixes(newSelected);
                        }}
                        onApplyFix={(id) => handleApplyFixes([id])}
                    />

                    {/* Bulk Actions */}
                    {(results.summary.brokenLinks > 0 || results.summary.missingAffiliate > 0) && (
                        <div className="results-actions">
                            <button
                                className="btn-secondary"
                                onClick={() => {
                                    const fixableIds = results.links
                                        .filter(l => l.status === 'broken' || l.status === 'missing_affiliate')
                                        .map(l => l.id);
                                    setSelectedFixes(new Set(fixableIds));
                                }}
                            >
                                Select All Fixable
                            </button>

                            {selectedFixes.size > 0 && (
                                <button
                                    className="btn-transformative"
                                    onClick={() => handleApplyFixes([...selectedFixes])}
                                >
                                    Apply {selectedFixes.size} Fixes
                                </button>
                            )}

                            <button
                                className="btn-transformative"
                                onClick={handleApplyAll}
                            >
                                🚀 Apply All Fixes
                            </button>
                        </div>
                    )}
                </section>
            )}
        </div>
    );
};

// Mock data generator for demo
const generateMockLinks = (sourceUrl) => {
    const mockLinks = [
        {
            id: `${Date.now()}_1`,
            sourceUrl,
            originalUrl: 'https://amazon.com/dp/B07X123456',
            anchorText: 'Blackstone 36" Griddle',
            status: 'broken',
            statusCode: 404,
            suggestedFix: 'https://amazon.com/dp/B09ABC123?tag=griddleking-20',
            network: 'amazon'
        },
        {
            id: `${Date.now()}_2`,
            sourceUrl,
            originalUrl: 'https://amazon.com/dp/B08DEF789',
            anchorText: 'Weber Spirit Grill',
            status: 'missing_affiliate',
            statusCode: 200,
            suggestedFix: 'https://amazon.com/dp/B08DEF789?tag=griddleking-20',
            network: 'amazon'
        },
        {
            id: `${Date.now()}_3`,
            sourceUrl,
            originalUrl: 'https://amazon.com/dp/B09GHI101?tag=griddleking-20',
            anchorText: 'Cuisinart 360 Griddle',
            status: 'valid',
            statusCode: 200,
            network: 'amazon'
        }
    ];

    return mockLinks;
};

export default LinkCheckerView;
