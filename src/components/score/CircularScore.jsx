/**
 * CircularScore Component
 * Animated circular progress bar with score (0-100) and color gradient
 */
import React, { useEffect, useState } from 'react';
import './CircularScore.css';

export const CircularScore = ({
    score = 0,
    size = 180,
    strokeWidth = 12,
    label = 'Health Score',
    animated = true
}) => {
    const [displayScore, setDisplayScore] = useState(animated ? 0 : score);

    // Animate score on mount/change
    useEffect(() => {
        if (!animated) {
            setDisplayScore(score);
            return;
        }

        let current = 0;
        const increment = score / 40; // Animate over ~40 frames
        const timer = setInterval(() => {
            current += increment;
            if (current >= score) {
                setDisplayScore(score);
                clearInterval(timer);
            } else {
                setDisplayScore(Math.round(current));
            }
        }, 20);

        return () => clearInterval(timer);
    }, [score, animated]);

    // Calculate circle dimensions
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (displayScore / 100) * circumference;

    // Get color based on score
    const getColor = (s) => {
        if (s >= 90) return '#22c55e'; // Green
        if (s >= 70) return '#eab308'; // Yellow
        if (s >= 50) return '#f97316'; // Orange
        return '#ef4444'; // Red
    };

    // Get gradient colors
    const getGradientId = () => {
        if (displayScore >= 90) return 'gradient-green';
        if (displayScore >= 70) return 'gradient-yellow';
        if (displayScore >= 50) return 'gradient-orange';
        return 'gradient-red';
    };

    const getScoreLabel = (s) => {
        if (s >= 90) return 'Excellent';
        if (s >= 70) return 'Good';
        if (s >= 50) return 'Fair';
        return 'Needs Work';
    };

    return (
        <div className="circular-score" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="circular-score__svg">
                {/* Gradient definitions */}
                <defs>
                    <linearGradient id="gradient-green" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#22c55e" />
                        <stop offset="100%" stopColor="#16a34a" />
                    </linearGradient>
                    <linearGradient id="gradient-yellow" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#eab308" />
                        <stop offset="100%" stopColor="#ca8a04" />
                    </linearGradient>
                    <linearGradient id="gradient-orange" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#f97316" />
                        <stop offset="100%" stopColor="#ea580c" />
                    </linearGradient>
                    <linearGradient id="gradient-red" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#ef4444" />
                        <stop offset="100%" stopColor="#dc2626" />
                    </linearGradient>
                </defs>

                {/* Background circle */}
                <circle
                    className="circular-score__bg"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                />

                {/* Progress circle */}
                <circle
                    className="circular-score__progress"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    stroke={`url(#${getGradientId()})`}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                />
            </svg>

            <div className="circular-score__content">
                <span
                    className="circular-score__value"
                    style={{ color: getColor(displayScore) }}
                >
                    {displayScore}
                </span>
                <span className="circular-score__label">{label}</span>
                <span
                    className="circular-score__status"
                    style={{ color: getColor(displayScore) }}
                >
                    {getScoreLabel(displayScore)}
                </span>
            </div>
        </div>
    );
};

export default CircularScore;
