import { useState } from "react";
import clients from "./data/recommendations.json";
import Sidebar from "./components/Sidebar";
import ClientTabs from "./components/ClientTabs";
import SectionNav from "./components/SectionNav";
import Section from "./components/Section";
import SignalPills from "./components/SignalPills";
import SourceColumn from "./components/SourceColumn";
import RecommendationCard from "./components/RecommendationCard";
import "./App.css";

export default function App() {
  const [activeClientId, setActiveClientId] = useState(clients[0].client_id);
  const client = clients.find((c) => c.client_id === activeClientId);

  const [selectedTicker, setSelectedTicker] = useState(client.holdings[0].ticker);
  const entry = client.holdings.find((h) => h.ticker === selectedTicker) ?? client.holdings[0];

  function handleClientChange(clientId) {
    setActiveClientId(clientId);
    const next = clients.find((c) => c.client_id === clientId);
    setSelectedTicker(next.holdings[0].ticker);
  }

  return (
    <div className="page">
      <div className="topbar">
        <div className="topbar-inner">
          <span className="brand-mark serif">Insight Trader</span>
          <SectionNav />
        </div>
      </div>

      <div className="wrap">
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

        <ClientTabs clients={clients} activeId={activeClientId} onSelect={handleClientChange} />

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
      </div>
    </div>
  );
}
