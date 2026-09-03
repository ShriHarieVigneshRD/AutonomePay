import React, { useState, useRef, useEffect } from 'react';
import { Sparkle, CaretDown, MagnifyingGlass, Funnel, Storefront, Tag, Buildings, ListNumbers, Check, X } from '@phosphor-icons/react';

export default function ScenarioSelector({ scenarios = [], activeScenario, onSelectScenario }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [groupBy, setGroupBy] = useState('merchant'); // 'merchant' | 'intent' | 'sector' | 'flat'
  const [filterType, setFilterType] = useState('all'); // 'all' | 'multi' | 'single' | 'adversarial'
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter scenarios
  const filteredScenarios = scenarios.filter((sc) => {
    const query = search.toLowerCase().trim();
    const matchesSearch =
      !query ||
      sc.title.toLowerCase().includes(query) ||
      sc.id.toLowerCase().includes(query) ||
      sc.merchant_name.toLowerCase().includes(query) ||
      sc.customer_name.toLowerCase().includes(query) ||
      sc.category.toLowerCase().includes(query) ||
      sc.scenario_type_title?.toLowerCase().includes(query);

    if (!matchesSearch) return false;

    if (filterType === 'multi') return sc.is_multi_turn;
    if (filterType === 'single') return !sc.is_multi_turn;
    if (filterType === 'adversarial') return sc.scenario_type === 'ADVERSARIAL_INJECTION_ATTEMPT';
    return true;
  });

  // Group scenarios
  const groupScenarios = () => {
    if (groupBy === 'flat') {
      return { 'All 50 Benchmark Cases': filteredScenarios };
    }

    const groups = {};
    filteredScenarios.forEach((sc) => {
      let key = 'Other';
      if (groupBy === 'merchant') key = sc.merchant_name || sc.merchant_id;
      else if (groupBy === 'intent') key = sc.scenario_type_title || sc.scenario_type;
      else if (groupBy === 'sector') key = sc.category || 'General';

      if (!groups[key]) groups[key] = [];
      groups[key].push(sc);
    });

    return groups;
  };

  const grouped = groupScenarios();

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Trigger Button Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2.5 bg-slate-900/90 hover:bg-slate-850 border border-slate-700/80 hover:border-emerald-500/50 rounded-xl px-3.5 py-2 text-xs transition-all shadow-md cursor-pointer group"
      >
        <Sparkle className="w-4 h-4 text-emerald-400 animate-pulse group-hover:scale-110 transition-transform" weight="fill" />
        <span className="text-slate-400 font-medium hidden sm:inline">Scenario:</span>
        <span className="text-slate-100 font-bold max-w-[200px] md:max-w-[260px] truncate">
          {activeScenario ? activeScenario.title : 'Select Scenario (50 Cases)'}
        </span>
        <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">
          50 Cases
        </span>
        <CaretDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180 text-emerald-400' : ''}`} />
      </button>

      {/* Dropdown Modal Container */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-[340px] sm:w-[460px] md:w-[560px] bg-slate-950/95 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-[580px] animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Header & Search */}
          <div className="p-4 bg-slate-900/90 border-b border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Funnel className="w-4 h-4 text-emerald-400" />
                <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wider">Benchmark Test Suite (50 Scenarios)</h4>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Search Input */}
            <div className="relative">
              <MagnifyingGlass className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search 50 cases by merchant, customer, case #, or intent..."
                className="w-full bg-slate-900 text-slate-100 placeholder-slate-500 text-xs pl-9 pr-4 py-2 rounded-xl border border-slate-800 focus:outline-none focus:border-emerald-500/60 font-sans"
              />
            </div>

            {/* Grouping Toggle Controls */}
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium">Group By:</span>
              <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setGroupBy('merchant')}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    groupBy === 'merchant' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Storefront className="w-3.5 h-3.5" />
                  <span>Merchant</span>
                </button>
                <button
                  onClick={() => setGroupBy('intent')}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    groupBy === 'intent' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Tag className="w-3.5 h-3.5" />
                  <span>Intent</span>
                </button>
                <button
                  onClick={() => setGroupBy('sector')}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    groupBy === 'sector' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Buildings className="w-3.5 h-3.5" />
                  <span>Sector</span>
                </button>
                <button
                  onClick={() => setGroupBy('flat')}
                  className={`flex items-center space-x-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    groupBy === 'flat' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ListNumbers className="w-3.5 h-3.5" />
                  <span>Flat</span>
                </button>
              </div>
            </div>

            {/* Quick Filter Badges */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-[10px] font-mono">
              <button
                onClick={() => setFilterType('all')}
                className={`px-2.5 py-1 rounded-full border transition-all ${
                  filterType === 'all' ? 'bg-slate-800 text-slate-100 border-slate-600 font-bold' : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                All ({scenarios.length})
              </button>
              <button
                onClick={() => setFilterType('multi')}
                className={`px-2.5 py-1 rounded-full border transition-all ${
                  filterType === 'multi' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold' : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                Multi-Turn (80%)
              </button>
              <button
                onClick={() => setFilterType('single')}
                className={`px-2.5 py-1 rounded-full border transition-all ${
                  filterType === 'single' ? 'bg-blue-500/20 text-blue-300 border-blue-500/40 font-bold' : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                Single-Turn (20%)
              </button>
              <button
                onClick={() => setFilterType('adversarial')}
                className={`px-2.5 py-1 rounded-full border transition-all ${
                  filterType === 'adversarial' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold' : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                Adversarial Attacks
              </button>
            </div>
          </div>

          {/* Grouped Scenarios List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5 max-h-[380px]">
            {Object.keys(grouped).length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No scenarios match your search query "{search}".
              </div>
            ) : (
              Object.entries(grouped).map(([groupTitle, caseList]) => (
                <div key={groupTitle} className="space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800/80 pb-1">
                    <span>{groupTitle}</span>
                    <span className="text-[10px] font-mono text-slate-500">({caseList.length} cases)</span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {caseList.map((sc) => {
                      const isActive = activeScenario?.id === sc.id;
                      return (
                        <div
                          key={sc.id}
                          onClick={() => {
                            onSelectScenario(sc);
                            setIsOpen(false);
                          }}
                          className={`p-3 rounded-xl border transition-all cursor-pointer hover:scale-[1.01] active:scale-[0.99] flex items-center justify-between ${
                            isActive
                              ? 'bg-emerald-500/10 border-emerald-500/50 shadow-md'
                              : 'bg-slate-900/70 hover:bg-slate-850 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="space-y-1 max-w-[85%]">
                            <div className="flex items-center space-x-2">
                              <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 shrink-0">
                                {sc.id.replace('eval_case_', '#')}
                              </span>
                              <span className="text-xs font-bold text-slate-100 truncate">{sc.title}</span>
                            </div>
                            <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-sans">
                              <span>Customer: <strong className="text-slate-300">{sc.customer_name}</strong></span>
                              <span>•</span>
                              <span>Plan: <strong className="text-amber-300">{sc.plan_name}</strong></span>
                              <span>•</span>
                              <span className="font-mono text-emerald-400 font-semibold">INR {sc.original_amount?.toFixed(2)}</span>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2">
                            {isActive && <Check className="w-5 h-5 text-emerald-400 shrink-0" weight="bold" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
