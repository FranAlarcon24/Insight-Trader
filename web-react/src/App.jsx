import { useState } from "react";
import data from "./data/recommendations.json";
import Sidebar from "./components/Sidebar";
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
        <div>
          <div className="brand">
            <span className="mark">IT</span>
            <h1>Insight Trader</h1>
          </div>
          <div className="sub">
            Copiloto de trading explicable — recomendaciones con fuentes citadas
          </div>
        </div>
      </header>

      <div className="demo-banner">
        <span>
          <strong>Demo: </strong>
          estas son respuestas reales generadas por el pipeline de agentes
          (RAG dual + MockLLM) del proyecto Python, exportadas a{" "}
          <code className="mono">recommendations.json</code>.
        </span>
      </div>

      <div className="layout">
        <Sidebar data={data} selectedTicker={selectedTicker} onSelect={setSelectedTicker} />

        {entry && (
          <div className="panel">
            <div className="question-card">
              <span className="eyebrow">Pregunta del cliente · {entry.ticker}</span>
              <span className="q">“{entry.question}”</span>
            </div>

            <SignalPills signal={entry.signal} />

            <div className="sources">
              <SourceColumn title="Fuentes internas" chunks={entry.internal} variant="internal" />
              <SourceColumn title="Fuentes externas" chunks={entry.external} variant="external" />
            </div>

            <RecommendationCard recommendation={entry.recommendation} />
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
