import { AppHeader } from './components/AppHeader';
import { BenchmarkView } from './features/benchmark/BenchmarkView';
import { CheckoutPage } from './features/checkout/CheckoutPage';
import { SandboxView } from './features/sandbox/SandboxView';
import { useScenarios } from './hooks/useScenarios';
import { useRoute } from './lib/route';

export default function App() {
  const path = useRoute();
  const { scenarios, loading, error, retry } = useScenarios();
  const isBenchmark = path.startsWith('/benchmark');
  const checkoutId = path.match(/^\/pay\/([\w-]+)$/)?.[1];

  if (checkoutId) {
    return (
      <div className="flex h-dvh flex-col">
        <AppHeader path={path} />
        <main className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
          <CheckoutPage linkId={checkoutId} />
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader path={path} />
      {/* The sandbox stays mounted so a conversation survives a visit to the benchmark. */}
      <main hidden={isBenchmark} className="min-h-0 flex-1 overflow-hidden">
        <SandboxView
          active={!isBenchmark}
          scenarios={scenarios}
          loading={loading}
          error={error}
          onRetry={retry}
        />
      </main>
      {isBenchmark && (
        <main className="scroll-quiet min-h-0 flex-1 overflow-y-auto">
          <BenchmarkView />
        </main>
      )}
    </div>
  );
}
