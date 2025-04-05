// Import global CSS for the entire application
import '../styles/globals.css';
// Import KaTeX CSS for math rendering
import 'katex/dist/katex.min.css';
// Import ChakraProvider for using Chakra UI component library
import { ChakraProvider } from '@chakra-ui/react';
// Import the ChatProvider we created to manage chat state
import { ChatProvider } from '../context/ChatContext';
import Head from 'next/head';

// MyApp component is the root component of the Next.js application
// It receives Component (the active page) and pageProps (props for that page)
function MyApp({ Component, pageProps }) {
  return (
    // ChakraProvider adds Chakra UI theming and components to our app
    <ChakraProvider>
      <Head>
        <style>{`
          /* Custom styles for math rendering */
          .katex-display {
            margin: 1em 0;
            overflow-x: auto;
            overflow-y: hidden;
            display: block;
            text-align: center;
            padding: 0.25em;
            max-width: 100%;
          }
          
          .katex {
            font-size: 1.1em;
            line-height: 1.2;
            text-indent: 0;
            text-rendering: auto;
          }
          
          /* Ensure inline math is properly aligned with text */
          .katex-inline {
            display: inline-flex !important;
            vertical-align: middle;
            line-height: normal;
            margin: 0 0.2em;
          }
          
          /* Fix spacing issues with inline math */
          span.mord, span.mbin, span.mrel, span.mopen, span.mclose, span.mpunct, span.mord.text {
            margin-top: 0;
            vertical-align: middle;
          }
          
          /* Force proper line wrapping for long formulas */
          .katex-html {
            white-space: normal;
            word-wrap: normal;
          }
          
          /* Make math inside bold text appear bold */
          [font-weight="bold"] .katex,
          strong .katex,
          b .katex {
            font-weight: bold;
          }
          
          /* Ensure correct rendering within bold elements */
          [font-weight="bold"] .katex .mord,
          strong .katex .mord,
          b .katex .mord {
            font-weight: bold;
          }
          
          /* Fix for math in various text environments */
          p .katex-display, li .katex-display {
            max-width: 100%;
            overflow-x: auto;
          }
          
          /* Fix for multi-line equations */
          .katex-display > .katex {
            display: block !important;
            text-align: center;
            max-width: 100%;
          }
        `}</style>
      </Head>
      {/* ChatProvider gives all components access to chat functionality */}
      <ChatProvider>
        {/* Render the active page with its props */}
        <Component {...pageProps} />
      </ChatProvider>
    </ChakraProvider>
  );
}

export default MyApp;