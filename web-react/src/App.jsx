import { useState } from "react";
import clients from "./data/recommendations.json";
import Sidebar from "./components/Sidebar";
import ClientTabs from "./components/ClientTabs";
import SectionNav from "./components/SectionNav";
import Section from "./components/Section";
import SignalPills from "./components/SignalPills";
import SourceColumn from "./components/SourceColumn";
import RecommendationCard from "./components/RecommendationCard";
import HowItWorks from "./components/HowItWorks";
import ClientDirectory from "./components/ClientDirectory";
import "./App.css";

const CLIENT_NAV_LINKS = [
  { id: "sec-consulta", num: "01", label: "Consulta" },
  { id: "sec-analisis", num: "02", label: "Análisis" },
  { id: "sec-evidencia", num: "03", label: "Evidencia" },
  { id: "sec-recomendacion", num: "04", label: "Recomendación" },
];

const HOME_NAV_LINKS = [
  { id: "sec-como-funciona", label: "Cómo funciona" },
  { id: "sec-clientes", label: "Clientes" },
];

function HomeView({ onOpenClient }) {
  return (
    <>
      <header className="app">
        <div className="sub">
          Copiloto de trading explicable — recomendaciones con fuentes citadas
        </div>
        <p className="demo-note">
          <strong>Demo:</strong> respuestas reales generadas por el pipeline
          de agentes (RAG dual + MockLLM) para 3 clientes simulados con
          perfiles de riesgo distintos, exportadas a{" "}
          <code className="mono">recommendations.json</code>.
        </p>
      </header>

      <HowItWorks />
      <ClientDirectory clients={clients} onOpenClient={onOpenClient} />
    </>
  );
}

function ClientView({ client, onBack, onSelectClient }) {
  const [selectedTicker, setSelectedTicker] = useState(client.holdings[0].ticker);
  const entry = client.holdings.find((h) => h.ticker === selectedTicker) ?? client.holdings[0];

  return (
    <>
      <button className="back-link" onClick={onBack}>
        ← Todos los clientes
      </button>

      <ClientTabs clients={clients} activeId={client.client_id} onSelect={onSelectClient} />

      <div className="client-summary">
        <span className="k">Perfil</span>
        <span className="v">{client.risk_category}</span>
        <span className="k">Tolerancia drawdown</span>
        <span className="v">{client.risk_tolerance.toFixed(1)}%</span>
        <span className="k">Horizonte</span>
        <span className="v">{client.investment_horizon_years} años</span>
        <span className="note">{client.notes}</span>
      </div>

      <div className="layout">
        <Sidebar holdings={client.holdings} selectedTicker={selectedTicker} onSelect={setSelectedTicker} />

        <div className="panel">
          <Section id="sec-consulta" number="01" title="Consulta">
            <span className="q">“{entry.question}”</span>
            <span className="q-ticker mono">activo objetivo: {entry.ticker}</span>
          </Section>

          <Section id="sec-analisis" number="02" title="Análisis riesgo-mercado">
            <SignalPills signal={entry.signal} />
          </Section>

          <Section id="sec-evidencia" number="03" title="Evidencia recuperada (RAG)">
            <div className="sources">
              <SourceColumn title="Fuentes internas" chunks={entry.internal} variant="internal" />
              <SourceColumn title="Fuentes externas" chunks={entry.external} variant="external" />
            </div>
          </Section>

          <Section id="sec-recomendacion" number="04" title="Recomendación generada">
            <RecommendationCard recommendation={entry.recommendation} />
          </Section>
        </div>
      </div>

      <footer className="app">
        <span>
          Cliente: {client.client_name} · Perfil {client.risk_category} · Horizonte{" "}
          {client.investment_horizon_years} años
        </span>
        <span>Insight Trader · Evaluación ISY0101</span>
      </footer>
    </>
  );
}

export default function App() {
  const [activeClientId, setActiveClientId] = useState(null);
  const client = clients.find((c) => c.client_id === activeClientId) ?? null;

  function goHome() {
    setActiveClientId(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const navLinks = client
    ? [{ id: "back", label: "← Clientes", onClick: goHome }, ...CLIENT_NAV_LINKS]
    : HOME_NAV_LINKS;

  return (
    <div className="page">
      <div className="topbar">
        <div className="topbar-inner">
          <button className="brand-mark serif" onClick={goHome}>
            Insight Trader
          </button>
          <SectionNav links={navLinks} />
        </div>
      </div>

      <div className="wrap">
        {client ? (
          <ClientView
            key={client.client_id}
            client={client}
            onBack={goHome}
            onSelectClient={setActiveClientId}
          />
        ) : (
          <HomeView onOpenClient={setActiveClientId} />
        )}
      </div>
    </div>
  );
}
