const P: Record<string, string> = {
  brief: "M3 4h10M3 8h10M3 12h6",
  atlas: "M2 4l4-2 4 2 4-2v10l-4 2-4-2-4 2zM6 2v10M10 4v10",
  graph: "M4 4m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M12 4m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M8 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M5.5 5.5l1.5 4.5M10.5 5.5l-1.5 4.5M6 4h4",
  lab: "M6 2v4L2.5 13a1 1 0 0 0 .9 1.5h9.2a1 1 0 0 0 .9-1.5L10 6V2M5 2h6M4.5 10h7",
  theater: "M2 3h12v8H2zM6 5.5v3l3-1.5zM5 14h6",
  cockpit: "M3 3h4v4H3zM9 4h4M9 6h3M3 9h4v4H3zM9 10h4M9 12h3",
  model: "M8 2l5 3v6l-5 3-5-3V5zM8 8l5-3M8 8v6M8 8L3 5",
  research: "M7 2a5 5 0 1 0 0 10A5 5 0 0 0 7 2zM11 11l3 3",
  search: "M7 2a5 5 0 1 0 0 10A5 5 0 0 0 7 2zM11 11l3 3",
  close: "M4 4l8 8M12 4l-8 8",
  play: "M5 3l8 5-8 5z",
  pause: "M5 3h2v10H5zM9 3h2v10H9z",
  step: "M4 3l6 5-6 5zM11 3h2v10h-2z",
  back: "M12 3L6 8l6 5zM3 3h2v10H3z",
  undo: "M5 4L2 7l3 3M2 7h8a4 4 0 0 1 0 8H8",
  sun: "M8 5a3 3 0 1 0 0 6a3 3 0 0 0 0-6M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5L13 13M3 13l1.5-1.5M11.5 4.5L13 3",
  download: "M8 2v8M5 7l3 3 3-3M3 13h10",
  flag: "M3 14V2M3 2h8l-2 3 2 3H3",
};

export function Icon({ name, size = 16 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.4}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={P[name] || P.brief} />
    </svg>
  );
}
