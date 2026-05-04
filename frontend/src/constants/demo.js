/** Fixed session id for local preview (no API). */
export const DEMO_SESSION_ID = '00000000-0000-4000-8000-000000000001';

/** Sample requirements matching backend-style fields used by the UI. */
export const MOCK_REQUIREMENTS = [
  {
    id: '10000000-0000-4000-8000-000000000001',
    req_id: 'FR-01',
    statement:
      'The system shall authenticate users within two seconds of submitting valid credentials.',
    classification: { type: 'functional' },
    validation_report: { result: 'valid', issues: [] },
    finalization_status: 'draft',
    pipeline_status: 'traced',
  },
  {
    id: '10000000-0000-4000-8000-000000000002',
    req_id: 'NFR-01',
    statement:
      'The service shall maintain 99.9% monthly availability excluding scheduled maintenance windows.',
    classification: { type: 'non-functional' },
    validation_report: { result: 'valid', issues: [] },
    finalization_status: 'draft',
    pipeline_status: 'traced',
  },
  {
    id: '10000000-0000-4000-8000-000000000003',
    req_id: 'FR-02',
    statement:
      'The application maybe should allow export of reports in PDF format when user clicks export.',
    classification: { type: 'functional' },
    validation_report: {
      result: 'flagged',
      issues: ['Ambiguous wording ("maybe")', 'Missing acceptance criteria'],
    },
    finalization_status: 'draft',
    pipeline_status: 'traced',
  },
];
