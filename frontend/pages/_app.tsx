/**
 * App Component
 * Next.js custom App for global styles and providers
 */

import type { AppProps } from 'next/app';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
    return <Component {...pageProps} />;
}
