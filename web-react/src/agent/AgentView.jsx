import { useEffect, useRef, useState } from "react";
import demo from "../data/agent_demo.json";
import {
  askAgent,
  deleteClient,
  detectLiveApi,
  fetchClients,
  resetMemory,
} from "./api";
import { SCENARIOS, SUGGESTIONS, scenarioLabel } from "./format";
import InfoPage from "./InfoPages";
import MarketPage from "./MarketPage";
import RecommendationsPage from "./RecommendationsPage";
import ObservabilityPage from "./ObservabilityPage";
import AgentTurn from "./AgentTurn";
import NewClientModal from "./NewClientModal";
import {
  IconClipboard,
  IconClose,
  IconFlow,
  IconGauge,
  IconMemory,
  IconPanel,
  IconPlus,
  IconPulse,
  IconSend,
  IconSpark,
  IconTarget,
  IconTrash,
  LogoMark,
} from "./icons";
import "./agent.css";
import "./forms.css";
import "./market.css";
import "./observability.css";

// Ids generados solo desde manejadores de eventos (nunca durante el render)
let idSeq = 0;
const nextId = (prefix) => `${prefix}-${Date.now()}-${++idSeq}`;

// Secciones informativas fijas (barra lateral, sobre "Nueva conversacion")
const INFO_PAGES = [
  { id: "como-funciona", label: "¿Cómo funciona?", Icon: IconFlow },
  { id: "para-que-sirve", label: "¿Para qué sirve?", Icon: IconTarget },
  { id: "que-evaluamos", label: "¿Qué evaluamos?", Icon: IconGauge },
  { id: "como-te-beneficia", label: "¿Cómo te beneficia?", Icon: IconSpark },
];

const initials = (name) =>
  name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");

