/**
 * Comprehensive Automated Test Suite for Milestone 3:
 * Frontend Offline Queue & Persistent Storage Service (R3)
 * 
 * Target File: frontend/src/services/offlineQueue.test.js
 * 
 * Covers:
 * - SUITE 1: Queueing & Data Normalization (enqueueReport, status, IDs, timestamps)
 * - SUITE 2: LocalStorage Persistence & Safe Retrieval (getQueuedReports, corrupted JSON recovery)
 * - SUITE 3: Queue Count, Removal & Reset (getQueuedCount, removeReport, clearQueue)
 * - SUITE 4: Photo Base64 Compression, Size Limits (<120KB) & File Reconstitution
 * - SUITE 5: QuotaExceededError Recovery (photo shedding fallback)
 * - SUITE 6: API Reconnection Synchronization (flushQueue, verified cache, error resilience)
 * - SUITE 7: window.ononline Auto-Flush Simulation & Lifecycle
 * - SUITE 8: Reactive Event Subscriptions (subscribeToQueue, EVENT_QUEUE_CHANGED)
 * - SUITE 9: Backward Compatibility Contract Aliases (PROJECT.md & DISPATCH.md)
 */

import {
  OFFLINE_QUEUE_STORAGE_KEY,
  VERIFIED_REPORTS_STORAGE_KEY,
  EVENT_QUEUE_CHANGED,
  EVENT_SYNC_STARTED,
  EVENT_SYNC_COMPLETED,
  enqueueReport,
  getQueuedReports,
  getQueuedCount,
  removeReport,
  clearQueue,
  compressImageToBase64,
  base64ToFile,
  flushQueue,
  initOfflineQueueSync,
  subscribeToQueue,
  enqueueOfflineReport,
  getQueuedOfflineReports,
  clearOfflineQueueItem,
  flushOfflineReportsQueue
} from './offlineQueue';

