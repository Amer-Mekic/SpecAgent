import { useState } from 'react';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import UploadPage from './pages/UploadPage';
import ReviewPage from './pages/ReviewPage';
import { useSession } from './hooks/useSession';
import './App.css';

export default function App() {
  const { hasAccess, guestMode, logout } = useAuth();
  const [page, setPage] = useState('upload');
  const session = useSession(guestMode);

  if (!hasAccess) {
    return <LoginPage />;
  }

  const handleSessionStart = (sessionId) => {
    session.startSession(sessionId);
    setPage('review');
  };

  const goHome = () => {
    setPage('upload');
    session.startSession(null);
    session.setRequirements([]);
  };

  return (
    <div className="app">
      {guestMode && (
        <div className="guest-banner">
          <span>Guest preview — sample data only. Sign out and use <strong>Log in</strong> for real uploads and API features.</span>
          <button type="button" className="guest-banner-btn" onClick={logout}>
            Exit guest
          </button>
        </div>
      )}

      <header className="app-header">
        <div className="header-left">
          <button className="logo-btn" onClick={goHome}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            SpecAgent
          </button>
        </div>
        <div className="header-right">
          {!guestMode && page === 'review' && (
            <button className="btn-new" onClick={goHome} type="button">
              + New document
            </button>
          )}
          {!guestMode && page === 'upload' && null}
          {guestMode && page === 'review' && (
            <button className="btn-new" onClick={goHome} type="button">
              + Back to upload
            </button>
          )}
          <button type="button" className="btn-signout" onClick={logout}>
            {guestMode ? 'Sign in…' : 'Sign out'}
          </button>
        </div>
      </header>

      <main className="app-main">
        {page === 'upload' && (
          <UploadPage guestMode={guestMode} onSessionStart={handleSessionStart} />
        )}
        {page === 'review' && (
          <ReviewPage
            guestMode={guestMode}
            sessionId={session.sessionId}
            requirements={session.requirements}
            loadRequirements={session.loadRequirements}
            approveRequirement={session.approveRequirement}
            rejectRequirement={session.rejectRequirement}
            editRequirement={session.editRequirement}
            pipelineStatus={session.pipelineStatus}
          />
        )}
      </main>
    </div>
  );
}
