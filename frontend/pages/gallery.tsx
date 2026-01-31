/**
 * Gallery Page
 * Displays user's matched photos with search and upload functionality
 */

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import ImageGrid, { ImageModal } from '../components/ImageGrid';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ImageResult {
    image_id: string;
    similarity: number;
    rank: number;
    filename?: string;
    file_path?: string;
}

interface GalleryData {
    images: ImageResult[];
    total: number;
    page: number;
    per_page: number;
    has_next: boolean;
    has_prev: boolean;
}

export default function GalleryPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [gallery, setGallery] = useState<GalleryData | null>(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedImage, setSelectedImage] = useState<ImageResult | null>(null);
    const [page, setPage] = useState(1);

    // Get auth token
    const getAuthToken = () => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('access_token');
        }
        return null;
    };

    // Fetch gallery
    const fetchGallery = useCallback(async (pageNum: number = 1) => {
        const token = getAuthToken();
        if (!token) {
            router.push('/scan');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_URL}/api/v1/gallery?page=${pageNum}&per_page=20`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (response.status === 401) {
                localStorage.removeItem('access_token');
                router.push('/scan');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to load gallery');
            }

            const data: GalleryData = await response.json();

            // Transform data to match ImageResult interface
            const transformedImages: ImageResult[] = data.images.map((img: any, index: number) => ({
                image_id: img.id,
                similarity: 1.0, // Gallery items don't have similarity, set to 1
                rank: index + 1,
                filename: img.filename,
                file_path: img.file_path
            }));

            setGallery({
                ...data,
                images: transformedImages
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load gallery');
        } finally {
            setLoading(false);
        }
    }, [router]);

    // Handle file upload
    const handleUpload = async (files: FileList) => {
        const token = getAuthToken();
        if (!token) return;

        setUploading(true);
        setError(null);

        let successCount = 0;
        let errorCount = 0;

        for (const file of Array.from(files)) {
            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(`${API_URL}/api/v1/scan/upload`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                if (response.ok) {
                    successCount++;
                } else {
                    const data = await response.json();
                    console.error(`Upload failed for ${file.name}:`, data.detail);
                    errorCount++;
                }
            } catch (err) {
                console.error(`Upload error for ${file.name}:`, err);
                errorCount++;
            }
        }

        setUploading(false);

        if (successCount > 0) {
            fetchGallery(page);
        }

        if (errorCount > 0) {
            setError(`${errorCount} file(s) failed to upload`);
        }
    };

    // Handle file input change
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            handleUpload(e.target.files);
        }
    };

    // Initial load
    useEffect(() => {
        fetchGallery(page);
    }, [fetchGallery, page]);

    // Logout
    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
        router.push('/');
    };

    return (
        <>
            <Head>
                <title>My Photos - Dev Studio</title>
                <meta name="description" content="View and manage your photos" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
            </Head>

            <main className="page">
                <div className="container">
                    {/* Header */}
                    <header className="flex justify-between items-center" style={{ marginBottom: '2rem' }}>
                        <h2 style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            background: 'var(--color-accent-gradient)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent'
                        }}>
                            My Photos
                        </h2>

                        <div className="flex gap-2">
                            <button
                                className="btn btn-secondary"
                                onClick={() => router.push('/scan')}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                                    <circle cx="12" cy="13" r="4" />
                                </svg>
                                Scan
                            </button>

                            <button
                                className="btn btn-ghost"
                                onClick={handleLogout}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                                </svg>
                            </button>
                        </div>
                    </header>

                    {/* Stats Bar */}
                    {gallery && (
                        <div className="card fade-in" style={{
                            marginBottom: '2rem',
                            padding: '1rem 1.5rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '1rem'
                        }}>
                            <div>
                                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                                    Total Photos
                                </p>
                                <p style={{
                                    fontSize: '1.5rem',
                                    fontWeight: 700,
                                    color: 'var(--color-text-primary)'
                                }}>
                                    {gallery.total}
                                </p>
                            </div>

                            <button
                                className="btn btn-primary"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                            >
                                {uploading ? (
                                    <>
                                        <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                                        </svg>
                                        Upload Photos
                                    </>
                                )}
                            </button>

                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                multiple
                                onChange={handleFileChange}
                                style={{ display: 'none' }}
                            />
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="status-message status-error fade-in" style={{ marginBottom: '1.5rem' }}>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                            </svg>
                            {error}
                        </div>
                    )}

                    {/* Image Grid */}
                    <ImageGrid
                        images={gallery?.images || []}
                        loading={loading}
                        onImageClick={setSelectedImage}
                        emptyMessage="No photos yet. Upload some photos or scan your face to find matches!"
                    />

                    {/* Pagination */}
                    {gallery && (gallery.has_prev || gallery.has_next) && (
                        <div className="flex justify-center gap-4" style={{ marginTop: '2rem' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setPage(p => p - 1)}
                                disabled={!gallery.has_prev || loading}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M15 18l-6-6 6-6" />
                                </svg>
                                Previous
                            </button>

                            <span style={{
                                display: 'flex',
                                alignItems: 'center',
                                color: 'var(--color-text-secondary)'
                            }}>
                                Page {gallery.page}
                            </span>

                            <button
                                className="btn btn-secondary"
                                onClick={() => setPage(p => p + 1)}
                                disabled={!gallery.has_next || loading}
                            >
                                Next
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M9 18l6-6-6-6" />
                                </svg>
                            </button>
                        </div>
                    )}

                    {/* Empty State CTA */}
                    {!loading && gallery?.total === 0 && (
                        <div className="text-center" style={{ marginTop: '2rem' }}>
                            <button
                                className="btn btn-primary btn-large"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                                </svg>
                                Upload Your First Photos
                            </button>
                        </div>
                    )}
                </div>
            </main>

            {/* Image Modal */}
            <ImageModal
                image={selectedImage}
                onClose={() => setSelectedImage(null)}
            />
        </>
    );
}
