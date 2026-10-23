import { useEffect, useState } from "react";
import { createClient, fetchCatalog } from "./api";
import { IconClose, IconPlus } from "./icons";

const PROFILES = [
  { id: "conservador", label: "Conservador", hint: "Prioriza estabilidad" },
  { id: "moderado", label: "Moderado", hint: "Equilibrio riesgo/retorno" },
  { id: "agresivo", label: "Agresivo", hint: "Tolera alta volatilidad" },
];
const FALLBACK_TOLERANCE = { conservador: 6, moderado: 12, agresivo: 30 };

const emptyRow = (ticker = "") => ({
  ticker,
  quantity: "",
  avg_buy_price: "",
  current_weight_pct: "",
});

export default function NewClientModal({ onClose, onCreated }) {
  const [catalog, setCatalog] = useState(null);
  const [form, setForm] = useState({
    client_name: "",
    risk_category: "moderado",
    max_drawdown_tolerance_pct: FALLBACK_TOLERANCE.moderado,
    investment_horizon_years: 5,
    notes: "",
  });
  const [rows, setRows] = useState([emptyRow()]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCatalog()
      .then((data) => {
        if (cancelled) return;
        setCatalog(data);
        setRows((prev) =>
          prev.map((r) =>
            r.ticker ? r : { ...r, ticker: data.activos[0].ticker },
          ),
        );
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const assets = catalog?.activos ?? [];
  const suggested = catalog?.tolerancia_sugerida ?? FALLBACK_TOLERANCE;
  const totalWeight = rows.reduce(
    (sum, r) => sum + (Number(r.current_weight_pct) || 0),
    0,
  );
  const weightOk = Math.abs(totalWeight - 100) <= 0.5;
  const usedTickers = new Set(rows.map((r) => r.ticker));

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  function pickProfile(id) {
    setForm((f) => ({
      ...f,
      risk_category: id,
      max_drawdown_tolerance_pct: suggested[id],
    }));
  }

  function updateRow(i, field, value) {
    setRows((prev) =>
      prev.map((r, j) => (j === i ? { ...r, [field]: value } : r)),
    );
  }

  function addRow() {
    const free = assets.find((a) => !usedTickers.has(a.ticker));
    if (free) setRows((prev) => [...prev, emptyRow(free.ticker)]);
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const info = await createClient({
        ...form,
        holdings: rows.map((r) => ({ ...r, ticker: r.ticker })),
      });
      onCreated(info);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <form
        className="modal"
        onSubmit={submit}
        aria-labelledby="new-client-title"
      >
        <div className="modal-head">
          <div>
            <h2 id="new-client-title">Nuevo cliente</h2>
            <p>El agente usará este perfil y portafolio en sus herramientas.</p>
          </div>
          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label="Cerrar"
          >
            <IconClose size={16} />
          </button>
        </div>

        <div className="modal-body">
          <label className="field">
            <span>Nombre completo</span>
            <input
              value={form.client_name}
              onChange={set("client_name")}
              placeholder="Ej. Martina Soto"
              autoFocus
              required
            />
          </label>

          <div className="field">
            <span>Perfil de riesgo</span>
            <div className="profile-options" role="radiogroup">
              {PROFILES.map((p) => (
                <button
                  type="button"
                  key={p.id}
                  role="radio"
                  aria-checked={form.risk_category === p.id}
                  className={`profile-opt ${form.risk_category === p.id ? "on" : ""}`}
                  onClick={() => pickProfile(p.id)}
                >
                  <strong>{p.label}</strong>
                  <small>{p.hint}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Tolerancia a drawdown (%)</span>
              <input
                type="number"
                min="1"
                max="100"
                step="0.5"
                value={form.max_drawdown_tolerance_pct}
                onChange={set("max_drawdown_tolerance_pct")}
                required
              />
            </label>
            <label className="field">
              <span>Horizonte de inversión (años)</span>
              <input
                type="number"
                min="1"
                max="50"
                value={form.investment_horizon_years}
                onChange={set("investment_horizon_years")}
                required
              />
            </label>
          </div>

          <label className="field">
            <span>
              Notas del asesor <em>(opcional)</em>
            </span>
            <textarea
              rows="2"
              value={form.notes}
              onChange={set("notes")}
              placeholder="Ej. Próximo a jubilarse, necesita liquidez en 2 años."
            />
          </label>

          <div className="field">
            <div className="holdings-head">
              <span>Portafolio</span>
              <span className={`weight-total ${weightOk ? "ok" : ""}`}>
                Total: {Math.round(totalWeight * 10) / 10}% / 100%
              </span>
            </div>
            <div className="holdings-grid">
              <span className="grid-label">Activo</span>
              <span className="grid-label">Cantidad</span>
              <span className="grid-label">Precio promedio</span>
              <span className="grid-label">Peso %</span>
              <span />
              {rows.map((r, i) => (
                <div className="holdings-row" key={i}>
                  <select
                    value={r.ticker}
                    onChange={(e) => updateRow(i, "ticker", e.target.value)}
                    aria-label={`Activo de la posición ${i + 1}`}
                  >
                    {assets.map((a) => (
                      <option
                        key={a.ticker}
                        value={a.ticker}
                        disabled={
                          a.ticker !== r.ticker && usedTickers.has(a.ticker)
                        }
                      >
                        {a.ticker} · {a.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={r.quantity}
                    onChange={(e) => updateRow(i, "quantity", e.target.value)}
                    aria-label="Cantidad"
                    required
                  />
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={r.avg_buy_price}
                    onChange={(e) =>
                      updateRow(i, "avg_buy_price", e.target.value)
                    }
                    aria-label="Precio promedio"
                    required
                  />
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="any"
                    value={r.current_weight_pct}
                    onChange={(e) =>
                      updateRow(i, "current_weight_pct", e.target.value)
                    }
                    aria-label="Peso en el portafolio"
                    required
                  />
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() =>
                      setRows((prev) => prev.filter((_, j) => j !== i))
                    }
                    disabled={rows.length === 1}
                    aria-label="Quitar posición"
                  >
                    <IconClose size={14} />
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="link-btn add-row"
              onClick={addRow}
              disabled={!catalog || rows.length >= assets.length}
            >
              <IconPlus size={13} /> Agregar posición
            </button>
            <p className="field-hint">
              Solo se listan activos con datos en el feed de mercado, para que
              el agente pueda evaluar su riesgo.
            </p>
          </div>

          {error && <div className="convo-error">{error}</div>}
        </div>

        <div className="modal-foot">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={saving || !catalog || !weightOk}
          >
            {saving ? "Creando…" : "Crear cliente"}
          </button>
        </div>
      </form>
    </div>
  );
}
