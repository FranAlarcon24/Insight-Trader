function highlightNumbers(text) {
  const parts = text.split(/(-?\d+(?:\.\d+)?%?)/g);
  return parts.map((part, i) =>
    /^-?\d/.test(part) ? (
      <span className="num" key={i}>
        {part}
      </span>
    ) : (
      part
    )
  );
}

export default function SourceColumn({ title, chunks, variant }) {
  return (
    <div className={"source-col " + variant}>
      <h3>{title}</h3>
      {chunks.map((chunk, i) => (
        <div className="chunk" key={i}>
          {highlightNumbers(chunk)}
        </div>
      ))}
    </div>
  );
}
