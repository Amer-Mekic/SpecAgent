import { useEffect, useState, useCallback } from 'react';
import PipelineBar from '../components/PipelineBar';
import RequirementCard from '../components/RequirementCard';
import CorrectionChat from '../components/CorrectionChat';
import ExportBar from '../components/ExportBar';
import { requirements as reqApi } from '../api/client';

export default function ReviewPage({
  guestMode,
  sessionId,
  requirements,
  loadRequirements,
  approveRequirement,
  rejectRequirement,
  editRequirement,
}) {
  const [filter, setFilter] = useState('all');
  const [chatOpen, setChatOpen] = useState(true);
  const [pinnedReq, setPinnedReq] = useState(null);
  const [polling, setPolling] = useState(() => !guestMode);

  // Poll for requirements while pipeline is running
  useEffect(() => {
    if (guestMode || !sessionId || !polling) return;
    const interval = setInterval(async () => {
      try {
        const data = await reqApi.list(sessionId);
        loadRequirements(sessionId);
        const allDone = data.every(r => r.pipeline_status === 'traced');
        if (allDone && data.length > 0) setPolling(false);
      // eslint-disable-next-line no-empty
      } catch {}
    }, 4000);
    return () => clearInterval(interval);
  }, [guestMode, sessionId, polling, loadRequirements]);

  useEffect(() => {
    if (sessionId) loadRequirements(sessionId);
  }, [loadRequirements, sessionId]);

 const filtered = (requirements ?? []).filter(r => {
    if (filter === 'all') return true;
    if (filter === 'functional') return r.classification?.type === 'functional';
    if (filter === 'non-functional') return r.classification?.type === 'non-functional';
    if (filter === 'flagged') return r.validation_report?.result === 'flagged';
    if (filter === 'approved') return r.finalization_status === 'final';
    if (filter === 'rejected') return r.finalization_status === 'rejected';
    return true;
  });

  const handlePin = useCallback((reqId) => {
    const req = requirements.find(r => r.id === reqId);
    setPinnedReq(prev => prev?.id === reqId ? null : req);
    setChatOpen(true);
  }, [requirements]);

  const handleApplySuggestion = useCallback(async (reqId, statement) => {
    if (reqId) await editRequirement(reqId, statement);
  }, [editRequirement]);

  
  const approvedCount = (requirements ?? []).filter(r => r.finalization_status === 'final').length;

  return (
    <div className="review-page">
      <PipelineBar currentStage={polling ? 'extract' : null} />

      <div className="review-toolbar">
        <div className="review-title-row">
          <h2>Extracted requirements</h2>
          <span className="req-count">{requirements.length} found</span>
        </div>

        <div className="filter-row">
          {['all', 'functional', 'non-functional', 'flagged', 'approved', 'rejected'].map(f => (
            <button
              key={f}
              className={`filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          <span className="approved-count">{approvedCount} approved</span>
        </div>
      </div>

      <div className="review-body">
        <div className="req-grid">
          {filtered.length === 0 && (
            <div className="empty-state">
              {polling ? (
                <>
                  <div className="spinner" />
                  <p>Pipeline is running… requirements will appear here shortly.</p>
                </>
              ) : (
                <p>No requirements match this filter.</p>
              )}
            </div>
          )}
          {filtered.map((req) => (
            <RequirementCard
              key={req.id}
              req={req}
              index={requirements.indexOf(req)}
              onApprove={approveRequirement}
              onReject={rejectRequirement}
              onEdit={editRequirement}
              onPin={handlePin}
              pinned={pinnedReq?.id === req.id}
            />
          ))}
        </div>

        {chatOpen && (
          <CorrectionChat
            guestMode={guestMode}
            sessionId={sessionId}
            pinnedRequirement={pinnedReq}
            onApplySuggestion={handleApplySuggestion}
          />
        )}

        <button
          className="chat-toggle"
          onClick={() => setChatOpen(o => !o)}
          title={chatOpen ? 'Hide chat' : 'Open correction chat'}
        >
          {chatOpen ? '✕' : '💬'}
        </button>
      </div>

      <ExportBar guestMode={guestMode} sessionId={sessionId} />
    </div>
  );
}