describe('offlineQueue Service Test Suite (Milestone 3)', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ============================================================================
  // SUITE 1: Queueing & Data Normalization
  // ============================================================================
  describe('Queueing Operations (enqueueReport)', () => {
    test('enqueues a report with full metadata, generating unique ID and queued_offline status', async () => {
      const listener = jest.fn();
      window.addEventListener(EVENT_QUEUE_CHANGED, listener);

      const result = await enqueueReport({
        note: 'Fresh tension cracks observed on upper road berm.',
        severity: 'high',
        latitude: 25.5788,
        longitude: 91.8933,
        reporter: 'Observer Unit 1'
      });

      expect(result.success).toBe(true);
      expect(result.queued).toBe(true);
      expect(result.report).toBeDefined();

      const report = result.report;
      expect(report.id).toMatch(/^REP-OFFLINE-/);
      expect(report.status).toBe('queued_offline');
      expect(report.note).toBe('Fresh tension cracks observed on upper road berm.');
      expect(report.severity).toBe('high');
      expect(report.latitude).toBe(25.5788);
      expect(report.longitude).toBe(91.8933);
      expect(report.location_name).toContain('25.5788° N');
      expect(report.reporter).toBe('Observer Unit 1');
      expect(report.queued_at).toBeDefined();
      expect(report.timestamp).toBe('Queued (Offline)');

      expect(listener).toHaveBeenCalledTimes(1);
      window.removeEventListener(EVENT_QUEUE_CHANGED, listener);
    });

    test('enqueues report without coordinates using pending location fallback', async () => {
      const result = await enqueueReport({
        note: 'General rockfall warning in valley sector without GPS fix.',
        severity: 'moderate'
      });

      expect(result.success).toBe(true);
      expect(result.report.latitude).toBeNull();
      expect(result.report.longitude).toBeNull();
      expect(result.report.location_name).toBe('Field Coordinates Pending');
    });

    test('preserves custom client id if provided', async () => {
      const customId = 'REP-CUSTOM-TEST-ID-123';
      const result = await enqueueReport({
        id: customId,
        note: 'Specific tracker station inspection log.'
      });

      expect(result.report.id).toBe(customId);
      const queue = getQueuedReports();
      expect(queue[0].id).toBe(customId);
    });
  });

  // ============================================================================
  // SUITE 2: LocalStorage Persistence & Safe Retrieval
  // ============================================================================
  describe('LocalStorage Persistence & Safe Retrieval', () => {
    test('getQueuedReports returns empty array when storage is empty', () => {
      expect(getQueuedReports()).toEqual([]);
      expect(getQueuedCount()).toBe(0);
    });

    test('persists queue to localStorage under key ner_lews_offline_hazard_queue', async () => {
      await enqueueReport({ note: 'Persistent report 1' });
      await enqueueReport({ note: 'Persistent report 2' });

      const raw = localStorage.getItem(OFFLINE_QUEUE_STORAGE_KEY);
      expect(raw).not.toBeNull();

      const parsed = JSON.parse(raw);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed.length).toBe(2);
      expect(parsed[0].note).toBe('Persistent report 1');
      expect(parsed[1].note).toBe('Persistent report 2');
    });

    test('recovers gracefully when localStorage contains corrupted non-JSON data', () => {
      const spyWarn = jest.spyOn(console, 'error').mockImplementation(() => {});
      localStorage.setItem(OFFLINE_QUEUE_STORAGE_KEY, 'invalid{{json-content');

      const reports = getQueuedReports();
      expect(reports).toEqual([]);
      expect(getQueuedCount()).toBe(0);
      spyWarn.mockRestore();
    });

    test('recovers gracefully when localStorage contains JSON of non-array type', () => {
      localStorage.setItem(OFFLINE_QUEUE_STORAGE_KEY, JSON.stringify({ key: 'not an array' }));
      expect(getQueuedReports()).toEqual([]);
      expect(getQueuedCount()).toBe(0);
    });
  });

  // ============================================================================
  // SUITE 3: Queue Count, Removal & Reset
  // ============================================================================
  describe('Queue Count, Removal & Reset', () => {
    test('getQueuedCount reflects current pending queue size', async () => {
      expect(getQueuedCount()).toBe(0);
      await enqueueReport({ note: 'Item 1' });
      expect(getQueuedCount()).toBe(1);
      await enqueueReport({ note: 'Item 2' });
      expect(getQueuedCount()).toBe(2);
    });

    test('removeReport deletes single item by ID and updates localStorage', async () => {
      const r1 = await enqueueReport({ note: 'Observation Alpha' });
      const r2 = await enqueueReport({ note: 'Observation Beta' });
      expect(getQueuedCount()).toBe(2);

      const removed = removeReport(r1.report.id);
      expect(removed).toBe(true);
      expect(getQueuedCount()).toBe(1);

      const remaining = getQueuedReports();
      expect(remaining[0].id).toBe(r2.report.id);
    });

    test('removeReport returns false when item ID does not exist', async () => {
      await enqueueReport({ note: 'Existing item' });
      const removed = removeReport('non-existent-id-999');
      expect(removed).toBe(false);
      expect(getQueuedCount()).toBe(1);
    });

    test('clearQueue empties entire queue and dispatches empty queue event', async () => {
      const listener = jest.fn();
      window.addEventListener(EVENT_QUEUE_CHANGED, listener);

      await enqueueReport({ note: 'Item A' });
      await enqueueReport({ note: 'Item B' });
      expect(getQueuedCount()).toBe(2);

      const cleared = clearQueue();
      expect(cleared).toBe(true);
      expect(getQueuedCount()).toBe(0);
      expect(getQueuedReports()).toEqual([]);
      expect(localStorage.getItem(OFFLINE_QUEUE_STORAGE_KEY)).toBeNull();

      expect(listener).toHaveBeenCalled();
      window.removeEventListener(EVENT_QUEUE_CHANGED, listener);
    });
  });

  // ============================================================================
  // SUITE 4: Photo Base64 Compression, Size Limits (<120KB) & File Reconstitution
  // ============================================================================
  describe('Photo Base64 Compression & Size Limits', () => {
    test('compressImageToBase64 returns null when file is missing', async () => {
      const result = await compressImageToBase64(null);
      expect(result).toBeNull();
    });

    test('base64ToFile reconstructs a standard File object with correct MIME and name', () => {
      // 1x1 white pixel base64
      const base64Data = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';
      const file = base64ToFile(base64Data, 'test_hazard.jpg');

      expect(file).not.toBeNull();
      expect(file).toBeInstanceOf(File);
      expect(file.name).toBe('test_hazard.jpg');
      expect(file.type).toBe('image/jpeg');
      expect(file.size).toBeGreaterThan(0);
    });

    test('base64ToFile returns null for malformed base64 strings without crashing', () => {
      const spyWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});
      expect(base64ToFile('not-a-data-uri')).toBeNull();
      expect(base64ToFile(null)).toBeNull();
      spyWarn.mockRestore();
    });

    test('enqueueReport stores pre-encoded photo_base64 string', async () => {
      const sampleBase64 = 'data:image/jpeg;base64,dGVzdA==';
      const result = await enqueueReport({
        note: 'Observation with pre-compressed photo',
        photo_base64: sampleBase64,
        photo_name: 'evidence.jpg'
      });

      expect(result.report.photo_base64).toBe(sampleBase64);
      expect(result.report.photo_name).toBe('evidence.jpg');
    });
  });

  // ============================================================================
  // SUITE 5: QuotaExceededError Recovery (Photo Shedding Fallback)
  // ============================================================================
  describe('Storage Quota Exceeded Recovery', () => {
    test('gracefully sheds photo payload and saves report metadata on QuotaExceededError', async () => {
      let callCount = 0;

      // First call throws QuotaExceededError, second call succeeds (after photo dropped)
      const setItemSpy = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(function(key, value) {
        callCount++;
        if (callCount === 1) {
          const error = new Error('Quota exceeded');
          error.name = 'QuotaExceededError';
          error.code = 22;
          throw error;
        }
        return undefined;
      });

      const result = await enqueueReport({
        note: 'Critical slope movement during storage overflow',
        photo_base64: 'data:image/jpeg;base64,' + 'X'.repeat(40000)
      });

      expect(result.success).toBe(true);
      expect(result.warning).toContain('quota exceeded');
      expect(result.report.photo_base64).toBeNull();
      expect(result.report.photo_dropped).toBe(true);
      expect(result.report.note).toBe('Critical slope movement during storage overflow');

      setItemSpy.mockRestore();
    });

    test('returns QUOTA_EXCEEDED error when storage is completely full even without photo', async () => {
      const setItemSpy = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(function() {
        const error = new Error('Quota exceeded permanently');
        error.name = 'QuotaExceededError';
        error.code = 22;
        throw error;
      });

      const result = await enqueueReport({
        note: 'Report attempting write when device storage is completely 100% full'
      });

      expect(result.success).toBe(false);
      expect(result.error).toBe('QUOTA_EXCEEDED');

      setItemSpy.mockRestore();
    });
  });

  // ============================================================================
  // SUITE 6: API Reconnection Synchronization (flushQueue)
  // ============================================================================
  describe('Queue Synchronization (flushQueue)', () => {
    test('flushQueue returns zeroes when queue is already empty', async () => {
      const summary = await flushQueue();
      expect(summary.synced).toBe(0);
      expect(summary.failed).toBe(0);
      expect(summary.remaining).toBe(0);
    });

    test('flushes queue via POST /reports, removes synced items and caches to verified store', async () => {
      await enqueueReport({
        note: 'Mudslide blocking culvert at Km 24',
        severity: 'high',
        latitude: 25.55,
        longitude: 91.88
      });
      expect(getQueuedCount()).toBe(1);

      const mockServerReport = {
        id: 'REP-2026-099',
        reporter: 'Citizen Field Responder',
        location_name: '25.5500° N, 91.8800° E',
        note: 'Mudslide blocking culvert at Km 24',
        severity: 'high',
        status: 'verified',
        timestamp: 'Just now'
      };

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockServerReport
      });

      const onSyncSuccess = jest.fn();
      const startListener = jest.fn();
      const completeListener = jest.fn();

      window.addEventListener(EVENT_SYNC_STARTED, startListener);
      window.addEventListener(EVENT_SYNC_COMPLETED, completeListener);

      const summary = await flushQueue(onSyncSuccess, 'http://mock-backend/api/v1');

      expect(summary.synced).toBe(1);
      expect(summary.failed).toBe(0);
      expect(summary.remaining).toBe(0);
      expect(getQueuedCount()).toBe(0);

      // Verify server report cached in verified store for UI immediate display
      const verifiedRaw = localStorage.getItem(VERIFIED_REPORTS_STORAGE_KEY);
      expect(verifiedRaw).not.toBeNull();
      const verifiedList = JSON.parse(verifiedRaw);
      expect(verifiedList.length).toBe(1);
      expect(verifiedList[0].id).toBe('REP-2026-099');

      expect(onSyncSuccess).toHaveBeenCalledWith(mockServerReport, expect.any(Object));
      expect(startListener).toHaveBeenCalled();
      expect(completeListener).toHaveBeenCalled();

      window.removeEventListener(EVENT_SYNC_STARTED, startListener);
      window.removeEventListener(EVENT_SYNC_COMPLETED, completeListener);
    });

    test('preserves remaining reports when network fails mid-flush', async () => {
      await enqueueReport({ note: 'Item 1' });
      await enqueueReport({ note: 'Item 2' });
      expect(getQueuedCount()).toBe(2);

      global.fetch = jest.fn().mockRejectedValue(new TypeError('Failed to fetch'));

      const summary = await flushQueue(null, 'http://mock-backend/api/v1');
      expect(summary.synced).toBe(0);
      expect(summary.failed).toBe(1);
      // Both reports remain safe in localStorage
      expect(getQueuedCount()).toBe(2);
    });

    test('drops poisoned report that receives 422 Unprocessable Entity and continues', async () => {
      await enqueueReport({ note: 'Poisoned report rejected by server' });
      expect(getQueuedCount()).toBe(1);

      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity'
      });

      const summary = await flushQueue(null, 'http://mock-backend/api/v1');
      expect(summary.synced).toBe(0);
      expect(summary.failed).toBe(1);
      // Poisoned report is discarded from queue so it does not block future syncs
      expect(getQueuedCount()).toBe(0);
    });

    test('halts flush and preserves queue when server returns 500 error', async () => {
      await enqueueReport({ note: 'Report during backend outage' });

      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const summary = await flushQueue(null, 'http://mock-backend/api/v1');
      expect(summary.synced).toBe(0);
      expect(summary.failed).toBe(1);
      // Server error preserves report for future retry
      expect(getQueuedCount()).toBe(1);
    });
  });

  // ============================================================================
  // SUITE 7: window.ononline Auto-Flush Simulation
  // ============================================================================
  describe('window.ononline Auto-Flush Integration', () => {
    test('triggers auto-flush when online window event fires', async () => {
      await enqueueReport({ note: 'Queued while in mountain dead-zone' });
      expect(getQueuedCount()).toBe(1);

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: 'REP-SYNCED', note: 'Queued while in mountain dead-zone' })
      });

      const onSyncSuccess = jest.fn();
      const cleanup = initOfflineQueueSync({ onSyncSuccess, apiBaseUrl: 'http://test/api/v1' });

      // Simulate browser online event
      window.dispatchEvent(new Event('online'));

      // Allow flush microtask to run
      await new Promise((r) => setTimeout(r, 50));

      expect(global.fetch).toHaveBeenCalled();
      cleanup();
    });

    test('cleanup function detaches online event listener', () => {
      const removeSpy = jest.spyOn(window, 'removeEventListener');
      const cleanup = initOfflineQueueSync();
      cleanup();
      expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function));
      removeSpy.mockRestore();
    });
  });

  // ============================================================================
  // SUITE 8: Reactive Event Subscriptions
  // ============================================================================
  describe('Reactive Event Subscriptions (subscribeToQueue)', () => {
    test('invokes subscriber callback with initial state immediately upon subscription', () => {
      const callback = jest.fn();
      const unsubscribe = subscribeToQueue(callback);

      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({ count: 0, reports: [] })
      );
      unsubscribe();
    });

    test('invokes subscriber on queue mutations and stops after unsubscribe', async () => {
      const callback = jest.fn();
      const unsubscribe = subscribeToQueue(callback);

      await enqueueReport({ note: 'Subscriber notification test' });
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({ count: 1 })
      );

      unsubscribe();
      await enqueueReport({ note: 'Another report after unsub' });
      // Should not receive third call after unsubscribe
      expect(callback).toHaveBeenCalledTimes(2);
    });
  });

  // ============================================================================
  // SUITE 9: Backward Compatibility Contract Aliases
  // ============================================================================
  describe('Contract Aliases Compatibility', () => {
    test('satisfies PROJECT.md and DISPATCH.md function aliases', () => {
      expect(typeof enqueueOfflineReport).toBe('function');
      expect(typeof getQueuedOfflineReports).toBe('function');
      expect(typeof clearOfflineQueueItem).toBe('function');
      expect(typeof flushOfflineReportsQueue).toBe('function');

      expect(enqueueOfflineReport).toBe(enqueueReport);
      expect(getQueuedOfflineReports).toBe(getQueuedReports);
      expect(clearOfflineQueueItem).toBe(removeReport);
      expect(flushOfflineReportsQueue).toBe(flushQueue);
    });
  });
});
