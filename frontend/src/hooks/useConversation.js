import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, newSessionId } from '../lib/api';

const greeting = (scenario) => (scenario ? [{ role: 'assistant', content: scenario.initial_message }] : []);

/**
 * One negotiation with the agent for the selected scenario.
 * A failed send is reported in `failed` and is never added to the history sent to the backend.
 */
export function useConversation(scenario) {
  const [scenarioId, setScenarioId] = useState(scenario?.id);
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState(() => greeting(scenario));
  const [trace, setTrace] = useState(null);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(null); // { text, error }
  const activeSession = useRef(sessionId);

  useEffect(() => {
    activeSession.current = sessionId;
  }, [sessionId]);

  const reset = () => {
    setSessionId(newSessionId());
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

  const send = async (text) => {
    const content = text.trim();
    if (!scenario || !content || sending) return;
    const session = sessionId;
    const history = [...messages, { role: 'user', content }];
    setMessages(history);
    setSending(true);
    setFailed(null);
    try {
      const data = await api.chat({
        merchant_id: scenario.merchant_id,
        customer_id: scenario.customer_id,
        invoice_id: scenario.invoice_id,
        session_id: session,
        messages: history,
      });
      if (activeSession.current !== session) return; // user moved on to another conversation
      setMessages([...history, { role: 'assistant', content: data.final_response }]);
      setTrace(data);
    } catch (error) {
      if (activeSession.current !== session) return;
      setMessages(messages);
      setFailed({ text: content, error: errorMessage(error) });
    } finally {
      if (activeSession.current === session) setSending(false);
    }
  };

  return { messages, trace, sending, failed, send, reset, retry: () => failed && send(failed.text) };
}
