/**
 * TALK2TOPICS — Core Application (app.js)
 * Handles routing, state management, and view rendering.
 * Phase 1: Real async pipeline with SSE-style polling.
 */

const app = {
    // ─── State ───────────────────────────────────────────────────────
    currentRoute: 'upload',

    // ─── Initialization ───────────────────────────────────────────────
    init() {
        try {
            this.initTheme();
            if (typeof Mascot !== 'undefined' && Mascot.init) {
                Mascot.init();
            }
            this.cacheDOM();
            if (this.shell) {
                this.shell.classList.remove('hidden');
            }
            this.bindEvents();
            this.navigate('upload');
        } catch (e) {
            console.error('Critical failure during app initialization:', e);
            document.body.innerHTML = `
                <div style="padding:2rem;color:red;font-family:sans-serif;">
                    <h2>Failed to load application</h2>
                    <p>${e.message}</p>
                    <p>Check the browser console for details.</p>
                </div>`;
        }
    },

    initTheme() {
        const savedTheme = localStorage.getItem('talk2topics_theme') || 'light';
        this.setTheme(savedTheme);
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('talk2topics_theme', theme);
    },

    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        this.setTheme(next);
        this.showToast(`Switched to ${next === 'light' ? 'Creme & Burgundy' : 'Obsidian Black'} theme`, 'info');
    },

    renderIcons() {
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            try { lucide.createIcons(); } catch (err) { console.warn('Lucide icon error:', err); }
        }
    },

    cacheDOM() {
        this.shell          = document.getElementById('app');
        this.routeContent   = document.getElementById('route-content');
        this.toastContainer = document.getElementById('toast-container');
        this.navLinks       = document.querySelectorAll('.nav-link');
        this.exportModal    = document.getElementById('export-modal');
        this.menuToggleBtn  = document.getElementById('menu-toggle-btn');
        this.themeToggleBtn = document.getElementById('theme-toggle-btn');
        this.sidebar        = document.querySelector('.sidebar');
    },

    bindEvents() {
        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigate(e.currentTarget.getAttribute('data-route'));
            });
        });

        // Menu Toggle (Sidebar Collapse / Mobile Off-canvas)
        if (this.menuToggleBtn && this.sidebar) {
            this.menuToggleBtn.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    this.sidebar.classList.toggle('mobile-open');
                } else {
                    this.sidebar.classList.toggle('collapsed');
                }
                this.renderIcons();
            });
        }

        // Theme Toggle (Light Creme & Burgundy <-> Dark Obsidian Black)
        if (this.themeToggleBtn) {
            this.themeToggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        const searchInput = document.getElementById('global-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                if (this.currentRoute === 'transcript') {
                    this.renderTranscriptView(e.target.value);
                }
            });
        }
    },

    // ─── Router ───────────────────────────────────────────────────────
    async navigate(route) {
        // Guard: most routes require processed data
        const requiresData = !['upload', 'library'].includes(route);
        if (requiresData && !API.getCurrentData()) {
            this.showToast('Please upload and process a podcast first.', 'error');
            this.navigate('upload');
            return;
        }

        this.currentRoute = route;

        // Update active nav link
        this.navLinks.forEach(l => l.classList.remove('active'));
        const activeLink = document.querySelector(`.nav-link[data-route="${route}"]`);
        if (activeLink) activeLink.classList.add('active');

        this.routeContent.innerHTML = '';

        const sidebar = document.querySelector('.sidebar');
        const header  = document.querySelector('.top-header');

        if (route === 'upload') {
            if (sidebar) sidebar.style.display = 'none';
            if (header)  header.style.display  = 'none';
            this.routeContent.innerHTML = Components.UploadView();
            setTimeout(() => this.bindUploadEvents(), 50);
            Mascot.reactToUpload();
        } else {
            if (sidebar) sidebar.style.display = 'flex';
            if (header)  header.style.display  = 'flex';

            switch (route) {
                case 'dashboard':     await this.renderDashboard();       break;
                case 'transcript':    this.renderTranscriptView();         break;
                case 'topics':        this.renderTopicsView();             break;
                case 'summary':       this.renderSummaryView();            break;
                case 'chat':          this.renderChatView();               break;
                case 'translation':   await this.renderTranslationView();  break;
                case 'romanization':  this.renderRomanizationView();       break;
                case 'keywords':      this.renderKeywordsView();           break;
                case 'library':       await this.renderLibraryView();      break;
                default:
                    this.routeContent.innerHTML =
                        `<div class="fade-in"><h2>${route}</h2><p>This section is coming in a future phase.</p></div>`;
            }
        }

        this.renderIcons();
    },

    // ─── Upload & Processing ──────────────────────────────────────────
    bindUploadEvents() {
        const dropzone  = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        if (!dropzone || !fileInput) return;

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragging');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragging');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragging');
            if (e.dataTransfer.files.length) this.handleFile(e.dataTransfer.files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) this.handleFile(e.target.files[0]);
        });
    },

    async handleFile(file) {
        // Validate extension client-side first
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['mp3', 'wav', 'm4a'].includes(ext)) {
            this.showToast(`Unsupported format: .${ext}. Please use MP3, WAV, or M4A.`, 'error');
            return;
        }

        // Switch to processing view immediately
        this.shell.classList.remove('hidden');
        const sidebar = document.querySelector('.sidebar');
        const header  = document.querySelector('.top-header');
        if (sidebar) sidebar.style.display = 'none';
        if (header)  header.style.display  = 'none';
        this.routeContent.innerHTML = Components.ProcessingView(file.name, file.size);
        this.renderIcons();
        Mascot.show();

        try {
            // ── Step 1: Upload (fast, returns job_id immediately) ──────
            this._setProcessingStage('Uploading...', 2);
            Mascot.reactToProcessing('Uploading audio file...');

            const jobId = await API.uploadPodcast(file);
            this._setProcessingStage('Upload complete. Starting AI pipeline...', 8);

            // ── Step 2: Poll for real progress ─────────────────────────
            await API.pollStatus(jobId, (stage, pct, elapsedSec) => {
                this._setProcessingStage(stage, pct, elapsedSec);
                Mascot.reactToProcessing(stage);
            });

            // ── Step 3: Navigate to dashboard ─────────────────────────
            Mascot.reactToSuccess();
            this.showToast('Processing complete! Your insights are ready.', 'success');
            await API.delay(800);
            this.navigate('dashboard');

        } catch (err) {
            console.error('[App] Processing failed:', err);
            this.showToast(err.message || 'Processing failed. See console for details.', 'error');
            // Show error state inline instead of redirecting silently
            this._showProcessingError(err.message);
        }
    },

    _setProcessingStage(label, pct, elapsedSec = 0) {
        const bar     = document.getElementById('progress-bar-fill');
        const stageLbl = document.getElementById('progress-stage');
        const pctLbl  = document.getElementById('progress-pct');

        if (bar)      bar.style.width        = `${Math.min(pct, 100)}%`;
        if (stageLbl) {
            const timeStr = elapsedSec > 0 ? ` · ${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s elapsed` : '';
            stageLbl.textContent = `${label}${timeStr}`;
        }
        if (pctLbl)   pctLbl.textContent     = `${Math.round(pct)}%`;

        // Light up the matching step icon
        const steps = document.querySelectorAll('.processing-step');
        const activeIdx = Math.floor((pct / 100) * steps.length);
        steps.forEach((step, i) => {
            const icon = step.querySelector('.step-icon');
            if (i < activeIdx) {
                step.style.opacity = '1';
                if (icon) { icon.style.background = '#D1FAE5'; icon.style.color = '#10B981'; }
            } else if (i === activeIdx) {
                step.style.opacity = '1';
                if (icon) { icon.style.background = 'var(--brand-light)'; icon.style.color = 'var(--brand-primary)'; }
            }
        });
    },

    _showProcessingError(message) {
        const errDiv = document.getElementById('processing-error');
        if (errDiv) {
            errDiv.style.display = 'block';
            const msgEl = document.getElementById('processing-error-msg');
            if (msgEl) msgEl.textContent = message || 'An unknown error occurred.';
        }
    },

    // ─── View Renderers ───────────────────────────────────────────────
    async renderDashboard() {
        const data = API.getCurrentData();
        if (!data) { this.navigate('upload'); return; }
        this.routeContent.innerHTML = Components.DashboardView(data);
    },

    renderTranscriptView(searchQuery = '') {
        const data     = API.getCurrentData();
        const segments = data.transcript || [];
        const filtered = searchQuery
            ? segments.filter(s => (s.text || '').toLowerCase().includes(searchQuery.toLowerCase()))
            : segments;
        this.routeContent.innerHTML = Components.TranscriptView(filtered);
    },

    renderTopicsView() {
        const data = API.getCurrentData();
        this.routeContent.innerHTML = Components.TopicsView(data.topics || []);
    },

    renderSummaryView() {
        const data = API.getCurrentData();
        this.routeContent.innerHTML = Components.SummaryView(data);
    },

    renderChatView() {
        this.routeContent.innerHTML = Components.ChatView();
        Mascot.reactToChat();

        const form    = document.getElementById('chat-form');
        const input   = document.getElementById('chat-input');
        const history = document.getElementById('chat-history');

        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const msg = input.value.trim();
            if (!msg) return;

            // Append user bubble
            history.innerHTML += Components.ChatBubble('user', msg);
            input.value = '';
            this.renderIcons();
            history.scrollTop = history.scrollHeight;
            Mascot.setAnimation('think');

            // Typing indicator
            const typingId = `typing-${Date.now()}`;
            history.innerHTML += Components.ChatTyping(typingId);
            this.renderIcons();
            history.scrollTop = history.scrollHeight;

            try {
                const res = await API.chatPodcast(msg);
                document.getElementById(typingId)?.remove();
                Mascot.setAnimation('idle');

                // Build answer with timestamp badge if available
                let answerHtml = res.answer.replace(/\n/g, '<br>');
                if (res.timestamp !== null && res.timestamp !== undefined) {
                    answerHtml += `
                        <div style="margin-top:0.75rem;">
                            <span style="
                                display:inline-flex; align-items:center; gap:0.35rem;
                                background:var(--brand-light); color:var(--brand-primary);
                                font-size:0.8rem; font-weight:600; padding:0.3rem 0.7rem;
                                border-radius:999px; cursor:pointer;
                            " onclick="app.showToast('Timestamp: ${this.formatTime(res.timestamp)}', 'success')">
                                <i data-lucide="clock" width="12" height="12"></i>
                                ${this.formatTime(res.timestamp)}
                            </span>
                        </div>`;
                }

                history.innerHTML += Components.ChatBubble('bot', answerHtml);
                this.renderIcons();
                history.scrollTop = history.scrollHeight;

            } catch (err) {
                document.getElementById(typingId)?.remove();
                Mascot.setAnimation('idle');
                history.innerHTML += Components.ChatBubble('bot',
                    `<span style="color:#EF4444">Error: ${err.message}</span>`);
                history.scrollTop = history.scrollHeight;
            }
        });
    },

    async renderTranslationView() {
        this.routeContent.innerHTML = Components.TranslationView();
        const data = API.getCurrentData();

        // Fix the \\n\\n typo from the prototype — use real newlines
        const originalText = (data.transcript || []).map(s => s.text || '').join('\n\n');
        const origEl = document.getElementById('trans-orig');
        if (origEl) origEl.textContent = originalText;

        const select = document.getElementById('lang-select');
        if (!select) return;

        select.addEventListener('change', async (e) => {
            const lang   = e.target.value;
            const result = document.getElementById('trans-result');
            if (result) result.textContent = 'Translating via AI pipeline...';

            // Translate first 800 words to keep it fast (Argos is CPU-heavy)
            const words = originalText.split(' ');
            const chunk = words.slice(0, 800).join(' ') + (words.length > 800 ? '...' : '');

            try {
                const translated = await API.translateText(chunk, lang);
                if (result) result.textContent = translated;
                this.lastTranslatedText = translated;
                this.lastTranslatedLang = lang;
            } catch (err) {
                if (result) result.textContent = `Translation failed: ${err.message}`;
            }
        });
    },

    renderRomanizationView() {
        this.routeContent.innerHTML = Components.RomanizationView();
        const data = API.getCurrentData() || {};

        // 1. Populate original English podcast transcript on the left
        const originalText = (data.transcript || []).map(s => s.text || '').join('\n\n');
        const origEl = document.getElementById('rom-orig');
        if (origEl) {
            origEl.textContent = originalText || 'No podcast transcript loaded. Upload a podcast to begin.';
        }

        const select = document.getElementById('rom-lang-select');
        const result = document.getElementById('rom-result');
        if (!select || !result) return;

        const langNames = {
            'te': 'Telugu (Tanglish)',
            'hi': 'Hindi (Hinglish)',
            'kn': 'Kannada (Kanglish)',
            'ta': 'Tamil (Tanglish)',
            'ml': 'Malayalam',
            'gu': 'Gujarati',
            'bn': 'Bengali'
        };

        const updateRomanization = async (targetLang) => {
            const words = (originalText || 'Hey guys, welcome to the podcast and today we talk about open source.').split(' ');
            const chunk = words.slice(0, 450).join(' ') + (words.length > 450 ? '...' : '');

            result.textContent = `Explaining podcast in ${langNames[targetLang] || targetLang} (English letters)...`;

            try {
                const res = await API.explainRomanized(chunk, targetLang);
                if (result) {
                    result.textContent = res.romanized || 'No romanization produced.';
                }
            } catch (err) {
                if (result) {
                    result.textContent = `Romanization failed: ${err.message}`;
                }
            }
        };

        // Auto-run for default selected language (Telugu) on view load
        const initialLang = select.value || 'te';
        updateRomanization(initialLang);

        // When user changes dropdown language (Hindi, Kannada, Tamil, etc.)
        select.addEventListener('change', (e) => {
            updateRomanization(e.target.value);
        });
    },

    renderKeywordsView() {
        const data     = API.getCurrentData();
        const keywords = data.global_keywords || [];
        this.routeContent.innerHTML = Components.KeywordsView(keywords);
    },

    async renderLibraryView() {
        this.routeContent.innerHTML = Components.LibraryLoading();
        try {
            const library = await API.getLibrary();
            this.routeContent.innerHTML = Components.LibraryView(library);
        } catch (err) {
            this.routeContent.innerHTML = Components.LibraryView([]);
            this.showToast(`Could not load library: ${err.message}`, 'error');
        }
        this.renderIcons();
    },

    // ─── Utilities ────────────────────────────────────────────────────
    formatTime(sec) {
        if (sec === null || sec === undefined) return '0:00';
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    },

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copied to clipboard!', 'success');
        }).catch(() => {
            this.showToast('Could not copy to clipboard.', 'error');
        });
    },

    showExportModal() {
        if (this.exportModal) this.exportModal.classList.remove('hidden');
    },

    hideExportModal() {
        if (this.exportModal) this.exportModal.classList.add('hidden');
    },

    async download(format) {
        this.hideExportModal();
        if (!API.currentJobId) {
            this.showToast('No processed podcast found to export.', 'error');
            return;
        }
        this.showToast(`Generating ${format.toUpperCase()} export...`, 'success');
        try {
            await API.exportData(format);
            this.showToast(`${format.toUpperCase()} download started!`, 'success');
        } catch (err) {
            this.showToast(`Export failed: ${err.message}`, 'error');
        }
    },

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = 'toast';
        const color = type === 'success' ? '#10B981' : '#EF4444';
        const icon  = type === 'success' ? 'check-circle' : 'alert-circle';

        toast.innerHTML = `
            <i data-lucide="${icon}" width="18" height="18" style="color:${color};flex-shrink:0;"></i>
            <span>${message}</span>
        `;
        this.toastContainer.appendChild(toast);
        this.renderIcons();

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-8px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    },
};

// ─── Global CSS injected once ──────────────────────────────────────────────
document.head.insertAdjacentHTML('beforeend', `
<style>
    .spin-icon    { animation: spin 1s linear infinite; }
    .pulse-icon   { animation: pulseOpacity 1.5s infinite; }
    @keyframes spin         { 100% { transform: rotate(360deg); } }
    @keyframes pulseOpacity { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
    #dropzone.dragging {
        border-color: var(--brand-secondary) !important;
        background: var(--brand-light) !important;
    }
</style>
`);

// ─── Boot ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => app.init());
