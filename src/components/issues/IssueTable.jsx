/**
 * IssueTable Component
 * Table displaying URLs with a specific issue type
 */
import React from 'react';
import './IssueTable.css';

export const IssueTable = ({
    issues = [],
    selectedUrls = new Set(),
    onToggleSelect,
    onSelectAll,
    onFixSingle,
    isFixing = false,
    pluginManager = null
}) => {
    const allSelected = issues.length > 0 && selectedUrls.size === issues.length;
    const someSelected = selectedUrls.size > 0 && selectedUrls.size < issues.length;

    const [expandedReasoning, setExpandedReasoning] = React.useState(new Set());

    const toggleReasoning = (url) => {
        const newSet = new Set(expandedReasoning);
        if (newSet.has(url)) newSet.delete(url);
        else newSet.add(url);
        setExpandedReasoning(newSet);
    };

    if (issues.length === 0) {
        return (
            <div className="issue-table__empty">
                <span className="empty-icon">✅</span>
                <p className="empty-text">No issues found in this category!</p>
            </div>
        );
    }

    return (
        <div className="issue-table">
            <table className="issue-table__table">
                <thead>
                    <tr>
                        <th className="col-checkbox">
                            <input
                                type="checkbox"
                                checked={allSelected}
                                ref={el => el && (el.indeterminate = someSelected)}
                                onChange={() => onSelectAll(!allSelected)}
                            />
                        </th>
                        <th className="col-url">URL</th>
                        <th className="col-issue">Issue Details</th>
                        <th className="col-action">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {issues.map((issue, idx) => (
                        <React.Fragment key={issue.url || idx}>
                            <tr
                                className={selectedUrls.has(issue.url) ? 'row--selected' : ''}
                            >
                                <td className="col-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={selectedUrls.has(issue.url)}
                                        onChange={() => onToggleSelect(issue.url)}
                                    />
                                </td>
                                <td className="col-url">
                                    <a
                                        href={issue.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="url-link"
                                    >
                                        {getUrlPath(issue.url)}
                                    </a>
                                    {pluginManager && (
                                        <span className="plugin-badge" title={`Managed by ${pluginManager}`}>
                                            {pluginManager}
                                        </span>
                                    )}
                                </td>
                                <td className="col-issue">
                                    <div className="issue-details-container">
                                        <span className="issue-message">{issue.message}</span>
                                        {issue.reasoning && (
                                            <button
                                                className="reasoning-toggle"
                                                onClick={() => toggleReasoning(issue.url)}
                                                title="View AI Logic"
                                            >
                                                🧠 {expandedReasoning.has(issue.url) ? 'Hide Logic' : 'AI Logic'}
                                            </button>
                                        )}
                                    </div>
                                </td>
                                <td className="col-action">
                                    <button
                                        className="fix-btn"
                                        onClick={() => onFixSingle(issue.url)}
                                        disabled={isFixing}
                                    >
                                        Fix →
                                    </button>
                                </td>
                            </tr>
                            {expandedReasoning.has(issue.url) && issue.reasoning && (
                                <tr className="reasoning-row">
                                    <td colSpan="4">
                                        <div className="reasoning-content">
                                            <div className="reasoning-header">
                                                <span className="reasoning-icon">🤖</span>
                                                <strong>AI Reasoning & Strategy</strong>
                                            </div>
                                            <p className="reasoning-text">{issue.reasoning}</p>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// Helper to extract path from URL
const getUrlPath = (url) => {
    try {
        const u = new URL(url);
        return u.pathname || '/';
    } catch {
        return url;
    }
};

export default IssueTable;
