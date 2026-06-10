"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ToolResult } from "@/lib/api";

/** Renders the chart type the backend selected from the spec shape:
 *  time series → line, categorical breakdown → bar, scalar → stat card. */
export function DynamicChart({ result }: { result: ToolResult }) {
  const { rows, suggested_chart } = result;
  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
        No matching data.
      </p>
    );
  }

  const dimension = Object.keys(rows[0]).find((k) => k !== "value");

  if (suggested_chart === "number" || !dimension) {
    return (
      <div className="w-fit rounded-lg border border-slate-200 bg-white px-4 py-3">
        <p className="text-2xl font-semibold text-slate-900">
          {rows[0].value}
        </p>
      </div>
    );
  }

  if (suggested_chart === "line") {
    return (
      <div className="h-56 rounded-lg border border-slate-200 bg-white p-2">
        <ResponsiveContainer>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={dimension} fontSize={11} />
            <YAxis fontSize={11} allowDecimals={false} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="h-56 rounded-lg border border-slate-200 bg-white p-2">
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" fontSize={11} />
          <YAxis type="category" dataKey={dimension} fontSize={11} width={90} />
          <Tooltip />
          <Bar dataKey="value" fill="#2563eb" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
