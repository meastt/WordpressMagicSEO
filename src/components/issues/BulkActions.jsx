/**
 * BulkActions Component
 * Actions bar for batch fixing issues
 */
import React, { useState } from 'react';
import './BulkActions.css';

export const BulkActions = ({
    selectedCount = 0,
    totalCount = 0,
    onFixSelected,
    onFixAll,
    isFixing = false,
    fixProgress = null // { current: 3, total: 10 }
}) => {
    const [showConfirm, setShowConfirm] = useState(false);

    const handleFixAll = () => {
        if (totalCount > 10) {
            setShowConfirm(true);
        } else {
            onFixAll();
        }
    };

    return (
        <div className="bulk-actions">
            <div className="bulk-actions__info">
                {selectedCount > 0 ? (
                    <span className="selected-count">
                        <strong>{selectedCount}</strong> of {totalCount} selected
                    </span>
                ) : (
                    <span className="total-count">
                        <strong>{totalCount}</strong> issues found
                    </span>
                )}
            </div>

            <div className="bulk-actions__buttons">
                {selectedCount > 0 && (
                    <button
                        className="btn-secondary"
                        onClick={onFixSelected}
                        disabled={isFixing}
                    >
                        {isFixing && fixProgress ? (
                            <>Fixing {fixProgress.current}/{fixProgress.total}...</>
                        ) : (
                            <>🔧 Fix Selected ({selectedCount})</>
                        )}
                    </button>
                )}

                <button
                    className="btn-transformative btn-fix-all"
                    onClick={handleFixAll}
                    disabled={isFixing || totalCount === 0}
                >
                    {isFixing ? (
                        <>
                            <span className="liquid-spinner" style={{ width: 18, height: 18 }}></span>
                            Fixing...
                        </>
                    ) : (
                        <>🚀 Do It All Now</>
                    )}
                </button>
            </div>

            {/* Confirmation Modal */}
            {showConfirm && (
                <div className="confirm-overlay" onClick={() => setShowConfirm(false)}>
                    <div className="confirm-modal glass-floating" onClick={e => e.stopPropagation()}>
                        <h3 className="confirm-title">Fix All {totalCount} Issues?</h3>
                        <p className="confirm-desc">
                            This will automatically fix all issues in this category.
                            Changes will be applied directly to your WordPress content.
                        </p>
                        <div className="confirm-actions">
                            <button
                                className="btn-secondary"
                                onClick={() => setShowConfirm(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-transformative"
                                onClick={() => {
                                    setShowConfirm(false);
                                    onFixAll();
                                }}
                            >
                                Yes, Fix All
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default BulkActions;
