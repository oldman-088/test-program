"""اختبارات آلية لمخرجات مهمة التشغيل بالحاويات وسكربتات التطوير المحلي.

تغطي: docker/Dockerfile.backend، docker/Dockerfile.frontend، docker/nginx.conf،
docker-compose.yml، docker-compose.override.yml، .dockerignore، scripts/dev.sh،
scripts/dev.ps1، وتوثيق النتيجة الفعلية للبناء في docs/ENVIRONMENT.md.

مستويات التحقق:
  * اختبارات بنيوية نصية تعمل دائمًا (لا تحتاج Docker ولا PyYAML).
  * اختبارات تحليل YAML تُتخطّى بلطف إن لم تكن pyyaml مثبتة (قاعدة E49).
  * اختبارات ``integration`` تتحقق فعليًا من ``docker compose``؛ تُتخطّى إن لم يتوفر
    Docker، وتُشغَّل في CI عبر المتغير NEXUS_RUN_DOCKER_INTEGRATION=1.
"""

import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

DOCKER_FILES = [
    "docker/Dockerfile.backend",
    "docker/Dockerfile.frontend",
    "docker/nginx.conf",
    "docker-compose.yml",
    "docker-compose.override.yml",
    ".dockerignore",
]
DEV_SCRIPTS = ["scripts/dev.sh", "scripts/dev.ps1"]


def read(rel: str) -> str:
    path = ROOT / rel
    assert path.is_file(), f"ملف مفقود: {rel}"
    return path.read_text(encoding="utf-8")


def load_yaml(rel: str):
    yaml = pytest.importorskip("yaml", reason="pyyaml غير مثبتة في هذه البيئة")
    return yaml.safe_load(read(rel))


def have_docker_cli() -> bool:
    """Docker CLI + Compose v2 متاحان فعلًا في هذه البيئة؟"""
    if os.environ.get("NEXUS_SKIP_DOCKER_TESTS") == "1":
        return False
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=60)
    except Exception:
        return False
    return probe.returncode == 0


def docker_integration_enabled() -> bool:
    """بناء صور وتشغيل حاويات فعلي: يتطلب Docker و NEXUS_RUN_DOCKER_INTEGRATION=1."""
    return have_docker_cli() and os.environ.get("NEXUS_RUN_DOCKER_INTEGRATION") == "1"


needs_docker = pytest.mark.skipif(not have_docker_cli(), reason="Docker / docker compose غير متوفر في هذه البيئة")
needs_docker_build = pytest.mark.skipif(
    not docker_integration_enabled(),
    reason="بناء الصور وتشغيل الحاويات يتطلبان Docker و NEXUS_RUN_DOCKER_INTEGRATION=1 (تُشغَّل في وظيفة CI ops-docker)",
)
integration = pytest.mark.integration

def _venv_with_uvicorn() -> Path | None:
    """مجلد venv الحالي إن كان يحتوي uvicorn جاهزًا (يُستخدم لبناء .venv في النموذج)."""
    if importlib.util.find_spec("uvicorn") is None:
        return None
    candidate = Path(sys.executable).parent
    return candidate.parent if (candidate / "uvicorn").is_file() else None


needs_uvicorn = pytest.mark.skipif(_venv_with_uvicorn() is None, reason="uvicorn غير مثبت في بيئة الاختبار")



# -------------------------------------------------
# وجود الملفات المطلوبة
# -------------------------------------------------
@pytest.mark.parametrize("rel", DOCKER_FILES + DEV_SCRIPTS)
def test_expected_ops_files_exist(rel):
    """يجب أن توجد كل ملفات التشغيل بالحاويات والسكربتات المحلية وغير فارغة."""
    assert (ROOT / rel).is_file(), f"ملف مفقود: {rel}"
    assert (ROOT / rel).read_text(encoding="utf-8").strip(), f"ملف فارغ: {rel}"


def test_dev_sh_is_executable():
    """يجب أن يكون scripts/dev.sh قابلًا للتنفيذ."""
    assert (ROOT / "scripts/dev.sh").stat().st_mode & 0o111, "scripts/dev.sh غير قابل للتنفيذ"


# -------------------------------------------------
# docker/Dockerfile.backend
# -------------------------------------------------
def test_backend_dockerfile_base_image_and_requirements():
    """البند 3: قاعدة python:3.12-slim وتثبيت backend/requirements.txt."""
    text = read("docker/Dockerfile.backend")
    assert re.search(r"(?m)^FROM\s+python:3\.12-slim\b", text), "يجب البدء من python:3.12-slim"
    assert "COPY backend/requirements.txt" in text, "يجب نسخ backend/requirements.txt لطبقة الاعتماديات"
    assert re.search(r"pip install .*-r\s+requirements\.txt", text), "يجب تثبيت المتطلبات بـ pip install -r"
    # uvicorn غير معلن في requirements.txt الخاصة بالخلفية: الصورة تثبّته صراحة.
    assert re.search(r"pip install .*uvicorn>=0\.30", text), "يجب تثبيت uvicorn صراحة في صورة التشغيل"
    assert "COPY backend/ /app/backend/" in text, "يجب نسخ شيفرة الخلفية إلى /app/backend"


def test_backend_files_that_the_image_copies_exist():
    """الصورة تنسخ `backend/requirements.txt` و`backend/app` — كلاهما مصدر حقيقي الآن.

    ملاحظة عقْدية مُختبَرة لا مفترضة: uvicorn غير معلنة في requirements.txt (ولا في
    requirements-dev.txt)، وهي التي تعالجها الصورة والسكربتات صراحةً؛ إن أُضيفت هناك
    لاحقًا فذاك السطر يصبح زائدًا ويجب تحديثه معًا.
    """
    reqs = ROOT / "backend" / "requirements.txt"
    main_py = ROOT / "backend" / "app" / "main.py"
    assert reqs.is_file(), "docker/Dockerfile.backend ينسخ backend/requirements.txt فيجب أن توجد"
    assert main_py.is_file(), "منفذ ASGI app.main:app يجب أن يكون موجودًا في backend/app/main.py"
    req_text = reqs.read_text(encoding="utf-8").lower()
    assert "fastapi" in req_text, "يجب أن تعلن requirements.txt عن fastapi"
    assert "uvicorn" not in req_text, (
        "uvicorn كانت معلنة في requirements.txt — يجب الآن إزالة سطر التثبيت الصريح "
        "من Dockerfile.backend ومن scripts/dev.* حتى لا يتضاعف مصدر الحقيقة"
    )
    assert re.search(r"^app\s*=\s*create_app\(\)", main_py.read_text(encoding="utf-8"), re.M), (
        "يجب أن يصدّر backend/app/main.py الكائن app كما تتوقعه الصورة والسكربتات"
    )
    # backend/.env لا يجوز أن يُلتزم: يتسرب إلى طبقة البناء ويخالف البند 22.
    tracked = subprocess.run(["git", "ls-files", "backend/.env"], capture_output=True, text=True, cwd=ROOT)
    assert tracked.stdout.strip() == "", (
        "backend/.env مُتتبَّع في Git — يجب حذفه من الفهرس: git rm --cached backend/.env"
    )


def test_backend_dockerfile_runs_uvicorn_on_all_interfaces_with_port_env():
    """البند 3: uvicorn على 0.0.0.0:8000 مع متغير بيئة للمنفذ."""
    text = read("docker/Dockerfile.backend")
    assert re.search(r"(?m)^ENV\s+BACKEND_PORT=8000\b", text), "يجب تعريف BACKEND_PORT=8000 كمتغير بيئة"
    assert "APP_IMPORT=app.main:app" in text, "منفذ ASGI الحقيقي للخلفية هو app.main:app"
    assert "API_V1_PREFIX=/api/v1" in text, "يجب مطابقة بادئة REST لدى الخلفية"
    cmd_lines = [l for l in text.splitlines() if l.startswith("CMD")]
    assert cmd_lines, "يجب أن تحتوي الصورة على CMD"
    cmd = " ".join(cmd_lines)
    for expected in ("uvicorn", "--host 0.0.0.0", "--port", "BACKEND_PORT"):
        assert expected in cmd, f"CMD يجب أن يتضمن {expected}: {cmd}"
    assert re.search(r"(?m)^EXPOSE\s+8000\b", text), "يجب EXPOSE 8000"


