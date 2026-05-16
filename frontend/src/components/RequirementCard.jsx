import { useState } from 'react';

const STATUS_COLORS = {
  final: 'status-approved',
  rejected: 'status-rejected',
  draft: '',
  reviewed: 'status-reviewed',
};

const TYPE_COLORS = {
  functional: 'tag-fr',
  'non-functional': 'tag-nfr',
};

export default function RequirementCard({ req, index, onApprove, onReject, onEdit, onPin, pinned }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(req.statement);
  const [saving, setSaving] = useState(false);

  const typeLabel = req.classification?.type === 'non-functional' ? 'NFR' : 'FR';
  const typeClass = req.classification?.type === 'non-functional' ? 'tag-nfr' : 'tag-fr';
  const statusClass = STATUS_COLORS[req.finalization_status] || '';
  const isApproved = req.finalization_status === 'final';
  const isRejected = req.finalization_status === 'rejected';

  const saveEdit = async () => {
    if (draft.trim() === req.statement) { setEditing(false); return; }
    setSaving(true);
    try {
      await onEdit(req.id, draft.trim());
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  return (
    <div className={`req-card ${statusClass} ${isRejected ? 'card-rejected' : ''} ${pinned ? 'card-pinned' : ''}`}>
      <div className="card-header">
        <span className={`req-tag ${typeClass}`}>{typeLabel}-{String(index + 1).padStart(2, '0')}</span>
        <div className="card-header-right">
          {isApproved && <span className="approved-badge">● Approved</span>}
          {isRejected && <span className="rejected-badge">● Rejected</span>}
          {req.validation_report?.result === 'flagged' && !isApproved && !isRejected && (
            <span className="flagged-badge">⚠ Flagged</span>
          )}
          <button
            className={`pin-btn ${pinned ? 'pinned' : ''}`}
            onClick={() => onPin(req.id)}
            title={pinned ? 'Unpin from chat' : 'Pin to chat'}
          >
            📌
          </button>
        </div>
      </div>

      <div className="card-body">
        {editing ? (
          <textarea
            className="edit-textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            autoFocus
          />
        ) : (
          <p className={`req-statement ${isRejected ? 'text-muted' : ''}`}>{req.statement}</p>
        )}

        {req.validation_report?.issues?.length > 0 && !isApproved && (
          <div className="validation-issues">
            {req.validation_report.issues.slice(0, 1).map((issue, i) => (
               <span key={i} className="issue-tag" title={issue.suggestion}>
                 ⚠ {issue.issue_type}: {issue.description}
               </span>
            ))}
          </div>
        )}
        {req.traceability_links?.length > 0 && (
          <div className="traceability-links">
            <span className="trace-label">📎 Traced to:</span>
            {req.traceability_links.slice(0, 3).map((link, i) => (
            <span key={i} className="trace-tag" title={`Similarity: ${(link.similarity_score * 100).toFixed(0)}%`}>
              {link.source_identifier || `Section ${i + 1}`}
            </span>
          ))}
          </div>
  )}
      </div>

      <div className="card-actions">
        {editing ? (
          <>
            <button className="btn-approve" onClick={saveEdit} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button className="btn-reject" onClick={() => { setEditing(false); setDraft(req.statement); }}>
              Cancel
            </button>
          </>
        ) : isRejected ? (
          <button className="btn-restore" onClick={() => onApprove(req.id)}>Restore</button>
        ) : (
          <>
            {!isApproved && <button className="btn-approve" onClick={() => onApprove(req.id)}>Approve</button>}
            {!isApproved && <button className="btn-reject" onClick={() => onReject(req.id)}>Reject</button>}
            <button className="btn-edit" onClick={() => setEditing(true)}>Edit</button>
          </>
        )}
      </div>
    </div>
  );
}