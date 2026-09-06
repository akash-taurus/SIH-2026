/**
 * NER-LEWS Offline Hazard Reporting Queue & Persistence Service
 * 
 * Target Path: frontend/src/services/offlineQueue.js
 * 
 * Provides offline-first client-side queuing for citizen and field responder
 * hazard reports during storm and landslide events when mountain telecommunications
 * are severed.
 * 
 * Features:
 * - Persistent localStorage queue: 'ner_lews_offline_hazard_queue'
 * - Automated base64 photo compression keeping payloads strictly < 120KB
 * - Robust QuotaExceededError recovery with graceful degradation
 * - Automatic background queue flush on 'online' window events
 * - Custom event notifications ('offline-queue-changed')
 * - Full backward-compatible export aliases matching PROJECT.md and DISPATCH.md
 */

export const OFFLINE_QUEUE_STORAGE_KEY = 'ner_lews_offline_hazard_queue';
export const VERIFIED_REPORTS_STORAGE_KEY = 'ner_lews_citizen_reports';
export const EVENT_QUEUE_CHANGED = 'offline-queue-changed';
export const EVENT_SYNC_STARTED = 'offline-sync-started';
export const EVENT_SYNC_COMPLETED = 'offline-sync-completed';

const MAX_PHOTO_BYTES = 120 * 1024; // 122,880 bytes / chars maximum
let isSyncing = false;
let isListenerInitialized = false;

// ---------------------------------------------------------------------------
// Helper: Safe LocalStorage Access
// ---------------------------------------------------------------------------

function getStorage() {
  try {
    if (typeof localStorage !== 'undefined') return localStorage;
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') return window.localStorage;
  } catch {
    return null;
  }
  return null;
}

function isStorageAvailable() {
  return getStorage() !== null;
}

function safeGetItem(key) {
  const storage = getStorage();
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch (err) {
    console.warn(`[OfflineQueue] Failed to read '${key}':`, err);
    return null;
  }
}

function safeSetItem(key, value) {
  const storage = getStorage();
  if (!storage) return false;
  storage.setItem(key, value);
  return true;
}

// ---------------------------------------------------------------------------
// Event Dispatching & Subscription
// ---------------------------------------------------------------------------

/**
 * Dispatches a custom event with current queue state.
 */
export function dispatchQueueChanged(queue = null) {
  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') return;
  try {
    const currentQueue = queue !== null ? queue : getQueuedReports();
    const event = new CustomEvent(EVENT_QUEUE_CHANGED, {
      detail: {
        count: currentQueue.length,
        reports: currentQueue,
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(event);
  } catch (err) {
    console.warn('[OfflineQueue] Failed to dispatch event:', err);
  }
}

/**
 * Subscribes a listener callback to queue change events.
 * Returns an unsubscribe cleanup function.
 */
export function subscribeToQueue(callback) {
  if (typeof window === 'undefined' || typeof window.addEventListener !== 'function') {
    return () => {};
  }
  const handler = (event) => {
    if (callback && typeof callback === 'function') {
      callback(event.detail);
    }
  };
  window.addEventListener(EVENT_QUEUE_CHANGED, handler);
  // Emit initial state immediately
  try {
    const initialQueue = getQueuedReports();
    callback({ count: initialQueue.length, reports: initialQueue, timestamp: new Date().toISOString() });
  } catch {
    // ignore
  }
  return () => {
    window.removeEventListener(EVENT_QUEUE_CHANGED, handler);
  };
}

// ---------------------------------------------------------------------------
// Image Compression & Base64 Serialization (< 120KB)
// ---------------------------------------------------------------------------

/**
 * Compresses an image File or Blob to a base64 Data URL strictly under 120KB.
 * Progressively reduces canvas resolution and JPEG quality.
 *
 * @param {File|Blob} file - Raw photo file
 * @param {number} maxDimension - Maximum width or height (default: 800)
 * @param {number} targetMaxBytes - Target size limit in bytes/chars (default: 120KB)
 * @returns {Promise<string|null>} Resolves with data:image/jpeg;base64,... or null
 */
export function compressImageToBase64(file, maxDimension = 800, targetMaxBytes = MAX_PHOTO_BYTES) {
  return new Promise((resolve, reject) => {
    if (!file) {
      resolve(null);
      return;
    }

    // In testing or non-browser environments where FileReader / Image might be mocked
    if (typeof FileReader === 'undefined' || typeof Image === 'undefined') {
      resolve(null);
      return;
    }

    const reader = new FileReader();
    reader.onerror = (err) => reject(err);
    reader.onload = (event) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          resolve(event.target.result?.slice(0, targetMaxBytes) || null);
        }
      }, 500);

      const img = new Image();
      img.onerror = (err) => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(err);
        }
      };
      img.onload = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);

        let width = img.width || 800;
        let height = img.height || 600;

        // Scale down to maxDimension
        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(event.target.result?.slice(0, targetMaxBytes) || null);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        // Quality stepping: 0.70 -> 0.50 -> 0.35 -> 0.20
        const qualities = [0.70, 0.50, 0.35, 0.20];
        let chosenDataUrl = null;

        for (const quality of qualities) {
          const dataUrl = canvas.toDataURL('image/jpeg', quality);
          if (dataUrl.length <= targetMaxBytes) {
            resolve(dataUrl);
            return;
          }
          chosenDataUrl = dataUrl;
        }

        // Secondary step: progressive canvas downscale if still > targetMaxBytes
        const downscaleWidths = [Math.round(width * 0.65), Math.round(width * 0.45)];
        for (const targetW of downscaleWidths) {
          const targetH = Math.round((height * targetW) / width);
          const scaledCanvas = document.createElement('canvas');
          scaledCanvas.width = targetW;
          scaledCanvas.height = targetH;
          const scaledCtx = scaledCanvas.getContext('2d');
          if (scaledCtx) {
            scaledCtx.drawImage(canvas, 0, 0, targetW, targetH);
            for (const q of [0.45, 0.25]) {
              const dataUrl = scaledCanvas.toDataURL('image/jpeg', q);
              if (dataUrl.length <= targetMaxBytes) {
                resolve(dataUrl);
                return;
              }
              chosenDataUrl = dataUrl;
            }
          }
        }

        // Return the best achieved representation
        resolve(chosenDataUrl);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Reconstructs a standard File object from a base64 Data URL.
 * Used during synchronization to send multipart/form-data to the backend.
 *
 * @param {string} dataUrl - Base64 Data URL
 * @param {string} filename - Desired output filename
 * @returns {File|null}
 */
