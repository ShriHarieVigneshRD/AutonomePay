import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { useConversation } from './useConversation';

vi.mock('../lib/api', async (importOriginal) => ({
  ...(await importOriginal()),
  api: { chat: vi.fn() },
}));

const hotstar = {
  id: 'eval_case_01',
  merchant_id: 'hotstar',
  customer_id: 'c1',
  invoice_id: 'i1',
  initial_message: 'Hi Aarav',
};
const notion = {
  id: 'eval_case_02',
  merchant_id: 'notion_saas',
  customer_id: 'c2',
  invoice_id: 'i2',
  initial_message: 'Hello Rohan',
};

afterEach(() => vi.clearAllMocks());

describe('useConversation', () => {
  it('sends the history with a session id and appends the reply', async () => {
    api.chat.mockResolvedValue({ final_response: 'Here is INR 279.00', guardrail_status: 'PASSED' });
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('Money is tight'));
    const body = api.chat.mock.calls[0][0];
    expect(body.session_id).toMatch(/^s_[a-f0-9]{32}$/);
    expect(body.messages).toEqual([
      { role: 'assistant', content: 'Hi Aarav' },
      { role: 'user', content: 'Money is tight' },
    ]);
    expect(result.current.messages.at(-1)).toEqual({ role: 'assistant', content: 'Here is INR 279.00' });
    expect(result.current.trace.guardrail_status).toBe('PASSED');
  });

  it('B16: a failed send is reported but never added to the history', async () => {
    api.chat.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'boom' } } });
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('Hello'));
    expect(result.current.messages).toEqual([{ role: 'assistant', content: 'Hi Aarav' }]);
    expect(result.current.failed).toEqual({ text: 'Hello', error: 'boom' });

    api.chat.mockResolvedValueOnce({ final_response: 'Hi again' });
    await act(() => result.current.retry());
    expect(api.chat.mock.calls[1][0].messages.map((m) => m.content)).toEqual(['Hi Aarav', 'Hello']);
    expect(result.current.failed).toBeNull();
  });

  it('switching scenario starts a fresh conversation with a new session', async () => {
    api.chat.mockResolvedValue({ final_response: 'ok' });
    const { result, rerender } = renderHook(({ scenario }) => useConversation(scenario), {
      initialProps: { scenario: hotstar },
    });
    await act(() => result.current.send('one'));
    const firstSession = api.chat.mock.calls[0][0].session_id;
    rerender({ scenario: notion });
    expect(result.current.messages).toEqual([{ role: 'assistant', content: 'Hello Rohan' }]);
    expect(result.current.trace).toBeNull();
    await act(() => result.current.send('two'));
    expect(api.chat.mock.calls[1][0].session_id).not.toBe(firstSession);
  });

  it('ignores blank messages', async () => {
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('   '));
    expect(api.chat).not.toHaveBeenCalled();
  });
});
