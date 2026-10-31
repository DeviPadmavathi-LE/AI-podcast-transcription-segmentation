"""
TALK2TOPICS — Flask Backend
Async job-based architecture: upload returns immediately with a job_id.
Poll /status/<job_id> for real-time progress updates.
"""

import os
import uuid
import traceback
import logging
import threading
import time
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB max

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a'}

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('talk2topics')

# ─────────────────────────────────────────────
# In-memory Job Store
# ─────────────────────────────────────────────
# Each job: { stage, progress, done, error, data }
jobs = {}
jobs_lock = threading.Lock()

def get_job(job_id):
    with jobs_lock:
        return jobs.get(job_id, None)

def update_job(job_id, **kwargs):
    with jobs_lock:
        if job_id not in jobs:
            jobs[job_id] = {}
        jobs[job_id].update(kwargs)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Single-pipeline execution lock to prevent PyTorch thread contention and attention hook collisions
pipeline_execution_lock = threading.Lock()


def run_pipeline_async(filepath, job_id):
    """Runs the full AI pipeline in a background thread."""
    with pipeline_execution_lock:
        log.info(f"[{job_id}] ▶ Background pipeline started for: {filepath}")
        start_epoch = time.time()
        update_job(job_id, start_time=start_epoch, elapsed_sec=0)

        def progress_callback(stage: str, pct: int):
            now = time.time()
            elapsed = int(now - start_epoch)
            update_job(job_id, stage=stage, progress=pct, elapsed_sec=elapsed)
            log.info(f"[{job_id}] [{pct:3d}%] ({elapsed}s) {stage}")

        try:
            from pipeline.orchestrator import process_audio
            result = process_audio(filepath, job_id, progress_callback=progress_callback)
            elapsed = int(time.time() - start_epoch)
            update_job(job_id, stage='Complete', progress=100, done=True, data=result['data'], elapsed_sec=elapsed)
            log.info(f"[{job_id}] ✔ Pipeline complete in {elapsed}s.")

        except Exception as e:
            error_msg = str(e)
            log.error(f"[{job_id}] ✘ Pipeline failed: {error_msg}")
            traceback.print_exc()
            update_job(job_id, stage='Error', progress=0, done=True, error=error_msg)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