def test_backend_dockerfile_is_non_root_with_data_dir():
    """الأمان: مستخدم غير جذري، ومجلد بيانات /app/data قابل للكتابة للـ volume."""
    text = read("docker/Dockerfile.backend")
    assert re.search(r"(?m)^USER\s+app\b", text), "يجب التشغيل كمستخدم غير جذري"
    assert "useradd" in text and "chown app:app /app/data" in text, "يجب تمكين المستخدم من كتابة /app/data فقط"
    assert "DATA_DIR=/app/data" in text, "يجب تعريف مجلد البيانات /app/data"
    assert "PYTHONPATH=/app/backend" in text, "جذر الحزمة app داخل backend/ فيتطلب PYTHONPATH"
    assert "HEALTHCHECK" in text, "يجب تعريف فحص صحة للحاوية"
    assert "alembic upgrade head" in text, "يجب دعم تطبيق الهجرات عند الإقلاع (MIGRATE_ON_START)"


def test_dockerfiles_have_no_unescaped_newlines_in_json_form():
    """صيغة exec form يجب أن تكون JSON صحيحًا على سطر واحد (لا أسطر داخل السلسلة)."""
    for rel in ("docker/Dockerfile.backend", "docker/Dockerfile.frontend"):
        text = read(rel)
        for line in text.splitlines():
            if line.lstrip().startswith('CMD ["') or line.lstrip().startswith('ENTRYPOINT ["'):
                assert line.rstrip().endswith("]"), f"سطر CMD بصيغة JSON غير مكتمل في {rel}: {line[:80]}"


def test_dockerfiles_do_not_bake_secrets():
    """لا تُخبز أسرار في الصور (القاعدة 4 من AGENTS)."""
    for rel in ("docker/Dockerfile.backend", "docker/Dockerfile.frontend"):
        for line in read(rel).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert not re.match(r"^(ENV|ARG)\s+(SECRET_KEY|API_KEY|PASSWORD|TOKEN)=[^$]", stripped), (
                f"ممنوع تعيين سر حرفي في {rel}: {stripped}"
            )


# -------------------------------------------------
# docker/Dockerfile.frontend
# -------------------------------------------------
def test_frontend_dockerfile_multistage_node_then_nginx():
    """البند 3: بناء بـ node:20-alpine ثم خدمة الملفات المبنية بـ nginx:alpine."""
    text = read("docker/Dockerfile.frontend")
    assert re.search(r"(?m)^FROM\s+node:20-alpine\s+AS\s+build\b", text), "مرحلة البناء يجب أن تكون node:20-alpine AS build"
    assert re.search(r"(?m)^FROM\s+nginx:alpine\s+AS\s+runtime\b", text), "مرحلة التشغيل يجب أن تكون nginx:alpine AS runtime"
    assert re.search(r"(?m)^FROM\s+node:20-alpine\s+AS\s+dev\b", text), "يجب وجود هدف dev للتسخّر المحلي"
    assert "npm run build" in text, "يجب تنفيذ npm run build في مرحلة البناء"
    assert "COPY --from=build /app/dist /usr/share/nginx/html" in text, "يجب نسخ dist إلى nginx"
    assert "COPY docker/nginx.conf /etc/nginx/conf.d/default.conf" in text, "يجب نسخ nginx.conf إلى conf.d"
    assert re.search(r"(?m)^EXPOSE\s+8080\b", text), "يجب EXPOSE 8080"
    assert "HEALTHCHECK" in text, "يجب تعريف فحص صحة لـ nginx"


# -------------------------------------------------
# docker/nginx.conf
# -------------------------------------------------
def test_nginx_conf_serves_static_and_proxies_api():
    """البند 3 و 22: خدمة الملفات الثابتة وتوجيه /api إلى خدمة الخلفية."""
    text = read("docker/nginx.conf")
    assert re.search(r"listen\s+8080;", text), "يجب الإصغاء على 8080 داخل الحاوية"
    assert re.search(r"root\s+/usr/share/nginx/html;", text), "يجب تحديد root للملفات الثابتة"
    assert "location ^~ /api/" in text, "يجب تعريف موقع /api/"
    assert re.search(r"proxy_pass\s+http://\$nexus_backend;", text), "يجب تمرير /api إلى متغيّر الخلفية"
    assert re.search(r'set\s+\$nexus_backend\s+"backend:8000";', text), "يجب أن يشير المنفذ إلى خدمة backend:8000"
    assert "resolver 127.0.0.11" in text, "يجب استخدام DNS الخاص بشبكة Docker لحلّ اسم الخدمة وقت الطلب"
    assert "try_files $uri $uri/ /index.html;" in text, "يجب دعم SPA fallback"
    assert "location ^~ /ws/" in text and "$connection_upgrade" in text, "يجب دعم ترقية WebSocket لمسار /ws"
    assert "location = /healthz" in text, "يجب توفير مسار فحص صحة لـ nginx"


def test_nginx_conf_structure_is_sane():
    """ملفات conf.d تُضمَّن داخل http{}: لا كتل user/events/http، وأقواس متوازنة."""
    body = "\n".join(l for l in read("docker/nginx.conf").splitlines() if not l.strip().startswith("#"))
    for directive in ("http {", "events {", "user "):
        assert directive not in body, f"nginx.conf داخل conf.d يجب ألا يحتوي على: {directive}"
    assert body.count("{") == body.count("}"), "أقواس غير متوازنة في nginx.conf"

    pending_values = False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if pending_values:
            # استمرار قائمة قيم (مثل gzip_types): حتى سطر ينتهي بفاصلة منقوطة.
            pending_values = not stripped.endswith(";")
            continue
        if stripped.endswith(("{", "}")):
            continue
        if re.match(r"^gzip_types$", stripped):
            pending_values = True
            continue
        assert stripped.endswith(";"), f"سطر غير مكتمل في nginx.conf: {stripped}"


def test_nginx_conf_uses_service_name_not_localhost():
    """القاعدة 6 من AGENTS: التوجيه يتم باسم الخدمة لا بـ localhost."""
    proxy_targets = re.findall(r"proxy_pass\s+([^;]+);", read("docker/nginx.conf"))
    assert proxy_targets, "يجب أن يوجد proxy_pass واحد على الأقل"
    for target in proxy_targets:
        assert "localhost" not in target and "127.0.0.1" not in target, (
            f"proxy_pass يجب أن يستخدم اسم الخدمة: {target}"
        )


def test_nginx_conf_parses_as_real_nginx_config(tmp_path):
    """تحليل nginx.conf بمحلّل nginx الحقيقي القواعد (crossplane) داخل سياق http{}."""
    crossplane = pytest.importorskip("crossplane", reason="crossplane غير مثبتة في هذه البيئة")
    fragment = read("docker/nginx.conf")
    full = tmp_path / "nginx.conf"
    full.write_text("worker_processes 1;\nevents {}\nhttp {\n" + fragment + "\n}\n", encoding="utf-8")
    report = crossplane.parse(str(full), catch_errors=True)
    assert not report["errors"], f"أخطاء في nginx.conf: {report['errors']}"
    assert report["status"] in ("ok", "passed"), f"حالة التحليل: {report['status']}"

    def walk(blocks, depth=0, out=None):
        out = [] if out is None else out
        for block in blocks:
            out.append((depth, block.get("directive", ""), " ".join(block.get("args", []))))
            if "block" in block:
                walk(block["block"], depth + 1, out)
        return out

    tree = walk(report["config"][0]["parsed"])
    locations = [args for _, directive, args in tree if directive == "location"]
    assert any(a.startswith("^~ /api/") for a in locations), f"موقع /api/ مفقود: {locations}"
    assert any(a.startswith("^~ /ws/") for a in locations), f"موقع /ws/ مفقود: {locations}"
    assert any(a == "/" for a in locations), "موقع الجذر (SPA) مفقود"
    listens = [args for _, directive, args in tree if directive == "listen"]
    assert "8080" in listens, f"منفذ الاستماع غير 8080: {listens}"
    assert any("proxy_pass" == d for _, d, _ in tree), "لا proxy_pass في التحليل"


