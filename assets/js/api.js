/**
 * TALK2TOPICS — API Layer
 * Thin data layer that communicates with the Flask backend.
 * All responses come from real AI processing — no mocks.
 */

const API = {
    // ─── State ───────────────────────────────────────────────────────
    currentData: null,
    currentJobId: null,
    _pollTimer: null,

    // ─── Helpers ─────────────────────────────────────────────────────
    delay: (ms) => new Promise(resolve => setTimeout(resolve, ms)),

    get BASE_URL() {
        if (window.BACKEND_URL) return window.BACKEND_URL;
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return 'http://localhost:5000';
        }
        return window.BACKEND_URL || 'http://localhost:5000';
    },

    async _post(endpoint, body) {
        try {
            const res = await fetch(`${this.BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
            return data;
        } catch (err) {
            if (err.message && err.message.includes('Failed to fetch')) {
                throw new Error(`Cannot reach AI backend at ${this.BASE_URL}. Ensure server.py is running!`);
            }
            throw err;
        }
    },

    async _get(endpoint) {
        const res = await fetch(`${this.BASE_URL}${endpoint}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        return data;
    },

    // ─── Upload ───────────────────────────────────────────────────────
    /**
     * Upload an audio file and immediately receive a job_id.
     * The backend processes asynchronously; use pollStatus() to track progress.
     *
     * @param {File} file - The audio file to upload
     * @returns {Promise<string>} Resolves with the job_id
     */
    async uploadPodcast(file) {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${this.BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || `Upload failed with HTTP ${res.status}`);
        }

        if (!data.job_id) {
            throw new Error('Server did not return a job_id. Check backend logs.');
        }

        this.currentJobId = data.job_id;
        console.log('[API] Upload accepted. Job ID:', data.job_id);
        return data.job_id;
    },

    // ─── Status Polling ───────────────────────────────────────────────
    /**
     * Poll /status/<job_id> every 2 seconds until the job completes.
     *
     * @param {string} jobId
     * @param {function} onProgress - Called with (stage: string, progress: number)
     * @returns {Promise<Object>} Resolves with the full data payload on success
     */
    pollStatus(jobId, onProgress) {
        return new Promise((resolve, reject) => {
            const INTERVAL_MS = 2000;
            const MAX_WAIT_MS = 10 * 60 * 1000; // 10-minute hard timeout
            const started = Date.now();

            const tick = async () => {
                try {
                    const status = await this._get(`/status/${jobId}`);

                    // Report progress to UI
                    if (typeof onProgress === 'function') {
                        onProgress(status.stage || 'Processing...', status.progress || 0);
                    }

                    if (status.done) {
                        if (status.error) {
                            reject(new Error(`Pipeline failed: ${status.error}`));
                        } else {
                            // Store data globally for all views
                            this.currentData = status.data;
                            this.currentJobId = jobId;
                            console.log('[API] Job complete. Data stored.');
                            resolve(status.data);
                        }
                        return; // stop polling
                    }

                    // Hard timeout guard
                    if (Date.now() - started > MAX_WAIT_MS) {
                        reject(new Error('Processing timed out after 10 minutes. Please try again.'));
                        return;
                    }

                    // Schedule next poll
                    setTimeout(tick, INTERVAL_MS);

                } catch (err) {
                    console.error('[API] Poll error:', err);
                    reject(err);
                }
            };

            // Start immediately
            setTimeout(tick, INTERVAL_MS);
        });
    },

    // ─── Data Accessor ────────────────────────────────────────────────
    getCurrentData() {
        return this.currentData;
    },

    // ─── Chat ─────────────────────────────────────────────────────────
    /**
     * RAG-style semantic search over the transcript.
     * @param {string} query
     * @returns {Promise<{answer: string, sources: Array, timestamp: number|null}>}
     */
    async chatPodcast(query) {
        if (!this.currentData || !this.currentData.transcript) {
            throw new Error('No podcast loaded. Please upload and process a podcast first.');
        }

        return await this._post('/chat', {
            query,
            transcript: this.currentData.transcript,
        });
    },

    // ─── Translation ──────────────────────────────────────────────────
    /**
     * Translate text to the target language.
     * @param {string} text
     * @param {string} language - Language code, e.g. 'es', 'fr', 'hi'
     * @returns {Promise<string>} Translated text
     */
    async translateText(text, language) {
        const data = await this._post('/translate', { text, language });
        return data.translated;
    },

    // ─── Romanization ─────────────────────────────────────────────────
    /**
     * Romanize Indic-script text to Latin/IAST.
     * @param {string} text
     * @param {string} sourceLang - e.g. 'Devanagari', 'Telugu'
     * @returns {Promise<string>} Romanized text
     */
    async romanize(text, sourceLang) {
        const data = await this._post('/romanize', { text, language: sourceLang });
        return data.romanized;
    },

    // ─── Library ──────────────────────────────────────────────────────
    /**
     * Returns a list of previously processed podcasts from the server's outputs folder.
     * @returns {Promise<Array>}
     */
    async getLibrary() {
        const data = await this._get('/library');
        return data.library || [];
    },

    // ─── Export ───────────────────────────────────────────────────────
    /**
     * Download an exported file for the current job.
     * @param {string} format - One of: txt, json, srt, md, csv
     */
    async exportData(format) {
        if (!this.currentJobId) {
            throw new Error('No job loaded. Please upload and process a podcast first.');
        }

        const url = `${this.BASE_URL}/export/${this.currentJobId}/${format}`;
        const a = document.createElement('a');
        a.href = url;
        a.download = `talk2topics_${this.currentJobId.substring(0, 8)}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    },
};
