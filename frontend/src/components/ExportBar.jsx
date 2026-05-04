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
      const blob = await exportApi.srs(sessionId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SpecAgent-${type.toUpperCase()}.${format}`;
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