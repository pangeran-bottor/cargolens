"use client";

import { useRef, useState } from "react";

import { askQuestion, ChatResponse, ToolResult } from "@/lib/api";
import { DynamicChart } from "@/components/DynamicChart";

const SUGGESTIONS: { level: string; questions: string[] }[] = [
  {
    level: "Descriptive — what happened",
    questions: [
      "What is the on-time delivery rate?",
      "Show order volume by month",
      "Break down orders by region",
    ],
  },
  {
    level: "Diagnostic — why",
    questions: [
      "Show delayed orders by week for the last 3 months",
      "Which carrier has the highest delay rate?",
      "How many orders were delivered late last month?",
    ],
  },
  {
    level: "Predictive & prescriptive — what's next",
    questions: [
      "Predict demand for CRAYON for the next 4 months",
      "How much inventory should I plan for paper products?",
    ],
  },
];

interface Turn {
  question: string;
  response?: ChatResponse;
  pending?: boolean;
}

function ExplainPanel({ result }: { result: ToolResult }) {
  const [open, setOpen] = useState(false);
  const { explain } = result;
  return (
    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-3 py-2 text-left font-medium text-slate-600 hover:text-slate-900"
      >
        {open ? "▾" : "▸"} How this was computed
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3">
          <p>
            <span className="font-medium">Tool:</span> {result.tool}
            {explain.spec.metric != null && (
              <>
                {" "}· <span className="font-medium">Metric:</span>{" "}
                {String(explain.spec.metric)} ·{" "}
                <span className="font-medium">Grouped by:</span>{" "}
                {String(explain.spec.group_by)}
              </>
            )}
            {explain.entity != null && (
              <>
                {" "}· <span className="font-medium">Entity:</span>{" "}
                {String(explain.entity)} ·{" "}
                <span className="font-medium">Demand:</span>{" "}
                {String(explain.demand_metric)}
              </>
            )}
          </p>
          {(explain.filters_applied?.length ?? 0) > 0 && (
            <p>
              <span className="font-medium">Filters:</span>{" "}
              {explain.filters_applied!.join("; ")}
            </p>
          )}
          {(explain.implicit_filters?.length ?? 0) > 0 && (
            <p>
              <span className="font-medium">Built-in rules:</span>{" "}
              {explain.implicit_filters!.join("; ")}
            </p>
          )}
          {explain.methodology && (
            <p>
              <span className="font-medium">Methodology:</span>{" "}
              {explain.methodology}
            </p>
          )}
          {explain.sql && (
            <p className="font-mono text-[11px] text-slate-500">{explain.sql}</p>
          )}
          {result.rows.length > 0 && (
            <div className="max-h-48 overflow-auto rounded border border-slate-200 bg-white">
              <table className="w-full text-left text-[11px]">
                <thead className="sticky top-0 bg-slate-100">
                  <tr>
                    {Object.keys(result.rows[0]).map((col) => (
                      <th key={col} className="px-2 py-1 font-medium">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      {Object.values(row).map((v, j) => (
                        <td key={j} className="px-2 py-1">{String(v)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ExampleQuestions({
  open,
  onToggle,
  onPick,
}: {
  open: boolean;
  onToggle: () => void;
  onPick: (q: string) => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50">
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 text-left text-xs font-medium text-slate-600 hover:text-slate-900"
      >
        {open ? "▾" : "▸"} Example questions — three levels of intelligence
      </button>
      {open && (
        <div className="space-y-3 px-3 pb-3">
          {SUGGESTIONS.map(({ level, questions }) => (
            <div key={level}>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                {level}
              </p>
              <div className="space-y-1">
                {questions.map((q) => (
                  <button
                    key={q}
                    onClick={() => onPick(q)}
                    className="block w-full rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-left text-xs text-slate-700 hover:border-blue-300 hover:bg-blue-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showExamples, setShowExamples] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function submit(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setInput("");
    setShowExamples(false);
    setTurns((t) => [...t, { question, pending: true }]);
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    try {
      const response = await askQuestion(question);
      setTurns((t) =>
        t.map((turn, i) => (i === t.length - 1 ? { question, response } : turn)),
      );
    } catch (e) {
      setTurns((t) =>
        t.map((turn, i) =>
          i === t.length - 1
            ? {
                question,
                response: {
                  answer: null,
                  results: [],
                  error: `Could not reach the API: ${e}`,
                },
              }
            : turn,
        ),
      );
    } finally {
      setBusy(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="font-semibold text-slate-900">Ask the data</h2>
        <p className="text-xs text-slate-500">
          Questions are interpreted by AI, computed deterministically from the
          dataset, and every answer shows its work.
        </p>
      </div>

      <div className="max-h-[32rem] space-y-4 overflow-y-auto p-4">
        {turns.length === 0 && !showExamples && (
          <p className="text-sm text-slate-500">
            Ask a question below, or open the example questions.
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <div className="ml-auto w-fit max-w-[85%] rounded-xl bg-blue-600 px-3 py-2 text-sm text-white">
              {turn.question}
            </div>
            {turn.pending && (
              <div className="w-fit rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-500">
                Thinking…
              </div>
            )}
            {turn.response?.error && (
              <div className="w-fit max-w-[85%] rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                {turn.response.error}
              </div>
            )}
            {turn.response?.answer && (
              <div className="w-fit max-w-[85%] whitespace-pre-wrap rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-800">
                {turn.response.answer}
              </div>
            )}
            {turn.response?.results.map((result, j) => (
              <div key={j}>
                <DynamicChart result={result} />
                <ExplainPanel result={result} />
              </div>
            ))}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-200 p-3 pb-0">
        <ExampleQuestions
          open={showExamples}
          onToggle={() => setShowExamples(!showExamples)}
          onPick={submit}
        />
      </div>

      <form
        className="flex gap-2 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about orders, delays, carriers…"
          maxLength={500}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-400"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
