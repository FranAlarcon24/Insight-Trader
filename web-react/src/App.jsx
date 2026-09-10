import { useState } from "react";
import data from "./data/recommendations.json";
import Sidebar from "./components/Sidebar";
import Section from "./components/Section";
import SignalPills from "./components/SignalPills";
import SourceColumn from "./components/SourceColumn";
import RecommendationCard from "./components/RecommendationCard";
import "./App.css";

export default function App() {
  const [selectedTicker, setSelectedTicker] = useState(data[0].ticker);
  const entry = data.find((d) => d.ticker === selectedTicker);

  return (
    <div className="wrap">
      <header className="app">
        <h1>Insight Trader</h1>
        <div className="sub">
          Copiloto de trading explicable — recomendaciones con fuentes citadas
        </div>
      </header>

      <p className="demo-note">
        <strong>Demo:</strong> estas son respuestas reales generadas por el
        pipeline de agentes (RAG dual + MockLLM) del proyecto Python,
        exportadas a <code className="mono">recommendations.json</code>.
      </p>

      <div className="layout">
        <Sidebar data={data} selectedTicker={selectedTicker} onSelect={setSelectedTicker} />

        {entry && (
          <div className="panel">
            <Section number="01" title="Consulta">
              <span className="q">“{entry.question}”</span>
              <span className="q-ticker mono">activo objetivo: {entry.ticker}</span>
            </Section>

            <Section number="02" title="Análisis riesgo-mercado">
              <SignalPills signal={entry.signal} />
            </Section>

            <Section number="03" title="Evidencia recuperada (RAG)">
              <div className="sources">
                <SourceColumn title="Fuentes internas" chunks={entry.internal} variant="internal" />
                <SourceColumn title="Fuentes externas" chunks={entry.external} variant="external" />
              </div>
            </Section>

            <Section number="04" title="Recomendación generada">
              <RecommendationCard recommendation={entry.recommendation} />
            </Section>
          </div>
        )}
      </div>

      <footer className="app">
        <span>Cliente: Constanza Fuentes · Perfil de riesgo moderado · Horizonte 5 años</span>
        <span>Insight Trader · Evaluación ISY0101</span>
      </footer>
    </div>
  );
}
