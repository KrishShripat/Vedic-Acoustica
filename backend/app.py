import os
import subprocess
import time
import threading

try:
    import spaces
    _HAS_SPACES = True
except ImportError:  # CPU/basic Spaces do not ship the ZeroGPU 'spaces' package
    spaces = None
    _HAS_SPACES = False

import gradio as gr
import django
from django.core.asgi import get_asgi_application

print("Starting Trojan Horse (Gradio-launcher Edition)...")

# 1. Configure Django Environment.
# NOTE: no fallback DJANGO_SECRET_KEY is injected here — settings.py refuses
# (R2) to boot in production with a known-insecure key.  A real value must be
# set as a Space secret (Settings -> Variables -> DJANGO_SECRET_KEY).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vedic_acoustica.settings')
# Hugging Face forwards requests with Host: <space>.hf.space. Production
# (DEBUG=False) requires DJANGO_ALLOWED_HOSTS, so cover the HF proxy hosts here
# (never '*' — that would disable Host-header validation entirely).
if not os.environ.get('DJANGO_ALLOWED_HOSTS'):
    os.environ['DJANGO_ALLOWED_HOSTS'] = '.hf.space,localhost,127.0.0.1'
# settings.py reads CORS_EXTRA_ORIGINS, not FRONTEND_URL. Translate the HF
# Space variable so the Vercel frontend can call the API.
if os.environ.get('FRONTEND_URL') and not os.environ.get('CORS_EXTRA_ORIGINS'):
    os.environ['CORS_EXTRA_ORIGINS'] = os.environ['FRONTEND_URL']

# 2. Start Redis
print("Starting Redis...")
subprocess.Popen(["redis-server"])
time.sleep(2)

# 3. Run Database Migrations
print("Running migrations...")
django.setup()
if os.system("python manage.py migrate --noinput") != 0:
    print("WARNING: migrations failed, continuing anyway.")

# 3b. Seed bundled sample recordings (R3): the landing page links to
# /media/recordings/test_10s.wav which only exists if a sample has been
# uploaded.  A Space volume wipe used to break it until a user re-uploaded.
# seeding is idempotent (skips clips already present) and enqueues analysis
# on the Celery worker started below.
print("Seeding bundled sample recordings (idempotent)...")
if os.system("python manage.py seed_samples --analyze") != 0:
    print("WARNING: sample seeding failed, continuing anyway.")

# 4. Start Celery Worker
print("Starting Celery...")
celery_log = open("celery.log", "a")
subprocess.Popen(
    ["celery", "-A", "vedic_acoustica", "worker", "--loglevel=info", "--concurrency=2"],
    stdout=celery_log,
    stderr=subprocess.STDOUT,
)

# 5. Real Gradio app with a GPU decoy bound to a real event handler.
# ZeroGPU's startup scan walks Gradio's registered handlers for @spaces.GPU
# functions, so the decorated fn MUST be wired to a .click(...). It is never
# actually invoked, so we consume zero GPU quota. On non-ZeroGPU hardware
# (CPU/basic) the 'spaces' package is absent, so we skip the decoy entirely
# instead of crashing the Space at import time.
if _HAS_SPACES:
    @spaces.GPU
    def decoy_gpu(text):  # noqa: ANN001
        return "GPU active"

with gr.Blocks() as demo:
    gr.Markdown("Vedic Acoustica backend is running.")
    _in = gr.Textbox(label="Ping", value="ping")
    _out = gr.Textbox(label="Reply", interactive=False)
    if _HAS_SPACES:
        _btn = gr.Button("Send")
        _btn.click(fn=decoy_gpu, inputs=_in, outputs=_out)

# 6. Launch Gradio on 7860 via gradio's own launcher - this is what the
#    ZeroGPU runtime scans and what owns port 7860.
demo.queue().launch(
    server_name="0.0.0.0",
    server_port=7860,
    prevent_thread_lock=True,
    ssr_mode=False,
)

# 7. Attach Django to gradio's underlying FastAPI app. Path-preserving Mounts
#    are inserted at the FRONT of gradio's router, so /api, /admin, /metrics
#    and /media are handled by Django before any gradio route can swallow
#    them. Mount (not add_middleware) is used because it is legal after
#    launch(); add_middleware raises "Cannot add middleware after an
#    application has started". Starlette strips the mount prefix before
#    passing the request down, so a restorer re-prepends it - otherwise
#    django's urlconf sees /recordings/ instead of /api/recordings/ and 404s.
from starlette.routing import Mount


class _PathRestorer:
    def __init__(self, prefix, app):
        self.prefix = prefix
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        new_scope = dict(scope)
        if path and not path.startswith(self.prefix):
            new_scope["path"] = self.prefix + path
        # CRITICAL: Starlette's Mount sets root_path=prefix on the child scope.
        # Django treats root_path as SCRIPT_NAME and strips it from path_info,
        # so /api/recordings/ would resolve as /recordings/ and 404. Reset it.
        new_scope["root_path"] = ""
        await self.app(new_scope, receive, send)


django_app = get_asgi_application()
for _prefix in ("/api", "/admin", "/metrics", "/media"):
    demo.app.router.routes.insert(0, Mount(_prefix, _PathRestorer(_prefix, django_app)))

print("Trojan Horse deployed: Django serving inside Gradio on port 7860.")
threading.Event().wait()
