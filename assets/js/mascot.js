/**
 * TALK2TOPICS — Mascot (Talkie) — Phase 1
 * Fixed: 'happy' animation was undefined (was causing silent JS error).
 * Added: autonomous blinking loop.
 */

const Mascot = {
    container: null,
    svg: null,
    bubble: null,
    hideTimeout: null,
    blinkInterval: null,

    init() {
        try {
            this.container = document.getElementById('talkie-mascot');
            this.svg       = document.getElementById('talkie-svg');
            this.bubble    = document.getElementById('talkie-bubble');
            this._startBlinking();
        } catch (e) {
            console.warn('Mascot init failed:', e);
        }
    },

    show() {
        if (!this.container) return;
        this.container.classList.remove('hidden');
        this.container.classList.add('fade-in');
    },

    hide() {
        if (!this.container) return;
        this.container.classList.add('hidden');
    },

    setAnimation(type) {
        if (!this.svg) return;
        this.svg.className = '';

        switch (type) {
            case 'idle':
            case 'happy':
                this.svg.classList.add('talkie-idle');
                this._setEyeColor('var(--robot-eye)');
                break;
            case 'wave':
                this.svg.classList.add('talkie-wave');
                this._setEyeColor('var(--robot-eye)');
                break;
            case 'think':
                this.svg.classList.add('talkie-idle');
                this._setEyeColor('#F59E0B'); // amber = thinking
                break;
            case 'success':
                this.svg.classList.add('talkie-wave');
                this._setEyeColor('#10B981'); // green = success
                break;
            default:
                this.svg.classList.add('talkie-idle');
                this._setEyeColor('var(--robot-eye)');
        }
    },

    say(text, duration = 4000) {
        if (!this.bubble) return;
        this.bubble.textContent = text;
        this.bubble.classList.remove('hidden');

        if (this.hideTimeout) clearTimeout(this.hideTimeout);

        if (duration > 0) {
            this.hideTimeout = setTimeout(() => {
                this.bubble.classList.add('hidden');
            }, duration);
        }
    },

    // ─── Contextual Reactions ─────────────────────────────────────
    reactToUpload() {
        this.show();
        this.setAnimation('idle');    // was 'happy' — now correctly 'idle'
        this.say("Hi! I'm Talkie. Drop an MP3, WAV, or M4A and let's go! 🎧", 6000);
    },

    reactToProcessing(stageName) {
        this.setAnimation('think');
        this.say(stageName, 0); // 0 = keep showing until next call
    },

    reactToSuccess() {
        this.setAnimation('success');
        this.say("All done! Your insights are ready. ✨", 5000);
        setTimeout(() => this.setAnimation('idle'), 2500);
    },

    reactToChat() {
        this.setAnimation('idle');
        this.say("Ask me anything about this podcast!", 5000);
    },

    // ─── Blink Loop ───────────────────────────────────────────────
    _startBlinking() {
        if (this.blinkInterval) clearInterval(this.blinkInterval);

        const blink = () => {
            const eyes = document.querySelectorAll('.talkie-eye');
            if (!eyes.length) return;

            // Squint: shrink r to near-zero
            eyes.forEach(eye => eye.setAttribute('r', '0.5'));
            setTimeout(() => {
                eyes.forEach(eye => eye.setAttribute('r', '4'));
            }, 130);
        };

        // Blink randomly every 3–6 seconds
        const scheduleNext = () => {
            const delay = 3000 + Math.random() * 3000;
            this.blinkInterval = setTimeout(() => {
                blink();
                scheduleNext();
            }, delay);
        };

        scheduleNext();
    },

    _setEyeColor(color) {
        document.querySelectorAll('.talkie-eye').forEach(eye => {
            eye.setAttribute('fill', color);
        });
    },
};

document.addEventListener('DOMContentLoaded', () => Mascot.init());
