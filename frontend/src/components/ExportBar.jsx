import { useState } from 'react';
import { exportApi } from '../api/client';

export default function ExportBar({ guestMode, sessionId }) {
  const [exporting, setExporting] = useState(null);

  const triggerExport = async (type, format) => {
    if (guestMode) {
      alert('Sign in to export SRS or RTM from the server. Guest mode is UI preview only.');
      return;
    }
    const key = `${type}-${format}`;
    setExporting(key);
    try {
      let blob;
      let filename;

      if (type === 'srs') {
        blob = await exportApi.srs(sessionId, format);
        filename = `SpecAgent-SRS.${format}`;

      } else if (type === 'rtm' && format === 'pdf') {
        blob = await exportApi.rtmPdf(sessionId);
        filename = 'SpecAgent-RTM.pdf';

      } else if (type === 'rtm' && format === 'csv') {
        // Fetch RTM data and build CSV client-side
        const data = await exportApi.rtm(sessionId);
        const rows = data.rows || [];
        const header = ['REQ-ID', 'Statement', 'Type', 'Sub-Category', 'Validation', 'Finalization', 'Sources'];
        const csvRows = rows.map(r => [
          r.req_id,
          `"${(r.statement || '').replace(/"/g, '""')}"`,
          r.type || '',
          r.sub_category || '',
          r.validation_result || '',
          r.finalization_status || '',
          `"${(r.sources || []).map(s => s.source_identifier).filter(Boolean).join(', ')}"`,
        ]);
        const csv = [header, ...csvRows].map(row => row.join(',')).join('\n');
        blob = new Blob([csv], { type: 'text/csv' });
        filename = 'SpecAgent-RTM.csv';
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

    } catch (e) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setExporting(null);
    }
  };

  const buttons = [
    { label: 'SRS document (.docx)', type: 'srs', format: 'docx' },
    { label: 'SRS document (.pdf)', type: 'srs', format: 'pdf' },
    { label: 'RTM (.pdf)', type: 'rtm', format: 'pdf' },
    { label: 'RTM (.csv)', type: 'rtm', format: 'csv' },
  ];

  return (
    <div className="export-bar">
      <span className="export-label">EXPORT</span>
      {buttons.map(({ label, type, format }) => {
        const key = `${type}-${format}`;
        return (
          <button
            key={key}
            className="btn-export"
            onClick={() => triggerExport(type, format)}
            disabled={!!exporting}
          >
            {exporting === key ? 'Exporting…' : label}
          </button>
        );
      })}
    </div>
  );
}