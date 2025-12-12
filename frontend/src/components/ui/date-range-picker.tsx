'use client';

import * as React from "react";

export interface DateRange {
  from: string;
  to: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (next: DateRange) => void;
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const handleChange =
    (field: keyof DateRange) => (event: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, [field]: event.target.value });
    };

  return (
    <div className="grid gap-2 rounded-2xl border border-white/15 bg-slate-900/80 p-3">
      <p className="text-xs uppercase tracking-wide text-white/50">Date range</p>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <label className="flex flex-col gap-1 text-white/70">
          <span className="text-[11px] uppercase tracking-wide text-white/40">From</span>
          <input
            type="date"
            value={value.from}
            onChange={handleChange("from")}
            className="rounded-xl border border-white/20 bg-transparent px-3 py-2 text-white outline-none focus:border-emerald-400/70"
          />
        </label>
        <label className="flex flex-col gap-1 text-white/70">
          <span className="text-[11px] uppercase tracking-wide text-white/40">To</span>
          <input
            type="date"
            value={value.to}
            onChange={handleChange("to")}
            className="rounded-xl border border-white/20 bg-transparent px-3 py-2 text-white outline-none focus:border-emerald-400/70"
          />
        </label>
      </div>
    </div>
  );
}
