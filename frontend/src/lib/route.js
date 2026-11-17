import { useEffect, useState } from 'react';

// shortcut: three static routes don't justify a router dependency; adopt react-router if routes grow.
export function navigate(path) {
  if (path === window.location.pathname) return;
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export function useRoute() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onChange = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onChange);
    return () => window.removeEventListener('popstate', onChange);
  }, []);
  return path;
}
