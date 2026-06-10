import { Kpis } from "@/lib/api";

const CARDS: { key: keyof Kpis; label: string; fmt?: (v: number) => string }[] = [
  { key: "total_orders", label: "Total orders" },
  { key: "delivered_orders", label: "Delivered" },
  { key: "delayed_orders", label: "Delayed" },
  {
    key: "on_time_rate",
    label: "On-time delivery rate",
    fmt: (v) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: "avg_delivery_days",
    label: "Avg delivery time",
    fmt: (v) => `${v} days`,
  },
];

export default function KpiCards({ kpis }: { kpis: Kpis }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {CARDS.map(({ key, label, fmt }) => (
        <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {fmt ? fmt(kpis[key]) : kpis[key]}
          </p>
        </div>
      ))}
    </div>
  );
}
