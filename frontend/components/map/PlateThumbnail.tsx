// MOCK_MODE-only demo authenticity fixture. Per DECISIONS.md's Kaggle
// license gate (DataCluster Labs' Indian Number Plates Dataset ships as a
// commercial-license sample on Kaggle, not a clear permissive grant), this
// renders a procedurally-drawn plate graphic from the already-known plate
// string instead of any real photo or third-party asset — format realism,
// not real vehicle imagery. Never rendered against a real backend response.
export function PlateThumbnail({ plateText }: { plateText: string }) {
  return (
    <svg
      viewBox="0 0 200 60"
      role="img"
      aria-label={`Indian number plate ${plateText}`}
      className="h-9 w-auto rounded-[3px] border border-black/40 shadow-sm"
    >
      <rect width="200" height="60" fill="#f5f5f0" />
      <rect x="1" y="1" width="198" height="58" fill="none" stroke="#1a1a1a" strokeWidth="2" />
      <rect x="4" y="4" width="14" height="52" fill="#0a3d91" />
      <text x="11" y="24" textAnchor="middle" fontSize="7" fill="#fff" fontFamily="sans-serif">
        IND
      </text>
      <text
        x="108"
        y="40"
        textAnchor="middle"
        fontSize="26"
        fontWeight="700"
        fontFamily="'Arial Narrow', sans-serif"
        letterSpacing="2"
        fill="#111"
      >
        {plateText}
      </text>
    </svg>
  );
}
