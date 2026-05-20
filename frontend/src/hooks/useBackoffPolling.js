import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook to poll a URL with exponential backoff on failure.
 *
 * @param {string} url - The endpoint URL to fetch.
 * @param {function} callback - Callback function invoked on successful response.
 * @param {number} baseInterval - Starting poll interval in milliseconds (default 3000).
 * @param {number} maxInterval - Maximum backoff poll interval in milliseconds (default 30000).
 */
export function useBackoffPolling(url, callback, baseInterval = 3000, maxInterval = 30000) {
  const [status, setStatus] = useState('connected'); // 'connected' | 'disconnected'
  const [retryCount, setRetryCount] = useState(0);
  const currentInterval = useRef(baseInterval);
  const timeoutId = useRef(null);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Server responded with error status");
        const data = await res.json();
        
        if (active) {
          callback(data);
          setStatus('connected');
          setRetryCount(0);
          currentInterval.current = baseInterval; // Reset backoff interval
        }
      } catch (error) {
        if (active) {
          console.warn("Polling error, backoff active:", error);
          setStatus('disconnected');
          setRetryCount(prev => prev + 1);
          // Exponential backoff: multiply interval by 2 up to maxInterval
          currentInterval.current = Math.min(currentInterval.current * 2, maxInterval);
        }
      } finally {
        if (active) {
          timeoutId.current = setTimeout(poll, currentInterval.current);
        }
      }
    };

    poll();

    return () => {
      active = false;
      if (timeoutId.current) clearTimeout(timeoutId.current);
    };
  }, [url, baseInterval, maxInterval]);

  return { status, retryCount };
}
