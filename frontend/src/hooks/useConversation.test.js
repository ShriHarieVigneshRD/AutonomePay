import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { useConversation } from './useConversation';

vi.mock('../lib/api', async (importOriginal) => ({
  ...(await importOriginal()),
  api: { startConversation: vi.fn(), sendMessage: vi.fn(), getConversation: vi.fn() },
}));

const hotstar = { id: 'eval_case_01', initial_message: 'Hi Aarav' };
const notion = { id: 'eval_case_02', initial_message: 'Hello Rohan' };
const flush = () => act(() => Promise.resolve());

afterEach(() => vi.clearAllMocks());

describe('useConversation', () => {
  it('creates the conversation on the first send and only sends new text', async () => {
    api.startConversation.mockResolvedValue({ conversation_id: 'conv_1' });
    api.sendMessage.mockResolvedValue({ final_response: 'Here is INR 279.00', guardrail_status: 'PASSED' });
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('Money is tight'));
    await act(() => result.current.send('Yes please'));

    expect(api.startConversation).toHaveBeenCalledTimes(1);
    expect(api.startConversation).toHaveBeenCalledWith('eval_case_01');
    expect(api.sendMessage.mock.calls).toEqual([
      ['conv_1', 'Money is tight'],
      ['conv_1', 'Yes please'],
    ]);
    expect(result.current.conversationId).toBe('conv_1');
    expect(result.current.messages).toHaveLength(5);
    expect(result.current.messages.at(-1).meta.guardrail_status).toBe('PASSED');
  });

  it('B16: a failed send is reported but never added to the history', async () => {
    api.startConversation.mockResolvedValue({ conversation_id: 'conv_1' });
    api.sendMessage.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'boom' } } });
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('Hello'));
    expect(result.current.messages).toEqual([{ role: 'assistant', content: 'Hi Aarav' }]);
    expect(result.current.failed).toEqual({ text: 'Hello', error: 'boom' });

    api.sendMessage.mockResolvedValueOnce({ final_response: 'Hi again' });
    await act(() => result.current.retry());
    expect(api.sendMessage).toHaveBeenLastCalledWith('conv_1', 'Hello');
    expect(api.startConversation).toHaveBeenCalledTimes(1);
    expect(result.current.failed).toBeNull();
  });

  it('switching scenario starts a fresh conversation', async () => {
    api.startConversation
      .mockResolvedValueOnce({ conversation_id: 'conv_1' })
      .mockResolvedValueOnce({ conversation_id: 'conv_2' });
    api.sendMessage.mockResolvedValue({ final_response: 'ok' });
    const { result, rerender } = renderHook(({ scenario }) => useConversation(scenario), {
      initialProps: { scenario: hotstar },
    });
    await act(() => result.current.send('one'));
    rerender({ scenario: notion });
    expect(result.current.messages).toEqual([{ role: 'assistant', content: 'Hello Rohan' }]);
    expect(result.current.conversationId).toBeNull();
    await act(() => result.current.send('two'));
    expect(api.sendMessage).toHaveBeenLastCalledWith('conv_2', 'two');
  });

  it('restores a conversation by id for the same scenario', async () => {
    const stored = [
      { role: 'assistant', content: 'Hi Aarav', meta: null },
      { role: 'user', content: 'Yes', meta: null },
      { role: 'assistant', content: 'Done', meta: { step: 'LINK_ISSUED' } },
    ];
    api.getConversation.mockResolvedValue({
      conversation_id: 'conv_9',
      scenario_id: 'eval_case_01',
      messages: stored,
    });
    const { result } = renderHook(() => useConversation(hotstar, 'conv_9'));
    await flush();
    expect(result.current.conversationId).toBe('conv_9');
    expect(result.current.messages).toEqual(stored);
    expect(result.current.trace).toEqual({ step: 'LINK_ISSUED' });
  });

  it('ignores blank messages', async () => {
    const { result } = renderHook(() => useConversation(hotstar));
    await act(() => result.current.send('   '));
    expect(api.startConversation).not.toHaveBeenCalled();
  });
});
