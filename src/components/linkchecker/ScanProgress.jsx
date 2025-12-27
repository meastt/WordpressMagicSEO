/**
 * ScanProgress Component
 * Progress indicator for link scanning
 */
import React from 'react';
import './ScanProgress.css';

export const ScanProgress = ({ progress }) => {
    const percentage = progress.total > 0
        ? Math.round((progress.current / progress.total) * 100)
        : 0;

    return (
        <div className="scan-progress glass-panel">
            <div className="scan-progress__header">
                <div className="scan-progress__spinner liquid-spinner"></div>
                <div className="scan-progress__info">
                    <div className="scan-progress__title">
                        Scanning URLs ({progress.current}/{progress.total})
                    </div>
                    <div className="scan-progress__status">
                        {progress.status}
                    </div>
                </div>
                <div className="scan-progress__percentage">
                    {percentage}%
                </div>
            </div>

            <div className="scan-progress__bar">
                <div
                    className="scan-progress__fill"
                    style={{ width: `${percentage}%` }}
                ></div>
            </div>
        </div>
    );
};

export default ScanProgress;
