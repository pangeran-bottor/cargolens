"use client";

import { useEffect, useState } from "react";

import Chat from "@/components/Chat";
import KpiCards from "@/components/KpiCards";
import { CarrierChart, PerformanceChart, VolumeChart } from "@/components/charts";
import { getKpis, Kpis, QueryRow, runQuery } from "@/lib/api";

interface PerfRow {
  month: string;
  delivered: number;
  delayed: number;
}

export default function Dashboard() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [volume, setVolume] = useState<QueryRow[]>([]);
  const [perf, setPerf] = useState<PerfRow[]>([]);
  const [carriers, setCarriers] = useState<QueryRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [k, vol, delivered, delayed, car] = await Promise.all([
          getKpis(),
          runQuery({ metric: "count", group_by: "month" }),
          runQuery({ metric: "count", group_by: "month", filters: { statuses: ["delivered"] } }),
          runQuery({ metric: "count", group_by: "month", filters: { statuses: ["delayed"] } }),
          runQuery({ metric: "count", group_by: "carrier" }),
        ]);
        setKpis(k);
        setVolume(vol.rows);
        setCarriers(car.rows);
        const delayedByMonth = new Map(delayed.rows.map((r) => [r.month, r.value]));
        setPerf(
          delivered.rows.map((r) => ({
            month: r.month as string,
            delivered: r.value,
            delayed: (delayedByMonth.get(r.month) as number) ?? 0,
          })),
        );
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">CargoLens</h1>
        <p className="text-sm text-slate-500">
          Logistics analytics — calendar year 2025, 400 orders
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not reach the analytics API: {error}
        </div>
      )}

      {kpis && <KpiCards kpis={kpis} />}

      <div className="grid gap-4 lg:grid-cols-2">
        {volume.length > 0 && <VolumeChart rows={volume} />}
        {perf.length > 0 && <PerformanceChart rows={perf} />}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {carriers.length > 0 && <CarrierChart rows={carriers} />}
        <Chat />
      </div>
    </main>
  );
}
