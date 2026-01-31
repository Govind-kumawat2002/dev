/**
 * ImageGrid Component
 * Displays search results in a responsive grid
 */

'use client';

import React from 'react';

interface ImageResult {
    image_id: string;
    similarity: number;
    rank: number;
    filename?: string;
    file_path?: string;
}

interface ImageGridProps {
    images: ImageResult[];
    onImageClick?: (image: ImageResult) => void;
    loading?: boolean;
    emptyMessage?: string;
    apiUrl?: string;
}

export default function ImageGrid({
    images,
    onImageClick,
    loading = false,
    emptyMessage = 'No images found',
    apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}: ImageGridProps) {

    // Get image URL
    const getImageUrl = (image: ImageResult): string => {
        return `${apiUrl}/api/v1/gallery/${image.image_id}/file`;
    };

    // Format similarity percentage
    const formatSimilarity = (similarity: number): string => {
        return `${(similarity * 100).toFixed(1)}%`;
    };

    // Loading skeleton
    if (loading) {
        return (
            <div className="image-grid">
                {[...Array(6)].map((_, i) => (
                    <div key={i} className="image-card">
                        <div className="loading-skeleton" style={{ width: '100%', height: '100%' }} />
                    </div>
                ))}
            </div>
        );
    }

    // Empty state
    if (images.length === 0) {
        return (
            <div className="card text-center" style={{ padding: '4rem 2rem' }}>
                <svg
                    width="80"
                    height="80"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1"
                    style={{ margin: '0 auto', opacity: 0.3 }}
                >
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                </svg>
                <p style={{ marginTop: '1.5rem', color: 'var(--color-text-muted)' }}>
                    {emptyMessage}
                </p>
            </div>
        );
    }

    return (
        <div className="image-grid fade-in">
            {images.map((image, index) => (
                <div
                    key={image.image_id}
                    className="image-card"
                    onClick={() => onImageClick?.(image)}
                    style={{ animationDelay: `${index * 50}ms` }}
                >
                    {/* Similarity badge */}
                    <span className="similarity-badge">
                        {formatSimilarity(image.similarity)}
                    </span>

                    {/* Image */}
                    <img
                        src={getImageUrl(image)}
                        alt={image.filename || `Match ${image.rank}`}
                        loading="lazy"
                        onError={(e) => {
                            (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Crect fill="%231a1a25" width="100" height="100"/%3E%3Ctext fill="%23555" x="50" y="55" text-anchor="middle" font-size="14"%3ENo Preview%3C/text%3E%3C/svg%3E';
                        }}
                    />

                    {/* Overlay with info */}
                    <div className="image-card-overlay">
                        <div className="image-card-info">
                            {image.filename && (
                                <p style={{
                                    fontSize: '0.875rem',
                                    fontWeight: 500,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                }}>
                                    {image.filename}
                                </p>
                            )}
                            <p style={{
                                fontSize: '0.75rem',
                                opacity: 0.8,
                                marginTop: '0.25rem'
                            }}>
                                Rank #{image.rank}
                            </p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}


// Image Modal Component for full view
interface ImageModalProps {
    image: ImageResult | null;
    onClose: () => void;
    apiUrl?: string;
}

export function ImageModal({ image, onClose, apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000' }: ImageModalProps) {
    if (!image) return null;

    const imageUrl = `${apiUrl}/api/v1/gallery/${image.image_id}/file`;

    return (
        <div
            className="loading-overlay scale-in"
            onClick={onClose}
            style={{ cursor: 'pointer' }}
        >
            <div
                className="card"
                onClick={(e) => e.stopPropagation()}
                style={{
                    maxWidth: '90vw',
                    maxHeight: '90vh',
                    padding: 0,
                    overflow: 'hidden'
                }}
            >
                <img
                    src={imageUrl}
                    alt={image.filename || 'Full size image'}
                    style={{
                        maxWidth: '100%',
                        maxHeight: '80vh',
                        display: 'block'
                    }}
                />

                <div style={{ padding: '1rem', background: 'var(--color-bg-card)' }}>
                    <div className="flex justify-between items-center">
                        <div>
                            <p style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                                {image.filename || 'Image'}
                            </p>
                            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                Similarity: {(image.similarity * 100).toFixed(1)}%
                            </p>
                        </div>

                        <button className="btn btn-secondary" onClick={onClose}>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
