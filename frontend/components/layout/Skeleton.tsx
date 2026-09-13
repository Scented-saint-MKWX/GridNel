// Shimmer skeleton for "about to have real content" states — distinct from
// RadarSweep, which is for genuinely-no-data states. See CLAUDE.md "Design
// bar" empty-state requirement.
export function Skeleton({
  className = "",
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`rounded-lg bg-gradient-to-r from-white/[0.03] via-white/[0.07] to-white/[0.03] bg-[length:200%_100%] ${className}`}
      style={{ animation: "shimmer 1.8s ease-in-out infinite", ...style }}
    />
  );
}
