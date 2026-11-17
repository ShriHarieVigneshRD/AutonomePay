import { useEffect, useRef, useState } from 'react';
import { api, errorMessage } from '../lib/api';

const greeting = (scenario) => (scenario ? [{ role: 'assistant', content: scenario.initial_message }] : []);
const lastTrace = (messages) => messages.findLast((m) => m.meta)?.meta ?? null;

/**
 * One server-side negotiation for the selected scenario.
 * The conversation is created on the first send; only the new text is sent each turn.
 * A failed send is reported in `failed` and never stored. Agent replies carry their turn result in `meta`.
 * `restoreId` (e.g. from the URL) reloads an existing conversation for this scenario.
 */
export function useConversation(scenario, restoreId = null) {
  const [scenarioId, setScenarioId] = useState(scenario?.id);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState(() => greeting(scenario));
  const [trace, setTrace] = useState(null);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(null); // { text, error }
  // Bumps on reset, so late replies from an old conversation are ignored (ref mirrors it for async code).
  const [epoch, setEpoch] = useState(0);
  const liveEpoch = useRef(0);
  const pendingRestore = useRef(restoreId);

  useEffect(() => {
    liveEpoch.current = epoch;
  }, [epoch]);

  const reset = () => {
    setEpoch((e) => e + 1);
    setConversationId(null);
    setMessages(greeting(scenario));
    setTrace(null);
    setSending(false);
    setFailed(null);
  };

  // Switching scenario starts a fresh conversation (adjusting state during render, per React docs).
  if (scenario?.id !== scenarioId) {
    setScenarioId(scenario?.id);
    reset();
  }

  useEffect(() => {
    const id = pendingRestore.current;
    if (!id || !scenario) return;
    pendingRestore.current = null;
    const at = liveEpoch.current;
    api.getConversation(id).then(
      (conv) => {
        if (liveEpoch.current !== at || conv.scenario_id !== scenario.id) return;
        setConversationId(conv.conversation_id);
        setMessages(conv.messages);
        setTrace(lastTrace(conv.messages));
      },
      () => {}, // an expired or foreign id just means a fresh conversation
    );
  }, [scenario]);

  const send = async (text) => {
    const content = text.trim();
    if (!scenario || !content || sending) return;
    const at = epoch;
    const before = messages;
    setMessages([...before, { role: 'user', content }]);
    setSending(true);
    setFailed(null);
    try {
      let id = conversationId;
      if (!id) {
        id = (await api.startConversation(scenario.id)).conversation_id;
        if (liveEpoch.current !== at) return;
        setConversationId(id);
      }
      const data = await api.sendMessage(id, content);
      if (liveEpoch.current !== at) return; // user moved on to another conversation
      setMessages([
        ...before,
        { role: 'user', content },
        { role: 'assistant', content: data.final_response, meta: data },
      ]);
      setTrace(data);
    } catch (error) {
      if (liveEpoch.current !== at) return;
      setMessages(before);
      setFailed({ text: content, error: errorMessage(error) });
    } finally {
      if (liveEpoch.current === at) setSending(false);
    }
  };

  return {
    conversationId,
    messages,
    trace,
    sending,
    failed,
    send,
    reset,
    retry: () => failed && send(failed.text),
  };
}
