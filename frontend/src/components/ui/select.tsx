'use client';

import * as React from "react";

type NativeSelectProps = Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "onChange"> & {
  onValueChange?: (value: string) => void;
  placeholder?: string;
};

export const Select = React.forwardRef<HTMLSelectElement, NativeSelectProps>(
  ({ className = "", children, onValueChange, placeholder, value, defaultValue, ...rest }, ref) => {
    const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
      onValueChange?.(event.target.value);
    };

    return (
      <select
        ref={ref}
        value={value}
        defaultValue={defaultValue}
        onChange={handleChange}
        className={`h-11 w-full rounded-xl border border-white/20 bg-slate-900/80 px-3 text-sm text-white outline-none transition focus:border-emerald-400/70 ${className}`}
        {...rest}
      >
        {placeholder ? (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        ) : null}
        {children}
      </select>
    );
  },
);
Select.displayName = "Select";

export const SelectOption = ({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) => <option value={value}>{children}</option>;
