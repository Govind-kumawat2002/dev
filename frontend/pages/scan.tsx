/**
 * Face Scan Page
 * Camera-based face scanning for user identification
 */

'use client';

import React, { useState, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Camera from '../components/Camera';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type ScanStatus = 'idle' | 'scanning' | 'success' | 'no-match' | 'error';

interface ScanResult {
    success: boolean;
    message: string;
    faces_detected: number;
    user_id?: string;
    access_token?: string;
    match_count: number;
}

export default function ScanPage() {
    const router = useRouter();
    const { session, token } = router.query;

    const [status, setStatus] = useState<ScanStatus>('idle');
    const [result, setResult] = useState<ScanResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Handle captured image
    const handleCapture = useCallback(async (imageBlob: Blob) => {
        setStatus('scanning');
        setError(null);

        try {
            const formData = new FormData();
            const filename = imageBlob instanceof File ? imageBlob.name : 'capture.jpg';
            formData.append('file', imageBlob, filename);

            if (session) {
                formData.append('session_id', session as string);
            }

            const headers: Record<string, string> = {};
            const storedToken = localStorage.getItem('access_token');
            if (storedToken) {
                headers['Authorization'] = `Bearer ${storedToken}`;
            }

            const response = await fetch(`${API_URL}/api/v1/scan/face`, {
                method: 'POST',
                body: formData,
                headers
            });

            const data: ScanResult = await response.json();
            setResult(data);

            if (data.success && data.match_count > 0) {
                // Store token if returned
                if (data.access_token) {
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('user_id', data.user_id || '');
                }

                // Navigate to gallery immediately
                router.push('/gallery');
            } else if (data.faces_detected === 0) {
                setStatus('error');
                setError('No face detected. Please try again.');
            } else {
                setStatus('no-match');
            }
        } catch (err) {
            setStatus('error');
            setError(err instanceof Error ? err.message : 'Scan failed. Please try again.');
        }
    }, [session, router]);

    // Handle camera error
    const handleCameraError = (errorMessage: string) => {
        setError(errorMessage);
        setStatus('error');
    };

    // Retry scan
    const handleRetry = () => {
        setStatus('idle');
        setResult(null);
        setError(null);
    };

    return (
        <>
            <Head>
                <title>Scan Face - Dev Studio</title>
                <meta name="description" content="Scan your face to find your photos" />
                <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
            </Head>

            <main className="page">
                <div className="container">
                    {/* Header */}
                    <header className="flex justify-between items-center" style={{ marginBottom: '2rem' }}>
                        <button
                            className="btn btn-ghost"
                            onClick={() => router.push('/')}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M19 12H5M12 19l-7-7 7-7" />
                            </svg>
                            Back
                        </button>

                        <h2 style={{
                            fontSize: '1.25rem',
                            fontWeight: 600,
                            background: 'var(--color-accent-gradient)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent'
                        }}>
                            Face Scan
                        </h2>

                        <div style={{ width: 80 }} /> {/* Spacer for centering */}
                    </header>

                    {/* Instructions */}
                    <section className="text-center" style={{ marginBottom: '2rem' }}>
                        <p style={{ color: 'var(--color-text-secondary)' }}>
                            Position your face within the frame and tap the button to scan
                        </p>
                    </section>

                    {/* Camera */}
                    <section className="slide-up">
                        <Camera
                            onCapture={handleCapture}
                            onError={handleCameraError}
                            autoStart={true}
                        />
                    </section>

                    {/* Status Messages */}
                    <section style={{ marginTop: '2rem', maxWidth: '480px', margin: '2rem auto 0' }}>
                        {status === 'scanning' && (
                            <div className="card text-center fade-in">
                                <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
                                <p style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>
                                    Processing...
                                </p>
                            </div>
                        )}

                        {status === 'no-match' && (
                            <div className="card text-center fade-in">
                                <svg
                                    width="64"
                                    height="64"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.5"
                                    style={{ margin: '0 auto', color: 'var(--color-text-muted)' }}
                                >
                                    <circle cx="12" cy="12" r="10" />
                                    <path d="M16 16s-1.5-2-4-2-4 2-4 2M9 9h.01M15 9h.01" />
                                </svg>
                                <h4 style={{ marginTop: '1rem' }}>No Photos Found</h4>
                                <p style={{
                                    color: 'var(--color-text-secondary)',
                                    marginTop: '0.5rem',
                                    marginBottom: '1.5rem'
                                }}>
                                    We couldn't find any similar photos.
                                </p>
                                <div className="flex gap-4 justify-center">
                                    <button className="btn btn-secondary" onClick={handleRetry}>
                                        Try Again
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={() => router.push('/gallery')}
                                    >
                                        Upload Photos
                                    </button>
                                </div>
                            </div>
                        )}

                        {status === 'error' && error && (
                            <div className="status-message status-error fade-in">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                                </svg>
                                <div>
                                    <p style={{ fontWeight: 600 }}>Something went wrong</p>
                                    <p style={{ fontSize: '0.875rem', opacity: 0.9 }}>{error}</p>
                                </div>
                            </div>
                        )}

                        {status === 'error' && (
                            <button
                                className="btn btn-primary w-full"
                                style={{ marginTop: '1rem' }}
                                onClick={handleRetry}
                            >
                                Try Again
                            </button>
                        )}
                    </section>

                    {/* Tips */}
                    {status === 'idle' && (
                        <section style={{
                            marginTop: '2rem',
                            maxWidth: '480px',
                            margin: '2rem auto 0'
                        }}>
                            <div className="card" style={{ padding: '1rem 1.5rem' }}>
                                <h4 style={{
                                    fontSize: '0.875rem',
                                    fontWeight: 600,
                                    color: 'var(--color-text-accent)',
                                    marginBottom: '0.75rem'
                                }}>
                                    Tips for best results:
                                </h4>
                                <ul style={{
                                    listStyle: 'none',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '0.5rem'
                                }}>
                                    <li style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        color: 'var(--color-text-secondary)',
                                        fontSize: '0.875rem'
                                    }}>
                                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                                        Good lighting on your face
                                    </li>
                                    <li style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        color: 'var(--color-text-secondary)',
                                        fontSize: '0.875rem'
                                    }}>
                                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                                        Face the camera directly
                                    </li>
                                    <li style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        color: 'var(--color-text-secondary)',
                                        fontSize: '0.875rem'
                                    }}>
                                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                                        Remove glasses or hats if possible
                                    </li>
                                </ul>
                            </div>
                        </section>
                    )}
                </div>
            </main>
        </>
    );
}
