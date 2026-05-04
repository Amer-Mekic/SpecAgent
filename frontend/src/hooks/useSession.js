import { useState, useCallback } from 'react';
import { requirements as reqApi } from '../api/client';
import { DEMO_SESSION_ID, MOCK_REQUIREMENTS } from '../constants/demo';

export function useSession(guestMode = false) {
  const [sessionId, setSessionId] = useState(null);
  const [requirements, setRequirements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState(null);

  const startSession = useCallback((id) => {
    setSessionId(id);
    if (!id) {
      setRequirements([]);
      setPipelineStatus(null);
      return;
    }
    setPipelineStatus(guestMode && id === DEMO_SESSION_ID ? 'complete' : 'processing');
  }, [guestMode]);

  const loadRequirements = useCallback(
    async (id) => {
      const sid = id || sessionId;
      if (!sid) return;
      if (guestMode && sid === DEMO_SESSION_ID) {
        setRequirements(MOCK_REQUIREMENTS);
        setPipelineStatus('complete');
        return;
      }
      setLoading(true);
      try {
        const data = await reqApi.list(sid);
        setRequirements(data);
        setPipelineStatus('complete');
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, guestMode],
  );

  const updateRequirement = useCallback((reqId, changes) => {
    setRequirements((prev) => prev.map((r) => (r.id === reqId ? { ...r, ...changes } : r)));
  }, []);

  const approveRequirement = useCallback(
    async (reqId) => {
      if (guestMode) {
        updateRequirement(reqId, { finalization_status: 'final' });
        return;
      }
      await reqApi.approve(reqId);
      updateRequirement(reqId, { finalization_status: 'final' });
    },
    [guestMode, updateRequirement],
  );

  const rejectRequirement = useCallback(
    async (reqId) => {
      if (guestMode) {
        updateRequirement(reqId, { finalization_status: 'rejected' });
        return;
      }
      await reqApi.reject(reqId);
      updateRequirement(reqId, { finalization_status: 'rejected' });
    },
    [guestMode, updateRequirement],
  );

  const editRequirement = useCallback(
    async (reqId, statement) => {
      if (guestMode) {
        updateRequirement(reqId, { statement });
        return { id: reqId, statement };
      }
      const updated = await reqApi.update(reqId, { statement });
      updateRequirement(reqId, updated);
      return updated;
    },
    [guestMode, updateRequirement],
  );

  return {
    sessionId,
    requirements,
    loading,
    pipelineStatus,
    startSession,
    loadRequirements,
    approveRequirement,
    rejectRequirement,
    editRequirement,
    setRequirements,
  };
}