function Welcome({
  live,
  clients,
  scripts,
  onPickClient,
  onPickScript,
  onNewClient,
}) {
  return (
    <div className="welcome">
      <LogoMark size={44} />
      <h1>Agente de inversiones</h1>
      <p>
        Insight Trader planifica, consulta el portafolio y el mercado, evalúa el
        riesgo y deja alertas e informes para el asesor. Cada decisión queda
        trazada.
      </p>
      {live !== false ? (
        <>
          <div className="welcome-label">
            Selecciona el cliente que vas a asesorar
          </div>
          <div className="welcome-grid">
            {clients.map((c) => (
              <button
                key={c.client_id}
                className="welcome-card"
                onClick={() => onPickClient(c.client_id)}
                disabled={live === null}
              >
                <span className="initials">{initials(c.client_name)}</span>
                <span className="welcome-card-name">{c.client_name}</span>
                <span className="welcome-card-id mono">{c.client_id}</span>
              </button>
            ))}
          </div>
          {live && (
            <button className="new-client-cta" onClick={onNewClient}>
              <span className="cta-icon">
                <IconPlus size={20} />
              </span>
              <span className="cta-text">
                <strong>Agregar nuevo cliente</strong>
                <small>
                  Crea su perfil de riesgo y portafolio para que el agente lo
                  asesore
                </small>
              </span>
            </button>
          )}
        </>
      ) : (
        <>
          <div className="welcome-label">
            Elige un escenario de demostración
          </div>
          <div className="welcome-grid scripts">
            {scripts.map((s) => (
              <button
                key={s.id}
                className="welcome-card"
                onClick={() => onPickScript(s.id)}
              >
                <span className="welcome-card-name">{s.titulo}</span>
                <span className="welcome-card-desc">{s.descripcion}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Conversation({
  items,
  loading,
  clientName,
  onSuggestion,
  showSuggestions,
  onRequery,
}) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items.length, loading]);

  return (
    <div className="convo">
      {items.length === 0 && (
        <div className="convo-start">
          <h2>Conversación con {clientName}</h2>
          <p>
            Pregunta por un activo, pide una revisión del portafolio o registra
            una preferencia. El agente obtendrá los datos del cliente con sus
            herramientas.
          </p>
          {showSuggestions && (
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion"
                  onClick={() => onSuggestion(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {items.map((item) => {
        if (item.type === "system") {
          return (
            <div key={item.id} className="convo-system-wrap">
              <div className="convo-system">
                <span>{item.text}</span>
              </div>
              {item.requery && (
                <button
                  className="requery-btn"
                  onClick={() => onRequery(item.requery)}
                  disabled={loading}
                >
                  Reevaluar “{item.requery}” con este escenario
                </button>
              )}
            </div>
          );
        }
        if (item.type === "user") {
          return (
            <div key={item.id} className="user-msg">
              {item.text}
            </div>
          );
        }
        return (
          <AgentTurn key={item.id} turn={item.turn} animate={item.fresh} />
        );
      })}
      {loading && (
        <div className="agent-msg">
          <div className="msg-avatar">
            <LogoMark size={28} />
          </div>
          <div className="agent-content">
            <div className="thinking">
              <span className="spinner small" /> Interpretando la solicitud y
              armando el plan…
            </div>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

function Composer({ onSend, disabled, placeholder }) {
  const [text, setText] = useState("");
  return (
    <form
      className="composer-box"
      onSubmit={(e) => {
        e.preventDefault();
        const q = text.trim();
        if (!q || disabled) return;
        onSend(q);
        setText("");
      }}
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        aria-label="Mensaje para el agente"
        disabled={disabled}
      />
      <button
        type="submit"
        className="send-btn"
        disabled={disabled || !text.trim()}
        aria-label="Enviar"
      >
        <IconSend size={16} />
      </button>
    </form>
  );
}

function ContextPanel({
  client,
  live,
  onClose,
  onClearMemory,
  onDelete,
  busy,
}) {
  return (
    <aside className="context-panel" aria-label="Contexto del cliente">
      <div className="panel-head">
        <span>Contexto del cliente</span>
        <button
          className="icon-btn"
          onClick={onClose}
          aria-label="Cerrar panel"
        >
          <IconClose size={16} />
        </button>
      </div>
      <div className="panel-body">
        <div className="ctx-identity">
          <span className="initials lg">{initials(client.client_name)}</span>
          <div>
            <div className="ctx-name">{client.client_name}</div>
            <div className="ctx-id mono">{client.client_id}</div>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-label">Perfil de riesgo</div>
          <dl className="ctx-kv">
            <dt>Categoría</dt>
            <dd className="cap">{client.risk_category}</dd>
            <dt>Tolerancia a drawdown</dt>
            <dd>{client.risk_tolerance}%</dd>
            <dt>Horizonte</dt>
            <dd>{client.investment_horizon_years} años</dd>
          </dl>
          <p className="ctx-note">{client.notes}</p>
        </div>

        <div className="panel-section">
          <div className="panel-label">Posiciones</div>
          <table className="holdings">
            <tbody>
              {client.holdings.map((h) => (
                <tr key={h.ticker}>
                  <td className="mono">{h.ticker}</td>
                  <td className="holding-name">{h.name}</td>
                  <td className="num mono">{h.weight}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {live && (
          <div className="panel-section">
            <div className="panel-label">Memoria de largo plazo</div>
            <div className="memory-stat">
              <IconMemory size={16} />
              <span>
                <strong>{client.memory_count}</strong> registros persistidos
                (SQLite)
              </span>
            </div>
            <button
              className="btn-secondary"
              onClick={onClearMemory}
              disabled={busy}
            >
              Borrar memoria del cliente
            </button>
          </div>
        )}

        {live && client.custom && (
          <div className="panel-section">
            <div className="panel-label">Cliente creado desde la web</div>
            <button className="btn-danger" onClick={onDelete} disabled={busy}>
              <IconTrash size={15} /> Eliminar cliente
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

export default function AgentView() {
  const [live, setLive] = useState(null);
  const [clients, setClients] = useState(demo.clientes);
  const [clientId, setClientId] = useState(null);
  const [scenario, setScenario] = useState("normal");
  const [threads, setThreads] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [contextOpen, setContextOpen] = useState(false);
  // "chat" o el id de una seccion; #observabilidad abre el dashboard directo
  const [page, setPage] = useState(() =>
    window.location.hash.startsWith("#observabilidad") ? "observabilidad" : "chat",
  );
  const scrollRef = useRef(null);

  // Cada seccion informativa se abre desde el inicio
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [page]);
  const [showNewClient, setShowNewClient] = useState(false);

  const [scriptId, setScriptId] = useState(null);
  const [played, setPlayed] = useState({});

  useEffect(() => {
    let cancelled = false;
    detectLiveApi().then(async (ok) => {
      if (cancelled) return;
      setLive(ok);
      if (ok) setClients(await fetchClients());
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const thread = (clientId && threads[clientId]) || { id: null, items: [] };

  // Modo grabado: la conversacion se arma con los turnos ya reproducidos
  const script = demo.guiones.find((g) => g.id === scriptId) ?? null;
  const playedCount = script ? (played[scriptId] ?? 0) : 0;
  const recordedItems = [];
  script?.turnos.slice(0, playedCount).forEach((turn, i) => {
    const prev = script.turnos[i - 1];
    if (prev && prev.escenario !== turn.escenario) {
      recordedItems.push({
        type: "system",
        id: `${scriptId}-s${i}`,
        text: `Condición de mercado: ${scenarioLabel(turn.escenario)}`,
      });
    }
    recordedItems.push({
      type: "user",
      id: `${scriptId}-u${i}`,
      text: turn.pregunta,
    });
    recordedItems.push({
      type: "agent",
      id: `${scriptId}-a${i}`,
      turn,
      fresh: i === playedCount - 1,
    });
  });

  const activeClientId = live === false ? script?.client_id : clientId;
  const client = clients.find((c) => c.client_id === activeClientId) ?? null;
  const items = live === false ? recordedItems : thread.items;
  const started = live === false ? Boolean(script) : Boolean(clientId);

  function updateThread(cid, fn) {
    setThreads((prev) => ({
      ...prev,
      [cid]: fn(prev[cid] ?? { id: null, items: [] }),
    }));
  }

  function changeScenario(next) {
    if (next === scenario) return;
    setScenario(next);
    if (clientId && thread.items.length > 0) {
      // Las respuestas anteriores son historial: se ofrece repetir la ultima
      // pregunta para ver como cambia la decision con el nuevo escenario.
      const lastQuestion = [...thread.items]
        .reverse()
        .find((i) => i.type === "user")?.text;
      updateThread(clientId, (t) => ({
        ...t,
        items: [
          ...t.items,
          {
            type: "system",
            id: nextId("sys"),
            text: `Condición de mercado: ${scenarioLabel(next)}`,
            requery: lastQuestion,
          },
        ],
      }));
    }
  }

  // `cid` permite enviar a otro cliente (ej. desde Recomendaciones) en el
  // mismo evento en que se cambia de cliente, antes de que se actualice el estado
  async function send(question, cid = clientId, sc = scenario) {
    setError(null);
    setLoading(true);
    const current = threads[cid] ?? { id: null, items: [] };
    const threadId = current.id ?? nextId(`web-${cid}`);
    updateThread(cid, (t) => ({
      ...t,
      id: threadId,
      items: [
        ...t.items.map((i) => ({ ...i, fresh: false, requery: undefined })),
        { type: "user", id: nextId("msg"), text: question },
      ],
    }));
    try {
      const data = await askAgent({
        client_id: cid,
        question,
        thread_id: threadId,
        scenario: sc,
      });
      updateThread(cid, (t) => ({
        ...t,
        items: [
          ...t.items,
          {
            type: "agent",
            id: nextId("msg"),
            turn: data.resultado,
            fresh: true,
          },
        ],
      }));
      setClients((prev) =>
        prev.map((c) => (c.client_id === cid ? data.cliente : c)),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Vacia el chat actual; un thread_id nuevo = memoria de corto plazo nueva
  function resetThread() {
    if (live === false) {
      if (scriptId) setPlayed((prev) => ({ ...prev, [scriptId]: 0 }));
      return;
    }
    if (clientId)
      setThreads((prev) => ({ ...prev, [clientId]: { id: null, items: [] } }));
  }

  function goHome() {
    setClientId(null);
    setScriptId(null);
    setContextOpen(false);
    setError(null);
    setPage("chat");
  }

  function openClient(id) {
    setClientId(id);
    setPage("chat");
  }

  // Desde Recomendaciones: abre el chat del cliente y pregunta por el activo
  // Usa el mismo escenario que se estaba viendo, para que la respuesta del
  // agente coincida con la recomendacion mostrada
  function askAbout(cid, ticker, sc) {
    setScenario(sc);
    openClient(cid);
    setContextOpen(false);
    send(`¿Qué hago con ${ticker}?`, cid, sc);
  }

  function openScript(id) {
    setScriptId(id);
    setPage("chat");
  }

  function onClientCreated(info) {
    setClients((prev) =>
      [...prev, info].sort((a, b) => a.client_id.localeCompare(b.client_id)),
    );
    setShowNewClient(false);
    openClient(info.client_id);
  }

  async function removeClient() {
    if (
      !window.confirm(
        `¿Eliminar a ${client.client_name} y su memoria? Esta acción no se puede deshacer.`,
      )
    )
      return;
    try {
      await deleteClient(clientId);
      setClients((prev) => prev.filter((c) => c.client_id !== clientId));
      setThreads((prev) => ({ ...prev, [clientId]: undefined }));
      goHome();
    } catch (e) {
      setError(e.message);
    }
  }

  // Como en un asistente: reinicia el chat y vuelve a elegir cliente
  function newConversation() {
    resetThread();
    goHome();
  }

  async function clearMemory() {
    const info = await resetMemory(clientId);
    setClients((prev) =>
      prev.map((c) => (c.client_id === clientId ? info : c)),
    );
    resetThread();
  }

  const title = live === false ? script?.titulo : client?.client_name;
  const infoPage = INFO_PAGES.find((p) => p.id === page);
  // Paneles de mercado: "market:<escenario>"
  const marketScenario = page.startsWith("market:") ? page.slice(7) : null;
  const onRecs = page === "recomendaciones";
  const onObs = page === "observabilidad";
  // Cualquier pagina que no es el chat oculta el composer y el panel de contexto
  const onAbout =
    Boolean(infoPage) || Boolean(marketScenario) || onRecs || onObs;

  return (
    <div
      className={`app-shell ${contextOpen && client && !onAbout ? "with-panel" : ""}`}
    >
      <nav className="sidebar" aria-label="Navegación del agente">
        <button className="brand" onClick={goHome}>
          <LogoMark size={26} />
          <span>
            <strong>Insight Trader</strong>
            <small>Agente de inversiones</small>
          </span>
        </button>

        <div className="nav-section">
          <div className="nav-label">Insight Trader</div>
          {INFO_PAGES.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
          <button
            className={`nav-item ${onRecs ? "active" : ""}`}
            onClick={() => setPage("recomendaciones")}
            disabled={live === null}
          >
            <IconClipboard size={16} />
            Recomendaciones
          </button>
          <button
            className={`nav-item ${onObs ? "active" : ""}`}
            onClick={() => setPage("observabilidad")}
          >
            <IconPulse size={16} />
            Observabilidad
          </button>
        </div>

        <button
          className="new-chat"
          onClick={newConversation}
          disabled={loading}
        >
          <IconPlus size={15} /> Nueva conversación
        </button>

        <div className="nav-section">
          <div className="nav-label">
            {live === false ? "Escenarios de demostración" : "Clientes"}
            {live && (
              <button
                className="nav-add"
                onClick={() => setShowNewClient(true)}
                disabled={loading}
                title="Agregar cliente"
                aria-label="Agregar cliente"
              >
                <IconPlus size={14} />
              </button>
            )}
          </div>
          {live === false
            ? demo.guiones.map((g) => (
                <button
                  key={g.id}
                  className={`nav-item ${g.id === scriptId && !onAbout ? "active" : ""}`}
                  onClick={() => openScript(g.id)}
                >
                  {g.titulo}
                </button>
              ))
            : clients.map((c) => (
                <button
                  key={c.client_id}
                  className={`nav-item ${c.client_id === clientId && !onAbout ? "active" : ""}`}
                  onClick={() => openClient(c.client_id)}
                  disabled={loading || live === null}
                >
                  <span className="initials sm">{initials(c.client_name)}</span>
                  {c.client_name}
                </button>
              ))}
        </div>

        {live !== null && (
          <div className="nav-section">
            <div className="nav-label">Simulación de mercado</div>
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                className={`nav-item scenario-item sc-${s.id} ${page === `market:${s.id}` ? "active" : ""}`}
                onClick={() => setPage(`market:${s.id}`)}
                title={s.hint}
              >
                <span className="sc-dot" />
                <span className="scenario-name">{s.label}</span>
              </button>
            ))}
          </div>
        )}

        <div className="sidebar-footer">
          <div
            className={`status ${live ? "on" : live === false ? "rec" : ""}`}
          >
            <span className="status-dot" />
            {live === null
              ? "Conectando con el agente…"
              : live
                ? "Conectado al agente (API local)"
                : "Modo demostración (grabado)"}
          </div>
        </div>
      </nav>

      <main className="workspace">
        <header className="workspace-head">
          <div className="head-title">
            <span className="head-name">
              {onObs
                ? "Observabilidad"
                : onRecs
                ? "Recomendaciones"
                : marketScenario
                  ? `Mercado · ${scenarioLabel(marketScenario)}`
                  : onAbout
                    ? infoPage.label
                    : started
                      ? title
                      : "Inicio"}
            </span>
            {started && live && !onAbout && (
              <span className={`scenario-chip sc-${scenario}`}>
                {scenarioLabel(scenario)}
              </span>
            )}
          </div>
          {started && client && !onAbout && (
            <button
              className={`btn-secondary ${contextOpen ? "on" : ""}`}
              onClick={() => setContextOpen((o) => !o)}
              aria-pressed={contextOpen}
            >
              <IconPanel size={15} /> Contexto del cliente
            </button>
          )}
        </header>

        <div className="workspace-scroll" ref={scrollRef}>
          {onObs ? (
            <ObservabilityPage live={Boolean(live)} />
          ) : onRecs ? (
            <RecommendationsPage
              live={Boolean(live)}
              activeScenario={scenario}
              onAsk={askAbout}
            />
          ) : marketScenario ? (
            <MarketPage
              scenarioId={marketScenario}
              live={Boolean(live)}
              activeScenario={scenario}
              onActivate={changeScenario}
            />
          ) : onAbout ? (
            <InfoPage page={page} />
          ) : !started ? (
            <Welcome
              live={live}
              clients={clients}
              scripts={demo.guiones}
              onPickClient={openClient}
              onPickScript={openScript}
              onNewClient={() => setShowNewClient(true)}
            />
          ) : (
            <Conversation
              items={items}
              loading={loading}
              clientName={client?.client_name ?? ""}
              onSuggestion={send}
              onRequery={send}
              showSuggestions={Boolean(live)}
            />
          )}
        </div>

        {started && !onAbout && (
          <div className="composer">
            {error && <div className="convo-error">{error}</div>}
            {live ? (
              <Composer
                onSend={send}
                disabled={loading}
                placeholder={`Escribe un mensaje sobre el portafolio de ${client?.client_name ?? "este cliente"}…`}
              />
            ) : (
              <div className="recorded-bar">
                <span>
                  {playedCount < script.turnos.length
                    ? `Siguiente mensaje: “${script.turnos[playedCount].pregunta}”`
                    : "Escenario completo. Elige otro en el panel izquierdo."}
                </span>
                <button
                  className="btn-primary"
                  onClick={() =>
                    setPlayed((prev) => ({
                      ...prev,
                      [scriptId]: playedCount + 1,
                    }))
                  }
                  disabled={playedCount >= script.turnos.length}
                >
                  Enviar ({Math.min(playedCount + 1, script.turnos.length)}/
                  {script.turnos.length})
                </button>
              </div>
            )}
            <div className="composer-hint">
              Datos simulados con fines académicos. Las recomendaciones no
              constituyen asesoría financiera.
            </div>
          </div>
        )}
      </main>

      {contextOpen && client && !onAbout && (
        <ContextPanel
          client={client}
          live={live}
          onClose={() => setContextOpen(false)}
          onClearMemory={clearMemory}
          onDelete={removeClient}
          busy={loading}
        />
      )}

      {showNewClient && (
        <NewClientModal
          onClose={() => setShowNewClient(false)}
          onCreated={onClientCreated}
        />
      )}
    </div>
  );
}
