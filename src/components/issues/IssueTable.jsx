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
    isFixing = false
}) => {
    const allSelected = issues.length > 0 && selectedUrls.size === issues.length;
    const someSelected = selectedUrls.size > 0 && selectedUrls.size < issues.length;

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
                        <tr
                            key={issue.url || idx}
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
                            </td>
                            <td className="col-issue">
                                <span className="issue-message">{issue.message}</span>
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
