/**
 * MorphingProgress Component
 * Step indicator with morphing animations and liquid transitions
 */
import React from 'react';
import './MorphingProgress.css';

export const MorphingProgress = ({ currentStep, steps }) => {
    return (
        <div className="morphing-progress">
            {steps.map((step, idx) => (
                <div
                    key={idx}
                    className={`morph-step ${idx < currentStep ? 'morph-step--complete' :
                            idx === currentStep ? 'morph-step--active' :
                                'morph-step--pending'
                        }`}
                >
                    <div className="morph-step__dot">
                        {idx < currentStep && (
                            <svg className="morph-step__check check-animated" viewBox="0 0 16 16">
                                <path
                                    d="M3 8l3 3 7-7"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                />
                            </svg>
                        )}
                        {idx === currentStep && (
                            <>
                                <div className="liquid-spinner"></div>
                                <div className="ripple"></div>
                            </>
                        )}
                        {idx > currentStep && (
                            <span className="morph-step__number">{idx + 1}</span>
                        )}
                    </div>

                    <div className="morph-step__label">{step}</div>

                    {idx < steps.length - 1 && (
                        <div className="morph-connector">
                            <div
                                className="morph-connector__fill"
                                style={{
                                    width: idx < currentStep ? '100%' : '0%'
                                }}
                            ></div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default MorphingProgress;
