import { useCallback, useEffect, useState } from 'react';
import { api, errorMessage } from '../lib/api';

export function useScenarios() {
  const [state, setState] = useState({ scenarios: [], loading: true, error: null });

  const fetchScenarios = useCallback(
    () =>
      api.scenarios().then(
        (scenarios) => setState({ scenarios, loading: false, error: null }),
        (error) => setState({ scenarios: [], loading: false, error: errorMessage(error) }),
      ),
    [],
  );

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  const retry = () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    fetchScenarios();
  };

  return { ...state, retry };
}
