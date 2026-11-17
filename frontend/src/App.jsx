import { AppHeader } from './components/AppHeader';
import { BenchmarkView } from './features/benchmark/BenchmarkView';
import { SandboxView } from './features/sandbox/SandboxView';
import { useScenarios } from './hooks/useScenarios';
import { useRoute } from './lib/route';

export default function App() {
  const path = useRoute();
  const { scenarios, loading, error, retry } = useScenarios();
  const isBenchmark = path.startsWith('/benchmark');

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader path={path} />
      <main className={`min-h-0 flex-1 ${isBenchmark ? 'scroll-quiet overflow-y-auto' : 'overflow-hidden'}`}>
        {isBenchmark ? (
          <BenchmarkView />
        ) : (
          <SandboxView scenarios={scenarios} loading={loading} error={error} onRetry={retry} />
        )}
      </main>
    </div>
  );
}
