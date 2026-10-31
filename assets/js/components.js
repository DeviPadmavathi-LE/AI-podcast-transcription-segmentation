/**
 * TALK2TOPICS — UI Components (components.js)
 * Generates HTML strings for each view.
 * Phase 1: All components wired to real backend data — no mocks.
 *
 * Data contract (from orchestrator.py):
 *   transcript    → [{ start, end, text }]
 *   topics        → [{ id, start, end, text, title, summary, keywords[], sentiment{label,score}, translation, romanization }]
 *   global_keywords → string[]
 *   global_sentiment → { label, score }
 *   executive_summary → string
 *   metadata      → { duration_str, word_count, topic_count, reading_time, processed_at }
 *   intelligence_score → number
 *   speakers      → [{ name, percentage, words }]
 */

const Components = {

    // ─────────────────────────────────────────────────────────────────
    // 1. Upload View
    // ─────────────────────────────────────────────────────────────────
    UploadView() {
        return `
            <div class="upload-container fade-in">
                <div class="upload-badge">
                    <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-right:6px;box-shadow:0 0 8px var(--accent-glow);"></span>
                    AI Podcast Intelligence &amp; Chapter Discovery
                </div>

                <h1 class="upload-title">
                    TALK2TOPICS <span class="font-editorial">Intelligence</span>
                </h1>

                <p class="upload-subtitle">
                    Transform any podcast or discussion into structured topic chapters, crisp executive summaries, keyword intelligence, and semantic search.
                </p>

                <div id="dropzone" class="dropzone">
                    <i data-lucide="upload-cloud" class="dropzone-icon"></i>
                    <h3 class="dropzone-heading">Drop your audio file here</h3>
                    <p class="dropzone-sub">Supports MP3, WAV, M4A · Up to 200 MB</p>
                    <input type="file" id="fileInput" accept=".mp3,.wav,.m4a"
                           style="position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;">
                </div>

                <div class="upload-features">
                    ${['Whisper Transcription', 'Semantic Topics', 'Hierarchical Summary', 'Keyword Cloud',
                       'RAG Chat', 'Translation', 'Romanization', 'Multi-Format Export'].map(f => `
                        <div class="feature-chip">
                            <i data-lucide="check" width="13" height="13" style="color:var(--accent);"></i> ${f}
                        </div>`).join('')}
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 2. Processing View
    // ─────────────────────────────────────────────────────────────────
    ProcessingView(filename = 'audio file', sizeBytes = 0) {
        const sizeMB = sizeBytes ? `${(sizeBytes / 1024 / 1024).toFixed(1)} MB` : '';

        const steps = [
            { icon: 'upload',        label: 'Upload' },
            { icon: 'cpu',           label: 'Whisper AI' },
            { icon: 'git-branch',    label: 'Segmentation' },
            { icon: 'tag',           label: 'Keywords' },
            { icon: 'align-left',    label: 'Summary' },
            { icon: 'activity',      label: 'Sentiment' },
            { icon: 'globe',         label: 'Translation' },
            { icon: 'database',      label: 'Saving' },
        ];

        const stepsHtml = steps.map((s, i) => `
            <div class="processing-step" id="step-${i}">
                <div class="step-icon">
                    <i data-lucide="${s.icon}" width="14" height="14"></i>
                </div>
                <span>${s.label}</span>
            </div>
        `).join('');

        return `
            <div class="processing-container fade-in">
                <div class="processing-card">

                    <div class="processing-file-info">
                        <i data-lucide="file-audio" width="20" height="20"
                           style="color:var(--brand-primary);"></i>
                        <span style="font-weight:500;">${this._escapeHtml(filename)}</span>
                        ${sizeMB ? `<span style="color:var(--text-tertiary);font-size:0.85rem;">${sizeMB}</span>` : ''}
                    </div>

                    <h2 class="processing-title">Analyzing Podcast with AI...</h2>
                    <p class="processing-sub">Running local Whisper ASR &amp; NLP models (~2–3 minutes for a 10-minute podcast).</p>

                    <div class="processing-bar-wrap">
                        <div class="processing-bar">
                            <div id="progress-bar-fill" class="processing-bar-fill"></div>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-top:0.5rem;">
                            <span id="progress-stage" style="font-size:0.875rem;color:var(--text-secondary);">
                                Starting pipeline...
                            </span>
                            <span id="progress-pct" style="font-size:0.875rem;font-weight:600;color:var(--brand-primary);">
                                0%
                            </span>
                        </div>
                    </div>

                    <div class="processing-steps">
                        ${stepsHtml}
                    </div>

                    <div id="processing-error" style="display:none;margin-top:1.5rem;
                         padding:1rem;background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;color:#DC2626;">
                        <strong>Pipeline Error:</strong>
                        <div id="processing-error-msg" style="margin-top:0.5rem;font-size:0.9rem;"></div>
                        <button onclick="app.navigate('upload')" style="margin-top:1rem;padding:0.5rem 1rem;
                                background:#DC2626;color:white;border:none;border-radius:6px;cursor:pointer;">
                            Try Again
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 3. Dashboard View
    // ─────────────────────────────────────────────────────────────────
    DashboardView(data) {
        if (!data) return `<p style="color:var(--text-secondary);">No data available.</p>`;

        const meta      = data.metadata || {};
        const sentiment = data.global_sentiment || { label: 'UNKNOWN', score: 0.5 };
        const score     = data.intelligence_score || 0;
        const keywords  = data.global_keywords || [];
        const topics    = data.topics || [];
        const transcript = data.transcript || [];

        const sentimentColor = {
            POSITIVE: '#10B981',
            NEGATIVE: '#EF4444',
        }[sentiment.label] || '#64748B';

        const sentimentEmoji = { POSITIVE: '😊', NEGATIVE: '😔', NEUTRAL: '😐' }[sentiment.label] || '🤔';

        const stats = [
            { label: 'Duration',    value: meta.duration_str || '—',         icon: 'clock' },
            { label: 'Words',       value: (meta.word_count || 0).toLocaleString(), icon: 'type' },
            { label: 'Segments',    value: transcript.length,                 icon: 'list' },
            { label: 'Topics',      value: topics.length,                     icon: 'layers' },
            { label: 'Keywords',    value: keywords.length,                   icon: 'tag' },
            { label: 'Reading',     value: meta.reading_time || '—',          icon: 'book-open' },
        ];

        const statsHtml = stats.map(s => `
            <div class="stat-card">
                <div class="stat-icon">
                    <i data-lucide="${s.icon}" width="18" height="18"></i>
                </div>
                <div class="stat-value">${s.value}</div>
                <div class="stat-label">${s.label}</div>
            </div>
        `).join('');

        const cards = [
            { icon: 'file-text',    label: 'Transcript',      sub: `${transcript.length} segments`,        route: 'transcript', color: '#8B5CF6' },
            { icon: 'layers',       label: 'Topics',           sub: `${topics.length} semantic clusters`,   route: 'topics',     color: '#3B82F6' },
            { icon: 'zap',          label: 'AI Summary',       sub: 'Executive overview',                   route: 'summary',    color: '#F59E0B' },
            { icon: 'tag',          label: 'Keywords',         sub: keywords.slice(0, 3).join(', ') || '—', route: 'keywords',   color: '#6366F1' },
            { icon: 'message-square', label: 'AI Chat',        sub: 'Ask questions about the podcast',      route: 'chat',       color: '#10B981', highlight: true },
            { icon: 'globe',        label: 'Translation',      sub: 'Argos Translate (en → es +)',           route: 'translation', color: '#06B6D4' },
            { icon: 'type',         label: 'Romanization',     sub: 'Indic script → IAST',                  route: 'romanization', color: '#EC4899' },
            { icon: 'library',      label: 'Library',          sub: 'Browse past podcasts',                  route: 'library',   color: '#84CC16' },
        ];

        const cardsHtml = cards.map(c => `
            <div class="dashboard-card ${c.highlight ? 'dashboard-card-highlight' : ''}"
                 onclick="app.navigate('${c.route}')" style="cursor:pointer;">
                <div class="dashboard-card-icon" style="color:${c.highlight ? 'white' : c.color};">
                    <i data-lucide="${c.icon}"></i>
                </div>
                <h3 class="dashboard-card-title">${c.label}</h3>
                <p class="dashboard-card-sub">${c.sub}</p>
            </div>
        `).join('');

        return `
            <div class="fade-in">
                <!-- Header -->
                <div class="dashboard-header">
                    <div>
                        <h2 class="dashboard-title">Podcast Dashboard</h2>
                        <p style="color:var(--text-secondary);margin-top:0.25rem;">
                            ${data.original_filename || 'Processed Audio'} · ${meta.processed_at ? new Date(meta.processed_at).toLocaleString() : ''}
                        </p>
                    </div>
                    <div class="intelligence-score">
                        <div class="intelligence-score-value">${score}</div>
                        <div class="intelligence-score-label">Intelligence Score</div>
                    </div>
                </div>

                <!-- Stats Bar -->
                <div class="stats-row">
                    ${statsHtml}
                </div>

                <!-- Sentiment -->
                <div class="card sentiment-card">
                    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
                        <span style="font-size:2rem;">${sentimentEmoji}</span>
                        <div>
                            <div style="font-weight:600;font-size:1.1rem;">Overall Sentiment</div>
                            <div style="color:${sentimentColor};font-weight:700;font-size:1.4rem;">
                                ${sentiment.label}
                                <span style="color:var(--text-tertiary);font-size:0.9rem;font-weight:400;">
                                    (${Math.round(sentiment.score * 100)}% confidence)
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Navigation Cards -->
                <div class="dashboard-grid">
                    ${cardsHtml}
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 4. Transcript View
    // ─────────────────────────────────────────────────────────────────
    TranscriptView(segments) {
        if (!segments || !segments.length) {
            return `<div class="fade-in"><p style="color:var(--text-secondary);">No transcript segments available.</p></div>`;
        }

        const segHtml = segments.map((seg, i) => {
            const timeRange = `${app.formatTime(seg.start)} – ${app.formatTime(seg.end)}`;
            const text = this._escapeHtml(seg.text || '');
            return `
                <div class="card transcript-card fade-in">
                    <div class="transcript-header">
                        <div class="transcript-time">
                            <i data-lucide="clock" width="14" height="14"></i> ${timeRange}
                        </div>
                        <button class="icon-btn" title="Copy segment"
                                onclick="app.copyToClipboard(${JSON.stringify(seg.text || '')})">
                            <i data-lucide="copy" width="14" height="14"></i>
                        </button>
                    </div>
                    <div class="transcript-text">${text}</div>
                </div>
            `;
        }).join('');

        return `
            <div class="fade-in" style="max-width:800px;margin:0 auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
                    <h2>Full Transcript</h2>
                    <span style="color:var(--text-tertiary);font-size:0.875rem;">
                        ${segments.length} segment${segments.length !== 1 ? 's' : ''}
                    </span>
                </div>
                ${segHtml}
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 5. Topics View (dedicated — was falling back to Dashboard)
    // ─────────────────────────────────────────────────────────────────
    TopicsView(topics) {
        if (!topics || !topics.length) {
            return `<div class="fade-in"><p style="color:var(--text-secondary);">No topics were detected. The audio may be too short.</p></div>`;
        }

        const sentimentColor = (label) => ({ POSITIVE: '#10B981', NEGATIVE: '#EF4444' }[label] || '#64748B');

        const topicsHtml = topics.map((t, i) => {
            const kws = (t.keywords || []).map(k =>
                `<span class="keyword-chip">${this._escapeHtml(k)}</span>`
            ).join('');

            const sent = t.sentiment || { label: 'NEUTRAL', score: 0.5 };
            const timeRange = `${app.formatTime(t.start)} – ${app.formatTime(t.end)}`;

            return `
                <div class="card topic-card fade-in">
                    <div class="topic-header">
                        <div class="topic-number">${i + 1}</div>
                        <div style="flex:1;">
                            <h3 class="topic-title">${this._escapeHtml(t.title || `Topic ${i + 1}`)}</h3>
                            <div class="topic-meta">
                                <span><i data-lucide="clock" width="13" height="13"></i> ${timeRange}</span>
                                <span style="color:${sentimentColor(sent.label)};font-weight:600;">
                                    ${sent.label} (${Math.round(sent.score * 100)}%)
                                </span>
                            </div>
                        </div>
                    </div>

                    ${kws ? `<div class="keyword-row">${kws}</div>` : ''}

                    ${t.summary ? `
                        <div class="topic-summary">
                            <strong>Summary:</strong> ${this._escapeHtml(t.summary)}
                        </div>` : ''}

                    <details class="topic-text-details">
                        <summary style="cursor:pointer;color:var(--brand-primary);font-size:0.875rem;font-weight:500;">
                            View transcript text
                        </summary>
                        <div class="topic-text">${this._escapeHtml(t.text || '')}</div>
                    </details>
                </div>
            `;
        }).join('');

        return `
            <div class="fade-in">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
                    <h2>Topic Explorer</h2>
                    <span style="color:var(--text-tertiary);font-size:0.875rem;">
                        ${topics.length} topic${topics.length !== 1 ? 's' : ''} detected
                    </span>
                </div>
                <div style="display:flex;flex-direction:column;gap:1.25rem;">
                    ${topicsHtml}
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 6. AI Summary View (dedicated — was falling back to Dashboard)
    // ─────────────────────────────────────────────────────────────────
    SummaryView(data) {
        if (!data) return `<p>No data.</p>`;

        const meta     = data.metadata || {};
        const topics   = data.topics || [];
        const keywords = data.global_keywords || [];
        const sentiment = data.global_sentiment || { label: 'NEUTRAL', score: 0.5 };

        const topicSummariesHtml = topics.map((t, i) => `
            <div style="margin-bottom:1.25rem;padding-bottom:1.25rem;
                        border-bottom:1px solid var(--border-color);">
                <div style="font-weight:600;color:var(--brand-primary);margin-bottom:0.35rem;">
                    ${i + 1}. ${this._escapeHtml(t.title || `Topic ${i + 1}`)}
                    <span style="font-size:0.8rem;color:var(--text-tertiary);font-weight:400;margin-left:0.5rem;">
                        ${app.formatTime(t.start)} – ${app.formatTime(t.end)}
                    </span>
                </div>
                <div style="color:var(--text-secondary);font-size:0.9375rem;line-height:1.6;">
                    ${this._escapeHtml(t.summary || 'No summary for this topic.')}
                </div>
            </div>
        `).join('');

        return `
            <div class="fade-in" style="max-width:800px;margin:0 auto;">
                <h2 style="margin-bottom:1.5rem;">AI Summary</h2>

                <!-- Executive Summary -->
                <div class="card" style="margin-bottom:1.5rem;">
                    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;color:var(--brand-primary);">
                        <i data-lucide="zap"></i>
                        <h3>Executive Summary</h3>
                    </div>
                    <p style="color:var(--text-secondary);line-height:1.7;font-size:1rem;">
                        ${this._escapeHtml(data.executive_summary || 'No summary available.')}
                    </p>
                </div>

                <!-- Quick Stats -->
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem;">
                    <div class="card" style="text-align:center;">
                        <div style="font-size:1.75rem;font-weight:700;color:var(--brand-primary);">
                            ${topics.length}
                        </div>
                        <div style="font-size:0.85rem;color:var(--text-secondary);">Topics</div>
                    </div>
                    <div class="card" style="text-align:center;">
                        <div style="font-size:1.75rem;font-weight:700;color:#8B5CF6;">
                            ${(meta.word_count || 0).toLocaleString()}
                        </div>
                        <div style="font-size:0.85rem;color:var(--text-secondary);">Words</div>
                    </div>
                    <div class="card" style="text-align:center;">
                        <div style="font-size:1.75rem;font-weight:700;color:#10B981;">
                            ${meta.reading_time || '—'}
                        </div>
                        <div style="font-size:0.85rem;color:var(--text-secondary);">Reading Time</div>
                    </div>
                </div>

                <!-- Top Keywords -->
                ${keywords.length ? `
                    <div class="card" style="margin-bottom:1.5rem;">
                        <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;color:#6366F1;">
                            <i data-lucide="tag"></i>
                            <h3>Top Keywords</h3>
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">
                            ${keywords.map(k => `<span class="keyword-chip">${this._escapeHtml(k)}</span>`).join('')}
                        </div>
                    </div>` : ''}

                <!-- Per-Topic Summaries -->
                ${topics.length ? `
                    <div class="card">
                        <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1.25rem;color:#F59E0B;">
                            <i data-lucide="layers"></i>
                            <h3>Topic Summaries</h3>
                        </div>
                        ${topicSummariesHtml}
                    </div>` : ''}
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 7. Chat View
    // ─────────────────────────────────────────────────────────────────
    ChatView() {
        return `
            <div class="fade-in" style="display:flex;flex-direction:column;height:calc(100vh - 140px);max-width:800px;margin:0 auto;">
                <h2 style="margin-bottom:1rem;">AI Chat</h2>
                <div class="card" style="flex:1;display:flex;flex-direction:column;overflow:hidden;padding:0;">
                    <div id="chat-history" style="flex:1;padding:1.5rem;overflow-y:auto;display:flex;flex-direction:column;gap:1rem;">
                        ${this.ChatBubble('bot', "Hi! I'm Talkie, your podcast AI. Ask me to summarize a topic, find a specific quote, or explain something from the podcast.")}
                    </div>
                    <div style="padding:1rem 1.5rem;border-top:1px solid var(--border-color);">
                        <form id="chat-form" style="display:flex;gap:0.75rem;align-items:center;">
                            <input type="text" id="chat-input"
                                   placeholder="Ask Talkie anything about this podcast..."
                                   style="flex:1;padding:0.875rem 1.25rem;border:1.5px solid var(--border-strong);
                                          border-radius:999px;background:var(--bg-card);color:var(--text-primary);
                                          font-family:var(--font-sans);font-size:0.95rem;font-weight:500;
                                          outline:none;caret-color:var(--brand-primary);"
                                   required autocomplete="off">
                            <button type="submit" id="chat-send"
                                    style="background:var(--brand-primary);color:white;border:none;
                                           width:44px;height:44px;border-radius:50%;cursor:pointer;
                                           display:flex;align-items:center;justify-content:center;
                                           flex-shrink:0;transition:all 0.2s;">
                                <i data-lucide="send" width="18" height="18"></i>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;
    },

    ChatBubble(role, html) {
        const isUser = role === 'user';
        return `
            <div style="display:flex;gap:0.75rem;${isUser ? 'flex-direction:row-reverse;' : ''}animation:slideUp 0.25s;">
                <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                            background:${isUser ? 'var(--brand-primary)' : 'var(--brand-light)'};
                            color:${isUser ? 'white' : 'var(--brand-primary)'};
                            display:flex;align-items:center;justify-content:center;">
                    <i data-lucide="${isUser ? 'user' : 'bot'}" width="18" height="18"></i>
                </div>
                <div style="background:${isUser ? 'var(--brand-primary)' : 'var(--bg-hover)'};
                            color:${isUser ? 'white' : 'var(--text-primary)'};
                            padding:0.875rem 1.25rem;border-radius:${isUser ? '1rem 4px 1rem 1rem' : '4px 1rem 1rem 1rem'};
                            max-width:80%;line-height:1.6;font-size:0.9375rem;">
                    ${html}
                </div>
            </div>
        `;
    },

    ChatTyping(id) {
        return `
            <div id="${id}" style="display:flex;gap:0.75rem;animation:slideUp 0.25s;">
                <div style="width:34px;height:34px;border-radius:50%;background:var(--brand-light);
                            color:var(--brand-primary);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <i data-lucide="bot" width="18" height="18"></i>
                </div>
                <div style="background:var(--bg-hover);padding:1rem 1.25rem;border-radius:4px 1rem 1rem 1rem;
                            display:flex;gap:0.35rem;align-items:center;">
                    <span style="width:7px;height:7px;border-radius:50%;background:var(--brand-primary);animation:pulseOpacity 1.2s 0s infinite;display:inline-block;"></span>
                    <span style="width:7px;height:7px;border-radius:50%;background:var(--brand-primary);animation:pulseOpacity 1.2s 0.2s infinite;display:inline-block;"></span>
                    <span style="width:7px;height:7px;border-radius:50%;background:var(--brand-primary);animation:pulseOpacity 1.2s 0.4s infinite;display:inline-block;"></span>
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 8. Translation View
    // ─────────────────────────────────────────────────────────────────
    TranslationView() {
        const languages = [
            { code: 'es', label: 'Spanish' },
            { code: 'fr', label: 'French' },
            { code: 'de', label: 'German' },
            { code: 'pt', label: 'Portuguese' },
            { code: 'it', label: 'Italian' },
            { code: 'hi', label: 'Hindi' },
            { code: 'te', label: 'Telugu' },
            { code: 'ta', label: 'Tamil' },
            { code: 'kn', label: 'Kannada' },
        ];

        return `
            <div class="fade-in" style="max-width:1000px;margin:0 auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
                    <h2>Translation Center</h2>
                    <select id="lang-select" style="padding:0.625rem 1rem;border-radius:var(--radius-sm);
                            border:1px solid var(--border-color);font-family:var(--font-sans);font-size:0.9375rem;
                            background:var(--bg-surface);">
                        <option value="">— Select language —</option>
                        ${languages.map(l => `<option value="${l.code}">${l.label}</option>`).join('')}
                    </select>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">
                    <!-- Left: Original Podcast (English) -->
                    <div class="card" style="height:60vh;display:flex;flex-direction:column;overflow:hidden;padding:0;">
                        <div style="padding:1rem 1.25rem;border-bottom:1px solid var(--border-color);background:var(--bg-surface);flex-shrink:0;">
                            <h3 style="margin:0;font-size:1rem;color:var(--text-secondary);display:flex;justify-content:space-between;align-items:center;">
                                <span>Original (English)</span>
                                <span style="font-size:0.75rem;font-weight:normal;color:var(--text-tertiary);">Podcast Transcript</span>
                            </h3>
                        </div>
                        <div style="flex:1;overflow-y:auto;padding:1.25rem;background:var(--bg-card);">
                            <div id="trans-orig" style="color:var(--text-primary);white-space:pre-wrap;line-height:1.75;font-size:0.9375rem;">
                                Loading transcript...
                            </div>
                        </div>
                    </div>

                    <!-- Right: Translated Output -->
                    <div class="card" style="height:60vh;display:flex;flex-direction:column;overflow:hidden;padding:0;border-color:var(--border-strong);">
                        <div style="padding:1rem 1.25rem;border-bottom:1px solid var(--border-color);background:var(--bg-surface);flex-shrink:0;display:flex;justify-content:space-between;align-items:center;">
                            <h3 style="margin:0;font-size:1rem;color:var(--brand-primary);font-weight:700;">
                                Translated
                            </h3>
                            <button class="icon-btn"
                                    onclick="app.copyToClipboard(document.getElementById('trans-result').textContent)"
                                    title="Copy Translation">
                                <i data-lucide="copy" width="15" height="15"></i>
                            </button>
                        </div>
                        <div style="flex:1;overflow-y:auto;padding:1.25rem;background:var(--bg-card);">
                            <div id="trans-result" style="white-space:pre-wrap;line-height:1.75;font-size:0.9375rem;font-weight:500;color:var(--text-primary);">
                                Select a language to begin translation...
                            </div>
                        </div>
                    </div>
                </div>
                <p style="margin-top:0.75rem;color:var(--text-tertiary);font-size:0.8125rem;">
                    Powered by Argos Translate (local, offline). First 800 words translated for performance.
                </p>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 9. Romanization View
    // ─────────────────────────────────────────────────────────────────
    RomanizationView() {
        return `
            <div class="fade-in" style="max-width:1050px;margin:0 auto;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;">
                    <div>
                        <h2 style="margin-bottom:0.25rem;">Romanization Studio</h2>
                        <p style="font-size:0.875rem;color:var(--text-secondary);margin:0;">
                            Explains your podcast in native Indian languages using English letters (Tanglish, Hinglish, Kanglish).
                        </p>
                    </div>
                    <div style="font-size:0.8125rem;color:var(--text-secondary);
                                background:var(--bg-hover);padding:0.4rem 0.9rem;border-radius:999px;">
                        Powered by Aksharamukha · IAST & Phonetic
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">
                    <!-- Left: Original Podcast (English) -->
                    <div class="card" style="height:60vh;display:flex;flex-direction:column;overflow:hidden;padding:0;">
                        <div style="padding:1rem 1.25rem;border-bottom:1px solid var(--border-color);background:var(--bg-surface);flex-shrink:0;">
                            <h3 style="margin:0;font-size:1rem;color:var(--text-secondary);display:flex;justify-content:space-between;align-items:center;">
                                <span>Original (English)</span>
                                <span style="font-size:0.75rem;font-weight:normal;color:var(--text-tertiary);">Podcast Transcript</span>
                            </h3>
                        </div>
                        <div style="flex:1;overflow-y:auto;padding:1.25rem;background:var(--bg-card);">
                            <div id="rom-orig" style="color:var(--text-primary);white-space:pre-wrap;line-height:1.75;font-size:0.9375rem;">
                                Loading transcript...
                            </div>
                        </div>
                    </div>

                    <!-- Right: Romanized Explanation (English Letters) with Language Dropdown -->
                    <div class="card" style="height:60vh;display:flex;flex-direction:column;overflow:hidden;padding:0;border-color:var(--border-strong);">
                        <div style="padding:0.875rem 1.25rem;border-bottom:1px solid var(--border-color);background:var(--bg-surface);flex-shrink:0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                            <div style="display:flex;align-items:center;gap:0.5rem;">
                                <h3 style="color:var(--brand-primary);margin:0;font-size:1rem;font-weight:700;">Romanized</h3>
                                <span style="font-size:0.75rem;background:var(--tag-bg);padding:0.2rem 0.5rem;border-radius:4px;color:var(--brand-primary);font-weight:600;">English Letters</span>
                            </div>

                            <div style="display:flex;align-items:center;gap:0.5rem;">
                                <select id="rom-lang-select" style="padding:0.45rem 0.75rem;border-radius:var(--radius-sm);
                                        border:1px solid var(--border-color);font-family:var(--font-sans);font-size:0.875rem;
                                        background:var(--bg-surface);color:var(--text-primary);cursor:pointer;font-weight:600;">
                                    <option value="te" selected>Telugu (Tanglish)</option>
                                    <option value="hi">Hindi (Hinglish)</option>
                                    <option value="kn">Kannada (Kanglish)</option>
                                    <option value="ta">Tamil (Tanglish)</option>
                                    <option value="ml">Malayalam</option>
                                    <option value="gu">Gujarati</option>
                                    <option value="bn">Bengali</option>
                                </select>
                                <button class="icon-btn"
                                        onclick="app.copyToClipboard(document.getElementById('rom-result').textContent)"
                                        title="Copy Romanized explanation">
                                    <i data-lucide="copy" width="15" height="15"></i>
                                </button>
                            </div>
                        </div>

                        <div style="flex:1;overflow-y:auto;padding:1.25rem;background:var(--bg-card);">
                            <div id="rom-result" style="white-space:pre-wrap;line-height:1.75;font-weight:500;
                                                        font-size:0.9375rem;color:var(--text-primary);">
                                Select a language to explain in English letters...
                            </div>
                        </div>
                    </div>
                </div>

                <p style="margin-top:0.75rem;color:var(--text-tertiary);font-size:0.8125rem;">
                    💡 Explains your podcast in the chosen Indian language, written phonetically in the English alphabet (Tanglish / Hinglish / Kanglish).
                </p>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 10. Keywords View
    // Fixed: backend returns string[], not {text, weight} objects
    // ─────────────────────────────────────────────────────────────────
    KeywordsView(keywords) {
        if (!keywords || !keywords.length) {
            return `
                <div class="fade-in">
                    <h2 style="margin-bottom:1.5rem;">Keywords & Analytics</h2>
                    <div class="card" style="text-align:center;padding:3rem;">
                        <p style="color:var(--text-secondary);">No keywords were extracted from this podcast.</p>
                    </div>
                </div>
            `;
        }

        // keywords is a plain string[] — weight is based on index position (first = most important)
        const cloudHtml = keywords.map((kw, i) => {
            const weight = Math.max(1 - (i / keywords.length), 0.2);
            const size   = (0.9 + weight * 0.9).toFixed(2);  // 0.9rem – 1.8rem
            const opacity = (0.5 + weight * 0.5).toFixed(2);
            const colors = ['var(--brand-primary)', '#8B5CF6', '#10B981', '#F59E0B', '#EC4899', '#06B6D4'];
            const color  = colors[i % colors.length];

            return `
                <span class="kw-cloud-word"
                      style="font-size:${size}rem;opacity:${opacity};color:${color};"
                      onclick="app.showToast('Keyword: ${this._escapeHtml(kw)}', 'success')">
                    ${this._escapeHtml(kw)}
                </span>
            `;
        }).join('');

        const listHtml = keywords.map((kw, i) => `
            <div class="kw-list-item">
                <span class="kw-list-rank">${i + 1}</span>
                <span class="kw-list-word">${this._escapeHtml(kw)}</span>
                <div class="kw-list-bar">
                    <div class="kw-list-bar-fill"
                         style="width:${Math.round((1 - i / keywords.length) * 100)}%"></div>
                </div>
            </div>
        `).join('');

        return `
            <div class="fade-in" style="max-width:900px;margin:0 auto;">
                <h2 style="margin-bottom:1.5rem;">Keywords & Analytics</h2>

                <!-- Word Cloud -->
                <div class="card" style="text-align:center;padding:3rem 2rem;margin-bottom:1.5rem;min-height:200px;">
                    <div style="display:flex;flex-wrap:wrap;gap:1rem;justify-content:center;align-items:center;">
                        ${cloudHtml}
                    </div>
                </div>

                <!-- Ranked List -->
                <div class="card">
                    <h3 style="margin-bottom:1rem;color:var(--text-secondary);">Keyword Ranking</h3>
                    <div style="display:flex;flex-direction:column;gap:0.75rem;">
                        ${listHtml}
                    </div>
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // 11. Library View
    // ─────────────────────────────────────────────────────────────────
    LibraryLoading() {
        return `
            <div class="fade-in">
                <h2 style="margin-bottom:1.5rem;">Podcast Library</h2>
                <p style="color:var(--text-secondary);">Loading library...</p>
            </div>
        `;
    },

    LibraryView(entries) {
        if (!entries || !entries.length) {
            return `
                <div class="fade-in">
                    <h2 style="margin-bottom:1.5rem;">Podcast Library</h2>
                    <div class="card" style="text-align:center;padding:3rem;">
                        <i data-lucide="inbox" width="48" height="48"
                           style="color:var(--text-tertiary);margin-bottom:1rem;"></i>
                        <p style="color:var(--text-secondary);">
                            No processed podcasts yet. Upload your first podcast to get started!
                        </p>
                        <button onclick="app.navigate('upload')"
                                style="margin-top:1.5rem;padding:0.75rem 1.5rem;
                                       background:var(--brand-primary);color:white;border:none;
                                       border-radius:var(--radius-md);cursor:pointer;font-weight:500;">
                            Upload a Podcast
                        </button>
                    </div>
                </div>
            `;
        }

        const cardsHtml = entries.map(e => {
            const duration = e.duration ? `${Math.floor(e.duration / 60)}m ${Math.floor(e.duration % 60)}s` : 'N/A';
            const processed = e.processed_at ? new Date(e.processed_at).toLocaleDateString() : 'Unknown';

            return `
                <div class="card" style="cursor:pointer;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;">
                        <div style="background:var(--brand-light);padding:0.6rem;border-radius:var(--radius-sm);color:var(--brand-primary);">
                            <i data-lucide="mic" width="22" height="22"></i>
                        </div>
                        <span style="font-size:0.75rem;background:#D1FAE5;color:#065F46;
                                     padding:0.25rem 0.6rem;border-radius:4px;font-weight:600;">
                            Processed
                        </span>
                    </div>
                    <h3 style="font-size:1rem;margin-bottom:0.5rem;
                               white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                        title="${this._escapeHtml(e.filename || e.job_id)}">
                        ${this._escapeHtml(e.filename || e.job_id)}
                    </h3>
                    <div style="font-size:0.8125rem;color:var(--text-tertiary);display:flex;gap:1rem;flex-wrap:wrap;">
                        <span><i data-lucide="clock" width="12" height="12" style="vertical-align:middle;"></i> ${duration}</span>
                        <span><i data-lucide="layers" width="12" height="12" style="vertical-align:middle;"></i> ${e.topic_count} topics</span>
                        <span><i data-lucide="calendar" width="12" height="12" style="vertical-align:middle;"></i> ${processed}</span>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="fade-in">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
                    <h2>Podcast Library</h2>
                    <span style="color:var(--text-tertiary);font-size:0.875rem;">
                        ${entries.length} podcast${entries.length !== 1 ? 's' : ''} processed
                    </span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.25rem;">
                    ${cardsHtml}
                </div>
            </div>
        `;
    },

    // ─────────────────────────────────────────────────────────────────
    // Shared Utilities
    // ─────────────────────────────────────────────────────────────────
    _escapeHtml(str) {
        if (typeof str !== 'string') return String(str || '');
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
};
