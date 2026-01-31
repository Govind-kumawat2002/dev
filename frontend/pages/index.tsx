/**
 * Landing Page (index.tsx)
 * QR code entry point for the face similarity platform
 */

'use client';

import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { QRCodeSVG } from 'qrcode.react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface QRSession {
    session_id: string;
    qr_token: string;
    qr_url: string;
    expires_in: number;
}

export default function Home() {
    const router = useRouter();
    const [qrSession, setQrSession] = useState<QRSession | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [countdown, setCountdown] = useState<number>(0);

    // Create QR session
    const createSession = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/api/v1/auth/session/qr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_info: navigator.userAgent })
            });

            if (!response.ok) {
                throw new Error('Failed to create session');
            }

            const data: QRSession = await response.json();
            setQrSession(data);
            setCountdown(Math.floor(data.expires_in / 60));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Connection failed');
        } finally {
            setLoading(false);
        }
    };

    // Direct navigation for mobile
    const handleMobileScan = () => {
        router.push('/scan');
    };

    // Countdown timer
    useEffect(() => {
        if (countdown > 0) {
            const timer = setInterval(() => {
                setCountdown(prev => {
                    if (prev <= 1) {
                        clearInterval(timer);
                        setQrSession(null);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 60000);

            return () => clearInterval(timer);
        }
    }, [countdown]);

    // Create session on mount
    useEffect(() => {
        createSession();
    }, []);

    return (
        <>
            <Head>
                <title>Dev Studio - Face Recognition Search</title>
                <meta name="description" content="Find your photos instantly with face recognition technology" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link rel="icon" href="/favicon.ico" />
            </Head>

            <main className="page">
                <div className="container">
                    {/* Hero Section */}
                    <section className="text-center" style={{ paddingTop: '4rem' }}>
                        {/* Logo */}
                        <div style={{ marginBottom: '2rem' }}>
                            <svg
                                width="80"
                                height="80"
                                viewBox="0 0 100 100"
                                fill="none"
                                style={{ margin: '0 auto' }}
                            >
                                <circle cx="50" cy="50" r="45" stroke="url(#gradient)" strokeWidth="3" fill="none" />
                                <circle cx="50" cy="40" r="15" stroke="url(#gradient)" strokeWidth="2.5" fill="none" />
                                <path d="M25 80 Q50 55 75 80" stroke="url(#gradient)" strokeWidth="2.5" fill="none" />
                                <defs>
                                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor="#6366f1" />
                                        <stop offset="50%" stopColor="#8b5cf6" />
                                        <stop offset="100%" stopColor="#a855f7" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>

                        <h1>Dev Studio</h1>
                        <p style={{
                            fontSize: '1.25rem',
                            marginTop: '1rem',
                            maxWidth: '600px',
                            margin: '1rem auto'
                        }}>
                            Find your photos instantly with advanced face recognition technology
                        </p>
                    </section>

                    {/* QR Code Section */}
                    <section className="card slide-up" style={{
                        maxWidth: '480px',
                        margin: '3rem auto',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ marginBottom: '1rem', color: 'var(--color-text-primary)' }}>
                            Scan to Start
                        </h3>
                        <p style={{ marginBottom: '2rem', color: 'var(--color-text-secondary)' }}>
                            Open your camera and scan this QR code to find your photos
                        </p>

                        {loading ? (
                            <div style={{ padding: '4rem' }}>
                                <div className="loading-spinner" style={{ margin: '0 auto' }} />
                                <p style={{ marginTop: '1rem', color: 'var(--color-text-muted)' }}>
                                    Generating QR code...
                                </p>
                            </div>
                        ) : error ? (
                            <div className="status-message status-error" style={{ marginBottom: '1rem' }}>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                                </svg>
                                {error}
                            </div>
                        ) : qrSession ? (
                            <>
                                <div className="qr-container" style={{ display: 'inline-block', marginBottom: '1.5rem' }}>
                                    <QRCodeSVG
                                        value={qrSession.qr_url}
                                        size={220}
                                        level="L"
                                        bgColor="#FFFFFF"
                                        fgColor="#12121a"
                                    />
                                </div>

                                <p style={{
                                    fontSize: '0.875rem',
                                    color: 'var(--color-text-muted)',
                                    marginBottom: '1.5rem'
                                }}>
                                    QR code expires in {countdown} minutes
                                </p>
                            </>
                        ) : null}

                        <button
                            className="btn btn-secondary w-full"
                            onClick={createSession}
                            disabled={loading}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M23 4v6h-6M1 20v-6h6M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
                            </svg>
                            Refresh QR Code
                        </button>
                    </section>

                    {/* Mobile Direct Access */}
                    <section className="text-center" style={{ marginTop: '2rem' }}>
                        <p style={{ color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
                            On mobile? Access directly:
                        </p>
                        <button
                            className="btn btn-primary btn-large"
                            onClick={handleMobileScan}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                                <circle cx="12" cy="13" r="4" />
                            </svg>
                            Open Camera
                        </button>
                    </section>

                    {/* Features */}
                    <section style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                        gap: '1.5rem',
                        marginTop: '4rem'
                    }}>
                        <div className="card text-center">
                            <div style={{
                                width: '56px',
                                height: '56px',
                                borderRadius: 'var(--radius-xl)',
                                background: 'var(--color-accent-gradient)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto 1rem'
                            }}>
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" />
                                </svg>
                            </div>
                            <h4 style={{ marginBottom: '0.5rem' }}>Face Recognition</h4>
                            <p style={{ fontSize: '0.9rem' }}>
                                Advanced AI identifies your face with 99%+ accuracy
                            </p>
                        </div>

                        <div className="card text-center">
                            <div style={{
                                width: '56px',
                                height: '56px',
                                borderRadius: 'var(--radius-xl)',
                                background: 'var(--color-accent-gradient)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto 1rem'
                            }}>
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
                                    <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
                                </svg>
                            </div>
                            <h4 style={{ marginBottom: '0.5rem' }}>Instant Results</h4>
                            <p style={{ fontSize: '0.9rem' }}>
                                Search through thousands of photos in milliseconds
                            </p>
                        </div>

                        <div className="card text-center">
                            <div style={{
                                width: '56px',
                                height: '56px',
                                borderRadius: 'var(--radius-xl)',
                                background: 'var(--color-accent-gradient)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto 1rem'
                            }}>
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
                                    <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z" />
                                </svg>
                            </div>
                            <h4 style={{ marginBottom: '0.5rem' }}>Private & Secure</h4>
                            <p style={{ fontSize: '0.9rem' }}>
                                Your photos are only visible to you
                            </p>
                        </div>
                    </section>

                    {/* Footer */}
                    <footer style={{
                        textAlign: 'center',
                        marginTop: '4rem',
                        paddingBottom: '2rem',
                        color: 'var(--color-text-muted)'
                    }}>
                        <p style={{ fontSize: '0.875rem' }}>
                            Powered by AI • Built with ❤️
                        </p>
                    </footer>
                </div>
            </main>
        </>
    );
}