export function base64ToFile(dataUrl, filename = 'synced_hazard.jpg') {
  if (!dataUrl || typeof dataUrl !== 'string') return null;
  try {
    const parts = dataUrl.split(',');
    if (parts.length < 2) return null;
    const mimeMatch = parts[0].match(/:(.*?);/);
    const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
    
    // Support window.atob or global atob
    const atobFn = typeof window !== 'undefined' && window.atob ? window.atob : (typeof atob !== 'undefined' ? atob : (typeof global !== 'undefined' ? global.atob : null));
    if (!atobFn) return null;
    
    const byteString = atobFn(parts[1]);
    let n = byteString.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = byteString.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime, lastModified: Date.now() });
  } catch (err) {
    console.warn('[OfflineQueue] base64ToFile conversion failed:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Queue Management Operations
// ---------------------------------------------------------------------------

/**
 * Retrieves all pending offline reports from localStorage.
 * @returns {Array<Object>}
 */
export function getQueuedReports() {
  const raw = safeGetItem(OFFLINE_QUEUE_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error('[OfflineQueue] Failed to parse offline queue JSON:', err);
    return [];
  }
}

/**
 * Returns the number of reports currently pending in the queue.
 * @returns {number}
 */
export function getQueuedCount() {
  return getQueuedReports().length;
}

/**
 * Completely clears the offline hazard queue.
 * @returns {boolean}
 */
export function clearQueue() {
  const storage = getStorage();
  if (!storage) return false;
  try {
    storage.removeItem(OFFLINE_QUEUE_STORAGE_KEY);
    dispatchQueueChanged([]);
    return true;
  } catch (err) {
    console.error('[OfflineQueue] Failed to clear queue:', err);
    return false;
  }
}

/**
 * Removes a specific report from the queue by its unique ID.
 * @param {string} id - Report ID to remove
 * @returns {boolean} True if found and removed
 */
export function removeReport(id) {
  if (!id || !isStorageAvailable()) return false;
  try {
    const queue = getQueuedReports();
    const filtered = queue.filter((item) => item.id !== id);
    if (filtered.length !== queue.length) {
      safeSetItem(OFFLINE_QUEUE_STORAGE_KEY, JSON.stringify(filtered));
      dispatchQueueChanged(filtered);
      return true;
    }
    return false;
  } catch (err) {
    console.error(`[OfflineQueue] Failed to remove report '${id}':`, err);
    return false;
  }
}

/**
 * Enqueues a new hazard report to persistent localStorage.
 * Compresses attached photos to base64 (<120KB) and handles QuotaExceededError.
 * 
 * @param {Object} reportData - { note, severity, latitude, longitude, photo, photo_base64, ... }
 * @returns {Promise<{ success: boolean, queued: boolean, report: Object, warning?: string, error?: string }>}
 */
export function enqueueReport(reportData) {
  return new Promise(async (resolve, reject) => {
    try {
      let photoBase64 = reportData.photo_base64 || null;
      let photoName = reportData.photo_name || reportData.photo?.name || 'field_evidence.jpg';

      // Compress photo if provided as File/Blob
      if (!photoBase64 && reportData.photo) {
        try {
          photoBase64 = await compressImageToBase64(reportData.photo, 800, MAX_PHOTO_BYTES);
        } catch (compressionErr) {
          console.warn('[OfflineQueue] Image compression failed, storing without photo:', compressionErr);
        }
      }

      const reportId = reportData.id || `REP-OFFLINE-${Date.now()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
      
      const lat = typeof reportData.latitude === 'number' ? reportData.latitude : null;
      const lon = typeof reportData.longitude === 'number' ? reportData.longitude : null;
      const locationName = reportData.location_name || (
        lat && lon
          ? `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`
          : 'Field Coordinates Pending'
      );

      const queuedItem = {
        id: reportId,
        reporter: reportData.reporter || 'Community Field Responder (Offline)',
        location_name: locationName,
        latitude: lat,
        longitude: lon,
        nearest_zone_id: reportData.nearest_zone_id || null,
        note: (reportData.note || '').trim(),
        severity: reportData.severity || 'high',
        status: 'queued_offline',
        queued_at: new Date().toISOString(),
        photo_base64: photoBase64,
        photo_name: photoName,
        timestamp: 'Queued (Offline)',
        sync_attempts: 0,
        last_sync_error: null
      };

      const currentQueue = getQueuedReports();
      const updatedQueue = [...currentQueue, queuedItem];

      try {
        safeSetItem(OFFLINE_QUEUE_STORAGE_KEY, JSON.stringify(updatedQueue));
        dispatchQueueChanged(updatedQueue);
        resolve({ success: true, queued: true, report: queuedItem });
      } catch (storageErr) {
        // QuotaExceededError detection across browsers (Chrome, Firefox, Safari)
        const isQuota = storageErr.name === 'QuotaExceededError' ||
                        storageErr.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
                        storageErr.code === 22 ||
                        storageErr.code === 1014;

        if (isQuota) {
          console.warn('[OfflineQueue] QuotaExceededError! Attempting recovery by shedding photo payload...');
          
          // Recovery attempt: enqueue report without photo
          if (queuedItem.photo_base64) {
            const strippedItem = {
              ...queuedItem,
              photo_base64: null,
              photo_dropped: true
            };
            const fallbackQueue = [...currentQueue, strippedItem];
            try {
              safeSetItem(OFFLINE_QUEUE_STORAGE_KEY, JSON.stringify(fallbackQueue));
              dispatchQueueChanged(fallbackQueue);
              resolve({
                success: true,
                queued: true,
                report: strippedItem,
                warning: 'Device storage quota exceeded: report saved locally without photo.'
              });
              return;
            } catch (fallbackErr) {
              console.error('[OfflineQueue] Fallback write without photo also failed:', fallbackErr);
            }
          }

          resolve({
            success: false,
            queued: false,
            error: 'QUOTA_EXCEEDED',
            message: 'Browser storage full. Please connect to internet to sync pending reports or clear storage.'
          });
        } else {
          console.error('[OfflineQueue] Failed to persist report:', storageErr);
          reject(storageErr);
        }
      }
    } catch (err) {
      console.error('[OfflineQueue] Unexpected error in enqueueReport:', err);
      reject(err);
    }
  });
}

// ---------------------------------------------------------------------------
// Auto-Flush & Reconnection Sync
// ---------------------------------------------------------------------------

/**
 * Flushes all pending reports in the offline queue to the backend API.
 * Uses mutex lock to prevent concurrent overlapping flushes.
 * 
 * @param {Function} onSyncSuccess - Callback invoked when a report is verified: (serverReport, queuedReport)
 * @param {string} apiBaseUrl - Base API URL (defaults to env or localhost:8000/api/v1)
 * @returns {Promise<{ synced: number, failed: number, remaining: number }>}
 */
export async function flushQueue(onSyncSuccess = null, apiBaseUrl = null) {
  if (isSyncing) {
    console.log('[OfflineQueue] Sync already in progress, skipping concurrent flush.');
    return { synced: 0, failed: 0, remaining: getQueuedCount(), alreadySyncing: true };
  }

  const queue = getQueuedReports();
  if (queue.length === 0) {
    return { synced: 0, failed: 0, remaining: 0 };
  }

  isSyncing = true;
  let syncedCount = 0;
  let failedCount = 0;

  const baseUrl = apiBaseUrl || (
    typeof process !== 'undefined' && process.env?.REACT_APP_API_BASE_URL
      ? process.env.REACT_APP_API_BASE_URL
      : 'http://localhost:8000/api/v1'
  );

  try {
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent(EVENT_SYNC_STARTED, { detail: { count: queue.length } }));
    }

    // Process reports sequentially to avoid server concurrency bursts
    for (const report of queue) {
      try {
        const formData = new FormData();
        formData.append('note', report.note);
        if (report.latitude !== null && report.latitude !== undefined) {
          formData.append('latitude', report.latitude);
        }
        if (report.longitude !== null && report.longitude !== undefined) {
          formData.append('longitude', report.longitude);
        }
        if (report.severity) {
          formData.append('severity', report.severity);
        }

        // Reconstruct photo File from base64 string
        if (report.photo_base64) {
          const file = base64ToFile(report.photo_base64, report.photo_name || 'hazard_evidence.jpg');
          if (file) {
            formData.append('photo', file);
          }
        }

        const response = await fetch(`${baseUrl}/reports`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const serverReport = await response.json();
          syncedCount++;

          // Remove successfully synced item from offline queue
          removeReport(report.id);

          // Append to local verified reports list so it remains visible in UI
          try {
            const rawVerified = safeGetItem(VERIFIED_REPORTS_STORAGE_KEY);
            const verifiedList = rawVerified ? JSON.parse(rawVerified) : [];
            const updatedVerified = [serverReport, ...verifiedList.filter((r) => r.id !== serverReport.id)];
            safeSetItem(VERIFIED_REPORTS_STORAGE_KEY, JSON.stringify(updatedVerified));
          } catch (storageErr) {
            console.warn('[OfflineQueue] Could not update verified reports in localStorage:', storageErr);
          }

          if (onSyncSuccess && typeof onSyncSuccess === 'function') {
            try {
              onSyncSuccess(serverReport, report);
            } catch (cbErr) {
              console.warn('[OfflineQueue] onSyncSuccess callback threw error:', cbErr);
            }
          }
        } else if (response.status >= 400 && response.status < 500) {
          // Client error (e.g. 422 Unprocessable Entity) - drop poisoned item or mark unrecoverable
          console.warn(`[OfflineQueue] Server rejected report ${report.id} (${response.status}). Removing from queue.`);
          removeReport(report.id);
          failedCount++;
        } else {
          // Server error 5xx - keep in queue for future retry
          failedCount++;
          console.warn(`[OfflineQueue] Server returned ${response.status} for report ${report.id}. Halting flush.`);
          break; // Stop sync loop if server is encountering 5xx errors
        }
      } catch (networkErr) {
        // Network failure (offline, timeout, DNS resolution) - halt loop and preserve remaining queue
        console.warn(`[OfflineQueue] Network error during sync of ${report.id}:`, networkErr.message);
        failedCount++;
        break;
      }
    }
  } finally {
    isSyncing = false;
    const remaining = getQueuedCount();
    
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(
        new CustomEvent(EVENT_SYNC_COMPLETED, {
          detail: { synced: syncedCount, failed: failedCount, remaining }
        })
      );
    }
  }

  return { synced: syncedCount, failed: failedCount, remaining: getQueuedCount() };
}

// ---------------------------------------------------------------------------
// Network Listener & Auto-Init
// ---------------------------------------------------------------------------

/**
 * Initializes auto-flush listeners on window 'online' event.
 * Returns cleanup function.
 */
export function initOfflineQueueSync(options = {}) {
  if (typeof window === 'undefined' || typeof window.addEventListener !== 'function') {
    return () => {};
  }

  const handleOnline = () => {
    console.log('[OfflineQueue] Network restored (online event detected). Initiating auto-flush...');
    flushQueue(options.onSyncSuccess, options.apiBaseUrl);
  };

  window.addEventListener('online', handleOnline);
  isListenerInitialized = true;

  return () => {
    window.removeEventListener('online', handleOnline);
    isListenerInitialized = false;
  };
}

// Auto-register listener in browser environment if not already registered
if (typeof window !== 'undefined' && !isListenerInitialized) {
  initOfflineQueueSync();
}

// ---------------------------------------------------------------------------
// Compatibility Aliases (satisfying both PROJECT.md & DISPATCH.md contracts)
// ---------------------------------------------------------------------------

export const enqueueOfflineReport = enqueueReport;
export const getQueuedOfflineReports = getQueuedReports;
export const clearOfflineQueueItem = removeReport;
export const flushOfflineReportsQueue = flushQueue;

export default {
  OFFLINE_QUEUE_STORAGE_KEY,
  VERIFIED_REPORTS_STORAGE_KEY,
  EVENT_QUEUE_CHANGED,
  compressImageToBase64,
  base64ToFile,
  getQueuedReports,
  getQueuedCount,
  clearQueue,
  removeReport,
  enqueueReport,
  flushQueue,
  initOfflineQueueSync,
  subscribeToQueue,
  enqueueOfflineReport,
  getQueuedOfflineReports,
  clearOfflineQueueItem,
  flushOfflineReportsQueue
};