@pytest.mark.parametrize(
    "rel,expected_parents",
    [
        ("docker/Dockerfile.backend", ["python:3.12-slim"]),
        ("docker/Dockerfile.frontend", ["node:20-alpine", "nginx:alpine", "node:20-alpine"]),
    ],
)
def test_dockerfiles_are_syntactically_parseable(rel, expected_parents):
    """ملفا Dockerfile يُحلَّلان كأوامر صالحة: استمرارات الخط الساطع وسلاسل JSON صحيحة."""
    dockerfile_parse = pytest.importorskip("dockerfile_parse", reason="dockerfile-parse غير مثبتة في هذه البيئة")
    with (ROOT / rel).open("rb") as fh:
        parser = dockerfile_parse.DockerfileParser(fileobj=fh)
        structure = parser.structure
        parents = list(parser.parent_images)
    assert parents == expected_parents, f"صور الأساس في {rel}: {parents}"
    instructions = [step["instruction"] for step in structure]
    assert "FROM" in instructions and "CMD" in instructions or rel.endswith("frontend"), instructions
    assert "COPY" in instructions, f"لا COPY في {rel}"
    run_values = [s["value"] for s in structure if s["instruction"] == "RUN"]
    assert all(v.strip() for v in run_values), "سطر RUN فارغ — استمرارات الخط الساطع مكسورة"


def _healthcheck_shell_cmd(rel: str) -> str:
    """يستخرج أمر HEALTHCHECK (shell form) كما سيُنفَّذ داخل الحاوية."""
    for line in read(rel).splitlines():
        stripped = line.strip()
        if stripped.startswith("CMD ") and "urllib" in stripped:
            return stripped[len("CMD "):]
    return ""


def test_backend_healthcheck_command_actually_works(tmp_path):
    """أمر HEALTHCHECK في Dockerfile.backend يُنفَّذ فعليًا مقابل خادم صلاحي.

    يضمن أن الفحص ينجح على ${API_PREFIX}/health، ويفشل على 404 (لا نجاح زائف)،
    ويعطّل نفسه عند HEALTHCHECK_PATH=""، ويحترم BACKEND_PORT.
    """
    cmd = _healthcheck_shell_cmd("docker/Dockerfile.backend")
    assert cmd, "لم يُعثر على أمر HEALTHCHECK في Dockerfile.backend"

    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        allowed = {"/api/health"}

        def do_GET(self):  # noqa: N802
            if self.path in Handler.allowed:
                payload = b'{"status":"ok"}'
                self.send_response(200)
            else:
                payload = b'{"detail":"not found"}'
                self.send_response(404)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):  # صمت في مخرجات الاختبار
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        Handler.allowed = {"/api/v1/health"}

        def run(**env):
            child_env = {k: v for k, v in os.environ.items()}
            child_env.pop("HEALTHCHECK_PATH", None)
            child_env.pop("API_V1_PREFIX", None)
            child_env.pop("API_PREFIX", None)
            child_env["BACKEND_PORT"] = str(port)
            child_env.update({k: str(v) for k, v in env.items()})
            return subprocess.run(["sh", "-c", cmd], env=child_env, capture_output=True, text=True, timeout=30)

        assert run(API_V1_PREFIX="/api/v1").returncode == 0, "الفحص يجب أن ينجح على /api/v1/health"
        Handler.allowed = {"/v1/health"}
        assert run(API_V1_PREFIX="/v1").returncode == 0, "الفحص يجب أن يتبع API_V1_PREFIX"
        assert run(API_V1_PREFIX="/api/v1").returncode != 0, "الفحص يجب أن يفشل عند 404 لا أن ينجح زائفًا"
        Handler.allowed = set()
        assert run(API_V1_PREFIX="/api/v1", HEALTHCHECK_PATH="").returncode == 0, (
            'HEALTHCHECK_PATH="" يجب أن يعطّل الفحص'
        )
        assert run(HEALTHCHECK_PATH="/api/v1/health", **{"API_V1_PREFIX": "/ignored"}).returncode != 0
    finally:
        server.shutdown()
        server.server_close()


# -------------------------------------------------
# docker-compose.yml
# -------------------------------------------------
def test_compose_defines_both_services_with_builds():
    """خدمتا backend و frontend تُبنى كل واحدة من Dockerfile الخاص بها."""
    services = load_yaml("docker-compose.yml")["services"]
    assert set(services) == {"backend", "frontend"}, f"الخدمات المتوقعة backend و frontend، الموجود: {sorted(services)}"
    assert services["backend"]["build"]["dockerfile"] == "docker/Dockerfile.backend"
    assert services["frontend"]["build"]["dockerfile"] == "docker/Dockerfile.frontend"
    assert services["backend"]["build"]["context"] == ".", "سياق البناء يجب أن يكون جذر المستودع"
    assert services["frontend"]["build"]["context"] == ".", "سياق البناء يجب أن يكون جذر المستودع"
    assert services["frontend"].get("depends_on"), "يجب أن تعتمد الواجهة على الخلفية"


def test_compose_publishes_frontend_and_backend_ports():
    """منفذ منشور للواجهة (3000→8080) وللمنفذ الخلفي (8000)."""
    services = load_yaml("docker-compose.yml")["services"]
    fe_ports = [str(p) for p in services["frontend"].get("ports", [])]
    be_ports = [str(p) for p in services["backend"].get("ports", [])]
    assert any(p.endswith(":8080") for p in fe_ports), f"يجب نشر منفذ الواجهة على هدف 8080: {fe_ports}"
    assert any(p.endswith(":8000") for p in be_ports), f"يجب نشر منفذ الخلفية 8000: {be_ports}"
    assert any("FRONTEND_PORT" in p for p in fe_ports), "يجب أن يُقرأ منفذ الواجهة من FRONTEND_PORT"


def test_compose_mounts_sqlite_volume_and_passes_env_file():
    """البند المطلوب: volume دائم لملف قاعدة البيانات + تمرير .env."""
    doc = load_yaml("docker-compose.yml")
    services = doc["services"]
    for name in ("backend", "frontend"):
        env_files = [str(e) for e in services[name].get("env_file", [])]
        assert ".env" in env_files, f"يجب تمرير .env إلى خدمة {name}: {env_files}"
    mounts = [str(v) for v in services["backend"].get("volumes", [])]
    assert any(v.startswith("nexus-data:/app/data") for v in mounts), f"يجب ربط volume مُسمّى بمجلد البيانات: {mounts}"
    assert "nexus-data" in (doc.get("volumes") or {}), "يجب إعلان الـ volume المُسمّى nexus-data"
    env = services["backend"].get("environment", {})
    assert "app/data" in str(env.get("DATABASE_URL", "")), "يجب أن تُشير SQLite داخل الحاوية إلى مسار الـ volume"
    # volume مُسمّى (لا bind مؤقت): يبقى بعد docker compose down بلا -v.
    volume_def = doc["volumes"]["nexus-data"] or {}
    assert volume_def.get("name"), "يجب تثبيت اسم الـ volume ليبقى بعد إعادة إنشاء المشروع"


def test_compose_backend_matches_the_real_backend_contract():
    """Compose يواكب عقد الخلفية المدموجة: المنفذ الداخلي، app.main:app، /api/v1، وقاعدة volume."""
    env = load_yaml("docker-compose.yml")["services"]["backend"].get("environment", {})
    assert str(env.get("BACKEND_PORT")) == "8000", "يجب تثبيت المنفذ الداخلي على 8000 ليطابق nginx.conf"
    assert "app.main:app" in str(env.get("APP_IMPORT", "")), "منفذ ASGI للخلفية هو app.main:app"
    assert str(env.get("PYTHONPATH")) == "/app/backend", "جذر الحزمة app داخل backend/"
    assert "/api/v1" in str(env.get("API_V1_PREFIX", "")), "يجب تمرير بادئة REST للخلفية"
    assert "aatm.db" in str(env.get("DATABASE_URL", "")), "اسم ملف القاعدة داخل الـ volume يجب أن يطابق الخلفية"
    assert str(env.get("ENVIRONMENT", "")).startswith("${"), "يجب تعيين ENVIRONMENT من APP_ENV الخاص بالمشروع"


