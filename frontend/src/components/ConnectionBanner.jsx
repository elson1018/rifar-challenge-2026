import React from 'react';
import { WifiOff } from 'lucide-react';

export default function ConnectionBanner({ status, retryCount }) {
  if (status === 'connected') return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] bg-gradient-to-r from-red-600 to-rose-700 text-white text-center py-2.5 px-4 flex items-center justify-center gap-2.5 shadow-lg border-b border-red-500/20 backdrop-blur-sm select-none">
      <WifiOff size={18} className="animate-pulse" />
      <span className="font-semibold text-sm tracking-wide">
        Connection to flood warning server lost. Reconnecting... (Attempt {retryCount})
      </span>
    </div>
  );
}
