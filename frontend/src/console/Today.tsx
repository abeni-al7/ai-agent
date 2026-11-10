import { Link } from "react-router-dom";
import type { Card, Event } from "../api";
import { Seal, StampMark, WekilMark } from "../Seal";
import { Empty, Serial, Status, TierMark, ago, date, describe, time } from "../ui";
import { usePoll } from "./usePoll";

interface Today {
  ready: Card[]; attention: Card[]; in_progress: Card[]; awaiting: Card[];
  overdue: { merchant_id: number; merchant: string; due_on: string; reminders: number; status: string }[];
  cases: { id: number; merchant_id: number; merchant: string; kind: string; detail: string; due_on: string }[];
  feed: Event[]; counts: Record<string, number>;
}

const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
};

export function TodayPage() {
  const { data } = usePoll<Today>("/api/today", 5000);
  if (!data) return <p className="muted pad">Loading today's desk…</p>;
  const decide = [...data.attention, ...data.ready];
  return (
    <div className="today">
      <header className="page-head">
        <h1>{greeting()}. {decide.length ? `${decide.length} decision${decide.length > 1 ? "s need" : " needs"} you.` : "Nothing needs your decision."}</h1>
        <p className="muted">
          {data.counts.awaiting_merchant ?? 0} waiting on merchants, {data.in_progress.length} being reviewed by Wekil,{" "}
          {data.cases.length} open monitoring case{data.cases.length === 1 ? "" : "s"}.
        </p>
      </header>

      <section aria-labelledby="decide">
        <h2 id="decide">Ready for your decision</h2>
        {decide.length === 0 ? <Empty>Wekil prepares a memo for every complete application. None are waiting.</Empty> : (
          <ul className="decisions">
            {decide.map((m) => (
              <li key={m.id}>
                <Link to={`/m/${m.id}`} className="decision">
                  <Seal tier={m.risk_tier} size={64} animate={false} />
                  <span className="decision__main">
                    <strong>{m.name}</strong>
                    <span className="decision__meta"><Serial id={m.id} /><Status status={m.status} /></span>
                  </span>
                  <span className="decision__flags">
                    <TierMark tier={m.risk_tier} score={m.risk_score} />
                    {m.open_hits > 0 && <span className="flag flag--block">{m.open_hits} possible sanctions match</span>}
                    {m.blockers > 0 && <span className="flag flag--hold">{m.blockers} open finding{m.blockers > 1 ? "s" : ""}</span>}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="today__split">
        <section aria-labelledby="cases">
          <h2 id="cases">Monitoring cases</h2>
          {data.cases.length === 0 && data.overdue.length === 0 ? <Empty>No open cases. Wekil checks expiries, reviews and the sanctions lists every morning.</Empty> : (
            <ul className="rows">
              {data.cases.map((c) => (
                <li key={`c${c.id}`}>
                  <Link to={`/m/${c.merchant_id}`}>
                    <span className={`case case--${c.kind}`}>{c.kind === "rescreen_hit" ? "Sanctions rescreen" : c.kind === "renewal" ? "Renewal" : "Periodic review"}</span>
                    <strong>{c.merchant}</strong>
                    <span className="muted">{c.detail}</span>
                    <span className="rows__date">due {date(c.due_on)}</span>
                  </Link>
                </li>
              ))}
              {data.overdue.map((r) => (
                <li key={`r${r.merchant_id}`}>
                  <Link to={`/m/${r.merchant_id}`}>
                    <span className="case case--overdue">{r.status === "escalated" ? "Escalated" : "Overdue reply"}</span>
                    <strong>{r.merchant}</strong>
                    <span className="muted">{r.reminders} reminder{r.reminders === 1 ? "" : "s"} sent</span>
                    <span className="rows__date">was due {date(r.due_on)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="log">
          <h2 id="log">What Wekil and the desk did</h2>
          <ol className="log">
            {data.feed.map((e, i) => (
              <li key={i} className={`log__item log__item--${e.actor}`}>
                {e.actor === "analyst" ? <StampMark /> : <WekilMark />}
                <span>
                  {e.merchant && e.merchant_id ? <Link to={`/m/${e.merchant_id}`}>{e.merchant}</Link> : null}
                  {e.merchant ? ": " : ""}{describe(e)}
                </span>
                <time dateTime={e.at} title={new Date(e.at).toLocaleString()}>{ago(e.at) === "today" ? time(e.at) : ago(e.at)}</time>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