def test_compose_files_contain_no_hardcoded_secrets():
    """لا أسرار حرفية في ملفات Compose؛ تُمرَّر عبر .env المستثنى من Git."""
    for rel in ("docker-compose.yml", "docker-compose.override.yml", ".dockerignore"):
        text = read(rel)
        assert "sk-ant-" not in text and "gsk_" not in text and "sessionid=" not in text, f"سر مشبوه في {rel}"
        for line in text.splitlines():
            assert not re.match(r"\s*(SECRET_KEY|API_KEY|PASSWORD|TOKEN)\s*:\s*['\"]?[A-Za-z0-9_\-]{12,}", line), (
                f"{rel} يعيّن سرًا حرفيًا: {line.strip()}"
            )


# -------------------------------------------------
# docker-compose.override.yml
# -------------------------------------------------
def test_override_enables_code_hot_reload():
    """البند المطلوب: تسخّر الكود أثناء التطوير عبر bind mounts."""
    services = load_yaml("docker-compose.override.yml")["services"]
    backend_vols = [str(v) for v in services["backend"].get("volumes", [])]
    assert "./backend:/app/backend" in backend_vols, f"يجب تركيب ./backend: {backend_vols}"
    assert str(services["backend"].get("environment", {}).get("UVICORN_RELOAD")) == "1", "يجب تفعيل UVICORN_RELOAD"
    assert str(services["backend"].get("environment", {}).get("MIGRATE_ON_START")) == "1", (
        "وضع التطوير يطبّق هجرات Alembic عند الإقلاع حتى تعمل نقاط العمل مباشرة"
    )
    frontend = services["frontend"]
    frontend_vols = [str(v) for v in frontend.get("volumes", [])]
    assert "./frontend:/app" in frontend_vols, f"يجب تركيب ./frontend: {frontend_vols}"
    assert any(str(v).endswith("/app/node_modules") for v in frontend_vols), "يجب حماية node_modules بـ volume مجهول"
    assert frontend.get("build", {}).get("target") == "dev", "يجب أن يستخدم هدف dev في وضع التطوير"


def test_override_does_not_republish_ports():
    """قوائم ports تُدمج مع الملف الأساسي: إعادة تعريفها هنا تسبب تعارض منفذ على المضيف."""
    for name, svc in (load_yaml("docker-compose.override.yml").get("services") or {}).items():
        assert not svc.get("ports"), f"يجب ألا يعرّف override منافذ للخدمة {name} (تعارض مع الملف الأساسي)"


# -------------------------------------------------
# .dockerignore / .gitignore / .env.example
# -------------------------------------------------
def test_dockerignore_excludes_heavy_and_sensitive_paths():
    """.dockerignore يمنع تسرّب .env أو node_modules أو .git إلى سياق البناء."""
    text = read(".dockerignore")
    for pattern in (".env", "node_modules", ".git", "__pycache__", "dist", ".venv"):
        assert pattern in text, f".dockerignore لا يستثني: {pattern}"


def test_gitignore_covers_local_run_artifacts():
    """ملفات التشغيل المحلي (.env، قواعد البيانات، مجلد data) يجب أن تُستثنى."""
    text = read(".gitignore")
    for pattern in (".env", "node_modules", "data/", "*.db", "*.sqlite3"):
        assert pattern in text, f".gitignore لا يستثني: {pattern}"


def test_env_example_documents_container_publish_ports():
    """منافذ النشر الخاصة بـ compose موثّقة في .env.example."""
    text = read(".env.example")
    assert "BACKEND_HOST_PORT" in text, "يجب توثيق BACKEND_HOST_PORT لنشر منفذ الخلفية"
    assert "BACKEND_PORT" in text and "FRONTEND_PORT" in text
    assert "APP_IMPORT=app.main:app" in text, "يجب توثيق منفذ ASGI الصحيح للخلفية"
    assert "API_V1_PREFIX=/api/v1" in text, "يجب توثيق بادئة REST الفعلية للخلفية"


# -------------------------------------------------
# scripts/dev.sh
# -------------------------------------------------
def test_dev_sh_bash_syntax():
    """يجب أن يجتاز dev.sh فحص bash -n."""
    result = subprocess.run(["bash", "-n", str(ROOT / "scripts/dev.sh")], capture_output=True, text=True)
    assert result.returncode == 0, f"scripts/dev.sh فشل في bash -n: {result.stderr}"


def test_dev_sh_help_lists_all_flags():
    """--help يجب أن يوثّق كل الوسائط."""
    result = subprocess.run(["bash", str(ROOT / "scripts/dev.sh"), "--help"], capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, result.stderr
    for flag in ("--backend-only", "--frontend-only", "--no-install", "--dry-run", "--port", "--host", "--migrate"):
        assert flag in result.stdout, f"--help لا يوثّق الوسيط {flag}"


def test_dev_scripts_document_the_real_backend_launch_contract():
    """السكربتات تشغّل الخلفية من `backend/` بـ PYTHONPATH وبالمنفذ app.main:app — لا تخمين."""
    sh = read("scripts/dev.sh")
    ps1 = read("scripts/dev.ps1")
    for label, text in (("dev.sh", sh), ("dev.ps1", ps1)):
        assert "app.main:app" in text, f"{label} يجب أن يستخدم منفذ ASGI الحقيقي"
        assert "API_V1_PREFIX" in text, f"{label} يجب أن يقرأ البادئة التي تعرفها الخلفية"
        assert "PYTHONPATH" in text, f"{label} يجب أن يصدر PYTHONPATH إلى backend/"
        assert "alembic" in text, f"{label} يجب أن يدعم هجرات Alembic (--migrate / -Migrate)"
    assert "uvicorn>=0.30" in sh and "uvicorn>=0.30" in ps1, (
        "uvicorn غير معلنة في requirements.txt: السكربتات تثبّتها صراحة"
    )


def test_dev_sh_does_not_invoke_docker():
    """المسار المحلي بديل عن Docker: لا يجوز أن ينفّذ أمر docker في الشيفرة."""
    code = [l for l in read("scripts/dev.sh").splitlines() if not l.strip().startswith("#")]
    for line in code:
        assert not re.match(r"^\s*(docker|sudo docker)\b", line), f"dev.sh ينفّذ docker: {line.strip()}"
        assert "$(docker" not in line and "; docker " not in line, f"dev.sh ينفّذ docker: {line.strip()}"


def _fixture_repo(tmp_path: Path, *, with_backend=True, with_frontend=True) -> Path:
    """نسخة من الجذر لاختبار السكربت: `backend/` الحقيقية إن وُجدت، وبديل مصغّر إن لا.

    نسخ `backend/` كما هي (بدون `var/` و`.env` و`__pycache__`) يجعل اختبار الإقلاع
    الفعلي يتحقق من التطبيق نفسه: نفس PYTHONPATH، ونفس المسار `/api/v1/health`،
    ونفس قراءة `.env` بدون source.
    """
    work = tmp_path / "repo"
    (work / "scripts").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/dev.sh", work / "scripts" / "dev.sh")
    shutil.copy2(ROOT / ".env.example", work / ".env.example")
    if with_backend:
        real = ROOT / "backend"
        if (real / "app" / "main.py").is_file():
            shutil.copytree(
                real, work / "backend",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "var", ".env"),
            )
        else:
            (work / "backend" / "app").mkdir(parents=True)
            (work / "backend" / "requirements.txt").write_text("uvicorn\n", encoding="utf-8")
            (work / "backend" / "app" / "main.py").write_text("app = None\n", encoding="utf-8")
    if with_frontend:
        (work / "frontend").mkdir()
        (work / "frontend" / "package.json").write_text(
            json.dumps({"name": "fx", "scripts": {"dev": "vite", "build": "vite build"}}) + "\n", encoding="utf-8"
        )
    return work


