// Iconos SVG en linea (trazo 1.75, heredan el color del texto).

function Svg({ size = 16, children, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function LogoMark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path
        d="M8 21.5l5-5.5 4 3.5 7-8.5"
        fill="none"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="24" cy="11" r="2.2" fill="var(--brand-accent)" />
    </svg>
  );
}

export const IconPlus = (p) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);

export const IconSearch = (p) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.2-4.2" />
  </Svg>
);

export const IconReason = (p) => (
  <Svg {...p}>
    <path d="M4 19V5M4 19h16" />
    <path d="M8 15l3.5-4 3 2.5L19 8" />
  </Svg>
);

export const IconWrite = (p) => (
  <Svg {...p}>
    <path d="M14.5 4.5l5 5L9 20H4v-5z" />
  </Svg>
);

export const IconPanel = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
    <path d="M15 4.5v15" />
  </Svg>
);

export const IconClose = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Svg>
);

export const IconSend = (p) => (
  <Svg {...p}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Svg>
);

export const IconReplan = (p) => (
  <Svg {...p}>
    <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8" />
    <path d="M4 4v4h4" />
    <path d="M4 13a8 8 0 0 0 14.3 4.9L20 16" />
    <path d="M20 20v-4h-4" />
  </Svg>
);

export const IconCheck = (p) => (
  <Svg {...p} strokeWidth="2.5">
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Svg>
);

export const IconChevron = ({ open, ...p }) => (
  <Svg
    {...p}
    style={{
      transform: open ? "rotate(90deg)" : "none",
      transition: "transform .15s",
    }}
  >
    <path d="M9 6l6 6-6 6" />
  </Svg>
);

export const IconDoc = (p) => (
  <Svg {...p}>
    <path d="M7 3.5h7l4 4V20.5H7z" />
    <path d="M14 3.5v4h4M9.5 12.5h6M9.5 16h6" />
  </Svg>
);

export const IconMemory = (p) => (
  <Svg {...p}>
    <ellipse cx="12" cy="6" rx="7" ry="2.5" />
    <path d="M5 6v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6" />
    <path d="M5 12v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6" />
  </Svg>
);

const TOOL_ICONS = {
  consulta: IconSearch,
  razonamiento: IconReason,
  escritura: IconWrite,
};

export function ToolIcon({ tipo, ...p }) {
  const Icon = TOOL_ICONS[tipo];
  return Icon ? <Icon {...p} /> : null;
}

export const IconInfo = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5M12 8h.01" />
  </Svg>
);

export const IconTrash = (p) => (
  <Svg {...p}>
    <path d="M4.5 7h15M10 11v6M14 11v6" />
    <path d="M6.5 7l1 12.5h9l1-12.5M9.5 7V4.5h5V7" />
  </Svg>
);

export const IconTarget = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="0.8" fill="currentColor" />
  </Svg>
);

export const IconFlow = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="4" width="6" height="5" rx="1.2" />
    <rect x="14.5" y="15" width="6" height="5" rx="1.2" />
    <path d="M6.5 9v4.5a2 2 0 0 0 2 2h6" />
  </Svg>
);

export const IconGauge = (p) => (
  <Svg {...p}>
    <path d="M4.5 17a8 8 0 1 1 15 0" />
    <path d="M12 13l3.5-4" />
    <circle cx="12" cy="13.5" r="1.2" />
  </Svg>
);

export const IconSpark = (p) => (
  <Svg {...p}>
    <path d="M12 3.5l2.2 5.3 5.3 2.2-5.3 2.2L12 18.5l-2.2-5.3L4.5 11l5.3-2.2z" />
    <path d="M19 17v4M17 19h4" />
  </Svg>
);

export const IconClipboard = (p) => (
  <Svg {...p}>
    <rect x="5" y="4.5" width="14" height="16" rx="2" />
    <path d="M9 4.5V3.5h6v1M8.5 10.5l2 2 4-4M8.5 16.5h7" />
  </Svg>
);

export const IconPulse = (p) => (
  <Svg {...p}>
    <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />
  </Svg>
);
