import { useEffect, useState } from 'react';
import { ChatsCircle, Files, Path } from '@phosphor-icons/react';
import { Segmented } from '../../components/ui/Segmented';
import { ErrorState } from '../../components/ui/States';
import { useConversation } from '../../hooks/useConversation';
import { AuditRail } from './AuditRail';
import { CaseFile } from './CaseFile';
import { ChatPanel } from './ChatPanel';
import { ScenarioPicker } from './ScenarioPicker';

const MOBILE_PANES = [
  { value: 'chat', label: 'Chat', icon: ChatsCircle },
  { value: 'case', label: 'Case', icon: Files },
  { value: 'audit', label: 'Audit', icon: Path },
];
const SIDE_PANES = MOBILE_PANES.slice(1);

// The selected case lives in the URL (?case=eval_case_07) so a case can be shared or reloaded.
const caseFromUrl = () => new URLSearchParams(window.location.search).get('case');
function setCaseInUrl(id) {
  const url = new URL(window.location.href);
  url.searchParams.set('case', id);
  window.history.replaceState(window.history.state, '', url);
}

/**
 * Layout: ≥1280px three columns (case · chat · audit); 768–1279px chat + a tabbed side column;
 * <768px one pane at a time behind a segmented control.
 */
export function SandboxView({ active = true, scenarios, loading, error, onRetry }) {
  const [selectedId, setSelectedId] = useState(caseFromUrl);
  const [pane, setPane] = useState('chat');
  const [side, setSide] = useState('case');
  const scenario = scenarios.find((s) => s.id === selectedId) ?? scenarios[0] ?? null;
  const conversation = useConversation(scenario);

  useEffect(() => {
    if (active && scenario) setCaseInUrl(scenario.id);
  }, [active, scenario]);

  const show = (name) =>
    `${pane === name ? 'flex' : 'hidden'} ${name === 'chat' || side === name ? 'md:flex' : 'md:hidden'} xl:flex`;

  return (
    <div className="mx-auto flex h-full min-h-0 max-w-[1440px] flex-col gap-3 p-3 md:p-4">
      {error && <ErrorState message={error} onRetry={onRetry} />}

      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <ScenarioPicker
          scenarios={scenarios}
          active={scenario}
          onSelect={(sc) => setSelectedId(sc.id)}
          disabled={loading || !scenarios.length}
        />
        <Segmented
          className="w-full md:hidden"
          options={MOBILE_PANES}
          value={pane}
          onChange={setPane}
          label="Sandbox panel"
          controls="sandbox"
        />
      </div>

      <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[300px_minmax(0,1fr)_380px]">
        <ChatPanel
          id="sandbox-chat"
          scenario={scenario}
          conversation={conversation}
          className={`${show('chat')} md:col-start-1 md:row-start-1 xl:col-start-2`}
        />

        {/* Side column on tablets; its children join the grid directly on desktop. */}
        <div className="contents md:col-start-2 md:row-start-1 md:flex md:min-h-0 md:flex-col md:gap-3 xl:contents">
          <Segmented
            className="hidden md:flex xl:hidden"
            options={SIDE_PANES}
            value={side}
            onChange={setSide}
            label="Side panel"
          />
          <CaseFile
            id="sandbox-case"
            scenario={scenario}
            loading={loading}
            className={`${show('case')} min-h-0 flex-1 xl:col-start-1 xl:row-start-1`}
          />
          <AuditRail
            id="sandbox-audit"
            turn={conversation.trace}
            sending={conversation.sending}
            className={`${show('audit')} min-h-0 flex-1 xl:col-start-3 xl:row-start-1`}
          />
        </div>
      </div>
    </div>
  );
}