def test_dev_sh_dry_run_prints_both_commands(tmp_path):
    """dry-run يطبع أمرَي uvicorn و npm بوسائطهما الصحيحة ويولّد .env."""
    work = _fixture_repo(tmp_path)
    result = subprocess.run(
        ["bash", "scripts/dev.sh", "--dry-run", "--host", "127.0.0.1", "--port", "8137"],
        capture_output=True, text=True, cwd=str(work),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "uvicorn" in out and "--reload" in out, f"أمر uvicorn --reload غير موجود في:\n{out}"
    assert "--port '8137'" in out, f"المنفذ الممرّر غير مستخدم في:\n{out}"
    assert "--host '127.0.0.1'" in out, f"المضيف الممرّر غير مستخدم في:\n{out}"
    assert "npm run dev" in out and "--port '3000'" in out, f"أمر خادم تطوير الواجهة غير موجود في:\n{out}"
    assert "app.main:app" in out, f"يجب أن يستخدم dev.sh منفذ ASGI الحقيقي للخلفية:\n{out}"
    assert "PYTHONPATH=" in out, f"يجب أن يصدّر dev.sh PYTHONPATH إلى backend/:\n{out}"
    env_file = work / ".env"
    assert env_file.is_file(), "يجب أن يولّد dev.sh ملف .env"
    assert env_file.read_text(encoding="utf-8") == (work / ".env.example").read_text(encoding="utf-8"), (
        ".env المُولّد يجب أن يطابق .env.example"
    )


def test_dev_sh_dry_run_is_quiet_without_components(tmp_path):
    """بدون backend/ و frontend/: dry-run يخرج 0، والتشغيل الحقيقي يخرج 1 برسالة واضحة."""
    work = _fixture_repo(tmp_path, with_backend=False, with_frontend=False)
    dry = subprocess.run(["bash", "scripts/dev.sh", "--dry-run"], capture_output=True, text=True, cwd=str(work))
    assert dry.returncode == 0, f"dry-run يجب أن ينجح دائمًا:\n{dry.stderr}"
    real = subprocess.run(["bash", "scripts/dev.sh"], capture_output=True, text=True, cwd=str(work))
    assert real.returncode == 1, f"كان يجب الخروج 1 عند عدم وجود ما يُشغَّل:\n{real.stdout}"
    for expected in ("backend/", "frontend/", "docker compose up"):
        assert expected in real.stderr + real.stdout, f"الرسالة لا تذكر {expected}"


def test_dev_sh_reads_env_without_sourcing_it(tmp_path):
    """قراءة .env يجب أن تتحمّل القيم التي تحتوي مسافات (APP_NAME=NEXUS OSINT)."""
    work = _fixture_repo(tmp_path, with_frontend=False)
    (work / ".env").write_text("APP_NAME=NEXUS OSINT\nBACKEND_PORT=8231\nBACKEND_HOST=127.0.0.1\n", encoding="utf-8")
    result = subprocess.run(["bash", "scripts/dev.sh", "--dry-run", "--backend-only"], capture_output=True, text=True, cwd=str(work))
    assert result.returncode == 0, f"فشل عند قيمة تحتوي مسافة في .env:\n{result.stderr}{result.stdout}"
    assert "--port '8231'" in result.stdout, f"BACKEND_PORT من .env لم يُستخدم:\n{result.stdout}"
    assert "--host '127.0.0.1'" in result.stdout, f"BACKEND_HOST من .env لم يُستخدم:\n{result.stdout}"


def test_dev_sh_rejects_unknown_flag(tmp_path):
    """وسيط مجهول يجب أن يُرفض بخطأ واضح بدل الصمت."""
    work = _fixture_repo(tmp_path, with_backend=False, with_frontend=False)
    result = subprocess.run(["bash", "scripts/dev.sh", "--totally-made-up"], capture_output=True, text=True, cwd=str(work))
    assert result.returncode == 1, "كان يجب الرفض بخروج 1"
    assert "غير معروف" in result.stderr, result.stderr


@needs_uvicorn
def test_dev_sh_really_starts_and_stops_the_real_backend(tmp_path):
    """تشغيل فعلي لـ dev.sh مقابل **خلفية المستودع الحقيقية**: إقلاع، صحة، مصادقة، وتنظيف.

    يغطّي هذا العقد المحلي كاملًا بلا Docker:
    - `PYTHONPATH=backend` + cwd=`backend/` + `app.main:app` ⇒ `GET /api/v1/health` = 200؛
    - `GET /api/health` = 404 ⇒ النجاح ليس زائفًا (لو أخطأ السكربت البادئة لفشل الحقلان معًا)؛
    - `--migrate` يطبّق Alembic ⇒ `GET /api/v1/health/ready` يقول `ready`؛
    - `POST /api/v1/sessions` بـ `X-API-Key` = 201 ⇒ مفتاح `.env` يصل الخادم عبر البيئة؛
    - بعد `SIGTERM` لا تبقى عملية و لا منفذ مفتوح (بند 20: لا بقاء لعمليات يتيمة).
    """
    work = _fixture_repo(tmp_path, with_frontend=False)
    (work / ".venv").symlink_to(_venv_with_uvicorn(), target_is_directory=True)
    (work / "backend" / "var").mkdir(exist_ok=True)
    (work / ".env").write_text("BACKEND_HOST=127.0.0.1\nBACKEND_PORT=8391\n", encoding="utf-8")
    child_env = {**os.environ, "API_KEY": "dev-only-not-a-secret", "PYTHONUNBUFFERED": "1"}

    proc = subprocess.Popen(
        ["bash", "scripts/dev.sh", "--backend-only", "--no-install", "--migrate"],
        cwd=str(work), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=child_env, start_new_session=True,
    )

    def curl(path: str, *extra: str) -> str:
        return subprocess.run(
            ["curl", "-s", "-m", "5", "http://127.0.0.1:8391" + path, *extra],
            capture_output=True, text=True,
        ).stdout

    def code(path: str, *extra: str) -> str:
        return subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "5",
             "http://127.0.0.1:8391" + path, *extra],
            capture_output=True, text=True,
        ).stdout.strip()

    log_lines: list[str] = []
    try:
        health = ""
        for _ in range(60):
            if proc.poll() is not None:
                pytest.fail(f"خرج dev.sh مبكرًا:\n{proc.stdout.read()}")
            health = code("/api/v1/health")
            if health == "200":
                break
            subprocess.run(["sleep", "1"])
        log_lines.append(proc.stdout.readline() if proc.poll() is None else "")
        assert health == "200", f"لم تجب الخلفية الحقيقية على /api/v1/health خلال 60 ثانية (جاء {health!r})"
        assert code("/api/health") == "404", (
            "المسار بلا البادئة يجب أن يعيد 404 — يثبت أن 200 السابقة جاءت من التطابق الفعلي"
        )
        body = curl("/api/v1/health")
        assert '"status":"ok"' in body.replace(" ", ""), f"استجابة الصحة غير متوقعة: {body[:200]}"
        ready = curl("/api/v1/health/ready")
        assert "ready" in ready, f"هجرات --migrate لم تُطبَّق؟ {ready[:200]}"
        created = code(
            "/api/v1/sessions", "-X", "POST", "-H", "X-API-Key: dev-only-not-a-secret",
            "-H", "content-type: application/json",
            "-d", '{"task_id":"aatm-c740feee-a5ee-4519-958f-93dbc7b1241a","employee_id":"worker-5","branch":"arena/82fdba0c-test-program","worktree":"/app/backend"}',
        )
        assert created == "201", f"كان يجب 201 على إنشاء سجل العمل، جاء {created}"
        assert code("/api/v1/sessions", "-X", "POST", "-d", "{}") == "401", (
            "البند: بلا مفتاح يجب 401 (و 500 تعني أن API_KEY لم يصل الخادم من البيئة)"
        )
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
    assert proc.returncode == 0, f"كان يجب أن يخرج dev.sh بـ 0 بعد SIGTERM، خرج {proc.returncode}:\n{out[-1500:]}"
    # المنفذ أُغلق فعلًا (استطلاع، لا sleep ثابت).
    closed = False
    for _ in range(30):
        probe = subprocess.run(["curl", "-s", "-m", "2", "-o", "/dev/null", "-w", "%{http_code}",
                                "http://127.0.0.1:8391/api/v1/health"], capture_output=True, text=True)
        if probe.stdout.strip() in ("", "000"):
            closed = True
            break
        subprocess.run(["sleep", "0.2"])
    assert closed, "المنفذ 8391 ما زال يخدم بعد SIGTERM — بقاء يتعارض مع بند التنظيف"
    orphans = subprocess.run(["pgrep", "-f", "uvicorn app.main:app"], capture_output=True, text=True)
    assert orphans.stdout.strip() == "", f"بقيت عمليات uvicorn يتيمة:\n{orphans.stdout}"


