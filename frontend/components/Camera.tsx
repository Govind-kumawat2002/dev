/**
 * Camera Component
 * Handles camera access, display, and image capture
 */

'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';

interface CameraProps {
    onCapture: (imageBlob: Blob) => void;
    onError?: (error: string) => void;
    autoStart?: boolean;
}

export default function Camera({ onCapture, onError, autoStart = true }: CameraProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const [isReady, setIsReady] = useState(false);
    const [isCapturing, setIsCapturing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user');
    const isMounted = useRef(true);

    useEffect(() => {
        isMounted.current = true;
        return () => {
            isMounted.current = false;
        };
    }, []);

    // Start camera
    const startCamera = useCallback(async () => {
        try {
            setError(null);

            // Stop existing stream
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }

            const constraints: MediaStreamConstraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 960 },
                },
                audio: false,
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);

            if (!isMounted.current) {
                stream.getTracks().forEach(track => track.stop());
                return;
            }

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                try {
                    await videoRef.current.play();
                    if (isMounted.current) {
                        setIsReady(true);
                    }
                } catch (e) {
                    // Ignore DOMExceptions if unmounted (e.g. media removed)
                    if (isMounted.current) {
                        throw e;
                    }
                }
            }
        } catch (err) {
            if (!isMounted.current) return;
            const errorMessage = err instanceof Error ? err.message : 'Failed to access camera';
            setError(errorMessage);
            onError?.(errorMessage);
        }
    }, [facingMode, onError]);

    // Stop camera
    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        setIsReady(false);
    }, []);

    const fileInputRef = useRef<HTMLInputElement>(null);

    // Capture image
    const captureImage = useCallback(async () => {
        if (!videoRef.current || !canvasRef.current || !isReady) return;

        setIsCapturing(true);

        const video = videoRef.current;
        const canvas = canvasRef.current;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Flip horizontally for selfie camera
        if (facingMode === 'user') {
            ctx.translate(canvas.width, 0);
            ctx.scale(-1, 1);
        }

        ctx.drawImage(video, 0, 0);

        // Reset transform
        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // Convert to blob
        canvas.toBlob(
            (blob) => {
                if (blob) {
                    onCapture(blob);
                }
                setIsCapturing(false);
            },
            'image/jpeg',
            0.9
        );
    }, [isReady, facingMode, onCapture]);

    // Handle file upload
    const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            onCapture(file);
        }
        // Reset input so same file can be selected again
        if (event.target) {
            event.target.value = '';
        }
    }, [onCapture]);

    const triggerFileUpload = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    // Toggle camera
    const toggleCamera = useCallback(() => {
        setFacingMode(prev => prev === 'user' ? 'environment' : 'user');
    }, []);

    // Auto-start camera
    useEffect(() => {
        if (autoStart) {
            startCamera();
        }

        return () => {
            stopCamera();
        };
    }, [autoStart, startCamera, stopCamera]);

    // Restart camera when facing mode changes
    useEffect(() => {
        if (isReady) {
            startCamera();
        }
    }, [facingMode]);

    if (error) {
        return (
            <div className="camera-container">
                <div className="camera-video" style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    gap: '1rem',
                    background: 'var(--color-bg-secondary)',
                    aspectRatio: '4/3'
                }}>
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                    <p style={{ color: 'var(--color-error)', textAlign: 'center', padding: '0 1rem' }}>
                        {error}
                    </p>
                    <button className="btn btn-primary" onClick={startCamera}>
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="camera-container">
            <video
                ref={videoRef}
                className="camera-video"
                autoPlay
                playsInline
                muted
                style={{
                    transform: facingMode === 'user' ? 'scaleX(-1)' : 'none',
                    opacity: isReady ? 1 : 0,
                    transition: 'opacity 0.3s ease'
                }}
            />

            {/* Hidden canvas for capturing */}
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {/* Camera overlay with frame */}
            <div className="camera-overlay">
                <div className="camera-frame" />
            </div>

            {/* Loading state */}
            {!isReady && !error && (
                <div className="camera-overlay" style={{ background: 'var(--color-bg-secondary)' }}>
                    <div className="loading-spinner" />
                </div>
            )}

            {/* Controls */}
            <div className="camera-controls">
                {/* Switch camera button */}
                <button
                    className="btn btn-secondary btn-icon"
                    onClick={toggleCamera}
                    aria-label="Switch camera"
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M16 3h5v5M8 21H3v-5M21 3l-7 7M3 21l7-7" />
                    </svg>
                </button>

                {/* Capture button */}
                <button
                    className={`capture-btn ${isCapturing ? 'capturing' : ''}`}
                    onClick={captureImage}
                    disabled={!isReady || isCapturing}
                    aria-label="Capture photo"
                />

                {/* Upload button */}
                <input
                    type="file"
                    accept="image/*"
                    style={{ display: 'none' }}
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                />
                <button
                    className="btn btn-secondary btn-icon"
                    onClick={triggerFileUpload}
                    aria-label="Upload photo"
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
