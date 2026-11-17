import { describe, expect, it } from 'vitest';
import { outcomeOf } from '../benchmark/CaseLedger';
import { filterScenarios, groupScenarios } from './ScenarioPicker';

const sc = (id, merchant_name, extra = {}) => ({
  id,
  title: `${id} ${merchant_name}`,
  merchant_name,
  customer_name: 'Someone',
  category: 'OTT',
  scenario_type_title: 'Budget',
  scenario_type: 'X',
  is_multi_turn: true,
  ...extra,
});
const list = [
  sc('eval_case_01', 'Disney+ Hotstar'),
  sc('eval_case_02', 'Notion SaaS', { category: 'B2B' }),
  sc('eval_case_04', 'Disney+ Hotstar', {
    scenario_type: 'ADVERSARIAL_INJECTION_ATTEMPT',
    is_multi_turn: false,
  }),
];

describe('case browser filtering', () => {
  it('searches across merchant, id and customer', () => {
    expect(filterScenarios(list, 'notion', 'all').map((s) => s.id)).toEqual(['eval_case_02']);
    expect(filterScenarios(list, 'case_04', 'all')).toHaveLength(1);
  });

  it('filters by turn count and adversarial cases', () => {
    expect(filterScenarios(list, '', 'single').map((s) => s.id)).toEqual(['eval_case_04']);
    expect(filterScenarios(list, '', 'adversarial').map((s) => s.id)).toEqual(['eval_case_04']);
    expect(filterScenarios(list, '', 'multi')).toHaveLength(2);
  });

  it('treats every ADVERSARIAL_* scenario as adversarial', () => {
    const later = sc('eval_case_36', 'Disney+ Hotstar', {
      scenario_type: 'ADVERSARIAL_LATER_TURN_INJECTION',
    });
    expect(filterScenarios([...list, later], '', 'adversarial').map((s) => s.id)).toEqual([
      'eval_case_04',
      'eval_case_36',
    ]);
  });

  it('groups by merchant or sector, or not at all', () => {
    expect(groupScenarios(list, 'merchant').map(([name, cases]) => [name, cases.length])).toEqual([
      ['Disney+ Hotstar', 2],
      ['Notion SaaS', 1],
    ]);
    expect(groupScenarios(list, 'sector').map(([name]) => name)).toEqual(['OTT', 'B2B']);
    expect(groupScenarios(list, 'flat')[0][1]).toHaveLength(3);
  });
});

describe('ledger outcome', () => {
  it('ranks blocked, failed and corrected above within-bounds', () => {
    expect(outcomeOf(undefined)).toBe('pending');
    expect(outcomeOf({ guardrail_status: 'ADVERSARIAL_INTERCEPTED', passed: false })).toBe('blocked');
    expect(outcomeOf({ guardrail_status: 'POLICY_BREACH_CORRECTED', passed: false })).toBe('failed');
    expect(outcomeOf({ guardrail_status: 'POLICY_BREACH_CORRECTED', passed: true })).toBe('corrected');
    expect(outcomeOf({ guardrail_status: 'PASSED', passed: null })).toBe('within');
  });
});