# -------------------------------------------------
# scripts/dev.ps1
# -------------------------------------------------
def test_dev_ps1_has_no_bash_heredoc():
    """لا صيغة heredoc الخاصة بـ bash في نص PowerShell."""
    text = read("scripts/dev.ps1")
    assert "<<'" not in text and "<<PY" not in text, "dev.ps1 يحتوي صيغة heredoc غير صالحة في PowerShell"


def test_dev_ps1_mirrors_dev_sh_flags():
    """نفس الوسائط المتاحة في dev.sh يجب أن توجد في dev.ps1."""
    ps1 = read("scripts/dev.ps1")
    for flag in ("BackendOnly", "FrontendOnly", "NoInstall", "DryRun", "Port"):
        assert flag in ps1, f"dev.ps1 لا يدعم الوسيط {flag}"
    assert "uvicorn" in ps1 and "--reload" in ps1, "يجب تشغيل uvicorn بـ --reload"
    assert "npm run dev" in ps1, "يجب تشغيل خادم تطوير الواجهة"
    assert "Start-Process" in ps1, "يجب تشغيل العمليتين في الخلفية ثم الانتظار عليهما"
    assert "Stop-Process" in ps1, "يجب تنظيف العمليات التابعة عند الخروج"
    assert "Join-Path $PSScriptRoot" in ps1, "يجب تحديد جذر المستودع من موقع السكريبت"
    ps1_code = "\n".join(l for l in ps1.splitlines() if not l.strip().startswith("#"))
    assert "Invoke-Expression" not in ps1_code, "ممنوع تنفيذ قيم .env ككود في dev.ps1"


def test_dev_ps1_braces_and_quotes_are_balanced():
    """فحص بنيوي بلا pwsh: توازن الأقواس وعدم وجود استدعاءات bash."""
    text = read("scripts/dev.ps1")
    code = "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))
    assert code.count("{") == code.count("}"), "أقواس غير متوازنة في dev.ps1"
    assert code.count("(") == code.count(")"), "أقواس دائرية غير متوازنة في dev.ps1"
    for bashism in ("$(dirname", "set -euo pipefail", "export $", "BASH_SOURCE"):
        assert bashism not in code, f"dev.ps1 يحتوي صيغة bash: {bashism}"
    assert "$PID" not in code.replace("$PSScriptRoot", ""), "لا يجوز الكتابة على المتغيّر المحجوز $PID في PowerShell"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh غير متاح في هذه البيئة")
def test_dev_ps1_parses_with_pwsh():
    """إن كان pwsh متاحًا يجب أن يُحلَّل dev.ps1 بلا أخطاء نحو."""
    target = ROOT / "scripts" / "dev.ps1"
    script = (
        "$errs = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{target}', [ref] $null, [ref] $errs); "
        "if ($errs.Count -gt 0) { $errs | ForEach-Object { Write-Host $_.Message }; exit 1 }"
    )
    result = subprocess.run(["pwsh", "-NoProfile", "-Command", script], capture_output=True, text=True)
    assert result.returncode == 0, f"dev.ps1 لا يُحلَّل بنجاح: {result.stdout}{result.stderr}"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh غير متاح في هذه البيئة")
def test_dev_ps1_dry_run_with_pwsh(tmp_path):
    """dry-run عبر pwsh الحقيقي: يطبع الأمرين ويخرج 0 ويولّد .env."""
    work = _fixture_repo(tmp_path, with_frontend=False)
    shutil.copy2(ROOT / "scripts" / "dev.ps1", work / "scripts" / "dev.ps1")
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(work / "scripts" / "dev.ps1"), "-DryRun", "-Port", "8451"],
        capture_output=True, text=True, cwd=str(work),
    )
    assert result.returncode == 0, f"pwsh فشل في dry-run:\n{result.stdout}\n{result.stderr}"
    assert "uvicorn" in result.stdout and "8451" in result.stdout, result.stdout
    assert (work / ".env").is_file(), "يجب أن يولّد dev.ps1 ملف .env"


# -------------------------------------------------
# docs/ENVIRONMENT.md — النتيجة الفعلية للبناء
# -------------------------------------------------
def test_environment_documents_actual_build_result():
    """يجب أن يوثّق ENVIRONMENT.md نتيجة البناء الفعلية: نجاحًا أو تعذرًا بسبب البيئة."""
    text = read("docs/ENVIRONMENT.md")
    section = text.split("نتيجة البناء الفعلية", 1)
    assert len(section) > 1, "يجب وجود قسم صريح بعنوان «نتيجة البناء الفعلية»"
    body = section[1]
    for expected in (
        "docker/Dockerfile.backend",
        "docker-compose.yml",
        "docker compose up",
        "docker compose config",
        "scripts/dev.sh",
    ):
        assert expected in body, f"قسم نتيجة البناء لا يذكر: {expected}"
    assert re.search(r"(غير مثبت|غير متوفر|command not found)", body), "يجب التصريح بحالة Docker في البيئة"


def test_environment_documents_the_post_merge_ci_evidence():
    """التوثيق يجب أن يحمل رقم تشغيل CI بعد المزامنة، لا رقم الرأس السابق فقط.

    يمنع أن يُقرأ القسم على أنه إثبات لم يعد ينطبق على الرأس الحالي: يذكر الرأس
    `1464905` وملخص pytest الفعلي له، ويسجّل فشل التشغيل الأول على `aa19a21` والسبب.
    """
    text = read("docs/ENVIRONMENT.md")
    for sha in ("850c8d0", "26d90ba"):
        assert sha in text, f"يجب أن يوثّق الرأس الذي قِيست عليه نتيجة CI: {sha}"
    assert "30.22s" in text, "يجب توثيق زمن اختبار التكامل الفعلي: دليل على أنه نُفِّذ لا تُخطّي"
    assert "54 passed, 1 skipped" in text, "يجب نقل ملخص pytest الفعلي من وظيفة ops-docker"
    assert "aa19a21" in text and "NameError" in text, (
        "الفشل الأول على رأس المزامنة وسببه جزء من الدليل: لا تُحذف منه إلا بتوثيق بديل"
    )
    assert "test_compose_sandbox_builder_works_without_docker" in text, (
        "يجب توثيق الاختبار الذي يسدّ فجوة التغطية التي سمحت بالخطأ بالوصول إلى CI"
    )


def test_environment_states_docker_availability_truthfully():
    """ما يوثّه ENVIRONMENT.md يجب أن يطابق واقع البيئة (دليل لا ادعاء)."""
    text = read("docs/ENVIRONMENT.md")
    if shutil.which("docker") is None:
        assert "command not found" in text, "Docker غير مثبت هنا، ويجب أن يقول المستند ذلك صراحة"
        assert "docker compose build" in text, "يجب توثيق الأوامر البديلة التي على المضيف تشغيلها"


def test_environment_documents_sqlite_volume_and_ports():
    """توثيق سلوك البيانات والمنافذ في وضع الحاويات."""
    text = read("docs/ENVIRONMENT.md")
    assert "nexus-osint-data" in text, "يجب توثيق اسم الـ volume الدائم"
    assert "docker compose down -v" in text, "يجب توضيح الفرق بين down و down -v"
    assert "/api/v1/health" in text, "يجب توثيق مسار الفحص الحقيقي (/api/v1/health)"
    assert "alembic upgrade head" in text, "يجب توثيق أن الهجرات خطوة تشغيل في وضع الحاويات"
    for token in ("app.main:app", "MIGRATE_ON_START", "uvicorn>=0.30", "app/data/aatm.db"):
        assert token in text, f"التوثيق يجب أن يذكر عقد الخلفية المدموجة: {token}"
    assert "docker compose down -v" in text


# -------------------------------------------------
# التحقق الفعلي عبر Compose (يتطلب Docker): خلفية المستودع الحقيقية + واجهة بديلة
# -------------------------------------------------
FRONTEND_FIXTURE_BUILD = '''
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
mkdirSync("dist", { recursive: true });
writeFileSync("dist/index.html", readFileSync("index.html", "utf8").replace(/__MARKER__/g, "built-by-dockerfile-frontend"));
for (const asset of ["app.js", "app.css"]) {
  writeFileSync("dist/" + asset, readFileSync(asset, "utf8"));
}
console.log("dist built");
'''