@app.route('/index.html')
def serve_index():
    return send_file('index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Accepts an audio file, saves it, and starts the AI pipeline.
    If an existing job is actively running, attaches to it to prevent thrashing.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        log.warning(f"Rejected upload: invalid extension '{file.filename}'")
        return jsonify({"error": "Invalid file type. Only MP3, WAV, and M4A are supported."}), 400

    # If another job is currently active, re-attach to it
    with jobs_lock:
        active = [jid for jid, j in jobs.items() if not j.get('done', False) and j.get('stage') not in ('Error', 'Complete')]
        if active:
            active_job_id = active[0]
            log.info(f"Upload received while job '{active_job_id}' is active. Re-attaching client to active job.")
            return jsonify({
                "job_id": active_job_id,
                "status": "processing",
                "message": "A podcast is currently being processed. Re-attached to active job."
            }), 200

    # Save file with UUID name to avoid collisions
    job_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    safe_name = f"{job_id}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    file.save(filepath)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    log.info(f"[{job_id}] ✔ File saved: {safe_name} ({file_size_mb:.1f} MB)")

    # Register the job immediately so /status returns something right away
    update_job(job_id, stage='Queued', progress=0, done=False, error=None, data=None, elapsed_sec=0)

    # Kick off the background thread
    thread = threading.Thread(
        target=run_pipeline_async,
        args=(filepath, job_id),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    """
    Poll this endpoint to get the current progress of a processing job.
    Returns: { job_id, stage, progress, done, error, elapsed_sec, data }
    """
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    response = {
        "job_id": job_id,
        "stage": job.get('stage', 'Unknown'),
        "progress": job.get('progress', 0),
        "done": job.get('done', False),
        "error": job.get('error', None),
        "elapsed_sec": job.get('elapsed_sec', 0)
    }

    # Only include full data when job is complete and successful
    if job.get('done') and not job.get('error'):
        response['data'] = job.get('data')

    return jsonify(response), 200


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """
    RAG-style semantic search over the transcript.
    Body: { query: str, transcript: list[{start, end, text}] }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    query = data.get('query', '').strip()
    transcript = data.get('transcript', [])

    if not query:
        return jsonify({"error": "Query cannot be empty."}), 400
    if not transcript:
        return jsonify({"error": "No transcript provided."}), 400

    log.info(f"Chat query: '{query}' against {len(transcript)} segments.")

    from pipeline.chat import search_transcript
    result = search_transcript(query, transcript)
    return jsonify(result), 200


@app.route('/translate', methods=['POST'])
def translate_endpoint():
    """
    Translates text to target language.
    Body: { text: str, language: str }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    text = data.get('text', '').strip()
    lang = data.get('language', 'es')

    if not text:
        return jsonify({"error": "No text provided."}), 400

    log.info(f"Translating {len(text)} chars to '{lang}'...")

    try:
        from pipeline.translation import run_translation
        translated = run_translation(text, target_code=lang)
        return jsonify({"translated": translated}), 200
    except ImportError as e:
        log.error(f"Translation dependency missing: {e}")
        return jsonify({"error": f"Translation unavailable: {e}. Run: pip install argostranslate"}), 503
    except Exception as e:
        log.error(f"Translation error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500


@app.route('/romanize', methods=['POST'])
def romanize_endpoint():
    """
    Romanizes native script text to IAST.
    Body: { text: str, language: str }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    text = data.get('text', '').strip()
    lang = data.get('language', 'Devanagari')

    if not text:
        return jsonify({"error": "No text provided."}), 400

    log.info(f"Romanizing {len(text)} chars from '{lang}'...")

    try:
        from pipeline.romanization import run_romanization
        romanized = run_romanization(text, source_script=lang)
        return jsonify({"romanized": romanized}), 200
    except ImportError as e:
        log.error(f"Romanization dependency missing: {e}")
        return jsonify({"error": f"Romanization unavailable: {e}. Run: pip install aksharamukha"}), 503
    except Exception as e:
        log.error(f"Romanization error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Romanization failed: {str(e)}"}), 500


@app.route('/library', methods=['GET'])
def library_endpoint():
    """
    Returns a list of all previously processed podcasts from the outputs folder.
    """
    entries = []
    try:
        for fname in os.listdir(OUTPUT_FOLDER):
            if fname.startswith('final_') and fname.endswith('_data.json'):
                fpath = os.path.join(OUTPUT_FOLDER, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                    stat = os.stat(fpath)
                    entries.append({
                        "job_id": payload.get('job_id', fname),
                        "filename": payload.get('original_filename', 'Unknown'),
                        "duration": payload.get('metadata', {}).get('duration', 0),
                        "word_count": payload.get('metadata', {}).get('word_count', 0),
                        "topic_count": len(payload.get('topics', [])),
                        "processed_at": payload.get('metadata', {}).get('processed_at', ''),
                        "size_bytes": stat.st_size
                    })
                except Exception as e:
                    log.warning(f"Could not read library file {fname}: {e}")
    except Exception as e:
        log.error(f"Library scan failed: {e}")

    # Sort newest first
    entries.sort(key=lambda x: x.get('processed_at', ''), reverse=True)
    return jsonify({"library": entries}), 200


@app.route('/export/<job_id>/<fmt>', methods=['GET'])
def export_endpoint(job_id, fmt):
    """
    Generates and returns a downloadable file for the given job.
    Formats: txt, json, srt, md, csv
    """
    json_path = os.path.join(OUTPUT_FOLDER, f"final_{job_id}_data.json")
    if not os.path.exists(json_path):
        return jsonify({"error": "Job data not found. Process audio first."}), 404

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    from pipeline.export import generate_export
    try:
        file_path, mime_type = generate_export(data, fmt, job_id)
        return send_file(file_path, mimetype=mime_type, as_attachment=True,
                         download_name=f"talk2topics_{job_id[:8]}.{fmt}")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log.error(f"Export failed for {job_id} format={fmt}: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == '__main__':
    log.info("=" * 60)
    log.info("  TALK2TOPICS AI Backend")
    log.info("  http://localhost:5000")
    log.info("=" * 60)
    # use_reloader=False — prevents Flask from reloading when PyTorch touches site-packages
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
