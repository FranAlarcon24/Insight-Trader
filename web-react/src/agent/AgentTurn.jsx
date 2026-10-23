import { useEffect, useRef, useState } from "react";
import {
  PRIORITY_LABEL,
  TOOL_TYPE_LABEL,
  actionTone,
  fileName,
  formatArgs,
  ruleOf,
  scenarioLabel,
  summarizeResult,
} from "./format";
import {
  IconCheck,
  IconChevron,
  IconClose,
  IconDoc,
  IconReplan,
  LogoMark,
  ToolIcon,
} from "./icons";

const STEP_MS = 650;
const RULE_NAMES = {
  R0: "Contexto",
  R1: "Validación",
  R2: "Memoria",
  R3: "Riesgo",
  R4: "Calidad de datos",
  R5: "Concentración",
  R6: "Preferencia",
};

function sameTask(task, step) {
  return (
    task.herramienta === step.herramienta &&
    (task.args.ticker ?? null) === (step.args.ticker ?? null)
  );
}

function Replan({ entry }) {
  const rule = ruleOf(entry);
  const text = entry.replace(/^R\d\s+\w+:\s*/, "");
  return (
    <div className={`replan rule-${rule.id}`}>
      <span className="replan-tag">
        <IconReplan size={13} />
        {rule.id} · {RULE_NAMES[rule.id] ?? rule.name}
      </span>
      <span className="replan-text">{text}</span>
    </div>
  );
}