def _compose_sandbox(tmp_path: Path) -> Path:
    """نسخة من جذر البناء تستخدم **الخلفية الحقيقية من المستودع** وبديلًا مؤقتًا للواجهة.

    الواجهة (`frontend/`) لم تُدمج بعد في `main`، لذلك تُنشأ هنا شيفرة بسيطة داخل
    الدليل المؤقت فقط — أما `backend/` فيُنسخ كما هو، فيُختبَر ملفا Dockerfile
    و nginx.conf و Compose مقابل التطبيق الحقيقي (مساراته ومصادقته وقاعدته).
    """
    work = tmp_path / "repo"
    (work / "docker").mkdir(parents=True)
    for rel, dest in (
        ("docker-compose.yml", "docker-compose.yml"),
        ("docker-compose.override.yml", "docker-compose.override.yml"),
        (".env.example", ".env.example"),
        (".dockerignore", ".dockerignore"),
        ("docker/nginx.conf", "docker/nginx.conf"),
        ("docker/Dockerfile.backend", "docker/Dockerfile.backend"),
        ("docker/Dockerfile.frontend", "docker/Dockerfile.frontend"),
    ):
        shutil.copy2(ROOT / rel, work / dest)

    real_backend = ROOT / "backend"
    if real_backend.is_dir():
        shutil.copytree(
            real_backend, work / "backend",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "var", ".env", "node_modules"),
        )
    else:  # بيئة قديمة بلا شريحة خلفية: بحدّ أدنى يمنع فشل التحليل فقط
        (work / "backend" / "app").mkdir(parents=True)
        (work / "backend" / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
        (work / "backend" / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    assert (work / "backend" / "requirements.txt").is_file(), "backend/requirements.txt مفقود من المستودع"

    fe = work / "frontend"
    fe.mkdir()
    (fe / "package.json").write_text(
        json.dumps({
            "name": "nexus-frontend-fixture",
            "private": True,
            "version": "0.0.0",
            "scripts": {"build": "node build.mjs", "dev": "node dev-server.mjs"},
        }) + "\n",
        encoding="utf-8",
    )
    (fe / "index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<title>__MARKER__</title><link rel="stylesheet" href="/app.css">'
        '<script src="/app.js" defer></script></head><body><h1>__MARKER__</h1></body></html>\n',
        encoding="utf-8",
    )
    (fe / "app.js").write_text(
        "fetch('/api/v1/health').then(r => r.json()).then(d => { document.title = d.status; });\n", encoding="utf-8"
    )
    (fe / "app.css").write_text("body{font-family:system-ui;margin:2rem}\n", encoding="utf-8")
    (fe / "build.mjs").write_text(FRONTEND_FIXTURE_BUILD.lstrip("\n"), encoding="utf-8")
    (fe / "dev-server.mjs").write_text(
        "import http from 'node:http';\n"
        "import { readFileSync } from 'node:fs';\n"
        "const port = Number(process.env.PORT || 8080);\n"
        "http.createServer((req, res) => {\n"
        "  res.writeHead(200, {'content-type': 'text/html; charset=utf-8'});\n"
        "  res.end(readFileSync('index.html', 'utf8').replace(/__MARKER__/g, 'dev-server'));\n"
        "}).listen(port, '0.0.0.0', () => console.log('dev server on ' + port));\n",
        encoding="utf-8",
    )
    (work / ".env").write_text(
        "APP_ENV=development\nBACKEND_PORT=8000\nFRONTEND_PORT=3000\nAPI_V1_PREFIX=/api/v1\n", encoding="utf-8"
    )
    return work


def _free_port() -> int:
    """منفذ حر على حلقة الاسترجاع، لتفادي تعارض المنافذ المنشورة بين التشغيلات."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_request(method: str, url: str, attempts: int = 30, extra: list[str] | None = None) -> str:
    last = ""
    argv = ["curl", "-s", "-S", "-m", "10", "-X", method] + list(extra or []) + [url]
    for _ in range(attempts):
        result = subprocess.run(argv, capture_output=True, text=True)
        last = result.stdout
        if result.returncode == 0 and last.strip():
            return last
        subprocess.run(["sleep", "1"])
    return last


def _http_get(url: str) -> str:
    return _http_request("GET", url)


def test_compose_sandbox_builder_works_without_docker(tmp_path):
    """مُنشئ نموذج التكامل يعمل بلا Docker — يمنع أن يظهر NameError/خطأ مسار في CI فقط.

    درسه من واقع أمرٍ وقع: استبدال المُنشئ أزال ثابته، ففشلت ثلاثة اختبارات في CI
    ونجحت محليًا (كانت تُتخطّى لغياب Docker). لذلك يُستدعى المُنشئ هنا بلا Docker،
    وتُنفَّذ `build.mjs` بفعلها إن كان node متاحًا.
    """
    work = _compose_sandbox(tmp_path)
    for rel in (
        "docker-compose.yml", "docker-compose.override.yml", ".dockerignore", ".env.example", ".env",
        "docker/Dockerfile.backend", "docker/Dockerfile.frontend", "docker/nginx.conf",
        "backend/requirements.txt", "backend/app/main.py", "frontend/package.json",
        "frontend/index.html", "frontend/app.js", "frontend/app.css", "frontend/build.mjs",
        "frontend/dev-server.mjs",
    ):
        assert (work / rel).is_file(), f"نموذج التكامل ينقصه {rel}"
    pkg = json.loads((work / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert pkg["scripts"] == {"build": "node build.mjs", "dev": "node dev-server.mjs"}, pkg["scripts"]
    # الخلفية في النموذج هي خلية المستودع نفسها، لا ملف بديل.
    assert "create_app" in (work / "backend" / "app" / "main.py").read_text(encoding="utf-8"), (
        "يجب أن ينسخ النموذج backend/ الحقيقية بعد دمجها"
    )
    assert not list((work / "backend").rglob(".env")), "لا يجوز أن ينجرف .env المحلي إلى سياق البناء"
    if shutil.which("node") is None:
        pytest.skip("node غير متاح في هذه البيئة")
    built = subprocess.run(["node", "build.mjs"], cwd=str(work / "frontend"), capture_output=True, text=True)
    assert built.returncode == 0, f"فشل نموذج البناء: {built.stderr}"
    html = (work / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    assert "built-by-dockerfile-frontend" in html, html[:200]


@needs_docker
@integration
def test_docker_compose_config_is_valid(tmp_path):
    """``docker compose config`` يقبل الملف الأساسي ونسخة override المدمجة معه."""
    work = _compose_sandbox(tmp_path)
    for args in (["config", "--quiet"], ["-f", "docker-compose.yml", "config", "--quiet"],
                 ["-f", "docker-compose.yml", "-f", "docker-compose.override.yml", "config", "--quiet"]):
        result = subprocess.run(["docker", "compose", *args], capture_output=True, text=True, cwd=str(work), timeout=180)
        assert result.returncode == 0, f"docker compose {' '.join(args)} فشل:\n{result.stderr}"
    listed = subprocess.run(["docker", "compose", "config", "--services"], capture_output=True, text=True, cwd=str(work), timeout=180)
    assert sorted(listed.stdout.split()) == ["backend", "frontend"], listed.stdout


@needs_docker_build
@integration
def test_docker_compose_up_serves_frontend_proxies_api_and_persists_sqlite(tmp_path):
    """التحقق الكامل: بناء الصورتين، خدمة الواجهة على منفذ منشور، تمرير /api إلى
    **الخلفية الحقيقية**، وبقاء بيانات SQLite في volume دائم بعد إعادة الإنشاء.
    """
    work = _compose_sandbox(tmp_path)
    ports = {name: _free_port() for name in ("backend", "frontend")}
    api_key = "ci-only-not-a-secret"
    (work / ".env").write_text(
        "APP_ENV=development\n"
        "BACKEND_PORT=8000\n"
        f"BACKEND_HOST_PORT={ports['backend']}\n"
        f"FRONTEND_PORT={ports['frontend']}\n"
        "API_V1_PREFIX=/api/v1\n"
        f"API_KEY={api_key}\n",
        encoding="utf-8",
    )
    project = f"nexus-itest-{os.getpid()}"
    volume = "nexus-osint-data"
    base = ["docker", "compose", "-p", project, "-f", "docker-compose.yml"]

    def compose(*args, timeout=600):
        return subprocess.run([*base, *args], capture_output=True, text=True, cwd=str(work), timeout=timeout)

    def dump_state(tag):
        state = compose("ps", "--all")
        logs = compose("logs", "--no-color", timeout=180)
        return f"[{tag}]\ncompose ps:\n{state.stdout}{state.stderr}\nlogs:\n{logs.stdout[-8000:]}{logs.stderr[-2000:]}"

    def curl(method, url, *extra):
        return _http_request(method, url, extra=list(extra))

    try:
        # بيئة نظيفة: volume باسم ثابت قد يبقى من تشغيل سابق.
        subprocess.run(["docker", "volume", "rm", volume], capture_output=True, text=True)

        built = compose("build", timeout=1800)
        assert built.returncode == 0, f"فشل بناء الصورتين:\n{built.stdout[-4000:]}\n{built.stderr[-2000:]}"

        up = compose("up", "-d", "--wait", "--wait-timeout", "180", timeout=400)
        assert up.returncode == 0, dump_state("up") + f"\n{up.stdout[-2000:]}{up.stderr[-2000:]}"

        fe = f"http://127.0.0.1:{ports['frontend']}"
        be = f"http://127.0.0.1:{ports['backend']}"

        # 1) الواجهة تُخدم من الحاوية على منفذ منشور.
        page = _http_get(f"{fe}/")
        assert "<!doctype html>" in page, f"الواجهة لم تُخدم عبر nginx:\n{page[:300]}\n{dump_state('index')}"
        assert "built-by-dockerfile-frontend" in page, "مخرجات npm run build لم تُخدم من nginx"

        # 2) الأصول الثابتة + SPA fallback.
        assert "font-family" in _http_get(f"{fe}/app.css"), "الأصول الثابتة لا تُخدم من nginx"
        assert "<!doctype html>" in _http_get(f"{fe}/projects/42"), "SPA fallback (try_files) لا يعمل"

        # 3) /api/v1 يصل إلى التطبيق الحقيقي عبر nginx (نفس المسار بلا rewrite).
        api = _http_get(f"{fe}/api/v1/health")
        assert '"status":"ok"' in api or '"status": "ok"' in api, (
            f"تمرير /api إلى الخلفية الحقيقية فشل:\n{api[:300]}\n{dump_state('api')}"
        )
        assert "version" in api, f"الاستجابة ليست من عقد الخلفية المتوقع:\n{api[:300]}"
        assert '"status":"ok"' in _http_get(f"{be}/api/v1/health") or "ok" in _http_get(f"{be}/api/v1/health"), (
            "الخلفية لا تجيب على منفذها المنشور"
        )
        ready = _http_get(f"{fe}/api/v1/health/ready")
        assert "ready" in ready, f"فحص الاتصال بالقاعدة عبر nginx فشل:\n{ready[:300]}"

        # 4) المصادقة تمرّ عبر nginx كما في التطبيق (Q5): بلا مفتاح ⇒ 401.
        unauth = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10", "-X", "POST",
             f"{fe}/api/v1/sessions", "-H", "content-type: application/json", "-d", "{}"],
            capture_output=True, text=True,
        )
        assert unauth.stdout.strip() == "401", f"كان يجب 401 بلا مفتاح، جاء {unauth.stdout.strip()}"

        # 5) الهجرات خطوة تشغيل صريحة (الموثّقة في docker-compose.yml).
        migrated = compose("exec", "-T", "backend", "alembic", "upgrade", "head", timeout=300)
        assert migrated.returncode == 0, f"alembic upgrade head فشل:\n{migrated.stdout[-1500:]}{migrated.stderr[-1500:]}"

        # 6) كتابة سجل حقيقي ثم إعادة إنشاء الحاويات: البيانات تبقى في الـ volume.
        # task_id فريد لكل تشغيل: اسم الـ volume ثابت (`nexus-osint-data`) وقد يبقى من
        # تشغيل سابق، و POST على نفس المهمة يعيد 409 (لا 201) حسب عقد الجلسات.
        body = ('{"task_id":"aatm-c740feee-%08d","employee_id":"worker-5",'
                '"branch":"arena/82fdba0c-test-program","worktree":"/app/backend"}' % os.getpid())
        created = curl("POST", f"{fe}/api/v1/sessions", "-H", f"X-API-Key: {api_key}",
                       "-H", "content-type: application/json", "-d", body)
        assert '"task_id"' in created, f"لم يُنشأ السجل عبر nginx:\n{created[:400]}\n{dump_state('create')}"
        session_id = ""
        match = re.search(r'"id"\s*:\s*"(ses_[0-9a-f]+)"', created)
        if match:
            session_id = match.group(1)
        assert session_id, f"تعذّر قراءة معرّف الجلسة من: {created[:300]}"

        volumes = subprocess.run(["docker", "volume", "ls", "--filter", f"name={volume}", "--format", "{{.Name}}"],
                                 capture_output=True, text=True)
        assert volume in volumes.stdout, f"لم يُنشأ الـ volume المُسمّى: {volumes.stdout!r}"
        inside = compose("exec", "-T", "backend", "python", "-c",
                         "import glob; print(sorted(glob.glob('/app/data/*')))")
        assert "aatm.db" in inside.stdout, f"ملف القاعدة ليس في مسار الـ volume: {inside.stdout}{inside.stderr}"

        down = compose("down", timeout=400)
        assert down.returncode == 0, dump_state("down") + f"\n{down.stderr[-1500:]}"
        up2 = compose("up", "-d", "--wait", "--wait-timeout", "180", timeout=400)
        assert up2.returncode == 0, dump_state("re-up") + f"\n{up2.stderr[-1500:]}"
        after = curl("GET", f"{fe}/api/v1/sessions/{session_id}", "-H", f"X-API-Key: {api_key}")
        assert session_id in after and "aatm-c740feee" in after, (
            f"بيانات SQLite ضاعت بعد إعادة الإنشاء — الـ volume ليس دائمًا؟\n{after[:400]}"
        )

        # 7) الأمان: الحاوية لا تعمل بالجذر.
        who = compose("exec", "-T", "backend", "id", "-u")
        assert who.stdout.strip() != "0", f"يجب أن تعمل الخلفية بمستخدم غير جذري: {who.stdout.strip()}"
    finally:
        compose("down", "-v", "--remove-orphans", timeout=400)


@needs_docker_build
@integration
def test_docker_compose_override_switches_to_dev_target(tmp_path):
    """override يبدّل الواجهة إلى خادم التطوير (npm run dev) مع تسخّر الكود."""
    work = _compose_sandbox(tmp_path)
    port = _free_port()
    (work / ".env").write_text(
        f"APP_ENV=development\nBACKEND_PORT=8000\nBACKEND_HOST_PORT={_free_port()}\nFRONTEND_PORT={port}\nAPI_PREFIX=/api\n",
        encoding="utf-8",
    )
    project = f"nexus-itest-dev-{os.getpid()}"
    base = ["docker", "compose", "-p", project, "up", "-d", "--build"]
    try:
        up = subprocess.run([*base], capture_output=True, text=True, cwd=str(work), timeout=1800)
        assert up.returncode == 0, f"docker compose up بوضع التطوير فشل:\n{up.stdout[-4000:]}\n{up.stderr[-2000:]}"
        page = _http_get(f"http://127.0.0.1:{port}/")
        assert "dev-server" in page, f"خادم التطوير لم يخدم الصفحة:\n{page[:300]}"
        listing = subprocess.run(
            ["docker", "compose", "-p", project, "ps", "--format", "{{.Service}} {{.Image}}"],
            capture_output=True, text=True, cwd=str(work), timeout=180,
        )
        assert "frontend" in listing.stdout, listing.stdout
    finally:
        subprocess.run(["docker", "compose", "-p", project, "down", "-v", "--remove-orphans"],
                       capture_output=True, text=True, cwd=str(work), timeout=400)
