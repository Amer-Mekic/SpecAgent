const STAGES = ['Extract', 'Validate', 'Classify', 'Trace'];

export default function PipelineBar({ currentStage }) {
  const currentIndex = STAGES.findIndex(s => s.toLowerCase() === currentStage?.toLowerCase());

  return (
    <div className="pipeline-bar">
      {STAGES.map((stage, i) => {
        const done = currentIndex === -1 ? true : i < currentIndex;
        const active = i === currentIndex;
        return (
          <div key={stage} className="pipeline-step">
            <div className={`step-circle ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
              {done ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              ) : (
                active ? <div className="step-pulse" /> : null
              )}
            </div>
            <span className={`step-label ${done ? 'done' : ''} ${active ? 'active' : ''}`}>{stage}</span>
            {i < STAGES.length - 1 && (
              <div className={`step-line ${i < currentIndex ? 'done' : ''}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}