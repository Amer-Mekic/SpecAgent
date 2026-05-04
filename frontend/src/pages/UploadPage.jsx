import { useState, useRef, useCallback } from 'react';
import { upload } from '../api/client';
import { DEMO_SESSION_ID } from '../constants/demo';

export default function UploadPage({ guestMode, onSessionStart }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef();

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const ACCEPTED = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
  const MAX_MB = 10;

  const goPreview = useCallback(() => {
    onSessionStart(DEMO_SESSION_ID);
  }, [onSessionStart]);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    if (guestMode) {
      setError('Sign in to upload real documents to the server. Use “Open sample review” below to preview the UI.');
      return;
    }
    if (!ACCEPTED.includes(file.type)) {
      setError('Unsupported format. Please upload PDF, DOCX, or TXT.');
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File exceeds ${MAX_MB} MB limit.`);
      return;
    }
    setError('');
    setUploading(true);
    try {
      const res = await upload.document(file);
      onSessionStart(res.session_id || res.id, res);
    } catch (e) {
      setError(e.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  }, [ACCEPTED, guestMode, onSessionStart]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1>Upload document</h1>
        <p>The system will automatically extract, validate and classify all software requirements.</p>
        {guestMode && (
          <p className="upload-guest-note">
            You are in <strong>guest preview</strong>. Upload is disabled; open the sample review to explore the layout.
          </p>
        )}
      </div>

      <div
        className={`drop-zone ${dragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !uploading && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {uploading ? (
          <div className="upload-progress">
            <div className="spinner" />
            <p>Uploading and starting pipeline...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <p className="drop-label">Drag &amp; Drop your file here</p>
            <p className="drop-sub">or click and browse from your computer</p>
            <button className="btn-upload" onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}>
              Upload file
            </button>
            <div className="format-tags">
              <span className="format-tag">PDF</span>
              <span className="format-tag">DOCX</span>
              <span className="format-tag">TXT</span>
              <span className="format-tag">MAX 10 MB</span>
            </div>
          </>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {guestMode && (
        <div className="upload-preview-actions">
          <button type="button" className="btn-sample-review" onClick={goPreview}>
            Open sample review
          </button>
        </div>
      )}

      <div className="upload-note">
        After uploading, the AI pipeline will run automatically. Processing a standard document takes up to 3 minutes.
      </div>
    </div>
  );
}