"use client";

import AccessGate from "@/components/AccessGate";
import Dashboard from "@/components/Dashboard";

export default function Home() {
  return (
    <AccessGate>
      <Dashboard />
    </AccessGate>
  );
}
