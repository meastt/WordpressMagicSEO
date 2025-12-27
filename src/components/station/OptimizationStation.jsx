/**
 * OptimizationStation Component
 * Main action area with glassmorphic inputs, liquid toggles, and transformative CTA
 */
import React, { useState } from 'react';
import { LiquidToggle } from './LiquidToggle';
import { GlassInput } from './GlassInput';
import { MorphingProgress } from '../progress/MorphingProgress';
import './OptimizationStation.css';

export const OptimizationStation = ({
    onOptimize,
    isRunning = false,
    currentStep = 0,
    steps = ['Analyzing Content', 'Claude is Thinking', 'Imagen is Painting', 'Finalizing']
}) => {
    const [url, setUrl] = useState('');
    const [keyword, setKeyword] = useState('');
    const [options, setOptions] = useState({
        fixTitle: true,
        enhanceContent: true,
        generateImage: true
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!url || !keyword) return;

        onOptimize?.({
            url,
            keyword,
            options
        });
    };

    return (
        <div className="optimization-station">
            {/* Animated Blob Backgrounds */}
            <div className="station-blob-bg">
                <div className="blob blob--teal blob-1"></div>
                <div className="blob blob--mint blob-2"></div>
            </div>

            <div className="station-content">
                <h2 className="station-title">
                    <span className="station-title__icon">✨</span>
                    <span className="hand-underline">Optimization Station</span>
                </h2>

                <p className="station-desc">
                    Transform your content with AI-powered optimization
                </p>

                <form onSubmit={handleSubmit} className="station-form">
                    <div className="station-inputs">
                        <GlassInput
                            type="url"
                            placeholder="https://yoursite.com/post-to-optimize..."
                            value={url}
                            onChange={setUrl}
                            icon="🔗"
                            label="Target URL"
                            disabled={isRunning}
                        />

                        <GlassInput
                            type="text"
                            placeholder="e.g., best portable grills 2026"
                            value={keyword}
                            onChange={setKeyword}
                            icon="🎯"
                            label="Target Keyword"
                            disabled={isRunning}
                        />
                    </div>

                    <div className="station-options">
                        <LiquidToggle
                            label="Fix Title (High CTR)"
                            checked={options.fixTitle}
                            onChange={(v) => setOptions({ ...options, fixTitle: v })}
                            disabled={isRunning}
                        />

                        <LiquidToggle
                            label="Enhance Content"
                            checked={options.enhanceContent}
                            onChange={(v) => setOptions({ ...options, enhanceContent: v })}
                            disabled={isRunning}
                        />

                        <LiquidToggle
                            label="Generate Visuals"
                            checked={options.generateImage}
                            onChange={(v) => setOptions({ ...options, generateImage: v })}
                            disabled={isRunning}
                        />
                    </div>

                    {isRunning ? (
                        <div className="station-progress">
                            <MorphingProgress
                                currentStep={currentStep}
                                steps={steps}
                            />
                        </div>
                    ) : (
                        <button
                            type="submit"
                            className="btn-transformative btn-haptic pulse-glow"
                            disabled={!url || !keyword}
                        >
                            <SparkleIcon />
                            Run Optimization
                        </button>
                    )}
                </form>
            </div>
        </div>
    );
};

const SparkleIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z" />
    </svg>
);

export default OptimizationStation;
