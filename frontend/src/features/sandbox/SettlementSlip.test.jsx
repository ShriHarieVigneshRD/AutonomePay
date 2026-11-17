import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SettlementSlip } from './SettlementSlip';

const hotstar = { max_discount_inr: 20, max_grace_days: 3, policy: {} };
const turn = (overrides) => ({
  action: 'PROPOSE_SETTLEMENT',
  guardrail_status: 'PASSED',
  guardrail_violations: [],
  razorpay_payload: null,
  proposed_offer: {
    original_amount: 299,
    proposed_amount: 279,
    discount_inr: 20,
    grace_days: 0,
    split_amounts: [],
  },
  ...overrides,
});

describe('SettlementSlip', () => {
  it('shows invoice, concession, net payable and a full discount meter', () => {
    render(<SettlementSlip turn={turn()} scenario={hotstar} />);
    const slip = screen.getByRole('article', { name: 'Settlement slip' });
    expect(within(slip).getByText('−₹20.00')).toBeInTheDocument();
    expect(within(slip).getByText('₹279.00')).toBeInTheDocument();
    expect(within(slip).getByRole('meter', { name: /Discount used: ₹20.00 of ₹20.00/ })).toBeInTheDocument();
    expect(within(slip).getByText(/within bounds/i)).toBeInTheDocument();
    expect(within(slip).getByText(/only after the customer agrees/)).toBeInTheDocument();
  });

  it('shows instalments for a split and the amount due now', () => {
    const split = turn({
      action: 'MILESTONE_SPLIT',
      proposed_offer: {
        original_amount: 15000,
        proposed_amount: 7500,
        discount_inr: 0,
        grace_days: 0,
        split_amounts: [7500, 7500],
      },
    });
    render(<SettlementSlip turn={split} scenario={{ ...hotstar, max_discount_inr: 0 }} />);
    expect(screen.getByText('Instalment 2 (later)')).toBeInTheDocument();
    expect(screen.getByText('Due now')).toBeInTheDocument();
    expect(screen.queryByRole('meter', { name: /Discount used/ })).not.toBeInTheDocument();
  });

  it('shows the held portion for a partial settlement', () => {
    const partial = turn({
      action: 'PARTIAL_SETTLEMENT',
      proposed_offer: {
        original_amount: 85000,
        proposed_amount: 68000,
        discount_inr: 0,
        grace_days: 0,
        split_amounts: [],
      },
    });
    render(
      <SettlementSlip turn={partial} scenario={{ ...hotstar, policy: { partial_settlement_pct: 80 } }} />,
    );
    expect(screen.getByText('−₹17,000.00')).toBeInTheDocument();
  });

  it('shows the corrected stamp, the reason and the real payment link', () => {
    const corrected = turn({
      guardrail_status: 'POLICY_BREACH_CORRECTED',
      guardrail_violations: ['Proposed discount exceeds the ceiling.'],
      razorpay_payload: {
        success: true,
        sandbox: true,
        amount_in_inr: 279,
        short_url: 'http://localhost:5173/pay/x',
      },
    });
    render(<SettlementSlip turn={corrected} scenario={hotstar} />);
    expect(screen.getByText(/corrected/i)).toBeInTheDocument();
    expect(screen.getByText(/exceeds the ceiling/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Pay ₹279.00/ })).toHaveAttribute(
      'href',
      'http://localhost:5173/pay/x',
    );
  });

  it('renders nothing for escalations and blocked turns', () => {
    const { container } = render(
      <SettlementSlip turn={turn({ action: 'HUMAN_ESCALATION' })} scenario={hotstar} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