function PlanChecklist({ tasks, runningId, open, onToggle }) {
  const ordered = [...tasks].sort(
    (a, b) =>
      a.prioridad - b.prioridad ||
      Number(a.id.slice(1)) - Number(b.id.slice(1)),
  );
  const doneCount = tasks.filter((t) => t.estado !== "pendiente").length;
  const pct = tasks.length ? (doneCount / tasks.length) * 100 : 100;
  return (
    <div className="plan-card">
      <button
        className="plan-card-head"
        onClick={onToggle}
        aria-expanded={open}
      >
        <IconChevron open={open} size={14} />
        <span className="plan-card-title">Plan de ejecución</span>
        <span className="plan-progress">
          <span className="plan-bar">
            <span style={{ width: `${pct}%` }} />
          </span>
          {doneCount} de {tasks.length} tareas
        </span>
      </button>
      {open && (
        <ul className="checklist">
          {ordered.length === 0 && (
            <li className="check-empty">
              Sin tareas: no se identificó un activo.
            </li>
          )}
          {ordered.map((t) => {
            const status = t.id === runningId ? "en-curso" : t.estado;
            const [reason, cancelReason] = t.motivo.split(" | cancelada: ");
            return (
              <li
                key={t.id}
                className={`check status-${status} ${t.origen === "replanificacion" ? "is-new" : ""}`}
              >
                <span className="check-box">
                  {status === "en-curso" && <span className="spinner small" />}
                  {status === "completada" && <IconCheck size={11} />}
                  {status === "cancelada" && <IconClose size={11} />}
                </span>
                <span className="check-main">
                  <span className="check-line">
                    <span
                      className={`prio prio-${t.prioridad}`}
                      title={`Prioridad ${PRIORITY_LABEL[t.prioridad]}`}
                    >
                      P{t.prioridad}
                    </span>
                    <span className="check-tool mono">{t.herramienta}</span>
                    {t.origen === "replanificacion" && (
                      <span className="new-badge">Re-planificada</span>
                    )}
                  </span>
                  <span className="check-reason">
                    {cancelReason ? `Cancelada: ${cancelReason}` : reason}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function ToolStep({ step, index }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`step type-${step.tipo}`}>
      <button
        className="step-row"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="step-icon">
          <ToolIcon tipo={step.tipo} size={14} />
        </span>
        <span className="step-main">
          <span className="step-line">
            <span className="step-tool mono">{step.herramienta}</span>
            <span className="type-tag">{TOOL_TYPE_LABEL[step.tipo]}</span>
          </span>
          <span className="step-summary">
            {summarizeResult(step.herramienta, step.resultado)}
          </span>
        </span>
        <span className="step-side">
          <span className="step-num">{String(index + 1).padStart(2, "0")}</span>
          <IconChevron open={open} size={13} />
        </span>
      </button>
      {open && (
        <div className="step-detail">
          <div className="detail-label">Argumentos</div>
          <code className="mono">
            {formatArgs(step.args) || "(sin argumentos)"}
          </code>
          <div className="detail-label">Respuesta de la herramienta</div>
          <pre className="mono">{JSON.stringify(step.resultado, null, 2)}</pre>
        </div>
      )}
      {step.decisiones.map((d) => (
        <Replan key={d} entry={d} />
      ))}
    </li>
  );
}

function FinalAnswer({ turn }) {
  const tone = actionTone(turn.accion);
  // La ruta del informe y las alertas se muestran aparte
  const text = turn.respuesta.split("\nInforme guardado")[0];
  const [, justification = ""] = text.split("\nJustificacion: ");
  const body = justification
    ? justification.split("\nAlertas registradas")[0]
    : text;
  return (
    <div className={`final tone-${tone}`}>
      {turn.accion && (
        <div className="final-action">
          <span className="final-label">
            Recomendación{turn.ticker ? ` · ${turn.ticker}` : ""}
          </span>
          <span className="final-value">{turn.accion}</span>
        </div>
      )}
      <p className="final-body">{body}</p>
      {turn.alertas.length > 0 && (
        <div className="alert-box">
          <div className="detail-label">Alertas enviadas al asesor</div>
          <ul className="alert-list">
            {turn.alertas.map((a, i) => (
              <li key={i}>
                <span className={`sev sev-${a.severidad}`}>{a.severidad}</span>
                <span className="mono alert-ticker">{a.ticker}</span>
                <span>{a.motivo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {turn.informe && (
        <div className="final-file">
          <IconDoc size={14} />
          <span className="mono">{fileName(turn.informe)}</span>
        </div>
      )}
    </div>
  );
}

export default function AgentTurn({ turn, animate }) {
  const total = turn.pasos.length;
  const [shown, setShown] = useState(animate ? 0 : total);
  // null = automatico: abierto mientras el agente trabaja, colapsado al terminar
  const [planToggle, setPlanToggle] = useState(null);
  const endRef = useRef(null);
  const done = shown >= total;
  const planOpen = planToggle ?? !done;

  useEffect(() => {
    if (done) return undefined;
    const timer = setTimeout(() => setShown((k) => k + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [shown, done]);

  // Durante la animacion la vista sigue al ultimo paso ejecutado
  useEffect(() => {
    if (animate) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [shown, animate]);

  const tasks = shown === 0 ? turn.plan_inicial : turn.pasos[shown - 1].plan;
  const next = done ? null : turn.pasos[shown];
  const running = next
    ? tasks.find((t) => t.estado === "pendiente" && sameTask(t, next))
    : null;
  const interpretation = turn.plan_log.filter((e) => e.startsWith("R0"));

  return (
    <div className="agent-msg">
      <div className="msg-avatar">
        <LogoMark size={28} />
      </div>
      <div className="agent-content">
        <div className="agent-name">
          <span>Insight Trader</span>
          <span className={`scenario-chip sc-${turn.escenario}`}>
            {scenarioLabel(turn.escenario)}
          </span>
          <span className="agent-name-actions">
            {!done && (
              <button className="link-btn" onClick={() => setShown(total)}>
                Saltar animación
              </button>
            )}
            {done && total > 0 && animate && (
              <button
                className="link-btn"
                onClick={() => {
                  setShown(0);
                  setPlanToggle(null);
                }}
              >
                Repetir ejecución
              </button>
            )}
          </span>
        </div>

        {interpretation.map((e) => (
          <Replan key={e} entry={e} />
        ))}

        <PlanChecklist
          tasks={tasks}
          runningId={running?.id}
          open={planOpen}
          onToggle={() => setPlanToggle(!planOpen)}
        />

        {total > 0 && (
          <ol className="steps">
            {turn.pasos.slice(0, shown).map((step, i) => (
              <ToolStep key={i} step={step} index={i} />
            ))}
            {next && (
              <li className="step pending">
                <div className="step-row">
                  <span className="step-icon">
                    <span className="spinner small" />
                  </span>
                  <span className="pending-text">
                    Ejecutando <span className="mono">{next.herramienta}</span>…
                  </span>
                </div>
              </li>
            )}
          </ol>
        )}

        {done && <FinalAnswer turn={turn} />}
        <div ref={endRef} className="scroll-anchor" />
      </div>
    </div>
  );
}
