"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { QueryRow } from "@/lib/api";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-medium text-slate-700">{title}</h2>
      <div className="h-64">{children}</div>
    </div>
  );
}

export function VolumeChart({ rows }: { rows: QueryRow[] }) {
  return (
    <Card title="Order volume over time (monthly)">
      <ResponsiveContainer>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" fontSize={12} />
          <YAxis fontSize={12} allowDecimals={false} />
          <Tooltip />
          <Line type="monotone" dataKey="value" name="orders" stroke="#2563eb" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function PerformanceChart({
  rows,
}: {
  rows: { month: string; delivered: number; delayed: number }[];
}) {
  return (
    <Card title="Delivery performance (on-time vs delayed, monthly)">
      <ResponsiveContainer>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" fontSize={12} />
          <YAxis fontSize={12} allowDecimals={false} />
          <Tooltip />
          <Legend />
          <Bar dataKey="delivered" name="on-time" stackId="a" fill="#16a34a" isAnimationActive={false} />
          <Bar dataKey="delayed" name="delayed" stackId="a" fill="#dc2626" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function CarrierChart({ rows }: { rows: QueryRow[] }) {
  return (
    <Card title="Orders by carrier">
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" fontSize={12} allowDecimals={false} />
          <YAxis type="category" dataKey="carrier" fontSize={12} width={80} />
          <Tooltip />
          <Bar dataKey="value" name="orders" fill="#2563eb" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
