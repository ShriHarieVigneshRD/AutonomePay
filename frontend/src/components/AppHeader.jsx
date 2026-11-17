import { ChartBar, ChatsCircle, Moon, Sun } from '@phosphor-icons/react';
import { useTheme } from '../lib/theme';
import { navigate } from '../lib/route';

const NAV = [
  { path: '/', label: 'Sandbox', icon: ChatsCircle },
  { path: '/benchmark', label: 'Benchmark', icon: ChartBar },
];

export function AppHeader({ path }) {
  const { dark, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-30 border-b border-rule/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 md:px-6">
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate('/');
          }}
          className="flex items-center gap-2.5 rounded-control"
        >
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          <span className="text-base font-semibold tracking-tight max-[420px]:sr-only">AutonomePay</span>
          <span className="hidden text-xs text-ink-3 lg:inline">Settlement concierge</span>
        </a>

        <nav aria-label="Main" className="ml-auto flex items-center gap-1 sm:ml-6">
          {NAV.map(({ path: to, label, icon: Icon }) => {
            const current = to === '/' ? path === '/' : path.startsWith(to);
            return (
              <a
                key={to}
                href={to}
                aria-current={current ? 'page' : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(to);
                }}
                className={`inline-flex h-9 items-center gap-1.5 rounded-control px-3 text-sm font-medium transition-colors max-md:min-h-11 ${
                  current ? 'bg-well text-ink' : 'text-ink-3 hover:text-ink'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden />
                <span className="max-[380px]:sr-only">{label}</span>
              </a>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={toggle}
          aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
          className="inline-flex h-9 w-9 items-center justify-center rounded-control text-ink-3 transition-colors hover:bg-well hover:text-ink max-md:h-11 max-md:w-11 sm:ml-auto"
        >
          {dark ? (
            <Sun className="h-[18px] w-[18px]" aria-hidden />
          ) : (
            <Moon className="h-[18px] w-[18px]" aria-hidden />
          )}
        </button>
      </div>
    </header>
  );
}
