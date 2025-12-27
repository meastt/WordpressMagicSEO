/**
 * LinkResultsTable Component  
 * Table displaying scanned links with status and fix options
 */
import React from 'react';
import './LinkResultsTable.css';

export const LinkResultsTable = ({ links, selectedFixes, onToggleFix, onApplyFix }) => {
    const getStatusBadge = (status) => {
        switch (status) {
            case 'broken':
                return <span className="status-badge status-badge--broken">🔴 Broken</span>;
            case 'missing_affiliate':
                return <span className="status-badge status-badge--warning">🟡 Missing Affiliate</span>;
            case 'valid':
                return <span className="status-badge status-badge--valid">🟢 Valid</span>;
            case 'fixed':
                return <span className="status-badge status-badge--fixed">✅ Fixed</span>;
            default:
                return <span className="status-badge">Unknown</span>;
        }
    };

    return (
        <div className="link-results">
            <table className="link-results__table">
                <thead>
                    <tr>
                        <th className="col-select"></th>
                        <th className="col-status">Status</th>
                        <th className="col-anchor">Anchor Text</th>
                        <th className="col-original">Original URL</th>
                        <th className="col-fix">Suggested Fix</th>
                        <th className="col-action">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {links.map(link => (
                        <tr
                            key={link.id}
                            className={`link-row link-row--${link.status}`}
                        >
                            <td className="col-select">
                                {(link.status === 'broken' || link.status === 'missing_affiliate') && !link.applied && (
                                    <input
                                        type="checkbox"
                                        checked={selectedFixes.has(link.id)}
                                        onChange={() => onToggleFix(link.id)}
                                        className="link-checkbox"
                                    />
                                )}
                            </td>
                            <td className="col-status">
                                {getStatusBadge(link.status)}
                            </td>
                            <td className="col-anchor">
                                <span className="anchor-text">{link.anchorText}</span>
                            </td>
                            <td className="col-original">
                                <code className="url-code url-code--original">
                                    {link.originalUrl}
                                </code>
                                {link.statusCode && link.status === 'broken' && (
                                    <span className="status-code">{link.statusCode}</span>
                                )}
                            </td>
                            <td className="col-fix">
                                {link.suggestedFix ? (
                                    <code className="url-code url-code--fix">
                                        {link.suggestedFix}
                                    </code>
                                ) : (
                                    <span className="no-fix">—</span>
                                )}
                            </td>
                            <td className="col-action">
                                {(link.status === 'broken' || link.status === 'missing_affiliate') && !link.applied && (
                                    <button
                                        className="fix-btn"
                                        onClick={() => onApplyFix(link.id)}
                                    >
                                        Apply Fix
                                    </button>
                                )}
                                {link.applied && (
                                    <span className="applied-label">Applied ✓</span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default LinkResultsTable;
