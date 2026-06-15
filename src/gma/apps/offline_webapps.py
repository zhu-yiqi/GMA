from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gma.apps._shell import run_bash
from gma.apps.backend_baseline import BackendBaselineSpec, restore_backend_baseline

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


@dataclass(frozen=True)
class OfflineWebApp:
    label: str
    archive: str
    archive_flags: str
    export_root: str
    project_subdir: str
    compose_project: str
    containers: tuple[str, ...]
    health_urls: tuple[str, ...]
    wait_seconds: int
    archive_candidates: tuple[str, ...] = ()
    archive_prefixes: tuple[str, ...] = (
        "/app/dev",
        "/app/mobileworld",
        "/data/zhuyiqi/GMA",
        "/data/zhuyiqi",
    )

    @property
    def project_dir(self) -> str:
        return f"{self.export_root}/{self.project_subdir}"

    @property
    def archive_names(self) -> str:
        return " ".join(self.archive_candidates or (self.archive,))

    @property
    def archive_prefix_list(self) -> str:
        return " ".join(self.archive_prefixes)


MALL = OfflineWebApp(
    label="Mall",
    archive="mall-deploy.zip",
    archive_flags="xf",
    export_root="/tmp/gma_mall_export",
    project_subdir="mall",
    compose_project="gma-mall",
    containers=(
        "mall-mysql",
        "mall-redis",
        "mall-rabbitmq",
        "mall-mongo",
        "mall-minio",
        "mall-admin",
        "mall-portal",
        "mall-admin-web",
        "mall-app-web",
    ),
    health_urls=("http://localhost:8040", "http://localhost:8042"),
    wait_seconds=240,
    archive_candidates=("mall-deploy.zip",),
)

MEITUAN = OfflineWebApp(
    label="Meituan",
    archive="meituan-export.zip",
    archive_flags="xf",
    export_root="/tmp/gma_meituan_export",
    project_subdir="meituan",
    compose_project="gma-meituan",
    containers=("meituan-mongo", "meituan-backend", "meituan-frontend"),
    health_urls=("http://localhost:8050/meituan/",),
    wait_seconds=150,
    archive_candidates=("meituan-export.zip",),
)

XIAOSHILIU = OfflineWebApp(
    label="XiaoShiLiu",
    archive="xiaoshiliu-offline-deploy.tar.gz",
    archive_flags="xzf",
    export_root="/tmp/gma_xiaoshiliu_export",
    project_subdir="xiaoshiliu",
    compose_project="xiaoshiliu",
    containers=("xiaoshiliu-mysql", "xiaoshiliu-backend", "xiaoshiliu-frontend"),
    health_urls=("http://localhost:8031/api/health", "http://localhost:8030"),
    wait_seconds=120,
)

HMDP = OfflineWebApp(
    label="HMDP",
    archive="hmdp-export.zip",
    archive_flags="xzf",
    export_root="/tmp/gma_hmdp_export",
    project_subdir="hmdp",
    compose_project="gma-hmdp",
    containers=("hmdp-mysql", "hmdp-redis", "hmdp-kafka", "hmdp-backend", "hmdp-frontend"),
    health_urls=("http://localhost:8070/hmdp/", "http://localhost:8071/shop-type/list"),
    wait_seconds=360,
    archive_candidates=("hmdp-export.zip", "hmdp-deploy.zip"),
)

TRAVEL = OfflineWebApp(
    label="Travel",
    archive="travel-app-migration-pack.tar.gz",
    archive_flags="xzf",
    export_root="/tmp/gma_travel_export",
    project_subdir="travel-app-migration-pack",
    compose_project="travel-app-migration-pack",
    containers=("travel-mongo", "travel-app", "travel-nginx"),
    health_urls=("http://localhost:8060/trip",),
    wait_seconds=240,
    archive_candidates=("travel-app-migration-pack.tar.gz",),
    archive_prefixes=("/app/dev", "/app/mobileworld"),
)


def _compose(app: OfflineWebApp, command: str) -> str:
    return (
        f"cd {app.project_dir} && "
        "compose_files='-f docker-compose.yml'; "
        "if [ -f docker-compose.override.yml ]; then "
        "compose_files=\"$compose_files -f docker-compose.override.yml\"; "
        "fi; "
        f"docker compose --project-name {app.compose_project} $compose_files {command}"
    )


def _container_rm_args(app: OfflineWebApp) -> str:
    return " ".join(app.containers)


def offline_backend_baseline(app: OfflineWebApp) -> BackendBaselineSpec:
    return BackendBaselineSpec(
        label=app.label,
        project_dir=app.project_dir,
        compose_up=_compose(app, "up -d"),
        compose_down=_compose(app, "down --remove-orphans"),
        containers=app.containers,
        volume_prefixes=(app.compose_project, app.project_subdir),
        health_urls=app.health_urls,
        wait_seconds=app.wait_seconds,
    )


def _prepare_travel_reference_data(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -eu
if ! docker ps --format '{{.Names}}' | grep -qx travel-mongo; then
  exit 0
fi
cat >/tmp/gma_travel_reference.js <<'JS'
const timelineStart = new Date('2026-10-01T00:00:00.000Z');
const targetDate = new Date('2026-09-30T00:00:00.000Z');
const targetExpireAt = new Date(targetDate.getTime() - 30 * 60 * 1000);
const preTimelineCutoff = new Date('2026-09-01T00:00:00.000Z');

function shiftDateValue(value, deltaMs) {
  return value && typeof value.getTime === 'function' ? new Date(value.getTime() + deltaMs) : value;
}

function cutoffForFlightDate(value) {
  return value && typeof value.getTime === 'function'
    ? new Date(value.getTime() - 30 * 60 * 1000)
    : value;
}

function applyBulk(collectionName, operations) {
  if (operations.length) {
    db.getCollection(collectionName).bulkWrite(operations, {ordered: false});
  }
}

function normalizeFlightExpiryForSegments(query) {
  let segmentOps = [];
  let seatOps = [];
  function flush() {
    applyBulk('flightsegments', segmentOps);
    applyBulk('flightseats', seatOps);
    segmentOps = [];
    seatOps = [];
  }
  db.flightsegments.find(query).forEach(segment => {
    const expireAt = cutoffForFlightDate(segment.date);
    if (!expireAt) return;
    if (!segment.expireAt || segment.expireAt.getTime() !== expireAt.getTime()) {
      segmentOps.push({updateOne: {filter: {_id: segment._id}, update: {$set: {
        expireAt,
        updatedAt: new Date(),
      }}}});
    }
    const seatIds = segment.seats || [];
    if (seatIds.length) {
      seatOps.push({updateMany: {filter: {_id: {$in: seatIds}, $or: [
        {expireAt: {$exists: false}},
        {expireAt: {$ne: expireAt}},
      ]}, update: {$set: {
        expireAt,
        updatedAt: new Date(),
      }}}});
    }
    if (segmentOps.length + seatOps.length >= 500) flush();
  });
  flush();
}

const firstTimelineItinerary = db.flightitineraries.find({date: {$type: 'date'}}).sort({date: 1, _id: 1}).limit(1).toArray()[0];
if (firstTimelineItinerary && firstTimelineItinerary.date < preTimelineCutoff) {
  const deltaMs = timelineStart.getTime() - firstTimelineItinerary.date.getTime();
  const itineraryOps = [];
  db.flightitineraries.find({date: {$type: 'date', $lt: preTimelineCutoff}}).forEach(doc => {
    itineraryOps.push({updateOne: {filter: {_id: doc._id}, update: {$set: {
      date: shiftDateValue(doc.date, deltaMs),
      expireAt: shiftDateValue(doc.expireAt, deltaMs),
      updatedAt: new Date(),
    }}}});
  });
  applyBulk('flightitineraries', itineraryOps);

  const segmentOps = [];
  db.flightsegments.find({date: {$type: 'date', $lt: preTimelineCutoff}}).forEach(doc => {
    const shiftedDate = shiftDateValue(doc.date, deltaMs);
    const shiftedDeparture = shiftDateValue(doc.from && doc.from.scheduledDeparture, deltaMs);
    const shiftedArrival = shiftDateValue(doc.to && doc.to.scheduledArrival, deltaMs);
    segmentOps.push({updateOne: {filter: {_id: doc._id}, update: {$set: {
      date: shiftedDate,
      expireAt: cutoffForFlightDate(shiftedDate),
      'from.scheduledDeparture': shiftedDeparture,
      'to.scheduledArrival': shiftedArrival,
      updatedAt: new Date(),
    }}}});
  });
  applyBulk('flightsegments', segmentOps);
}

normalizeFlightExpiryForSegments({date: {$type: 'date', $gte: timelineStart}});

let itinerary = db.flightitineraries.findOne({flightCode: 'EK2106', departureAirportId: 'DXB', arrivalAirportId: 'LHR'});
if (!itinerary) {
  itinerary = db.flightitineraries.find({departureAirportId: 'DXB', arrivalAirportId: 'LHR'}).sort({date: 1, _id: 1}).limit(1).toArray()[0];
}
const ekAirplane = db.airplanes.findOne({airlineId: 'EK'}) || db.airplanes.findOne({});
const ekAirplanePatch = ekAirplane && ekAirplane._id ? {airplaneId: ekAirplane._id} : {};
if (!itinerary) {
  const itineraryId = ObjectId('6a04821d3603c9908e3d1ff8');
  const segmentId = ObjectId('6a04821d3603c9908e3708b0');
  const arrivalDate = new Date(targetDate.getTime() + (9 * 60 * 60 * 1000 + 56 * 60 * 1000));
  db.flightsegments.updateOne({_id: segmentId}, {$set: {
    flightNumber: 'EK2106-1',
    airlineId: 'EK',
    date: targetDate,
    'from.airport': 'DXB',
    'from.scheduledDeparture': targetDate,
    'to.airport': 'LHR',
    'to.scheduledArrival': arrivalDate,
    durationMinutes: 596,
    ...ekAirplanePatch,
    seats: [],
    expireAt: targetExpireAt,
    updatedAt: new Date(),
  }, $setOnInsert: {_id: segmentId, createdAt: new Date()}}, {upsert: true});
  db.flightitineraries.updateOne({_id: itineraryId}, {$set: {
    flightCode: 'EK2106',
    carrierInCharge: 'EK',
    departureAirportId: 'DXB',
    arrivalAirportId: 'LHR',
    date: targetDate,
    expireAt: targetExpireAt,
    segmentIds: [segmentId],
    updatedAt: new Date(),
  }, $setOnInsert: {_id: itineraryId, createdAt: new Date()}}, {upsert: true});
  itinerary = db.flightitineraries.findOne({_id: itineraryId});
}
if (itinerary) {
  const segmentIds = itinerary.segmentIds || [];
  const firstSegment = segmentIds.length ? db.flightsegments.findOne({_id: segmentIds[0]}) : null;
  const durationMs = firstSegment && firstSegment.to && firstSegment.to.scheduledArrival && firstSegment.from && firstSegment.from.scheduledDeparture
    ? new Date(firstSegment.to.scheduledArrival).getTime() - new Date(firstSegment.from.scheduledDeparture).getTime()
    : 9 * 60 * 60 * 1000 + 56 * 60 * 1000;
  const durationMinutes = Math.max(60, Math.round(durationMs / 60000));
  const arrivalDate = new Date(targetDate.getTime() + Math.max(durationMs, 60 * 60 * 1000));
  db.flightitineraries.updateOne({_id: itinerary._id}, {$set: {
    flightCode: 'EK2106',
    carrierInCharge: 'EK',
    departureAirportId: 'DXB',
    arrivalAirportId: 'LHR',
    date: targetDate,
    expireAt: targetExpireAt,
    updatedAt: new Date(),
  }});
  if (segmentIds.length) {
    db.flightsegments.updateOne({_id: segmentIds[0]}, {$set: {
      flightNumber: 'EK2106-1',
      airlineId: 'EK',
      date: targetDate,
      'from.airport': 'DXB',
      'from.scheduledDeparture': targetDate,
      'to.airport': 'LHR',
      'to.scheduledArrival': arrivalDate,
      durationMinutes,
      ...ekAirplanePatch,
      expireAt: targetExpireAt,
      updatedAt: new Date(),
    }});
    if (segmentIds.length > 1) {
      db.flightsegments.updateMany({_id: {$in: segmentIds.slice(1)}}, {$set: {date: targetDate, expireAt: targetExpireAt, updatedAt: new Date()}});
    }
    const ek2106Segments = db.flightsegments.find({_id: {$in: segmentIds}}).toArray();
    const ek2106SeatIds = ek2106Segments.flatMap(segment => segment.seats || []);
    if (ek2106SeatIds.length) {
      db.flightseats.updateMany({_id: {$in: ek2106SeatIds}}, {$set: {expireAt: targetExpireAt, updatedAt: new Date()}});
    }
  }
}
JS
docker exec -i travel-mongo mongosh --quiet -u travel -p travel_root_2025 --authenticationDatabase admin travel < /tmp/gma_travel_reference.js >/dev/null
""",
        timeout=180,
    )


def _clear_travel_task_state(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -eu
if ! docker ps --format '{{.Names}}' | grep -qx travel-mongo; then
  exit 0
fi
cat >/tmp/gma_travel_clear_task_state.js <<'JS'
for (const name of ['flightbookings', 'flightpayments', 'passengers', 'hotelbookings', 'hotelpayments', 'hotelguests', 'attractionbookings', 'attractionpayments']) {
  db.getCollection(name).deleteMany({});
}
db.users.updateMany({}, {$set: {'flights.bookmarked': [], 'hotels.bookmarked': [], 'attractions.bookmarked': [], updatedAt: new Date()}});
JS
docker exec -i travel-mongo mongosh --quiet -u travel -p travel_root_2025 --authenticationDatabase admin travel < /tmp/gma_travel_clear_task_state.js >/dev/null
""",
        timeout=60,
    )


def _prepare_travel_backend_state(client: AndroidController) -> None:
    _prepare_travel_reference_data(client)
    _clear_travel_task_state(client)


def reset_offline_webapp_backend(client: AndroidController, app: OfflineWebApp) -> None:
    if restore_backend_baseline(client, offline_backend_baseline(app)):
        if app.label == "Travel":
            _prepare_travel_backend_state(client)
        patch_offline_webapp_runtime(client, app)
        return
    run_bash(
        client,
        f"""
set -euo pipefail
if [ -d {app.project_dir} ]; then
  {_compose(app, "down -v --remove-orphans >/dev/null 2>&1 || true")}
fi
docker rm -f {_container_rm_args(app)} >/dev/null 2>&1 || true
for volume_prefix in {app.compose_project} {app.project_subdir}; do
  for volume in $(docker volume ls --format {{{{.Name}}}} | grep -E "^${{volume_prefix}}_" || true); do
    docker volume rm -f "$volume" >/dev/null 2>&1 || true
  done
done
rm -rf {app.export_root}
""",
        timeout=120,
    )


def ensure_offline_webapp_running(client: AndroidController, app: OfflineWebApp) -> None:
    """Fast path for loaded snapshots: verify health, rebuild only if missing."""
    health_checks = " && ".join(f"curl -fsS --max-time 5 {url} >/dev/null 2>&1" for url in app.health_urls)
    output = run_bash(
        client,
        f"""
set -euo pipefail
if {health_checks}; then
  echo healthy
else
  echo missing
fi
""",
        timeout=30,
    ).strip()
    if output == "healthy":
        return
    ensure_offline_webapp_backend(client, app)


def ensure_offline_webapp_backend(client: AndroidController, app: OfflineWebApp) -> None:
    health_checks = " && ".join(f"curl -fsS {url} >/dev/null 2>&1" for url in app.health_urls)
    status = run_bash(
        client,
        f"""
set -euo pipefail
if {health_checks}; then
  echo healthy
else
  echo missing
fi
""",
        timeout=30,
    ).strip()
    if status == "healthy":
        return
    run_bash(
        client,
        f"""
set -euo pipefail

archive=""
for name in {app.archive_names}; do
  for prefix in {app.archive_prefix_list}; do
    candidate="$prefix/$name"
    if [ -f "$candidate" ]; then
      archive="$candidate"
      break 2
    fi
  done
done
if [ -z "$archive" ]; then
  echo "{app.label} archive not found. Tried: {app.archive_names}" >&2
  exit 1
fi

if [ -d {app.project_dir} ]; then
  {_compose(app, "down -v --remove-orphans >/dev/null 2>&1 || true")}
fi
docker rm -f {_container_rm_args(app)} >/dev/null 2>&1 || true
for volume_prefix in {app.compose_project} {app.project_subdir}; do
  for volume in $(docker volume ls --format {{{{.Name}}}} | grep -E "^${{volume_prefix}}_" || true); do
    docker volume rm -f "$volume" >/dev/null 2>&1 || true
  done
done
rm -rf {app.export_root}
mkdir -p {app.export_root}
case "$archive" in
  *.zip|*.zip.crdownload) unzip -q "$archive" -d {app.export_root} ;;
  *) tar {app.archive_flags} "$archive" -C {app.export_root} ;;
esac
if [ "{app.label}" = "HMDP" ] && [ ! -d {app.project_dir} ] && [ -d {app.export_root}/hmdp-deploy/source/hmdp ]; then
  mv {app.export_root}/hmdp-deploy/source/hmdp {app.project_dir}
fi
if [ ! -d {app.project_dir} ]; then
  first_dir=$(find {app.export_root} -mindepth 1 -maxdepth 1 -type d | head -n 1)
  if [ -n "$first_dir" ]; then
    ln -s "$first_dir" {app.project_dir}
  fi
fi
if [ ! -d {app.project_dir} ]; then
  echo "{app.label} project directory not found after extracting $archive" >&2
  find {app.export_root} -maxdepth 2 -type d >&2 || true
  exit 1
fi
cd {app.project_dir}
python3 - <<PY
from pathlib import Path
import base64
import shutil
path = Path("docker-compose.yml")
text = path.read_text()
text = text.replace("http://localhost/", "http://127.0.0.1/")
if "{app.label}" == "Mall":
    text = text.replace("TZ=Asia/Shanghai", "TZ=UTC")
    text = text.replace("serverTimezone=Asia/Shanghai", "serverTimezone=UTC")
    text = text.replace(
        "mysqld --character-set-server=utf8mb4",
        "mysqld --innodb-use-native-aio=0 --character-set-server=utf8mb4",
    )
if "{app.label}" == "XiaoShiLiu":
    text = text.replace(
        "--default-authentication-plugin=mysql_native_password --character-set-server=utf8mb4",
        "--default-authentication-plugin=mysql_native_password --innodb-use-native-aio=0 --character-set-server=utf8mb4",
    )
if "{app.label}" == "HMDP":
    if '--innodb-use-native-aio=0' not in text:
        text = text.replace(
            '--default-authentication-plugin=mysql_native_password',
            '--default-authentication-plugin=mysql_native_password --innodb-use-native-aio=0',
        )
    text = text.replace(
        "--default-authentication-plugin=mysql_native_password --character-set-server=utf8mb4",
        "--default-authentication-plugin=mysql_native_password --innodb-use-native-aio=0 --character-set-server=utf8mb4",
    )
    text = text.replace(
        "./data/db/hmdp_0_full.sql:/docker-entrypoint-initdb.d/hmdp_0_full.sql",
        "./data/db/hmdp_0_full.sql:/hmdp-init/hmdp_0_full.sql:ro",
    )
    text = text.replace(
        "./data/db/hmdp_1_full.sql:/docker-entrypoint-initdb.d/hmdp_1_full.sql",
        "./data/db/hmdp_1_full.sql:/hmdp-init/hmdp_1_full.sql:ro",
    )
    init_script = Path("docker/mysql/init-db.sh")
    if init_script.exists():
        init_text = init_script.read_text()
        init_text = init_text.replace("/docker-entrypoint-initdb.d/hmdp_0_full.sql", "/hmdp-init/hmdp_0_full.sql")
        init_text = init_text.replace("/docker-entrypoint-initdb.d/hmdp_1_full.sql", "/hmdp-init/hmdp_1_full.sql")
        init_script.write_text(init_text)
path.write_text(text)

if '{app.label}' == 'Mall':
    for config_path in Path('backend').rglob('*'):
        if not config_path.is_file():
            continue
        if config_path.suffix not in {'.yml', '.yaml', '.properties'}:
            continue
        config_text = config_path.read_text(errors='replace')
        patched_config = config_text.replace('serverTimezone=Asia/Shanghai', 'serverTimezone=UTC')
        if patched_config != config_text:
            config_path.write_text(patched_config)

    sql_candidates = (
        Path('data-dumps/mall-full-dump.sql'),
        Path('init/mysql/mall-mysql-dump.sql'),
    )
    sql_path = next((path for path in sql_candidates if path.exists()), None)
    if sql_path is not None:
        sql_text = sql_path.read_text(errors='replace')
        if sql_text.startswith('mysqldump: [Warning]'):
            sql_path.write_text(''.join(sql_text.splitlines(True)[1:]))

mongo_restore = Path('docker/mongo/restore-mongo.sh')
if mongo_restore.exists():
    mongo_text = mongo_restore.read_text()
    dollar = chr(36)
    dq = chr(34)
    old_restore = 'mongorestore --archive=' + dq + dollar + 'ARCHIVE_FILE' + dq + ' --gzip --drop'
    new_restore = old_restore + ' || echo ' + dq + 'MongoDB archive restore failed; continuing without seeded Mongo data.' + dq
    mongo_text = mongo_text.replace(old_restore, new_restore)
    mongo_restore.write_text(mongo_text)

if '{app.label}' == 'HMDP':
    newline = chr(10)
    env_path = Path('.env')
    env_text = env_path.read_text() if env_path.exists() else ''
    desired = dict(
        MYSQL_PORT='8072',
        REDIS_PORT='8073',
        KAFKA_PORT='8074',
        BACKEND_PORT='8071',
        FRONTEND_PORT='8070',
    )
    lines = env_text.splitlines()
    seen = set()
    for idx, line in enumerate(lines):
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        key = line.split('=', 1)[0].strip()
        if key in desired:
            lines[idx] = key + '=' + desired[key]
            seen.add(key)
    for key, value in desired.items():
        if key not in seen:
            lines.append(key + '=' + value)
    env_path.write_text(newline.join(lines).rstrip() + newline)

    package_data_candidates = (
        Path('data'),
        Path('../hmdp-deploy/data'),
        Path('../hmdp-export/data'),
        Path('../hmdp-package/data'),
    )
    package_data = next((candidate for candidate in package_data_candidates if candidate.exists()), package_data_candidates[0])
    sql_map = (
        (package_data / 'db/hmdp_0_full.sql', Path('sql/hmdp_0.sql')),
        (package_data / 'db/hmdp_1_full.sql', Path('sql/hmdp_1.sql')),
    )
    for source, target in sql_map:
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    photos_source = package_data / 'yelp-photos'
    photos_target = Path('hmdp-vue3/public/yelp-photos')
    if photos_source.exists():
        shutil.rmtree(photos_target, ignore_errors=True)
        shutil.copytree(photos_source, photos_target)

    for dist_file in Path('hmdp-vue3/dist').rglob('*.js'):
        dist_text = dist_file.read_text(errors='replace')
        patched = dist_text.replace('x:120.149993,y:30.334229', 'x:null,y:null')
        import base64 as _gma_b64
        home_setup_old = _gma_b64.b64decode('c2V0dXAoZyl7Y29uc3QgYT1rKCExKSxkPWsoW10pLGk9ayhbXSkscj1rKDEpLGg9SSgoKT0+aS52YWx1ZS5maWx0ZXIoKG8sZSk9PmUlMj09PTApKSxXPUkoKCk9PmkudmFsdWUuZmlsdGVyKChvLGUpPT5lJTI9PT0xKSk7').decode('utf-8')
        home_setup_new = _gma_b64.b64decode('c2V0dXAoZyl7Y29uc3QgYT1rKCExKSxkPWsoW10pLGk9ayhbXSkscj1rKDEpLEdNQXNlYXJjaD1rKCIiKSxHTUFkb1NlYXJjaD0oKT0+e2NvbnN0IG89KEdNQXNlYXJjaC52YWx1ZXx8IiIpLnRyaW0oKTtvJiZfLnB1c2goe3BhdGg6Ii9zaG9wTGlzdCIscXVlcnk6e2tleXdvcmQ6b319KX0saD1JKCgpPT5pLnZhbHVlLmZpbHRlcigobyxlKT0+ZSUyPT09MCkpLFc9SSgoKT0+aS52YWx1ZS5maWx0ZXIoKG8sZSk9PmUlMj09PTEpKTs=').decode('utf-8')
        patched = patched.replace(home_setup_old, home_setup_new)
        home_input_old = _gma_b64.b64decode('bCh5LHtzaXplOiJtaW5pIixwbGFjZWhvbGRlcjoiU2VhcmNoIHNob3BzLCBwbGFjZXMifSx7cHJlZml4OnUoKCk9PmVbMF18fChlWzBdPVtzKCJpIix7Y2xhc3M6ImVsLWlucHV0X19pY29uIGVsLWljb24tc2VhcmNoIn0sbnVsbCwtMSldKSksXzoxfSk=').decode('utf-8')
        home_input_new = _gma_b64.b64decode('bCh5LHttb2RlbFZhbHVlOkdNQXNlYXJjaC52YWx1ZSwib25VcGRhdGU6bW9kZWxWYWx1ZSI6dD0+R01Bc2VhcmNoLnZhbHVlPXQsc2l6ZToibWluaSIscGxhY2Vob2xkZXI6IlNlYXJjaCBzaG9wcywgcGxhY2VzIixvbktleXVwOnQ9Pnt0LmtleT09PSJFbnRlciImJkdNQWRvU2VhcmNoKCl9fSx7cHJlZml4OnUoKCk9PltzKCJpIix7Y2xhc3M6ImVsLWlucHV0X19pY29uIGVsLWljb24tc2VhcmNoIixzdHlsZTp7Y3Vyc29yOiJwb2ludGVyIn0sb25DbGljazpHTUFkb1NlYXJjaH0sbnVsbCldKSxfOjF9LDgsWyJtb2RlbFZhbHVlIl0p').decode('utf-8')
        patched = patched.replace(home_input_old, home_input_new)
        shop_toggle_old = _gma_b64.b64decode('Xz0oKT0+e2wudmFsdWU9IWwudmFsdWUsbC52YWx1ZXx8aS52YWx1ZSYmKGkudmFsdWU9ITEscy52YWx1ZT0iIixyLnZhbHVlPVtdLGMudmFsdWUuY3VycmVudD0xLGgoKSl9LGY9KCk9Pnt0LmJhY2soKX0=').decode('utf-8')
        shop_toggle_new = _gma_b64.b64decode('Xz0oKT0+e2lmKGwudmFsdWUmJnMudmFsdWUudHJpbSgpKXtnKCk7cmV0dXJufWwudmFsdWU9IWwudmFsdWUsbC52YWx1ZXx8aS52YWx1ZSYmKGkudmFsdWU9ITEscy52YWx1ZT0iIixyLnZhbHVlPVtdLGMudmFsdWUuY3VycmVudD0xLGgoKSl9LGY9KCk9Pnt0LmJhY2soKX0=').decode('utf-8')
        patched = patched.replace(shop_toggle_old, shop_toggle_new)
        if patched != dist_text:
            dist_file.write_text(patched)


    search_prompt_script = base64.b64decode('PHNjcmlwdCBpZD0iZ21hLWhtZHAtc2VhcmNoLXByb21wdCI+d2luZG93Ll9fZ21hSG1kcFNlYXJjaFByb21wdEluc3RhbGxlZD10cnVlOzwvc2NyaXB0Pg==').decode('utf-8')
    index_html = Path('hmdp-vue3/dist/index.html')
    if index_html.exists():
        html = index_html.read_text(errors='replace')
        marker = '<script id="gma-hmdp-search-prompt">'
        if marker in html:
            before, rest = html.split(marker, 1)
            if '</script>' in rest:
                _, after = rest.split('</script>', 1)
                html = before.rstrip() + newline + after.lstrip()
        if '</body>' in html:
            html = html.replace('</body>', search_prompt_script + newline + '</body>', 1)
        else:
            html = html + newline + search_prompt_script + newline
        index_html.write_text(html)
    frontend_dockerfile = Path('hmdp-vue3/Dockerfile')
    if frontend_dockerfile.exists():
        frontend_dockerfile.write_text(newline.join([
            'FROM nginx:1.25-alpine',
            'COPY dist /usr/share/nginx/html',
            'COPY src/assets/imgs /usr/share/nginx/html/src/assets/imgs',
            'COPY public/yelp-photos /usr/share/nginx/html/yelp-photos',
            'COPY nginx.conf /etc/nginx/conf.d/default.conf',
            'EXPOSE 80',
            'HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -q --spider http://127.0.0.1/hmdp/ || exit 1',
            'CMD ["nginx", "-g", "daemon off;"]',
        ]) + newline)

    backend_dockerfile = Path('hmdp-core-service/Dockerfile')
    if backend_dockerfile.exists():
        backend_lines = backend_dockerfile.read_text().splitlines()
        filtered = []
        skip_run_apk = False
        skip_health_cmd = False
        for line in backend_lines:
            if line == '# Install curl for healthcheck':
                skip_run_apk = True
                continue
            if skip_run_apk and line.startswith('RUN apk add --no-cache curl'):
                skip_run_apk = False
                continue
            if line.startswith('HEALTHCHECK --interval=30s'):
                skip_health_cmd = True
                continue
            if skip_health_cmd and line.strip().startswith('CMD curl -f http://localhost:8085/actuator/health'):
                skip_health_cmd = False
                continue
            filtered.append(line)
        backend_dockerfile.write_text(newline.join(filtered).rstrip() + newline)

    shop_service = Path('hmdp-core-service/src/main/java/org/javaup/service/impl/ShopServiceImpl.java')
    if shop_service.exists():
        service_text = shop_service.read_text()
        brace = chr(123)
        old = 'if (x == null || y == null) ' + brace
        new = 'if (x == null || y == null || (Math.abs(x) < 0.000001D && Math.abs(y) < 0.000001D)) ' + brace
        if new not in service_text:
            service_text = service_text.replace(old, new, 1)
            shop_service.write_text(service_text)

    def use_prebuilt_image(compose_text, service, image):
        lines = compose_text.splitlines()
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            out.append(line)
            i += 1
            if line != '  ' + service + ':':
                continue
            inserted = False
            while i < len(lines):
                current = lines[i]
                if current.startswith('  ') and not current.startswith('    ') and current.strip():
                    break
                if current.startswith('    image:'):
                    if not inserted:
                        out.append('    image: ' + image)
                        inserted = True
                    i += 1
                    continue
                if current.startswith('    build:'):
                    i += 1
                    while i < len(lines) and (lines[i].startswith('      ') or not lines[i].strip()):
                        i += 1
                    if not inserted:
                        out.append('    image: ' + image)
                        inserted = True
                    continue
                out.append(current)
                i += 1
            if not inserted:
                out.append('    image: ' + image)
        return newline.join(out) + newline

    compose_path = Path('docker-compose.yml')
    if compose_path.exists() and Path('../hmdp-deploy/images').exists():
        compose_text = compose_path.read_text()
        compose_text = use_prebuilt_image(compose_text, 'backend', 'hmdp-plus-backend:latest')
        compose_text = use_prebuilt_image(compose_text, 'frontend', 'hmdp-plus-frontend:latest')
        compose_path.write_text(compose_text)
PY
chmod +x deploy.sh || true
if [ "{app.label}" = "Travel" ]; then
  python3 - <<'PYTRAVEL'
from pathlib import Path
path = Path('nginx.conf')
if path.exists():
    text = path.read_text()
    text = text.replace('proxy_set_header Host $host;', 'proxy_set_header Host $http_host;')
    text = text.replace('proxy_set_header X-Forwarded-Host $host;', 'proxy_set_header X-Forwarded-Host $http_host;')
    path.write_text(text)
PYTRAVEL
  cat > .env <<'ENV'
NEXT_PUBLIC_BASE_URL=http://10.0.2.2:8060/trip
NEXT_PUBLIC_REVALIDATION_TIME=600
MONGO_ROOT_PASSWORD=travel_root_2025
MONGODB_URI=mongodb://travel:travel_root_2025@travel-mongo:27017/travel?authSource=admin
CRON_SECRET=travel_cron_2025_secret
API_SECRET_TOKEN=travel_api_token_2025
AUTH_TRUST_HOST=true
AUTH_URL=http://10.0.2.2:8060
AUTH_SECRET=travel_auth_secret_2025_replace_with_32plus_bytes_xx
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
AUTH_FACEBOOK_ID=
AUTH_FACEBOOK_SECRET=
MAIL_SENDER_EMAIL=
MAIL_API_TOKEN=
MAIL_SECRET_TOKEN=
NEXT_PUBLIC_STRIPE_PK=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
ENV
  cat > docker-compose.override.yml <<'YML'
services:
  travel-app:
    build: !reset null
    image: travel-app-travel-app:latest
YML
fi
image_dirs=""
if [ -d docker-images ]; then
  image_dirs="$image_dirs docker-images"
fi
if [ "{app.label}" = "HMDP" ] && [ -d ../hmdp-deploy/images ]; then
  image_dirs="$image_dirs ../hmdp-deploy/images"
fi
if [ -n "$image_dirs" ]; then
  if [ -d docker-images ] && [ -x ./load-images.sh ]; then
    COMPOSE_PROJECT_NAME={app.compose_project} ./load-images.sh
  fi
	  for image_dir in $image_dirs; do
	    for image_archive in "$image_dir"/*.tar "$image_dir"/*.tar.gz; do
	      [ -f "$image_archive" ] || continue
	      docker load -i "$image_archive" >/dev/null
	    done
	  done
	  if [ "{app.label}" = "HMDP" ] && [ -d hmdp-vue3 ] && [ -f hmdp-vue3/package-lock.json ]; then
	    if ! command -v npm >/dev/null 2>&1; then
	      if command -v apt-get >/dev/null 2>&1; then
	        apt-get update >/dev/null
	        DEBIAN_FRONTEND=noninteractive apt-get install -y npm >/dev/null
	      fi
	    fi
	    if ! command -v npm >/dev/null 2>&1; then
	      echo "npm is required to rebuild the HMDP frontend from source" >&2
	      exit 1
	    fi
	    (cd hmdp-vue3 && npm ci --prefer-offline --no-audit --no-fund && npm run build)
	    python3 - <<'PY2'
from pathlib import Path

script = '<script id="gma-hmdp-search-prompt">window.__gmaHmdpSearchPromptInstalled=true;</script>'
index_html = Path('hmdp-vue3/dist/index.html')
if index_html.exists():
    html = index_html.read_text(errors='replace')
    marker = '<script id="gma-hmdp-search-prompt">'
    if marker in html:
        before, rest = html.split(marker, 1)
        if '</script>' in rest:
            _, after = rest.split('</script>', 1)
            html = before.rstrip() + '\n' + after.lstrip()
    if '</body>' in html:
        html = html.replace('</body>', script + '\n</body>', 1)
    else:
        html = html.rstrip() + '\n' + script + '\n'
    index_html.write_text(html)
PY2
	    docker build -t hmdp-plus-frontend:latest hmdp-vue3 >/dev/null
	  fi
	  if [ "{app.label}" = "HMDP" ] && [ -d data/uploads ]; then
	    docker volume create {app.compose_project}_upload_data >/dev/null
	    docker run --rm \
	      -v {app.compose_project}_upload_data:/target \
	      -v "$(pwd)/data/uploads":/backup:ro \
	      --entrypoint sh \
	      hmdp-plus-frontend:latest \
	      -lc 'cp -rn /backup/. /target/ || true' >/dev/null 2>&1 || true
	  fi
	  if [ "{app.label}" = "HMDP" ] && [ -d ../hmdp-deploy/volumes ]; then
	    docker volume create {app.compose_project}_upload_data >/dev/null
	    docker run --rm -v {app.compose_project}_upload_data:/target -v "$(cd ../hmdp-deploy/volumes && pwd)":/backup alpine:latest sh -lc 'cd /target && tar xzf /backup/upload_data.tar.gz' >/dev/null 2>&1 || true
	    docker volume create {app.compose_project}_redis_data >/dev/null
    docker run --rm -v {app.compose_project}_redis_data:/target -v "$(cd ../hmdp-deploy/volumes && pwd)":/backup alpine:latest sh -lc 'cd /target && tar xzf /backup/redis_data.tar.gz' >/dev/null 2>&1 || true
  fi
  compose_files="-f docker-compose.yml"
  if [ -f docker-compose.override.yml ]; then
    compose_files="$compose_files -f docker-compose.override.yml"
  fi
  COMPOSE_PROJECT_NAME={app.compose_project} docker compose $compose_files up -d --force-recreate
else
  COMPOSE_PROJECT_NAME={app.compose_project} ./deploy.sh
fi

if [ "{app.label}" = "Travel" ]; then
  deadline=$((SECONDS + 240))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if docker exec travel-mongo mongosh --quiet -u travel -p travel_root_2025 --authenticationDatabase admin --eval 'db.adminCommand({{ping:1}}).ok' >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  if [ -f db-backup/travel-db-dump.tar.gz ]; then
    rm -rf /tmp/travel-dump
    mkdir -p /tmp/travel-dump
    tar -xzf db-backup/travel-db-dump.tar.gz -C /tmp/travel-dump --strip-components=1
    if [ -d /tmp/travel-dump/travel ]; then
      docker cp /tmp/travel-dump/travel travel-mongo:/tmp/travel-dump >/dev/null
      docker exec travel-mongo mongorestore -u travel -p travel_root_2025 --authenticationDatabase admin --db travel --drop /tmp/travel-dump --quiet
    fi
  fi
fi

deadline=$((SECONDS + {app.wait_seconds}))
while [ "$SECONDS" -lt "$deadline" ]; do
  if {health_checks}; then
    exit 0
  fi
  sleep 3
done

echo "{app.label} backend did not become ready" >&2
compose_files="-f docker-compose.yml"
if [ -f docker-compose.override.yml ]; then
  compose_files="$compose_files -f docker-compose.override.yml"
fi
docker compose --project-name {app.compose_project} $compose_files ps >&2 || true
docker compose --project-name {app.compose_project} $compose_files logs --tail=80 >&2 || true
exit 1
""",
        timeout=max(300, app.wait_seconds + 180),
    )
    if app.label == "Travel":
        _prepare_travel_reference_data(client)
    patch_offline_webapp_runtime(client, app)


def patch_offline_webapp_runtime(client: AndroidController, app: OfflineWebApp) -> None:
    if app.label == "Mall":
        _patch_mall_runtime(client)
    elif app.label == "Meituan":
        _patch_meituan_runtime(client)
    elif app.label == "XiaoShiLiu":
        _patch_xiaoshiliu_runtime(client)
    elif app.label == "HMDP":
        repair_hmdp_runtime(client)
    elif app.label == "Travel":
        _patch_travel_runtime(client)


def _patch_travel_runtime(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -eu
if ! docker ps --format '{{.Names}}' | grep -qx travel-app; then
  exit 0
fi
# The packaged Travel image was built with the public reference URL baked into
# Next.js client chunks. Inside the Android emulator the same service is
# reachable through 10.0.2.2, so rewrite the baked URL after container start.
docker exec -u root travel-app sh -lc '
  set -eu
  find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -print0 \
    | xargs -0 sed -i "s#http://101.37.229.242:8060/trip#http://10.0.2.2:8060/trip#g"
  find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -print0 \
    | xargs -0 sed -i "s#http://101.37.229.242/trip#http://10.0.2.2:8060/trip#g"
  find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -print0 \
    | xargs -0 sed -i "s#101.37.229.242:8060#10.0.2.2:8060#g; s#101.37.229.242#10.0.2.2#g"
  for file in /app/server.js /app/.next/required-server-files.json; do
    [ -f "$file" ] || continue
    sed -i "s#101.37.229.242:8060#10.0.2.2:8060#g; s#101.37.229.242#10.0.2.2#g" "$file"
  done
'
# Several Travel review tasks seed historical orders with bookingStatus
# "completed". The packaged app only allows and styles active states, so patch
# the compiled schemas and badge maps to treat completed bookings as valid.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const replacements = [
  [
    'bookingStatus:{type:String,enum:["confirmed","pending","cancelled"],default:"confirmed"}',
    'bookingStatus:{type:String,enum:["confirmed","pending","cancelled","completed"],default:"confirmed"}',
  ],
  [
    'bookingStatus:{type:String,enum:["confirmed","pending","cancelled"],default:"pending"}',
    'bookingStatus:{type:String,enum:["confirmed","pending","cancelled","completed"],default:"pending"}',
  ],
  [
    '{pending:"text-yellow-500",confirmed:"text-green-700",cancelled:"text-destructive",failed:"text-destructive"}',
    '{pending:"text-yellow-500",confirmed:"text-green-700",completed:"text-blue-700",cancelled:"text-destructive",failed:"text-destructive"}',
  ],
  [
    '{pending:"bg-yellow-100",confirmed:"bg-green-100",cancelled:"bg-red-100",failed:"bg-red-100"}',
    '{pending:"bg-yellow-100",confirmed:"bg-green-100",completed:"bg-blue-100",cancelled:"bg-red-100",failed:"bg-red-100"}',
  ],
  [
    '{confirmed:"bg-green-100 text-green-800",pending:"bg-yellow-100 text-yellow-800",cancelled:"bg-red-100 text-red-800"}',
    '{confirmed:"bg-green-100 text-green-800",completed:"bg-blue-100 text-blue-800",pending:"bg-yellow-100 text-yellow-800",cancelled:"bg-red-100 text-red-800"}',
  ],
];
const files = [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")];
let patched = 0;
let alreadyPatched = 0;
for (const file of files) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (
    text.includes('enum:["confirmed","pending","cancelled","completed"]') ||
    text.includes('completed:"text-blue-700"') ||
    text.includes('completed:"bg-blue-100 text-blue-800"')
  ) {
    alreadyPatched += 1;
  }
  for (const [oldText, newText] of replacements) {
    text = text.split(oldText).join(newText);
  }
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel completed-booking patch did not match any bundle");
}
NODE
# Seeded Travel flight bookings are inserted directly into Mongo during task
# setup. The packaged My Bookings flight tab can keep using a cached helper that
# does not see those direct writes. Query FlightBooking directly and populate the
# itinerary, segment, passenger, seat, and payment fields needed by the cards.
docker exec -i -u root -w /app travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");

function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && /\.(js|html|json)$/.test(file)) out.push(file);
  }
  return out;
}

function helper(fnName, userArg, ttlArg) {
  return `async function ${fnName}(${userArg},${ttlArg}=600){if(!${userArg})throw Error("User id is required");try{const __gmaM=require("mongoose");if(process.env.MONGODB_URI&&__gmaM.connection.readyState===0)await __gmaM.connect(process.env.MONGODB_URI,{serverSelectionTimeoutMS:5000});const __gmaDb=__gmaM.connection.db;const __gmaRaw=v=>v&&v._id?v._id:v;const __gmaStr=v=>String(__gmaRaw(v));const __gmaOid=v=>{const s=__gmaStr(v);return __gmaM.Types.ObjectId.isValid(s)?new __gmaM.Types.ObjectId(s):s};const __gmaUniq=a=>[...new Set((a||[]).filter(Boolean).map(__gmaStr))];const __gmaObjIds=a=>__gmaUniq(a).filter(s=>__gmaM.Types.ObjectId.isValid(s)).map(s=>new __gmaM.Types.ObjectId(s));const __gmaMap=a=>new Map((a||[]).map(x=>[__gmaStr(x._id),x]));const __gmaFindByObjectIds=async(c,ids)=>{const q=__gmaObjIds(ids);return q.length?await __gmaDb.collection(c).find({_id:{$in:q}}).toArray():[]};let __gmaUserId=__gmaOid(${userArg});let __gmaBookings=await __gmaDb.collection("flightbookings").find({$or:[{userId:__gmaUserId},{userId:__gmaStr(${userArg})}]}).sort({createdAt:-1}).toArray();let __gmaItins=await __gmaFindByObjectIds("flightitineraries",__gmaBookings.map(b=>b.flightItineraryId));let __gmaItinMap=__gmaMap(__gmaItins);let __gmaSegmentIds=[...__gmaBookings.flatMap(b=>b.segmentIds||[]),...__gmaItins.flatMap(i=>i.segmentIds||[])];let __gmaSegments=await __gmaFindByObjectIds("flightsegments",__gmaSegmentIds);let __gmaPassengerMap=__gmaMap(await __gmaFindByObjectIds("passengers",__gmaBookings.flatMap(b=>b.passengers||[])));let __gmaSeatIds=__gmaBookings.flatMap(b=>(b.selectedSeats||[]).map(s=>s.seatId));let __gmaSeats=[...await __gmaFindByObjectIds("flightseats",__gmaSeatIds),...await __gmaFindByObjectIds("seats",__gmaSeatIds)];let __gmaSeatMap=__gmaMap(__gmaSeats);let __gmaPaymentMap=__gmaMap(await __gmaFindByObjectIds("flightpayments",__gmaBookings.map(b=>b.paymentId)));let __gmaAirlineIds=__gmaUniq([...__gmaSegments.map(s=>s.airlineId),...__gmaItins.map(i=>i.carrierInCharge)]);let __gmaAirlineMap=__gmaMap(__gmaAirlineIds.length?await __gmaDb.collection("airlines").find({_id:{$in:__gmaAirlineIds}}).toArray():[]);let __gmaAirportIds=__gmaUniq([...__gmaSegments.flatMap(s=>[s.from&&s.from.airport,s.to&&s.to.airport]),...__gmaItins.flatMap(i=>[i.departureAirportId,i.arrivalAirportId])]);let __gmaAirportMap=__gmaMap(__gmaAirportIds.length?await __gmaDb.collection("airports").find({_id:{$in:__gmaAirportIds}}).toArray():[]);let __gmaAirplaneMap=__gmaMap(await __gmaFindByObjectIds("airplanes",__gmaSegments.map(s=>s.airplaneId)));const __gmaPopulateSegment=s=>{if(!s)return s;let o={...s};o.airlineId=__gmaAirlineMap.get(__gmaStr(o.airlineId))||o.airlineId;o.airplaneId=o.airplaneId?(__gmaAirplaneMap.get(__gmaStr(o.airplaneId))||o.airplaneId):o.airplaneId;if(o.from&&o.from.airport)o.from={...o.from,airport:__gmaAirportMap.get(__gmaStr(o.from.airport))||o.from.airport};if(o.to&&o.to.airport)o.to={...o.to,airport:__gmaAirportMap.get(__gmaStr(o.to.airport))||o.to.airport};return o};let __gmaSegmentMap=__gmaMap(__gmaSegments.map(__gmaPopulateSegment));const __gmaPopulateItin=i=>{if(!i)return i;let o={...i};o.carrierInCharge=__gmaAirlineMap.get(__gmaStr(o.carrierInCharge))||o.carrierInCharge;o.departureAirportId=__gmaAirportMap.get(__gmaStr(o.departureAirportId))||o.departureAirportId;o.arrivalAirportId=__gmaAirportMap.get(__gmaStr(o.arrivalAirportId))||o.arrivalAirportId;o.segmentIds=(o.segmentIds||[]).map(id=>__gmaSegmentMap.get(__gmaStr(id))).filter(Boolean);return o};__gmaItinMap=__gmaMap(__gmaItins.map(__gmaPopulateItin));return __gmaBookings.map(b=>{let o={...b};o.flightItineraryId=__gmaItinMap.get(__gmaStr(o.flightItineraryId))||o.flightItineraryId;o.segmentIds=(o.segmentIds||[]).map(id=>__gmaSegmentMap.get(__gmaStr(id))).filter(Boolean);o.passengers=(o.passengers||[]).map(id=>__gmaPassengerMap.get(__gmaStr(id))).filter(Boolean);o.selectedSeats=(o.selectedSeats||[]).map(s=>({...s,seatId:s.seatId?(__gmaSeatMap.get(__gmaStr(s.seatId))||s.seatId):s.seatId}));o.paymentId=o.paymentId?(__gmaPaymentMap.get(__gmaStr(o.paymentId))||o.paymentId):o.paymentId;return o})}catch(e){throw console.log(e),e}}`;
}

const pattern = /async function ([A-Za-z_$][\w$]*)\(([^,{}()]+),([^=,{}()]+)=600\)\{if\(!\2\)throw Error\("User id is required"\);try\{return await \(0,[A-Za-z_$][\w$]*\.z\)\("FlightBooking",\{userId:(?:\2|\(0,[A-Za-z_$][\w$]*\.b\)\(\2\))\},\["userFlightBooking"\],\3\)\}catch\(([A-Za-z_$][\w$]*)\)\{throw console\.log\(\4\),\4\}\}/g;

let patched = 0;
let alreadyPatched = 0;
const stale = [];
for (const file of [...walk("/app/.next/server"), ...walk("/app/.next/static")]) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("FlightBooking") && !text.includes("flightbookings")) continue;
  if (text.includes('collection("flightbookings")')) alreadyPatched += 1;
  const before = text;
  text = text.replace(pattern, (_match, fnName, userArg, ttlArg) => helper(fnName, userArg, ttlArg));
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
for (const file of [...walk("/app/.next/server"), ...walk("/app/.next/static")]) {
  const text = fs.readFileSync(file, "utf8");
  if (
    text.includes('"FlightBooking",{userId:e},["userFlightBooking"]') ||
    (text.includes('"FlightBooking",{userId:(0,') && text.includes('},["userFlightBooking"]'))
  ) {
    stale.push(file);
  }
}
if (stale.length) {
  throw new Error(`Travel flight booking direct-list patch left ${stale.length} stale helper(s): ${stale.slice(0, 5).join(", ")}`);
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel flight booking direct-list patch did not match any bundle");
}
NODE
# Seeded Travel attraction bookings are inserted directly into Mongo during task
# setup. The packaged My Bookings attraction tab reads through a cached helper
# that can keep returning an old empty list after those direct writes. Query
# AttractionBooking directly so reset/reinit shows freshly seeded records.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");

function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}

function inferRequireVar(prefix, moduleId) {
  const re = new RegExp(String.raw`([A-Za-z_$][\w$]*)\s*=\s*[A-Za-z_$][\w$]*\(${moduleId}\)`, "g");
  let match;
  let value = null;
  while ((match = re.exec(prefix)) !== null) value = match[1];
  return value;
}

function patchFile(file) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("AttractionBooking") || !text.includes("attractionBookings")) {
    return { changed: false, count: 0 };
  }
  const before = text;
  let count = 0;
  const patterns = [
    /async function ([A-Za-z_$][\w$]*)\(e,([A-Za-z_$][\w$]*)=600\)\{if\(!e\)throw Error\("User id is required"\);try\{return await \(0,([A-Za-z_$][\w$]*)\.z\)\("AttractionBooking",\{userId:e\},\["attractionBookings"\],\2\)\}catch\(e\)\{throw console\.log\(e\),e\}\}/g,
    /async function ([A-Za-z_$][\w$]*)\(e,([A-Za-z_$][\w$]*)=600\)\{if\(!e\)throw Error\("User id is required"\);try\{return await \(0,([A-Za-z_$][\w$]*)\.z\)\("AttractionBooking",\{userId:\(0,([A-Za-z_$][\w$]*)\.b\)\(e\)\},\["attractionBookings"\],\2\)\}catch\(e\)\{throw console\.log\(e\),e\}\}/g,
  ];
  for (const pattern of patterns) {
    text = text.replace(pattern, (...args) => {
      const match = args[0];
      const fn = args[1];
      const ttl = args[2];
      const maybeDbVar = args.length === 7 ? args[4] : null;
      const offset = args[args.length - 2];
      if (match.includes(".FZ.find")) return match;
      const prefix = text.slice(Math.max(0, offset - 3000), offset);
      const modelVar = inferRequireVar(prefix, 82049);
      const dbVar = inferRequireVar(prefix, 6747) || maybeDbVar;
      if (!modelVar || !dbVar) return match;
      count += 1;
      return `async function ${fn}(e,${ttl}=600){if(!e)throw Error("User id is required");try{await (0,${dbVar}.PA)();return await ${modelVar}.FZ.find({userId:(0,${dbVar}.b)(e)}).sort({createdAt:-1}).populate("attractionId").lean()}catch(e){throw console.log(e),e}}`;
    });
  }
  if (text !== before) fs.writeFileSync(file, text);
  return { changed: text !== before, count };
}

const files = [...walk("/app/.next/server"), ...walk("/app/.next/static/chunks")];
let patched = 0;
let alreadyPatched = 0;
let replacements = 0;
const stale = [];
for (const file of files) {
  const result = patchFile(file);
  if (result.changed) patched += 1;
  replacements += result.count;
}
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  if (text.includes(".FZ.find({userId:(0,") && text.includes('.populate("attractionId").lean()')) {
    alreadyPatched += 1;
  }
  if (
    text.includes('"AttractionBooking",{userId:e},["attractionBookings"]') ||
    (text.includes('"AttractionBooking",{userId:(0,') && text.includes('},["attractionBookings"]'))
  ) {
    stale.push(file);
  }
}
if (stale.length) {
  throw new Error(`Travel attraction booking direct-list patch left ${stale.length} stale helper(s): ${stale.slice(0, 5).join(", ")}`);
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel attraction booking direct-list patch did not match any bundle");
}
NODE
# Seeded Travel hotel bookings are inserted directly into Mongo during task
# setup. The packaged My Bookings hotel tab can keep using a cached helper that
# does not see those direct writes. Query HotelBooking directly and populate the
# hotel/guest fields needed by the booking cards.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");

function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}

function directHotelBookingHelper(fn, ttl) {
  return `async function ${fn}(e,${ttl}=600){if(!e)throw Error("User id is required");try{let __gmaM=require("mongoose");if(__gmaM.connection.readyState===0)await __gmaM.connect(process.env.MONGODB_URI,{serverSelectionTimeoutMS:5000});let __gmaDb=__gmaM.connection.db,__gmaUserId=__gmaM.Types.ObjectId.isValid(e)?new __gmaM.Types.ObjectId(e):e,__gmaRows=await __gmaDb.collection("hotelbookings").find({userId:__gmaUserId}).sort({createdAt:-1}).toArray(),__gmaHotelIds=[...new Set(__gmaRows.map(e=>e.hotelId).filter(Boolean).map(String))].map(e=>new __gmaM.Types.ObjectId(e)),__gmaGuestIds=[...new Set(__gmaRows.flatMap(e=>e.guests||[]).filter(Boolean).map(String))].map(e=>new __gmaM.Types.ObjectId(e)),__gmaHotels=__gmaHotelIds.length?await __gmaDb.collection("hotels").find({_id:{$in:__gmaHotelIds}}).toArray():[],__gmaGuests=__gmaGuestIds.length?await __gmaDb.collection("hotelguests").find({_id:{$in:__gmaGuestIds}}).toArray():[],__gmaHotelMap=new Map(__gmaHotels.map(e=>[String(e._id),e])),__gmaGuestMap=new Map(__gmaGuests.map(e=>[String(e._id),e]));return __gmaRows.map(e=>({...e,hotelId:__gmaHotelMap.get(String(e.hotelId))||e.hotelId,guests:(e.guests||[]).map(e=>__gmaGuestMap.get(String(e))||e)}))}catch(e){throw console.log(e),e}}`;
}

function patchFile(file) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("HotelBooking") || !text.includes("hotelBookings")) {
    return { changed: false, count: 0 };
  }
  const before = text;
  let count = 0;
  const patterns = [
    /async function ([A-Za-z_$][\w$]*)\(e,([A-Za-z_$][\w$]*)=600\)\{if\(!e\)throw Error\("User id is required"\);try\{return await \(0,([A-Za-z_$][\w$]*)\.z\)\("HotelBooking",\{userId:e\},\["hotelBookings"\],\2\)\}catch\(e\)\{throw console\.log\(e\),e\}\}/g,
    /async function ([A-Za-z_$][\w$]*)\(e,([A-Za-z_$][\w$]*)=600\)\{if\(!e\)throw Error\("User id is required"\);try\{return await \(0,([A-Za-z_$][\w$]*)\.z\)\("HotelBooking",\{userId:\(0,([A-Za-z_$][\w$]*)\.b\)\(e\)\},\["hotelBookings"\],\2\)\}catch\(e\)\{throw console\.log\(e\),e\}\}/g,
  ];
  for (const pattern of patterns) {
    text = text.replace(pattern, (match, fn, ttl) => {
      if (match.includes("__gmaHotelBookings")) return match;
      count += 1;
      return directHotelBookingHelper(fn, ttl);
    });
  }
  if (text !== before) fs.writeFileSync(file, text);
  return { changed: text !== before, count };
}

const files = walk("/app/.next/server");
let patched = 0;
let alreadyPatched = 0;
const stale = [];
for (const file of files) {
  const result = patchFile(file);
  if (result.changed) patched += 1;
}
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  if (text.includes("__gmaHotelMap") && text.includes('collection("hotelbookings")')) {
    alreadyPatched += 1;
  }
  if (
    text.includes('"HotelBooking",{userId:e},["hotelBookings"]') ||
    (text.includes('"HotelBooking",{userId:(0,') && text.includes('},["hotelBookings"]'))
  ) {
    stale.push(file);
  }
}
if (stale.length) {
  throw new Error(`Travel hotel booking direct-list patch left ${stale.length} stale helper(s): ${stale.slice(0, 5).join(", ")}`);
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel hotel booking direct-list patch did not match any server bundle");
}
NODE
# The shared search popover can leave skeleton rows forever when an initial
# request fails or returns a non-OK response. Patch the compiled client chunks so
# loading always clears and subsequent airport/city search results can render.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const roots = ["/app/.next/static/chunks"];
const replacements = [
  [
    '(async function(){g(!0);let e=await fetch(`${f.url}?${m}`,{next:{revalidate:f?.next?.revalidate||600,tags:f?.next?.tags},method:f?.method||"GET",cache:"default"});if(!e.ok)return;let t=await e.json();b(t),n(t),g(!1)})()',
    '(async function(){g(!0);try{let e=await fetch(`${f.url}?${m}`,{next:{revalidate:f?.next?.revalidate||600,tags:f?.next?.tags},method:f?.method||"GET",cache:"no-store"});if(!e.ok){let e={success:!1,message:"Unable to load results",data:[]};b(e),n(e);return}let t=await e.json();b(t),n(t)}catch(e){let t={success:!1,message:"Unable to load results",data:[]};b(t),n(t)}finally{g(!1)}})()',
  ],
  [
    '(async function(){g(!0);let e=await fetch(`${u.url}?${h}`,{next:{revalidate:u?.next?.revalidate||600,tags:u?.next?.tags},method:u?.method||"GET",cache:"default"});if(!e.ok)return;let t=await e.json();p(t),s(t),g(!1)})()',
    '(async function(){g(!0);try{let e=await fetch(`${u.url}?${h}`,{next:{revalidate:u?.next?.revalidate||600,tags:u?.next?.tags},method:u?.method||"GET",cache:"no-store"});if(!e.ok){let e={success:!1,message:"Unable to load results",data:[]};p(e),s(e);return}let t=await e.json();p(t),s(t)}catch(e){let t={success:!1,message:"Unable to load results",data:[]};p(t),s(t)}finally{g(!1)}})()',
  ],
];
let patched = 0;
let alreadyPatched = 0;
for (const root of roots) {
  if (!fs.existsSync(root)) continue;
  for (const name of fs.readdirSync(root)) {
    if (!name.endsWith(".js")) continue;
    const file = `${root}/${name}`;
    let text = fs.readFileSync(file, "utf8");
    const before = text;
    if (before.includes("Unable to load results") && before.includes('cache:"no-store"')) {
      alreadyPatched += 1;
    }
    for (const [oldText, newText] of replacements) {
      text = text.split(oldText).join(newText);
    }
    if (text !== before) {
      fs.writeFileSync(file, text);
      patched += 1;
    }
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel search dropdown patch did not match any client chunk");
}
NODE
# The packaged flight search form initializes its allowed date range from the
# container/browser clock. GMA snapshots use 2026-10-01 as the Travel timeline,
# so force the flight picker to open on that same timeline instead of May.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const rangePattern = /availableFlightDateRange:\{from:Date\.parse\(([A-Za-z_$][\w$]*)\),to:\(0,([A-Za-z_$][\w$]*)\.B\)\(Date\.parse\(\1\),100\)\.getTime\(\)\}/g;
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes('availableFlightDateRange:{from:Date.parse("2026-10-01")')) {
    alreadyPatched += 1;
  }
  text = text.replace(rangePattern, (_match, _dateVar, addDaysVar) => {
    patched += 1;
    return `availableFlightDateRange:{from:Date.parse("2026-10-01"),to:(0,${addDaysVar}.B)(Date.parse("2026-10-01"),100).getTime()}`;
  });
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel flight date range patch did not match any bundle");
}
NODE
# The custom date picker header uses a month select and a year select. In the
# mobile WebView the year select collapses to a blank, tiny control unless it
# has an explicit width, making passport expiry years practically unselectable.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const replacements = [
  ['className:"grow-0 rounded-sm bg-white p-1"', 'className:"w-40 max-w-[11rem] grow-0 rounded-sm bg-white p-1 text-sm"'],
  ['className:"h-full grow-0 rounded-sm bg-white p-1"', 'className:"h-full w-24 grow-0 rounded-sm bg-white p-1 text-sm"'],
];
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes('w-24 grow-0 rounded-sm bg-white p-1 text-sm')) {
    alreadyPatched += 1;
  }
  for (const [oldText, newText] of replacements) {
    text = text.split(oldText).join(newText);
  }
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker year-width patch did not match any bundle");
}
NODE
# React DatePicker expects numeric year values. The packaged custom header
# forwards the select value as a string, which can put the WebView into a React
# update loop and leave the calendar body blank when Passport Expiry is open.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes("__gmaChangeYear")) {
    alreadyPatched += 1;
    continue;
  }
  text = text.replace(
    /onChange:\(\{target:\{value:([A-Za-z_$][\w$]*)\}\}\)=>((?:[A-Za-z_$][\w$]*|\([^)]*\)))\?\.changeYear\(\1\)/g,
    (_match, valueVar, propsVar) => {
      patched += 1;
      return `onChange:({target:{value:${valueVar}}})=>{let __gmaChangeYear=Number(${valueVar});Number.isFinite(__gmaChangeYear)&&${propsVar}?.changeYear(__gmaChangeYear)}`;
    }
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker changeYear patch did not match any bundle");
}
NODE
# The date picker derives year options from minDate/maxDate and also passes
# those bounds through to react-datepicker. If either bound is invalid, or if
# the bounds are inverted, passport expiry can crash the booking page. Normalize
# the compiled picker bounds before rendering.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const exactReplacements = [
  [
    'function j({customInput:e,className:a,date:o,setDate:m=()=>{},loading:t=!1,minDate:r=new Date,maxDate:j=(0,i.B)(new Date,1),...h}){let p=[];for(let e=r.getFullYear();e<=j.getFullYear();e++)p.push(e);',
    'function j({customInput:e,className:a,date:o,setDate:m=()=>{},loading:t=!1,minDate:r=new Date,maxDate:j=(0,i.B)(new Date,1),...h}){let p=[];r=new Date(r);j=new Date(j);let __gmaNow=new Date;if(!Number.isFinite(r.getTime()))r=__gmaNow;if(!Number.isFinite(j.getTime())){j=new Date(r);j.setFullYear(j.getFullYear()+20)}if(j.getTime()<r.getTime()){j=new Date(r);j.setFullYear(j.getFullYear()+20)}let __gmaBoundsV2=!0,__gmaMinYear=r.getFullYear(),__gmaMaxYear=j.getFullYear();for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)p.push(e);',
  ],
  [
    'function j({customInput:e,className:a,date:o,setDate:m=()=>{},loading:t=!1,minDate:r=new Date,maxDate:j=(0,i.B)(new Date,1),...h}){let p=[];r=new Date(r);j=new Date(j);let __gmaNow=new Date,__gmaMinYear=Number.isFinite(r.getTime())?r.getFullYear():__gmaNow.getFullYear(),__gmaMaxYear=Number.isFinite(j.getTime())?j.getFullYear():__gmaNow.getFullYear()+20;if(__gmaMaxYear<__gmaMinYear)__gmaMaxYear=__gmaMinYear+20;for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)p.push(e);',
    'function j({customInput:e,className:a,date:o,setDate:m=()=>{},loading:t=!1,minDate:r=new Date,maxDate:j=(0,i.B)(new Date,1),...h}){let p=[];r=new Date(r);j=new Date(j);let __gmaNow=new Date;if(!Number.isFinite(r.getTime()))r=__gmaNow;if(!Number.isFinite(j.getTime())){j=new Date(r);j.setFullYear(j.getFullYear()+20)}if(j.getTime()<r.getTime()){j=new Date(r);j.setFullYear(j.getFullYear()+20)}let __gmaBoundsV2=!0,__gmaMinYear=r.getFullYear(),__gmaMaxYear=j.getFullYear();for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)p.push(e);',
  ],
  [
    'function p({customInput:e,className:t,date:s,setDate:l=()=>{},loading:c=!1,minDate:d=new Date,maxDate:p=(0,n.B)(new Date,1),...m}){let f=[];for(let e=d.getFullYear();e<=p.getFullYear();e++)f.push(e);',
    'function p({customInput:e,className:t,date:s,setDate:l=()=>{},loading:c=!1,minDate:d=new Date,maxDate:p=(0,n.B)(new Date,1),...m}){let f=[];d=new Date(d);p=new Date(p);let __gmaNow=new Date;if(!Number.isFinite(d.getTime()))d=__gmaNow;if(!Number.isFinite(p.getTime())){p=new Date(d);p.setFullYear(p.getFullYear()+20)}if(p.getTime()<d.getTime()){p=new Date(d);p.setFullYear(p.getFullYear()+20)}let __gmaBoundsV2=!0,__gmaMinYear=d.getFullYear(),__gmaMaxYear=p.getFullYear();for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)f.push(e);',
  ],
  [
    'function p({customInput:e,className:t,date:s,setDate:l=()=>{},loading:c=!1,minDate:d=new Date,maxDate:p=(0,n.B)(new Date,1),...m}){let f=[];d=new Date(d);p=new Date(p);let __gmaNow=new Date,__gmaMinYear=Number.isFinite(d.getTime())?d.getFullYear():__gmaNow.getFullYear(),__gmaMaxYear=Number.isFinite(p.getTime())?p.getFullYear():__gmaNow.getFullYear()+20;if(__gmaMaxYear<__gmaMinYear)__gmaMaxYear=__gmaMinYear+20;for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)f.push(e);',
    'function p({customInput:e,className:t,date:s,setDate:l=()=>{},loading:c=!1,minDate:d=new Date,maxDate:p=(0,n.B)(new Date,1),...m}){let f=[];d=new Date(d);p=new Date(p);let __gmaNow=new Date;if(!Number.isFinite(d.getTime()))d=__gmaNow;if(!Number.isFinite(p.getTime())){p=new Date(d);p.setFullYear(p.getFullYear()+20)}if(p.getTime()<d.getTime()){p=new Date(d);p.setFullYear(p.getFullYear()+20)}let __gmaBoundsV2=!0,__gmaMinYear=d.getFullYear(),__gmaMaxYear=p.getFullYear();for(let e=__gmaMinYear;e<=__gmaMaxYear;e++)f.push(e);',
  ],
];
const pickerLoopPattern = /function ([A-Za-z_$][\w$]*)\(\{customInput:([A-Za-z_$][\w$]*),className:([A-Za-z_$][\w$]*),date:([A-Za-z_$][\w$]*),setDate:([A-Za-z_$][\w$]*)=\(\)=>\{\},loading:([A-Za-z_$][\w$]*)=!\d,minDate:([A-Za-z_$][\w$]*)=new Date,maxDate:([A-Za-z_$][\w$]*)=([\s\S]*?),\.\.\.([A-Za-z_$][\w$]*)\}\)\{let ([A-Za-z_$][\w$]*)=\[\];for\(let ([A-Za-z_$][\w$]*)=\7\.getFullYear\(\);\12<=\8\.getFullYear\(\);\12\+\+\)\11\.push\(\12\);/g;
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes("__gmaBoundsV3")) {
    alreadyPatched += 1;
    continue;
  }
  if (text.includes("__gmaBoundsV2")) {
    alreadyPatched += 1;
    continue;
  }
  for (const [oldText, newText] of exactReplacements) {
    text = text.split(oldText).join(newText);
  }
  text = text.replace(
    pickerLoopPattern,
    (match, fn, customInput, className, date, setDate, loading, minDate, maxDate, maxDefault, rest, years, idx) =>
      `function ${fn}({customInput:${customInput},className:${className},date:${date},setDate:${setDate}=()=>{},loading:${loading}=!1,minDate:${minDate}=new Date,maxDate:${maxDate}=${maxDefault},...${rest}}){let ${years}=[];${minDate}=new Date(${minDate});${maxDate}=new Date(${maxDate});let __gmaNow=new Date;__gmaNow.setHours(0,0,0,0);if(!Number.isFinite(${minDate}.getTime()))${minDate}=new Date(__gmaNow);if(!Number.isFinite(${maxDate}.getTime())){${maxDate}=new Date(${minDate});${maxDate}.setFullYear(${maxDate}.getFullYear()+20)}${minDate}.setHours(0,0,0,0);${maxDate}.setHours(0,0,0,0);if(${maxDate}.getTime()<${minDate}.getTime()){${maxDate}=new Date(${minDate});${maxDate}.setFullYear(${maxDate}.getFullYear()+20)}let __gmaBoundsV3=!0,__gmaMinYear=${minDate}.getFullYear(),__gmaMaxYear=${maxDate}.getFullYear();for(let ${idx}=__gmaMinYear;${idx}<=__gmaMaxYear;${idx}++)${years}.push(${idx});`
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker year-bounds patch did not match any bundle");
}
NODE
# Upgrade earlier date-picker patches in-place. V2 normalized invalid dates but
# still left "new Date" bounds with a changing millisecond value on every
# render. react-datepicker can loop when bounds change during its own update
# cycle, so canonicalize all bounds to local midnight.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes("__gmaBoundsV3")) {
    alreadyPatched += 1;
    continue;
  }
  text = text.replace(
    /let __gmaNow=new Date;if\(!Number\.isFinite\(([A-Za-z_$][\w$]*)\.getTime\(\)\)\)\1=__gmaNow;if\(!Number\.isFinite\(([A-Za-z_$][\w$]*)\.getTime\(\)\)\)\{\2=new Date\(\1\);\2\.setFullYear\(\2\.getFullYear\(\)\+20\)\}if\(\2\.getTime\(\)<\1\.getTime\(\)\)\{\2=new Date\(\1\);\2\.setFullYear\(\2\.getFullYear\(\)\+20\)\}let __gmaBoundsV2=!0/g,
    (_match, minVar, maxVar) => {
      patched += 1;
      return `let __gmaNow=new Date;__gmaNow.setHours(0,0,0,0);if(!Number.isFinite(${minVar}.getTime()))${minVar}=new Date(__gmaNow);if(!Number.isFinite(${maxVar}.getTime())){${maxVar}=new Date(${minVar});${maxVar}.setFullYear(${maxVar}.getFullYear()+20)}${minVar}.setHours(0,0,0,0);${maxVar}.setHours(0,0,0,0);if(${maxVar}.getTime()<${minVar}.getTime()){${maxVar}=new Date(${minVar});${maxVar}.setFullYear(${maxVar}.getFullYear()+20)}let __gmaBoundsV3=!0`;
    }
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker V3 bounds patch did not match any bundle");
}
NODE
# The packaged available-flight-date-range API derives the picker bounds from
# expireAt, which is a ticketing cutoff and can be before the actual flight day.
# Use itinerary date for picker bounds so the flight calendar follows the Travel
# timeline that starts on 2026-10-01.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const files = [
  "/app/.next/server/app/api/flights/available_flight_date_range/route.js",
  ...walk("/app/.next/server/chunks"),
];
const exact = 'async function f(){try{let e=await i.P.findOne({expireAt:{$gte:Date.now()}}).sort({expireAt:1}).lean(),t=await i.P.findOne({expireAt:{$gte:Date.now()}}).sort({expireAt:-1}).lean();return{success:!0,message:"Success",data:{from:new Date(e?.expireAt)?.getTime()||(0,o.B)(new Date,100).getTime(),to:new Date(t?.expireAt)?.getTime()||-1}}}catch(e){return console.log(e),{success:!1,message:"Failed to get flight date range"}}}';
const replacement = 'async function f(){try{let e=await i.P.findOne({expireAt:{$gte:Date.now()}}).sort({date:1}).lean(),t=await i.P.findOne({expireAt:{$gte:Date.now()}}).sort({date:-1}).lean();return{success:!0,message:"Success",data:{from:new Date(e?.date)?.getTime()||(0,o.B)(new Date,100).getTime(),to:new Date(t?.date)?.getTime()||-1}}}catch(e){return console.log(e),{success:!1,message:"Failed to get flight date range"}}}';
let patched = 0;
let alreadyPatched = 0;
for (const file of files) {
  if (!fs.existsSync(file)) continue;
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes('sort({date:1}).lean(),t=await i.P.findOne({expireAt:{$gte:Date.now()}}).sort({date:-1}).lean()')) {
    alreadyPatched += 1;
  }
  text = text.split(exact).join(replacement);
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel flight date range API patch did not match any bundle");
}
NODE
# Flight itineraries can outlive their referenced segment documents because
# itinerary expireAt is the booking cutoff while segment expireAt is shorter.
# Skip stale itineraries before fare/review shaping so search result rendering
# does not crash on missing segment airplane data.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const pattern = /([A-Za-z_$][\w$]*)\.map\(async ([A-Za-z_$][\w$]*)=>\{let ([A-Za-z_$][\w$]*)=\(0,([A-Za-z_$][\w$]*)\.F_\)\(\2\.segmentIds,\{adult:([A-Za-z_$][\w$]*)\.adults,child:\5\.children,infant:\5\.infants\},([A-Za-z_$][\w$]*)\);/g;
let patched = 0;
let alreadyPatched = 0;
for (const file of walk("/app/.next/server")) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("FlightItinerary") || !text.includes("airplaneModelName")) continue;
  const before = text;
  if (text.includes("__gmaValidFlightSegments")) {
    alreadyPatched += 1;
    continue;
  }
  text = text.replace(
    pattern,
    (_match, listVar, flightVar, fareVar, fareModuleVar, passengerVar, classVar) => {
      patched += 1;
      return `${listVar}.map(async ${flightVar}=>{let __gmaValidFlightSegments=Array.isArray(${flightVar}.segmentIds)&&${flightVar}.segmentIds.length>0&&${flightVar}.segmentIds.every(${flightVar}=>${flightVar}&&${flightVar}._id&&${flightVar}.airplaneId&&${flightVar}.airplaneId.model&&${flightVar}.fareDetails)&&${flightVar}.departureAirportId&&${flightVar}.departureAirportId._id&&${flightVar}.arrivalAirportId&&${flightVar}.arrivalAirportId._id&&${flightVar}.carrierInCharge&&${flightVar}.carrierInCharge._id;if(!__gmaValidFlightSegments)return null;let ${fareVar}=(0,${fareModuleVar}.F_)(${flightVar}.segmentIds,{adult:${passengerVar}.adults,child:${passengerVar}.children,infant:${passengerVar}.infants},${classVar});`;
    }
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel stale flight itinerary patch did not match any server bundle");
}
NODE
# When the Travel date picker has no selected value, react-datepicker opens on
# the browser's current month even when minDate is later. Make empty pickers open
# to their minDate so the flight search picker starts on 2026-10-01.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const selectedPattern = /selected:\(0,([A-Za-z_$][\w$]*)\.es\)\(([A-Za-z_$][\w$]*)\)\?new Date\(\2\):"",onChange:([A-Za-z_$][\w$]*)=>([A-Za-z_$][\w$]*)\(\3\),className:([A-Za-z_$][\w$]*),minDate:([A-Za-z_$][\w$]*),maxDate:/g;
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks"), ...walk("/app/.next/server")]) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (text.includes('openToDate:')) {
    alreadyPatched += 1;
  }
  text = text.replace(selectedPattern, (_match, utilVar, dateVar, eventVar, handlerVar, classVar, minDateVar) => {
    patched += 1;
    return `selected:(0,${utilVar}.es)(${dateVar})?new Date(${dateVar}):"",openToDate:(0,${utilVar}.es)(${dateVar})?new Date(${dateVar}):${minDateVar},onChange:${eventVar}=>${handlerVar}(${eventVar}),className:${classVar},minDate:${minDateVar},maxDate:`;
  });
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker openToDate patch did not match any bundle");
}
NODE
# Several packaged Travel API route bundles query Mongoose models without first
# opening the shared Mongo connection. Patch those compiled route handlers so
# airport/hotel/attraction search works after reset without rebuilding the app.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const routes = [
  "/app/.next/server/app/api/attractions/available_cities/route.js",
  "/app/.next/server/app/api/attractions/search_by_name/route.js",
  "/app/.next/server/app/api/flights/available_airlines/route.js",
  "/app/.next/server/app/api/flights/available_airports/route.js",
  "/app/.next/server/app/api/hotels/available_places/route.js",
  "/app/.next/server/app/api/hotels/search_by_name/route.js",
  "/app/.next/server/app/api/user/[id]/route.js",
];
const helper = "async function __gmaTravelConnect(){const m=require(\"mongoose\");if(process.env.MONGODB_URI&&m.connection.readyState===0)await m.connect(process.env.MONGODB_URI,{serverSelectionTimeoutMS:5000})}";
for (const route of routes) {
  if (!fs.existsSync(route)) continue;
  let text = fs.readFileSync(route, "utf8");
  text = text.replace(/async function __gmaTravelConnect\(\)\{(?:await __gmaTravelConnect\(\);)?const m=require\("mongoose"\);if\(process\.env\.MONGODB_URI&&m\.connection\.readyState===0\)await m\.connect\(process\.env\.MONGODB_URI,\{serverSelectionTimeoutMS:5000\}\)\};?/g, "");
  const marker = /let ([A-Za-z_$][\w$]*)="force-dynamic";async function ([A-Za-z_$][\w$]*)\(([^)]*)\)\{/;
  if (!marker.test(text)) throw new Error(`cannot find Travel route handler marker in ${route}`);
  text = text.replace(marker, `${helper};let $1="force-dynamic";async function $2($3){await __gmaTravelConnect();`);
  fs.writeFileSync(route, text);
}
NODE
# Asset-created credentials use the same default bcrypt hash as other GMA demo
# apps, but accept a plain stored password too so custom TravelUserAsset
# passwords can still be used by the wrapper login helper.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const route = "/app/.next/server/app/api/auth/[...nextauth]/route.js";
if (fs.existsSync(route)) {
  let text = fs.readFileSync(route, "utf8");
  const patched = "return g.ZP.compareSync(e.password,o)||e.password===o?n:null";
  const original = "return g.ZP.compareSync(e.password,o)?n:null";
  if (!text.includes(patched)) {
    if (!text.includes(original)) {
      throw new Error("Travel credentials auth patch did not match route bundle");
    }
    text = text.replace(original, patched);
    fs.writeFileSync(route, text);
  }
}
NODE
# The emulator clock can intentionally differ from the Travel container clock
# after loading a snapshot. The flight search flow stores a timeout timestamp
# generated by the server, then the WebView compares it against its own clock.
# Rewrite that client storage point to use the WebView clock so submitting a
# search does not immediately show the session timeout dialog.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
let clientPatched = 0;
let clientAlreadyPatched = 0;
for (const file of walk("/app/.next/static/chunks")) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  if (before.includes("__gmaSessionTimeoutAt")) {
    clientAlreadyPatched += 1;
  }
  text = text.replace(
    /localStorage\.setItem\("sessionTimeoutAt",([^;]+?)\);let ([A-Za-z_$][\w$]*)=new CustomEvent\("customStorage",\{detail:\{key:"sessionTimeoutAt",newValue:([^,}]+),oldValue:([^}]+?)\}\}\)/g,
    (match, storedValue, eventVar, eventValue, oldValue) => {
      if (storedValue !== eventValue) return match;
      return `var __gmaSessionTimeoutAt=Date.now()+12e5;localStorage.setItem("sessionTimeoutAt",__gmaSessionTimeoutAt);let ${eventVar}=new CustomEvent("customStorage",{detail:{key:"sessionTimeoutAt",newValue:__gmaSessionTimeoutAt,oldValue:${oldValue}}})`;
    }
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
    clientPatched += 1;
  }
}
let serverPatched = 0;
for (const file of walk("/app/.next/server")) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  text = text.split("new Date().getTime()+12e5").join("Date.now()+31536e6");
  if (text !== before) {
    fs.writeFileSync(file, text);
    serverPatched += 1;
  }
}
if (clientPatched === 0 && clientAlreadyPatched === 0) {
  throw new Error("Travel session timeout patch did not match any client chunk");
}
NODE
# Free attractions are valid in the seed data. The packaged attraction booking
# action rejects a zero total as an invalid price calculation; only negative or
# non-finite totals should be rejected.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
let patched = 0;
let alreadyPatched = 0;
for (const file of walk("/app/.next/server")) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("Invalid ticket price calculation")) continue;
  const before = text;
  if (text.includes("!Number.isFinite(c)||c<0") || text.includes("!Number.isFinite(R)||R<0")) {
    alreadyPatched += 1;
  }
  text = text.replace(/if\(([A-Za-z_$][\w$]*)<=0\)return\{success:!1,message:"Invalid ticket price calculation"\}/g, 'if(!Number.isFinite($1)||$1<0)return{success:!1,message:"Invalid ticket price calculation"}');
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel zero attraction price patch did not match any server bundle");
}
NODE
# Travel renders only five reviews per page. Sort review arrays newest-first in
# the compiled list component so newly seeded or user-written reviews appear on
# the first page instead of being hidden behind baseline reviews.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
const sorter = 'function __gmaSortReviews(e){return Array.isArray(e)?[...e].sort((a,b)=>new Date(b.createdAt||0)-new Date(a.createdAt||0)):e}';
let patched = 0;
let alreadyPatched = 0;
for (const file of walk("/app/.next/server")) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("FlightOrHotelReviewList") && !text.includes("SingleReview")) continue;
  if (!text.includes("slice(5*") || !text.includes(".map(e=>")) continue;
  const before = text;
  if (text.includes("__gmaSortReviews")) {
    alreadyPatched += 1;
    continue;
  }
  text = `${sorter};` + text.replace(/function ([A-Za-z_$][\w$]*)\(\{reviews:e,session:a\}\)\{/g, 'function $1({reviews:e,session:a}){e=__gmaSortReviews(e);');
  if (text !== before) {
    fs.writeFileSync(file, text);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel review sorting patch did not match any server bundle");
}
NODE
# Passport Expiry was the only flight passenger date field whose picker bounds
# were derived from dynamic itinerary metadata. In WebView that route can render
# with an invalid or stale metadata date, causing react-datepicker to crash when
# a passport expiry date is selected. Keep validation in the booking flow, but
# give the picker stable bounds like the Date of Birth field.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && file.endsWith(".js")) out.push(file);
  }
  return out;
}
let patched = 0;
let alreadyPatched = 0;
for (const file of [...walk("/app/.next/static/chunks/app"), ...walk("/app/.next/server/app")]) {
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("passportExpiryDate") || !text.includes("Passport Expiry Date")) continue;
  const before = text;
  if (/passportExpiryDate[\s\S]{0,500}?minDate:\(\(\)=>\{let [A-Za-z_$][\w$]*=new Date;[\s\S]{0,180}?return [A-Za-z_$][\w$]*\}\)\(\),maxDate:\(\(\)=>\{let [A-Za-z_$][\w$]*=new Date;[\s\S]{0,220}?return [A-Za-z_$][\w$]*\}\)\(\)/.test(text)) {
    alreadyPatched += 1;
  }
  text = text.replace(
    /(passportExpiryDate[\s\S]{0,500}?minDate:)\(0,[A-Za-z_$][\w$]*\.z\)\(new Date\([A-Za-z_$][\w$]*\?\.departureDate\),6\),(maxDate:)\(0,([A-Za-z_$][\w$]*)\.B\)\(new Date,15\)/g,
    (_match, prefix, maxDateLabel) => {
      patched += 1;
      return `${prefix}(()=>{let e=new Date;e.setHours(0,0,0,0);return e})(),${maxDateLabel}(()=>{let e=new Date;e.setHours(0,0,0,0);e.setFullYear(e.getFullYear()+20);return e})()`;
    }
  );
  text = text.replace(
    /(passportExpiryDate[\s\S]{0,500}?minDate:)new Date,(maxDate:)\(0,([A-Za-z_$][\w$]*)\.B\)\(new Date,20\)/g,
    (_match, prefix, maxDateLabel) => {
      patched += 1;
      return `${prefix}(()=>{let e=new Date;e.setHours(0,0,0,0);return e})(),${maxDateLabel}(()=>{let e=new Date;e.setHours(0,0,0,0);e.setFullYear(e.getFullYear()+20);return e})()`;
    }
  );
  if (text !== before) {
    fs.writeFileSync(file, text);
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel passport expiry date picker patch did not match any bundle");
}
NODE
# Patched Next chunks keep their original hashed filenames, but Next serves
# those URLs as immutable for a year. Add a small query string to the shared
# datepicker chunk and flight booking chunk references so WebView fetches the
# corrected bundles after a runtime patch instead of reusing old cached copies.
docker exec -i -u root travel-app node - <<'NODE'
const fs = require("fs");
const path = require("path");
function walk(root, out = []) {
  if (!fs.existsSync(root)) return out;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const file = path.join(root, entry.name);
    if (entry.isDirectory()) walk(file, out);
    else if (entry.isFile() && /\.(js|html|json)$/.test(file)) out.push(file);
  }
  return out;
}
const targets = [
  "static/chunks/4499-575ca425b929afa7.js",
  ...walk("/app/.next/static/chunks/app/(pages)/flights/[flightNumber]/book")
    .map(file => path.relative("/app/.next", file).split(path.sep).join("/")),
];
for (const target of [...targets]) {
  targets.push(target.replace("[flightNumber]", "%5BflightNumber%5D"));
}
let patched = 0;
let alreadyPatched = 0;
for (const file of walk("/app/.next")) {
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  for (const target of targets) {
    const busted = `${target}?gma=v3`;
    if (text.includes(busted)) alreadyPatched += 1;
    text = text.split(`${target}?gma=v2`).join(target).split(busted).join(target).split(target).join(busted);
  }
  const next = text;
  if (next !== before) {
    fs.writeFileSync(file, next);
    patched += 1;
  }
}
if (patched === 0 && alreadyPatched === 0) {
  throw new Error("Travel date picker cache-bust patch did not match any bundle");
}
NODE
docker restart travel-app >/dev/null
for _ in $(seq 1 30); do
  if curl -fsS --max-time 5 'http://localhost:8060/trip/api/flights/available_airports?searchQuery=lhr' >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done
docker logs --tail=80 travel-app >&2 || true
exit 1
""",
        timeout=180,
    )

def _patch_mall_runtime(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -euo pipefail

if docker ps -a --format "{{.Names}}" | grep -qx mall-mysql; then
  deadline=$((SECONDS + 240))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if [ "$(docker inspect -f "{{.State.Running}}" mall-mysql 2>/dev/null || true)" = "true" ] \
      && [ "$(docker inspect -f "{{.State.Running}}" mall-app-web 2>/dev/null || true)" = "true" ] \
      && [ "$(docker inspect -f "{{.State.Running}}" mall-admin-web 2>/dev/null || true)" = "true" ] \
      && [ "$(docker inspect -f "{{.State.Running}}" mall-portal 2>/dev/null || true)" = "true" ] \
      && [ "$(docker inspect -f "{{.State.Running}}" mall-admin 2>/dev/null || true)" = "true" ] \
      && docker exec mall-mysql mysqladmin ping -umall -pmall_pass_2025 --silent >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

seed_root=""
for candidate in \
  /data/zhuyiqi/GMA/src/gma/apps/seed_data/mall_meituan \
  /app/gma/src/gma/apps/seed_data/mall_meituan; do
  if [ -f "$candidate/mall_seed.sql" ]; then
    seed_root="$candidate"
    break
  fi
done
if [ -n "$seed_root" ] && docker ps --format '{{.Names}}' | grep -qx mall-mysql; then
  if [ -d "$seed_root/images/mall" ]; then
    docker exec mall-app-web mkdir -p /usr/share/nginx/html/static/annotator/mall
    docker cp "$seed_root/images/mall/." mall-app-web:/usr/share/nginx/html/static/annotator/mall/ >/dev/null
  fi
  docker exec -i mall-mysql mysql -umall -pmall_pass_2025 --default-character-set=utf8mb4 mall < "$seed_root/mall_seed.sql"
fi

cd /tmp/gma_mall_export/mall 2>/dev/null || true
if [ -f docker-compose.yml ]; then
  python3 - <<'PY'
from pathlib import Path

path = Path("docker-compose.yml")
text = path.read_text()
patched = text.replace("TZ=Asia/Shanghai", "TZ=UTC").replace("serverTimezone=Asia/Shanghai", "serverTimezone=UTC")
if patched != text:
    path.write_text(patched)

for config_path in Path("backend").rglob("*"):
    if not config_path.is_file() or config_path.suffix not in {".yml", ".yaml", ".properties"}:
        continue
    config_text = config_path.read_text(errors="replace")
    patched_config = config_text.replace("serverTimezone=Asia/Shanghai", "serverTimezone=UTC")
    if patched_config != config_text:
        config_path.write_text(patched_config)
PY

  portal_env="$(docker exec mall-portal sh -lc 'printf "%s|%s" "${TZ:-}" "${SPRING_DATASOURCE_URL:-}"' 2>/dev/null || true)"
  admin_env="$(docker exec mall-admin sh -lc 'printf "%s|%s" "${TZ:-}" "${SPRING_DATASOURCE_URL:-}"' 2>/dev/null || true)"
  if ! printf '%s' "$portal_env" | grep -q 'UTC.*serverTimezone=UTC' \
    || ! printf '%s' "$admin_env" | grep -q 'UTC.*serverTimezone=UTC'; then
    docker compose --project-name gma-mall -f docker-compose.yml up -d --force-recreate mall-admin mall-portal >/dev/null
    deadline=$((SECONDS + 120))
    while [ "$SECONDS" -lt "$deadline" ]; do
      if [ "$(docker inspect -f '{{.State.Running}}' mall-admin 2>/dev/null || true)" = "true" ] \
        && [ "$(docker inspect -f '{{.State.Running}}' mall-portal 2>/dev/null || true)" = "true" ]; then
        break
      fi
      sleep 2
    done
  fi
fi

python3 - <<'INNER_PY'
import subprocess
import tempfile
from pathlib import Path

old_text = 'buy:function(){uni.showToast({title:"Currently only supports ordering from cart!",icon:"none"})}'
new_text = 'buy:function(){if(this.checkForLogin()){var t=this,e=this.getSkuStock();if(!e){uni.showToast({title:"Please select a product type",icon:"none"});return}var n={price:this.product.price,productAttr:e.spData,productBrand:this.product.brandName,productCategoryId:this.product.productCategoryId,productId:this.product.id,productName:this.product.name,productPic:this.product.pic,productSkuCode:e.skuCode,productSkuId:e.id,productSn:this.product.productSn,productSubTitle:this.product.subTitle,quantity:1};Object(s["a"])(n).then((function(){return Object(s["d"])()})).then((function(n){var i=(n.data||[]).filter((function(n){return Number(n.productId)===Number(t.product.id)&&Number(n.productSkuId)===Number(e.id)&&0===Number(n.deleteStatus||0)}));if(!i.length){uni.showToast({title:"Failed to prepare checkout",icon:"none"});return}i.sort((function(t,e){return Number(e.id||0)-Number(t.id||0)}));var o=i[0];return Object(s["e"])({id:o.id,quantity:1}).then((function(){uni.navigateTo({url:"/pages/order/createOrder?cartIds=".concat(JSON.stringify([o.id]))})}))})).catch((function(){uni.showToast({title:"Failed to prepare checkout",icon:"none"})}))}}'
paths = subprocess.check_output(
    ["docker", "exec", "mall-app-web", "sh", "-lc", "ls /usr/share/nginx/html/static/js/pages-product-product*.js 2>/dev/null || true"],
    text=True,
).splitlines()
patched = 0
already_patched = 0
for remote_path in paths:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        local_path = Path(tmp.name)
    try:
        subprocess.run(["docker", "cp", f"mall-app-web:{remote_path}", str(local_path)], check=True, stdout=subprocess.DEVNULL)
        text = local_path.read_text(errors="ignore")
        if old_text not in text and "createOrder?cartIds" in text:
            already_patched += 1
            continue
        updated = text.replace(old_text, new_text)
        if updated != text:
            local_path.write_text(updated)
            subprocess.run(["docker", "cp", str(local_path), f"mall-app-web:{remote_path}"], check=True, stdout=subprocess.DEVNULL)
            patched += 1
    finally:
        local_path.unlink(missing_ok=True)
if patched == 0 and already_patched == 0:
    raise SystemExit("Mall direct-buy patch did not match product bundle")
INNER_PY

if docker exec mall-app-web test -f /tmp/gma_runtime_patched_v16 2>/dev/null \
  && docker exec mall-admin-web test -f /tmp/gma_runtime_patched_v16 2>/dev/null \
  && docker exec mall-mysql test -f /tmp/gma_runtime_patched_v16 2>/dev/null \
  && docker exec mall-portal test -f /tmp/gma_runtime_patched_v16 2>/dev/null \
  && docker exec mall-portal sh -lc 'jar tf /app/app.jar | grep -q GmaCommentController' 2>/dev/null; then
  exit 0
fi

if true; then
  cat > /tmp/GmaCommentController.java <<'JAVA'
package com.macro.mall.portal.controller;

import com.macro.mall.model.UmsMember;
import com.macro.mall.portal.service.UmsMemberService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Controller
@RequestMapping("/comment")
public class GmaCommentController {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private UmsMemberService memberService;

    private Map<String, Object> result(int code, String message, Object data) {
        Map<String, Object> result = new HashMap<String, Object>();
        result.put("code", code);
        result.put("message", message);
        result.put("data", data);
        return result;
    }

    private Long asLong(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return Long.valueOf(String.valueOf(value));
    }

    private Integer asInt(Object value, int fallback) {
        if (value == null) {
            return fallback;
        }
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return Integer.valueOf(String.valueOf(value));
    }

    @RequestMapping(value = "/list", method = RequestMethod.GET)
    @ResponseBody
    public Map<String, Object> list(
            @RequestParam("productId") Long productId,
            @RequestParam(value = "pageNum", defaultValue = "1") Integer pageNum,
            @RequestParam(value = "pageSize", defaultValue = "10") Integer pageSize) {
        if (productId == null) {
            return result(500, "Product ID is required", null);
        }
        int safePageNum = Math.max(pageNum == null ? 1 : pageNum, 1);
        int safePageSize = Math.max(pageSize == null ? 10 : pageSize, 1);
        int offset = (safePageNum - 1) * safePageSize;
        Integer total = jdbcTemplate.queryForObject(
                "select count(*) from pms_comment where product_id = ? and show_status = 1",
                Integer.class,
                productId
        );
        if (total == null) {
            total = 0;
        }
        List<Map<String, Object>> comments = total > 0
                ? jdbcTemplate.queryForList(
                        "select id, product_id as productId, member_id as memberId, order_id as orderId, order_item_id as orderItemId, "
                                + "member_nick_name as memberNickName, product_name as productName, star, create_time as createTime, "
                                + "show_status as showStatus, product_attribute as productAttribute, collect_couont as collectCouont, "
                                + "read_count as readCount, pics, replay_count as replayCount, content, member_icon as memberIcon "
                                + "from pms_comment where product_id = ? and show_status = 1 order by create_time desc, id desc limit ? offset ?",
                        productId,
                        safePageSize,
                        offset
                )
                : new ArrayList<Map<String, Object>>();
        Map<String, Object> data = new HashMap<String, Object>();
        data.put("pageNum", safePageNum);
        data.put("pageSize", safePageSize);
        data.put("totalPage", (total + safePageSize - 1) / safePageSize);
        data.put("total", total);
        data.put("list", comments);
        return result(200, "Success", data);
    }

    @RequestMapping(value = "/stats", method = RequestMethod.GET)
    @ResponseBody
    public Map<String, Object> stats(@RequestParam("productId") Long productId) {
        if (productId == null) {
            return result(500, "Product ID is required", null);
        }
        Integer total = jdbcTemplate.queryForObject(
                "select count(*) from pms_comment where product_id = ? and show_status = 1",
                Integer.class,
                productId
        );
        Integer good = jdbcTemplate.queryForObject(
                "select count(*) from pms_comment where product_id = ? and show_status = 1 and star >= 4",
                Integer.class,
                productId
        );
        if (total == null) {
            total = 0;
        }
        if (good == null) {
            good = 0;
        }
        Map<String, Object> data = new HashMap<String, Object>();
        data.put("total", total);
        data.put("goodRate", total == 0 ? 0 : Math.round(good * 100.0f / total));
        return result(200, "Success", data);
    }

    @RequestMapping(value = "/create", method = RequestMethod.POST)
    @ResponseBody
    public Map<String, Object> create(@RequestBody Map<String, Object> param) {
        Long orderId = asLong(param.get("orderId"));
        Integer star = asInt(param.get("star"), 5);
        String content = param.get("content") == null ? "" : String.valueOf(param.get("content"));
        String pics = param.get("pics") == null ? "" : String.valueOf(param.get("pics"));
        if (orderId == null) {
            return result(500, "Order ID is required", null);
        }
        if (content.trim().length() < 5) {
            return result(500, "Review must be at least 5 characters", null);
        }
        UmsMember member = memberService.getCurrentMember();
        Map<String, Object> order = jdbcTemplate.queryForMap(
                "select id, member_id, status, comment_time from oms_order where id = ?",
                orderId
        );
        Long orderMemberId = asLong(order.get("member_id"));
        if (!member.getId().equals(orderMemberId)) {
            return result(500, "Cannot review another user's order", null);
        }
        if (asInt(order.get("status"), -1) != 3) {
            return result(500, "Can only review completed orders", null);
        }
        if (order.get("comment_time") != null) {
            return result(500, "This order has already been reviewed", null);
        }
        List<Map<String, Object>> items = jdbcTemplate.queryForList(
                "select id, product_id, product_name, product_attr from oms_order_item where order_id = ?",
                orderId
        );
        if (items.isEmpty()) {
            return result(500, "Order items are empty", null);
        }
        Timestamp now = new Timestamp(System.currentTimeMillis());
        for (Map<String, Object> item : items) {
            jdbcTemplate.update(
                    "insert into pms_comment "
                            + "(product_id, member_id, order_id, order_item_id, member_nick_name, member_icon, product_name, star, content, pics, product_attribute, create_time, show_status, collect_couont, read_count, replay_count) "
                            + "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, 0)",
                    asLong(item.get("product_id")),
                    member.getId(),
                    orderId,
                    asLong(item.get("id")),
                    member.getNickname() != null ? member.getNickname() : member.getUsername(),
                    member.getIcon(),
                    item.get("product_name"),
                    star,
                    content,
                    pics,
                    item.get("product_attr"),
                    now
            );
        }
        jdbcTemplate.update("update oms_order set comment_time = ? where id = ?", now, orderId);
        return result(200, "OK", items.size());
    }
}
JAVA
  docker cp /tmp/GmaCommentController.java mall-portal:/tmp/GmaCommentController.java >/dev/null
  docker exec mall-portal sh -lc '
set -e
rm -rf /tmp/gma_mall_portal_patch
mkdir -p /tmp/gma_mall_portal_patch
cd /tmp/gma_mall_portal_patch
jar xf /app/app.jar BOOT-INF/classes BOOT-INF/lib
javac -encoding UTF-8 -cp "BOOT-INF/classes:BOOT-INF/lib/*" -d BOOT-INF/classes /tmp/GmaCommentController.java
jar uf /app/app.jar BOOT-INF/classes/com/macro/mall/portal/controller/GmaCommentController.class
'
  docker restart mall-portal >/dev/null
  for _ in $(seq 1 60); do
    if curl -s -m 2 http://localhost:8041/sso/info >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

docker exec -i mall-portal sh <<'MALL_PORTAL_SH'
set -e
rm -rf /tmp/gma_mall_portal_whitelist
mkdir -p /tmp/gma_mall_portal_whitelist
cd /tmp/gma_mall_portal_whitelist
jar xf /app/app.jar BOOT-INF/classes/application.yml
if ! grep -q "      - /comment/list" BOOT-INF/classes/application.yml; then
  awk '
    { print }
    $0 == "      - /brand/**" {
      print "      - /comment/list"
      print "      - /comment/stats"
      inserted = 1
    }
    END { if (!inserted) exit 2 }
  ' BOOT-INF/classes/application.yml > BOOT-INF/classes/application.yml.tmp
  mv BOOT-INF/classes/application.yml.tmp BOOT-INF/classes/application.yml
  jar uf /app/app.jar BOOT-INF/classes/application.yml
fi
MALL_PORTAL_SH
docker restart mall-portal >/dev/null
for _ in $(seq 1 60); do
  if curl -s -m 2 http://localhost:8041/sso/info >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

python3 - <<'INNER_PY'
import hashlib
import mimetypes
import os
import re
import shlex
import subprocess
import urllib.parse
import urllib.request

FRONTEND = "mall-app-web"
HTML_CACHE_DIR = "/usr/share/nginx/html/gma-cached-assets/mall"
HOST_CACHE_DIR = "/tmp/gma_mall_cached_assets"
CACHE_PREFIX = "http://10.0.2.2:8040/gma-cached-assets/mall"
FALLBACK_IMAGE = "http://10.0.2.2:8040/static/temp/banner1.jpg"
ICON_FONT_URL = "https://at.alicdn.com/t/font_1078604_w4kpxh0rafi.ttf"
ICON_FONT_FILENAME = "gma-yticon.ttf"
ICON_FONT_LOCAL_URL = f"/static/{ICON_FONT_FILENAME}"
cache_map = {}

ICON_SVGS = {
    "order": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M7 4h10l3 4v12H4V8z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><path d='M8 12h8M8 16h6' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "card": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='5' width='18' height='14' rx='2' fill='none' stroke='black' stroke-width='2'/><path d='M3 9h18M7 15h5' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "truck": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 6h11v10H3zM14 10h4l3 3v3h-7z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><circle cx='7' cy='18' r='2' fill='black'/><circle cx='18' cy='18' r='2' fill='black'/></svg>",
    "refund": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M7 7h9a5 5 0 0 1 0 10H8' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'/><path d='M7 7l4-4M7 7l4 4' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "pin": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 22s7-6.5 7-13a7 7 0 0 0-14 0c0 6.5 7 13 7 13z' fill='none' stroke='black' stroke-width='2'/><circle cx='12' cy='9' r='2.5' fill='black'/></svg>",
    "clock": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='9' fill='none' stroke='black' stroke-width='2'/><path d='M12 7v6l4 2' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "heart": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 21s-8-4.8-8-11a4.8 4.8 0 0 1 8-3.6A4.8 4.8 0 0 1 20 10c0 6.2-8 11-8 11z' fill='black'/></svg>",
    "star": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 16.9 6.6 19.8l1-6.1-4.4-4.3 6.1-.9z' fill='black'/></svg>",
    "review": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 5h16v11H8l-4 4z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><path d='M8 9h8M8 13h5' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "gear": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 3l1.3 2.3 2.6.4.4 2.6L19 9.6l-1.2 2.4L19 14.4l-2.7 1.3-.4 2.6-2.6.4L12 21l-1.3-2.3-2.6-.4-.4-2.6L5 14.4 6.2 12 5 9.6l2.7-1.3.4-2.6 2.6-.4z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><circle cx='12' cy='12' r='3' fill='black'/></svg>",
    "grid": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z' fill='none' stroke='black' stroke-width='2'/></svg>",
    "cart": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 4h2l2.5 11H18l2-7H7' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/><circle cx='9' cy='19' r='2' fill='black'/><circle cx='17' cy='19' r='2' fill='black'/></svg>",
    "message": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 5h16v11H9l-5 4z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><path d='M8 9h8M8 13h6' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "diamond": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 3l8 7-8 11-8-11z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><path d='M4 10h16M9 10l3 11 3-11' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/></svg>",
    "search": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='10.5' cy='10.5' r='6.5' fill='none' stroke='black' stroke-width='2'/><path d='M16 16l5 5' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "edit": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 17.5V21h3.5L18.8 9.7l-3.5-3.5z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><path d='M14 7.5L16.5 5 20 8.5 17.5 11' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/></svg>",
    "trash": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M5 7h14M9 7V4h6v3M8 10v9M12 10v9M16 10v9M6 7l1 14h10l1-14' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "plus": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='9' fill='none' stroke='black' stroke-width='2'/><path d='M12 7v10M7 12h10' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "minus": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='9' fill='none' stroke='black' stroke-width='2'/><path d='M7 12h10' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "close": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M6 6l12 12M18 6L6 18' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "check": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M20 6L9 17l-5-5' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "phone": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M6.5 4h3l1.5 5-2 1.5c1 2 2.5 3.5 4.5 4.5L15 13l5 1.5v3c0 1.4-1.1 2.5-2.5 2.5C10 20 4 14 4 6.5 4 5.1 5.1 4 6.5 4z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/></svg>",
    "thumbs_up": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M7 10v10H4V10zM7 10l4-7h2v6h5c1.2 0 2.1 1.1 1.9 2.3l-1 6c-.2 1-1 1.7-2 1.7H7z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/></svg>",
    "help": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='9' fill='none' stroke='black' stroke-width='2'/><path d='M9.5 9a2.7 2.7 0 0 1 5.1 1.2c0 2-2.6 2.2-2.6 4.3M12 18h.01' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "share": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='18' cy='5' r='3' fill='none' stroke='black' stroke-width='2'/><circle cx='6' cy='12' r='3' fill='none' stroke='black' stroke-width='2'/><circle cx='18' cy='19' r='3' fill='none' stroke='black' stroke-width='2'/><path d='M9 11l6-4M9 13l6 4' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "arrow": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M9 5l7 7-7 7' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "payment": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='5' width='18' height='14' rx='2' fill='none' stroke='black' stroke-width='2'/><path d='M3 10h18M7 15h3' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "coffee": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M5 8h11v6a5 5 0 0 1-5 5H10a5 5 0 0 1-5-5zM16 10h2a3 3 0 0 1 0 6h-2M7 3v2M11 3v2M15 3v2' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "alarm": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='13' r='7' fill='none' stroke='black' stroke-width='2'/><path d='M12 9v4l3 2M5 4L3 6M19 4l2 2M7 20l-2 2M17 20l2 2' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "camera": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 8h4l2-3h4l2 3h4v11H4z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/><circle cx='12' cy='13.5' r='3.5' fill='none' stroke='black' stroke-width='2'/></svg>",
    "scan": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5M7 12h10' fill='none' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "hot": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 22c4 0 7-2.8 7-6.8 0-3-1.8-5.2-4.4-7.8-.2 2-1.2 3.2-2.6 4.1.4-3.2-.8-5.7-3.4-8.5C8.7 7.2 5 9.4 5 15.2 5 19.2 8 22 12 22z' fill='black'/></svg>",
    "reply": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M10 7L4 12l6 5v-3h4c3 0 5 1 6 3 0-5-2.5-8-7-8h-3z' fill='none' stroke='black' stroke-width='2' stroke-linejoin='round'/></svg>",
}

ICON_CLASS_MAP = {
    "icon-shouye": "order",
    "icon-daifukuan": "card",
    "icon-yishouhuo": "truck",
    "icon-shouhoutuikuan": "refund",
    "icon-dizhi": "pin",
    "icon-shouhuodizhi": "pin",
    "icon-lishijilu": "clock",
    "icon-shoucang": "heart",
    "icon-shoucang2": "heart",
    "icon-shoucang_xuanzhongzhuangtai": "star",
    "icon-pingjia": "review",
    "icon-comment": "review",
    "icon-pinglun-copy": "review",
    "icon-shezhi": "gear",
    "icon-shezhi1": "gear",
    "icon-fenlei": "grid",
    "icon-fenlei1": "grid",
    "icon-gouwuche": "cart",
    "icon-gouwuche_": "cart",
    "icon-xiaoxi": "message",
    "icon-iLinkapp-": "diamond",
    "icon-sousuo": "search",
    "icon-bianji": "edit",
    "icon-iconfontshanchu1": "trash",
    "icon-shanchu4": "trash",
    "icon-jia1": "plus",
    "icon-jia2": "plus",
    "icon--jianhao": "minus",
    "icon-clear": "close",
    "icon-fork": "close",
    "icon-error": "close",
    "icon-success-no-circle": "check",
    "icon-xuanzhong2": "check",
    "icon-dianhua-copy": "phone",
    "icon-dianzan-ash": "thumbs_up",
    "icon-bangzhu": "help",
    "icon-bangzhu1": "help",
    "icon-fenxiang2": "share",
    "icon-share": "share",
    "icon-forward": "arrow",
    "icon-jiantour-copy": "arrow",
    "icon-arrow-fine-up": "arrow",
    "icon-arrow-left-bottom": "arrow",
    "icon-arrow-left-top": "arrow",
    "icon-arrow-right-bottom": "arrow",
    "icon-shang": "arrow",
    "icon-xia": "arrow",
    "icon-you": "arrow",
    "icon-zuo": "arrow",
    "icon-xiatubiao--copy": "arrow",
    "icon-zuojiantou-up": "arrow",
    "icon-zuoshang": "arrow",
    "icon-hot": "hot",
    "icon-huifu": "reply",
    "icon-iconfontweixin": "message",
    "icon-weixin": "message",
    "icon-weixinzhifu": "payment",
    "icon-alipay": "payment",
    "icon-erjiye-yucunkuan": "payment",
    "icon-kafei": "coffee",
    "icon-naozhong": "alarm",
    "icon-paizhao": "camera",
    "icon-saomiao": "scan",
    "icon-tuandui": "message",
    "icon-tuijian": "star",
    "icon-xingxing": "star",
    "icon-yiguoqi": "clock",
    "icon-yiguoqi1": "clock",
    "icon-zuanshi": "diamond",
    "icon-zhengxinchaxun-zhifubaoceping-": "diamond",
    "icon-Group-": "grid",
    "icon-icon-test": "grid",
    "icon-icon-test1": "grid",
    "icon-icon--": "arrow",
}

subprocess.run(["mkdir", "-p", HOST_CACHE_DIR], check=True)
subprocess.run(["docker", "exec", FRONTEND, "mkdir", "-p", HTML_CACHE_DIR], check=True)
for cached_name in subprocess.check_output(
    ["find", HOST_CACHE_DIR, "-maxdepth", "1", "-type", "f", "-printf", "%f\n"],
    text=True,
).splitlines():
    subprocess.run(
        ["docker", "cp", f"{HOST_CACHE_DIR}/{cached_name}", f"{FRONTEND}:{HTML_CACHE_DIR}/{cached_name}"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def ensure_icon_font(container: str) -> None:
    host_path = f"{HOST_CACHE_DIR}/{ICON_FONT_FILENAME}"
    if not os.path.exists(host_path) or os.path.getsize(host_path) < 10000:
        try:
            request = urllib.request.Request(ICON_FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            if len(data) < 10000:
                raise RuntimeError(f"Mall icon font download was unexpectedly small: {len(data)} bytes")
            with open(host_path, "wb") as handle:
                handle.write(data)
        except Exception as exc:
            print(f"Mall icon font cache failed: {exc}")
    subprocess.run(["docker", "exec", container, "mkdir", "-p", "/usr/share/nginx/html/static"], check=True)
    if os.path.exists(host_path) and os.path.getsize(host_path) > 0:
        subprocess.run(
            ["docker", "cp", host_path, f"{container}:/usr/share/nginx/html/static/{ICON_FONT_FILENAME}"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    else:
        subprocess.run(
            [
                "docker", "exec", container, "sh", "-lc",
                f"cp /usr/share/nginx/html/static/yticon.ttf /usr/share/nginx/html/static/{ICON_FONT_FILENAME} 2>/dev/null || true",
            ],
            check=True,
        )


def icon_fallback_css() -> str:
    lines = [
        "@font-face{font-family:yticon;src:url('/static/gma-yticon.ttf') format('truetype');font-weight:400;font-style:normal;font-display:block;}",
        ".yticon{font-family:yticon!important;}",
        ".yticon:before{display:inline-block;width:1em;height:1em;line-height:1;vertical-align:-.12em;background:currentColor;-webkit-mask:var(--gma-icon) center/contain no-repeat;mask:var(--gma-icon) center/contain no-repeat;}",
    ]
    for class_name, icon_name in ICON_CLASS_MAP.items():
        svg = urllib.parse.quote(ICON_SVGS[icon_name], safe="")
        lines.append(f".{class_name}:before{{content:\"\"!important;--gma-icon:url(\"data:image/svg+xml,{svg}\");}}")
    lines.extend(
        [
            ".icon-you:before{content:\"\\203A\"!important;display:inline;background:none;-webkit-mask:none;mask:none;width:auto;height:auto;vertical-align:baseline;}",
            ".icon-zuo:before{content:\"\\2039\"!important;display:inline;background:none;-webkit-mask:none;mask:none;width:auto;height:auto;vertical-align:baseline;}",
            ".icon-shang:before{content:\"\\2038\"!important;display:inline;background:none;-webkit-mask:none;mask:none;width:auto;height:auto;vertical-align:baseline;}",
            ".icon-xia:before{content:\"\\203A\"!important;display:inline-block;background:none;-webkit-mask:none;mask:none;width:auto;height:auto;vertical-align:baseline;transform:rotate(90deg);}",
        ]
    )
    return "\n".join(lines)


def install_icon_fallback(container: str) -> None:
    index_path = "/usr/share/nginx/html/index.html"
    original = read_file(container, index_path)
    style = f'<style id="gma-mall-icon-fallback">{icon_fallback_css()}</style>'
    patched = re.sub(r'<style id="gma-mall-icon-fallback">[\s\S]*?</style>', '', original)
    if "</head>" in patched:
        patched = patched.replace("</head>", style + "</head>", 1)
    else:
        patched = style + patched
    if patched != original:
        write_file(container, index_path, patched)


def list_files(container: str, root: str) -> list[str]:
    output = subprocess.check_output(
        [
            "docker", "exec", container, "find", root,
            "-type", "f",
            "(", "-name", "*.css", "-o", "-name", "*.html", "-o", "-name", "*.js", ")",
            "-size", "-1024k",
        ],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    ignored_fragments = ("/tinymce", "/tinymce6", "/monaco")
    return [
        path for path in output.splitlines()
        if not any(fragment in path for fragment in ignored_fragments)
    ]


def read_file(container: str, path: str) -> str:
    data = subprocess.check_output(["docker", "exec", container, "cat", path], timeout=10)
    return data.decode("utf-8", errors="replace")


def write_file(container: str, path: str, text: str) -> None:
    subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c", "cat > " + shlex.quote(path)],
        input=text.encode("utf-8"),
        check=True,
        timeout=10,
    )


normal_url = re.compile(r"https?://[^\"'\\\s)>,]*(?:macro-oss|bdstatic|baidu)[^\"'\\\s)>,]*")
escaped_url = re.compile(r"https?:\\?/\\?/[^\"'\\\s)>,]*(?:macro-oss|bdstatic|baidu)[^\"'\\\s)>,]*")


def normalize_url(url: str) -> str:
    return url.replace("\\/", "/")


def extension_for(url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return ".jpg" if guessed == ".jpeg" else guessed
    parsed = urllib.parse.urlparse(url)
    ext = "." + parsed.path.rsplit(".", 1)[-1].lower() if "." in parsed.path.rsplit("/", 1)[-1] else ""
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def cache_url(raw_url: str) -> str:
    url = normalize_url(raw_url)
    if url in cache_map:
        return cache_map[url]
    digest = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:16]
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type")
        if not data or (content_type and not content_type.lower().startswith("image/")):
            raise RuntimeError(f"non-image response: {content_type}")
        filename = f"{digest}{extension_for(url, content_type)}"
        host_path = f"{HOST_CACHE_DIR}/{filename}"
        with open(host_path, "wb") as handle:
            handle.write(data)
        subprocess.run(["docker", "cp", host_path, f"{FRONTEND}:{HTML_CACHE_DIR}/{filename}"], check=True, stdout=subprocess.DEVNULL)
        local = f"{CACHE_PREFIX}/{filename}"
    except Exception as exc:
        print(f"Mall image cache failed for {url}: {exc}")
        local = FALLBACK_IMAGE
    cache_map[url] = local
    return local


def replace_url(match: re.Match[str]) -> str:
    return cache_url(match.group(0))


def patch_container(container: str, root: str, replacement: str) -> None:
    for file_path in list_files(container, root):
        try:
            original = read_file(container, file_path)
        except subprocess.CalledProcessError:
            continue
        patched = normal_url.sub(replace_url, original)
        patched = escaped_url.sub(replace_url, patched)
        patched = patched.replace(
            ICON_FONT_URL,
            ICON_FONT_LOCAL_URL,
        ).replace("/static/yticon.ttf", ICON_FONT_LOCAL_URL)
        if patched != original:
            write_file(container, file_path, patched)


def patch_mall_address_form(container: str) -> None:
    file_names = subprocess.check_output(
        [
            "docker", "exec", container, "find", "/usr/share/nginx/html/static/js",
            "-type", "f", "-name", "pages-address-addressManage*.js",
        ],
        text=True,
    ).splitlines()
    prefix_old = "t.addressData.prefixAddress=t.addressData.province+t.addressData.city+t.addressData.region"
    prefix_new = 't.addressData.prefixAddress=[t.addressData.province,t.addressData.city,t.addressData.region].filter(Boolean).join(" ")'
    covert_old = (
        'covertAdderss:function(e){console.log("covertAdderss",e),-1!=e.indexOf("省")?'
        '(this.addressData.province=e.substr(0,e.indexOf("省")+1),e=e.replace(this.addressData.province,""),'
        'this.addressData.city=e.substr(0,e.indexOf("市")+1),e=e.replace(this.addressData.city,""),'
        'this.addressData.region=e.substr(0,e.indexOf("区")+1)):'
        '(this.addressData.province=e.substr(0,e.indexOf("市")+1),e=e.replace(this.addressData.province,""),'
        'this.addressData.city="",this.addressData.region=e.substr(0,e.indexOf("区")+1))},confirm:function(){'
    )
    covert_v8 = (
        'covertAdderss:function(e){var t=(e||"").trim(),r;console.log("covertAdderss",t),'
        '-1!=t.indexOf("省")?'
        '(this.addressData.province=t.substr(0,t.indexOf("省")+1),t=t.replace(this.addressData.province,"").trim(),'
        'this.addressData.city=t.substr(0,t.indexOf("市")+1),t=t.replace(this.addressData.city,"").trim(),'
        'this.addressData.region=t.substr(0,t.indexOf("区")+1)):'
        '-1!=t.indexOf("市")&&-1!=t.indexOf("区")?'
        '(this.addressData.province=t.substr(0,t.indexOf("市")+1),t=t.replace(this.addressData.province,"").trim(),'
        'this.addressData.city="",this.addressData.region=t.substr(0,t.indexOf("区")+1)):'
        '(r=t.match(/^(.+?\\b(?:Sheng|Province|State))\\s*(.+?\\b(?:Shi|City))?\\s*(.+?\\b(?:Qu|District|County|Borough))\\b/i),r?'
        '(this.addressData.province=(r[1]||"").trim(),this.addressData.city=(r[2]||"").trim(),this.addressData.region=(r[3]||"").trim()):'
        '(this.addressData.province="",this.addressData.city="",this.addressData.region=""))},confirm:function(){'
    )
    covert_new = (
        'covertAdderss:function(e){var t=(e||"").trim(),r;console.log("covertAdderss",t),'
        '-1!=t.indexOf("省")?'
        '(this.addressData.province=t.substr(0,t.indexOf("省")+1),t=t.replace(this.addressData.province,"").trim(),'
        'this.addressData.city=t.substr(0,t.indexOf("市")+1),t=t.replace(this.addressData.city,"").trim(),'
        'this.addressData.region=t.substr(0,t.indexOf("区")+1)):'
        '-1!=t.indexOf("市")&&-1!=t.indexOf("区")?'
        '(this.addressData.province=t.substr(0,t.indexOf("市")+1),t=t.replace(this.addressData.province,"").trim(),'
        'this.addressData.city="",this.addressData.region=t.substr(0,t.indexOf("区")+1)):'
        '(r=t.match(/^(.+?\\b(?:Sheng|Province|State))\\s*(.+?\\b(?:Shi|City))?\\s*(.+?\\b(?:Qu|District|County|Borough))\\b/i),r?'
        '(this.addressData.province=(r[1]||"").trim(),this.addressData.city=(r[2]||"").trim(),this.addressData.region=(r[3]||"").trim()):'
        '(this.addressData.province=t,this.addressData.city="",this.addressData.region=""))},confirm:function(){'
    )
    phone_validation_old = '/(^1[3|4|5|7|8][0-9]{9}$)/.test(t.phoneNumber)'
    phone_validation_new = 'String(t.phoneNumber||"").trim().length>0'
    numeric_input_old = 'attrs:{type:"number",placeholder:"Recipient phone number","placeholder-class":"placeholder"}'
    numeric_input_new = 'attrs:{type:"text",placeholder:"Recipient phone number","placeholder-class":"placeholder"}'
    post_code_input_old = 'attrs:{type:"number",placeholder:"Recipient postal code","placeholder-class":"placeholder"}'
    post_code_input_new = 'attrs:{type:"text",placeholder:"Recipient postal code","placeholder-class":"placeholder"}'
    for file_path in file_names:
        original = read_file(container, file_path)
        patched = (
            original.replace(prefix_old, prefix_new)
            .replace(covert_old, covert_new)
            .replace(covert_v8, covert_new)
            .replace(phone_validation_old, phone_validation_new)
            .replace(numeric_input_old, numeric_input_new)
            .replace(post_code_input_old, post_code_input_new)
        )
        if patched != original:
            write_file(container, file_path, patched)


def patch_mall_public_api_auth(container: str) -> None:
    config_path = "/etc/nginx/conf.d/default.conf"
    marker = "# GMA: strip stale auth from public Mall APIs"
    old_marker = "# GMA: strip stale auth from public Mall home APIs"
    try:
        original = read_file(container, config_path)
    except subprocess.CalledProcessError:
        return
    if marker not in original:
        block = '''    # GMA: strip stale auth from public Mall APIs
    location /mall/app/api/home/ {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /mall/app/api/brand/ {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /mall/app/api/product/ {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location = /mall/app/api/comment/list {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location = /mall/app/api/comment/stats {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

'''
        old_block = '''    # GMA: strip stale auth from public Mall home APIs
    location /mall/app/api/home/ {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

'''
        if old_marker in original and old_block in original:
            patched = original.replace(old_block, block, 1)
        else:
            needle = "    location /mall/app/api/ {"
            if needle not in original:
                return
            patched = original.replace(needle, block + needle, 1)
        write_file(container, config_path, patched)
    elif "location = /mall/app/api/comment/list" not in original:
        comment_block = '''    location = /mall/app/api/comment/list {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location = /mall/app/api/comment/stats {
        set $backend http://mall-portal:8085;
        rewrite ^/mall/app/api/(.*) /$1 break;
        proxy_pass $backend;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

'''
        needle = "    location /mall/app/api/ {"
        if needle not in original:
            return
        write_file(container, config_path, original.replace(needle, comment_block + needle, 1))
    subprocess.run(["docker", "exec", container, "nginx", "-t"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "exec", container, "nginx", "-s", "reload"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def patch_mall_request_ok_toast(container: str) -> None:
    file_names = subprocess.check_output(
        [
            "docker", "exec", container, "find", "/usr/share/nginx/html/static/js",
            "-type", "f", "-name", "*.js", "-size", "-2048k",
        ],
        text=True,
    ).splitlines()
    pattern = re.compile(
        r'console\.log\("response error",([A-Za-z_$][\w$]*)\),'
        r'uni\.showToast\(\{title:\1\.errMsg,duration:1500\}\),'
        r'Promise\.reject\(\1\)'
    )
    for file_path in file_names:
        original = read_file(container, file_path)
        patched = pattern.sub(
            r'console.log("response error",\1),'
            r'\1&&\1.errMsg&&!/^request:\\s*ok$/i.test(\1.errMsg)&&uni.showToast({title:\1.errMsg,duration:1500}),'
            r'Promise.reject(\1)',
            original,
        )
        if patched != original:
            write_file(container, file_path, patched)


ensure_icon_font("mall-app-web")
ensure_icon_font("mall-admin-web")
install_icon_fallback("mall-app-web")
patch_container("mall-app-web", "/usr/share/nginx/html", "/static/temp/banner1.jpg")
patch_mall_address_form("mall-app-web")
patch_mall_public_api_auth("mall-app-web")
patch_mall_request_ok_toast("mall-app-web")
patch_container(
    "mall-admin-web",
    "/usr/share/nginx/html",
    "http://10.0.2.2:8040/static/temp/banner1.jpg",
)

INNER_PY

python3 - <<'INNER_DB_PY'
import hashlib
import mimetypes
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import subprocess

MYSQL_BASE = ['docker', 'exec', '-i', 'mall-mysql', 'mysql', '-umall', '-pmall_pass_2025', '--default-character-set=utf8mb4']
MYSQL_ADMIN_BASE = ['docker', 'exec', '-i', 'mall-mysql', 'mysql', '-uroot', '-pmall_root_2025', '--default-character-set=utf8mb4']
MYSQL_QUERY = ['docker', 'exec', 'mall-mysql', 'mysql', '-umall', '-pmall_pass_2025', '--default-character-set=utf8mb4', '--batch', '--raw', '--skip-column-names']
FRONTEND = 'mall-app-web'
HTML_CACHE_DIR = '/usr/share/nginx/html/gma-cached-assets/mall'
HOST_CACHE_DIR = '/tmp/gma_mall_cached_assets'
CACHE_PREFIX = 'http://10.0.2.2:8040/gma-cached-assets/mall'
SOURCE_DB = 'gma_mall_source_for_images'
SOURCE_DUMP_CANDIDATES = (
    Path('/tmp/gma_mall_export/mall/data-dumps/mall-full-dump.sql'),
    Path('/tmp/gma_mall_export/mall/init/mysql/mall-mysql-dump.sql'),
)
SOURCE_DUMP = next((path for path in SOURCE_DUMP_CANDIDATES if path.exists()), SOURCE_DUMP_CANDIDATES[0])
URL_PATTERN = re.compile(r"https?://[^,'\"\\\s)>,]+")
LOCAL_IMAGES = [
    'http://10.0.2.2:8040/static/temp/banner1.jpg',
    'http://10.0.2.2:8040/static/temp/banner2.jpg',
    'http://10.0.2.2:8040/static/temp/banner3.jpg',
    'http://10.0.2.2:8040/static/temp/banner4.jpg',
    'http://10.0.2.2:8040/static/temp/ad1.jpg',
    'http://10.0.2.2:8040/static/temp/ad2.jpg',
    'http://10.0.2.2:8040/static/temp/ad3.jpg',
    'http://10.0.2.2:8040/static/temp/secskill-img.jpg',
    'http://10.0.2.2:8040/static/temp/cate1.jpg',
    'http://10.0.2.2:8040/static/temp/cate2.jpg',
    'http://10.0.2.2:8040/static/temp/cate3.jpg',
    'http://10.0.2.2:8040/static/temp/cate4.jpg',
]
FALLBACK_IMAGE = LOCAL_IMAGES[0]
cache_map = {}

subprocess.run(['mkdir', '-p', HOST_CACHE_DIR], check=True)
subprocess.run(['docker', 'exec', FRONTEND, 'mkdir', '-p', HTML_CACHE_DIR], check=True)
for cached_name in subprocess.check_output(
    ['find', HOST_CACHE_DIR, '-maxdepth', '1', '-type', 'f', '-printf', '%f\n'],
    text=True,
).splitlines():
    subprocess.run(['docker', 'cp', f'{HOST_CACHE_DIR}/{cached_name}', f'{FRONTEND}:{HTML_CACHE_DIR}/{cached_name}'], check=True, stdout=subprocess.DEVNULL)


def mysql(db: str | None, sql: str) -> None:
    cmd = MYSQL_BASE + ([db] if db else [])
    subprocess.run(cmd, input=sql, text=True, check=True, stdout=subprocess.DEVNULL)


def mysql_admin(db: str | None, sql: str) -> None:
    cmd = MYSQL_ADMIN_BASE + ([db] if db else [])
    subprocess.run(cmd, input=sql, text=True, check=True, stdout=subprocess.DEVNULL)


def mysql_rows(db: str, sql: str) -> list[list[str]]:
    out = subprocess.check_output(MYSQL_QUERY + [db, '-e', sql], text=True)
    return [line.split('\t') for line in out.splitlines() if line.strip()]


def q(value: str) -> str:
    return "'" + str(value).replace('\\', '\\\\').replace("'", "''") + "'"


def qi(identifier: str) -> str:
    return '`' + identifier.replace('`', '``') + '`'


def image_columns() -> list[tuple[str, str, str]]:
    rows = mysql_rows(
        'information_schema',
        '''
select c.table_name, c.column_name, k.column_name
from information_schema.columns c
join information_schema.key_column_usage k
  on k.table_schema = c.table_schema
 and k.table_name = c.table_name
 and k.constraint_name = 'PRIMARY'
where c.table_schema = 'mall'
  and c.data_type in ('char','varchar','text','tinytext','mediumtext','longtext')
  and lower(c.column_name) regexp '(pic|icon|logo|avatar|image|album|proof)'
  and (select count(*) from information_schema.key_column_usage kk where kk.table_schema = c.table_schema and kk.table_name = c.table_name and kk.constraint_name = 'PRIMARY') = 1
order by c.table_name, c.column_name
''',
    )
    return [(row[0], row[1], row[2]) for row in rows]


def local_image_expr(pk: str) -> str:
    choices = ", ".join(q(value) for value in LOCAL_IMAGES)
    return f"elt(mod(cast({qi(pk)} as unsigned), {len(LOCAL_IMAGES)}) + 1, {choices})"


def extension_for(url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(';', 1)[0].strip())
        if guessed in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            return '.jpg' if guessed == '.jpeg' else guessed
    parsed = urllib.parse.urlparse(url)
    name = parsed.path.rsplit('/', 1)[-1]
    ext = '.' + name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        return '.jpg' if ext == '.jpeg' else ext
    return '.jpg'


def fallback_for(value: str, index: int) -> str:
    digest = int(hashlib.sha1(value.encode('utf-8', errors='ignore')).hexdigest()[:8], 16)
    return LOCAL_IMAGES[(digest + index) % len(LOCAL_IMAGES)]


def cache_url(raw_url: str, index: int = 0) -> str:
    url = raw_url.replace('\\/', '/')
    if url.startswith('http://10.0.2.2:8040/') or url.startswith('/static/'):
        return url if url.startswith('http') else 'http://10.0.2.2:8040' + url
    if url in cache_map:
        return cache_map[url]
    digest = hashlib.sha1(url.encode('utf-8', errors='ignore')).hexdigest()[:16]
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get('Content-Type')
        if not data or (content_type and not content_type.lower().startswith('image/')):
            raise RuntimeError(f'non-image response: {content_type}')
        filename = f'{digest}{extension_for(url, content_type)}'
        host_path = f'{HOST_CACHE_DIR}/{filename}'
        with open(host_path, 'wb') as handle:
            handle.write(data)
        subprocess.run(['docker', 'cp', host_path, f'{FRONTEND}:{HTML_CACHE_DIR}/{filename}'], check=True, stdout=subprocess.DEVNULL)
        local = f'{CACHE_PREFIX}/{filename}'
    except Exception as exc:
        print(f'Mall image cache failed for {url}: {exc}')
        local = fallback_for(url, index)
    cache_map[url] = local
    return local


def cache_value(value: str, index: int = 0) -> str:
    if not isinstance(value, str) or not value:
        return value
    return URL_PATTERN.sub(lambda match: cache_url(match.group(0), index), value)


mysql_admin(
    None,
    f"drop database if exists {SOURCE_DB}; "
    f"create database {SOURCE_DB} default character set utf8mb4; "
    f"grant select on {SOURCE_DB}.* to 'mall'@'%'; flush privileges;",
)
if SOURCE_DUMP.exists():
    dump_sql = SOURCE_DUMP.read_text(encoding='utf-8', errors='ignore')
    dump_sql = re.sub(
        r"CREATE DATABASE [^;]*`mall`[^;]*;",
        f"CREATE DATABASE IF NOT EXISTS `{SOURCE_DB}` DEFAULT CHARACTER SET utf8mb4;",
        dump_sql,
        count=1,
    )
    dump_sql = dump_sql.replace('USE `mall`;', f'USE `{SOURCE_DB}`;')
    subprocess.run(MYSQL_ADMIN_BASE, input=dump_sql, text=True, check=True, stdout=subprocess.DEVNULL)

mysql(
    'mall',
    '''
update sms_home_advertise
set start_time = date_sub(now(), interval 1 day),
    end_time = date_add(now(), interval 365 day),
    status = 1
where status = 1;
update sms_flash_promotion
set start_date = curdate(),
    end_date = date_add(curdate(), interval 365 day),
    status = 1
where status = 1
   or id in (select distinct flash_promotion_id from sms_flash_promotion_product_relation);
update sms_flash_promotion_session
set start_time = '00:00:00',
    end_time = '23:59:59',
    status = 1
where id = 1;
update sms_flash_promotion_session
set status = 1
where start_time is not null and end_time is not null;
update sms_flash_promotion_product_relation
set flash_promotion_price = coalesce(flash_promotion_price, 1),
    flash_promotion_count = coalesce(flash_promotion_count, 10),
    flash_promotion_limit = coalesce(flash_promotion_limit, 1)
where flash_promotion_id in (select id from sms_flash_promotion);
''',
)

updated = 0
rows_seen = 0
for table, column, pk in image_columns():
    try:
        select_sql = (
            f"select {qi(pk)}, {qi(column)} from {qi(table)} "
            f"where {qi(column)} is not null and {qi(column)} <> '';"
        )
        rows = mysql_rows(SOURCE_DB, select_sql)
    except subprocess.CalledProcessError:
        rows = []
    if not rows:
        try:
            rows = mysql_rows('mall', select_sql)
        except subprocess.CalledProcessError:
            rows = []
    for index, row in enumerate(rows):
        if len(row) < 2:
            continue
        row_id, original_value = row[0], row[1]
        cached_value = cache_value(original_value, index)
        if cached_value == original_value:
            continue
        mysql(
            'mall',
            f"update {qi(table)} set {qi(column)} = {q(cached_value)} where {qi(pk)} = {q(row_id)};",
        )
        rows_seen += 1
    updated += 1
mysql_admin(None, f'drop database if exists {SOURCE_DB};')
print(f'Mall cached original image URLs for {rows_seen} row(s) across {updated} image column(s)')
INNER_DB_PY

docker exec mall-app-web touch /tmp/gma_runtime_patched_v16 >/dev/null 2>&1 || true
docker exec mall-admin-web touch /tmp/gma_runtime_patched_v16 >/dev/null 2>&1 || true
docker exec mall-mysql touch /tmp/gma_runtime_patched_v16 >/dev/null 2>&1 || true
docker exec mall-portal touch /tmp/gma_runtime_patched_v16 >/dev/null 2>&1 || true
""",
        timeout=600,
    )


def _patch_meituan_runtime(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -euo pipefail

seed_root=""
for candidate in \
  /data/zhuyiqi/GMA/src/gma/apps/seed_data/mall_meituan \
  /app/gma/src/gma/apps/seed_data/mall_meituan; do
  if [ -f "$candidate/meituan_restaurants.json" ]; then
    seed_root="$candidate"
    break
  fi
done
if [ -n "$seed_root" ]; then
  deadline=$((SECONDS + 120))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if docker ps --format '{{.Names}}' | grep -qx meituan-mongo       && docker ps --format '{{.Names}}' | grep -qx meituan-frontend; then
      break
    fi
    sleep 2
  done
fi
if [ -n "$seed_root" ] && docker ps --format '{{.Names}}' | grep -qx meituan-mongo; then
  if [ -d "$seed_root/images/meituan" ]; then
    docker exec meituan-frontend mkdir -p /usr/share/nginx/html/gma-cached-assets/annotator/meituan
    docker cp "$seed_root/images/meituan/." meituan-frontend:/usr/share/nginx/html/gma-cached-assets/annotator/meituan/ >/dev/null
  fi
  docker cp "$seed_root/meituan_restaurants.json" meituan-mongo:/tmp/gma_seed_restaurants.json >/dev/null
  docker cp "$seed_root/meituan_foods.json" meituan-mongo:/tmp/gma_seed_foods.json >/dev/null
  docker cp "$seed_root/meituan_categories.json" meituan-mongo:/tmp/gma_seed_categories.json >/dev/null
  cat >/tmp/gma_meituan_seed_import.js <<'JS'
function hydrate(value) {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map(hydrate);
  if (typeof value === 'object') {
    if (Object.keys(value).length === 1 && value.$date) return new Date(value.$date);
    var out = {};
    Object.keys(value).forEach(function(key) { out[key] = hydrate(value[key]); });
    return out;
  }
  return value;
}
function readJson(path) {
  return hydrate(JSON.parse(cat(path)));
}
var restaurants = readJson('/tmp/gma_seed_restaurants.json');
var foods = readJson('/tmp/gma_seed_foods.json');
var categories = readJson('/tmp/gma_seed_categories.json');
var keepRestaurantIds = restaurants.map(function(doc) { return doc.id; });
db.restaurants.remove({});
db.foods.remove({});
db.categories.remove({});
db.orders.remove({});
db.pays.remove({});
db.comments.remove({});
db.collections.remove({});
db.footprints.remove({});
db.shoppingcarts.remove({});
if (restaurants.length) db.restaurants.insert(restaurants);
if (categories.length) db.categories.insert(categories);
if (foods.length) db.foods.insert(foods);
db.categories.find().forEach(function(category) {
  var foodIds = db.foods.find({restaurant_id: category.restaurant_id, category_id: category.id}).map(function(food) { return food._id; });
  db.categories.update({id: category.id}, {$set: {spus: foodIds}});
});
var idsDoc = db.ids.findOne();
var idFields = idsDoc || {};
function maxId(collection, field) {
  var sortSpec = {};
  sortSpec[field] = -1;
  var doc = db.getCollection(collection).find().sort(sortSpec).limit(1).toArray()[0];
  return doc && doc[field] ? Number(doc[field]) : 0;
}
var next = {
  restaurant_id: maxId('restaurants', 'id'),
  food_id: maxId('foods', 'id'),
  category_id: maxId('categories', 'id'),
  order_id: maxId('orders', 'id'),
  comment_id: maxId('comments', 'id'),
  shopping_cart_id: maxId('shoppingcarts', 'id')
};
var setIds = {};
Object.keys(next).forEach(function(key) { setIds[key] = Math.max(Number(idFields[key] || 0), next[key]); });
if (idsDoc) {
  db.ids.update({_id: idsDoc._id}, {$set: setIds});
} else {
  db.ids.insert(setIds);
}
print('seededRestaurants=' + db.restaurants.count());
print('seededFoods=' + db.foods.count());
print('seededCategories=' + db.categories.count());
JS
  docker exec -i meituan-mongo mongo --quiet takeaway < /tmp/gma_meituan_seed_import.js >/dev/null
fi

runtime_already_patched=0
if docker exec meituan-frontend test -f /tmp/gma_runtime_patched_v8 2>/dev/null \
  && docker exec meituan-backend test -f /tmp/gma_runtime_patched_v8 2>/dev/null \
  && docker exec meituan-mongo test -f /tmp/gma_runtime_patched_v8 2>/dev/null; then
  runtime_already_patched=1
fi

if [ "$runtime_already_patched" -eq 0 ]; then
python3 - <<'INNER_PY'
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import shlex
import subprocess
import time
import urllib.parse
import urllib.request

FRONTEND = "meituan-frontend"
BACKEND = "meituan-backend"
MONGO = "meituan-mongo"
HTML_ROOT = "/usr/share/nginx/html"
CACHE_DIR = f"{HTML_ROOT}/gma-cached-assets"
CACHE_PREFIX = "/gma-cached-assets"
HOST_CACHE_DIR = "/tmp/gma_meituan_cached_assets"
MEITUAN_ICON_FONT_URL = "https://at.alicdn.com/t/font_407663_9ufqp98dcmw5qaor.ttf"
MEITUAN_ICON_FONT_FILENAME = "gma-meituan-iconfont.ttf"
MEITUAN_ICON_FONT_LOCAL_URL = f"{CACHE_PREFIX}/{MEITUAN_ICON_FONT_FILENAME}"
LOCAL_IMAGES = [
    "/img/restaurant.a244c07f.jpg",
    "/img/friend_img.f32c540c.png",
    "/img/pay_adv.ca2756cb.png",
    "/img/nothing.5cadc1b8.png",
    "/img/delivery-avatar.61d561c7.png",
]
FALLBACK_IMAGE = LOCAL_IMAGES[0]
FALLBACK_AVATAR = "/img/delivery-avatar.61d561c7.png"
MEITUAN_ICON_SVGS = {
    "back": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M15 5l-7 7 7 7' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "plus": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='9' fill='none' stroke='black' stroke-width='2'/><path d='M12 7v10M7 12h10' stroke='black' stroke-width='2' stroke-linecap='round'/></svg>",
    "trash": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M5 7h14M9 7V4h6v3M8 10v9M12 10v9M16 10v9M6 7l1 14h10l1-14' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "check": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M20 6L9 17l-5-5' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>",
}

image_url = re.compile(r"https?://[^\"'\\\s)>,]*(?:p\d\.meituan\.net|xs01\.meituan\.net|i\.waimai\.meituan\.com)[^\"'\\\s)>,]*")
escaped_image_url = re.compile(r"https?:\\?/\\?/[^\"'\\\s)>,]*(?:p\d\.meituan\.net|xs01\.meituan\.net|i\.waimai\.meituan\.com)[^\"'\\\s)>,]*")
icon_font_url = re.compile(r"url\((?:https?:)?//at\.alicdn\.com/t/font_407663_9ufqp98dcmw5qaor\.[^)]+\)")
flexible_script = re.compile(
    r"<script\s+src=http://g\.tbcdn\.cn/mtb/lib-flexible/0\.3\.4/\?\?flexible_css\.js,flexible\.js></script>"
)
inline_flexible = (
    "<script>(function(){function r(){var w=document.documentElement.clientWidth||375;"
    "document.documentElement.style.fontSize=Math.min(w,540)/10+'px'}"
    "r();window.addEventListener('resize',r)})();</script>"
)
cache_map = {}


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def check_output(args, **kwargs):
    return subprocess.check_output(args, **kwargs)


run(["mkdir", "-p", HOST_CACHE_DIR])
run(["docker", "exec", FRONTEND, "mkdir", "-p", CACHE_DIR])
for cached_name in check_output(["find", HOST_CACHE_DIR, "-maxdepth", "1", "-type", "f", "-printf", "%f\n"], text=True).splitlines():
    run(["docker", "cp", f"{HOST_CACHE_DIR}/{cached_name}", f"{FRONTEND}:{CACHE_DIR}/{cached_name}"], stdout=subprocess.DEVNULL)


def list_files(container: str, root: str) -> list[str]:
    output = check_output(
        ["docker", "exec", container, "find", root, "-type", "f"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    suffixes = (".css", ".html", ".js", ".map")
    return [path for path in output.splitlines() if path.endswith(suffixes)]


def read_file(container: str, file_path: str) -> str:
    data = check_output(["docker", "exec", container, "cat", file_path])
    return data.decode("utf-8", errors="replace")


def write_file(container: str, file_path: str, content: str) -> None:
    run(
        ["docker", "exec", "-i", container, "sh", "-c", "cat > " + shlex.quote(file_path)],
        input=content.encode("utf-8"),
    )


def cache_meituan_icon_font() -> None:
    host_path = Path(HOST_CACHE_DIR) / MEITUAN_ICON_FONT_FILENAME
    if not host_path.exists() or host_path.stat().st_size < 10000:
        try:
            request = urllib.request.Request(MEITUAN_ICON_FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            if len(data) < 10000:
                raise RuntimeError(f"unexpectedly small icon font: {len(data)} bytes")
            host_path.write_bytes(data)
        except Exception as exc:
            print(f"Meituan icon font cache failed: {exc}")
            return
    run(["docker", "cp", str(host_path), f"{FRONTEND}:{CACHE_DIR}/{MEITUAN_ICON_FONT_FILENAME}"], stdout=subprocess.DEVNULL)


def meituan_icon_mask(icon_name: str) -> str:
    data = urllib.parse.quote(MEITUAN_ICON_SVGS[icon_name], safe="")
    return f'url("data:image/svg+xml,{data}")'


def meituan_icon_fallback_css() -> str:
    return "\n".join([
        f"@font-face{{font-family:iconfont;src:url('{MEITUAN_ICON_FONT_LOCAL_URL}') format('truetype');font-weight:400;font-style:normal;font-display:block;}}",
        "#address .go-back .iconfont,#address .add .iconfont.icon,#address .container ul li .delete.iconfont,#address-info .gender .iconfont{font-family:iconfont,Arial,sans-serif!important;font-size:0!important;position:relative}",
        "#address .go-back .iconfont:before,#address .add .iconfont.icon:before,#address .container ul li .delete.iconfont:before,#address-info .gender .iconfont:before{content:\"\"!important;display:inline-block;width:1em;height:1em;line-height:1;vertical-align:-.12em;background:currentColor;-webkit-mask:var(--gma-icon) center/contain no-repeat;mask:var(--gma-icon) center/contain no-repeat;}",
        f"#address .go-back .iconfont:before{{--gma-icon:{meituan_icon_mask('back')};font-size:.72rem;color:#333;}}",
        f"#address .add .iconfont.icon:before{{--gma-icon:{meituan_icon_mask('plus')};font-size:.62rem;color:#ffd161;}}",
        f"#address .container ul li .delete.iconfont:before{{--gma-icon:{meituan_icon_mask('trash')};font-size:.58rem;color:#666;}}",
        f"#address-info .gender .iconfont:before{{--gma-icon:{meituan_icon_mask('check')};font-size:.38rem;color:#fff;}}",
    ])


def normalize_url(url: str) -> str:
    return url.replace("\\/", "/")


def extension_for(url: str, content_type: str | None) -> str:
    parsed = urllib.parse.urlparse(url)
    filename = parsed.path.rsplit("/", 1)[-1]
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if 1 <= len(ext) <= 6:
            return ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed:
            return guessed
    return ".bin"


def local_image_for(value: str, index: int = 0) -> str:
    if re.search(r"avatar|head|user", value, flags=re.I):
        return FALLBACK_AVATAR
    digest = int(hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
    return LOCAL_IMAGES[(digest + index) % len(LOCAL_IMAGES)]


def fallback_for(url: str) -> str:
    return local_image_for(url)


def cache_url(raw_url: str) -> str:
    url = normalize_url(raw_url)
    if url in cache_map:
        return cache_map[url]
    digest = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:16]
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type")
        if not data or (content_type and not content_type.lower().startswith("image/")):
            raise RuntimeError(f"non-image response: {content_type}")
        filename = f"{digest}{extension_for(url, content_type)}"
        host_path = f"{HOST_CACHE_DIR}/{filename}"
        with open(host_path, "wb") as handle:
            handle.write(data)
        run(["docker", "cp", host_path, f"{FRONTEND}:{CACHE_DIR}/{filename}"], stdout=subprocess.DEVNULL)
        local = f"{CACHE_PREFIX}/{filename}"
    except Exception as exc:
        print(f"Meituan image cache failed for {url}: {exc}")
        local = fallback_for(url)
    cache_map[url] = local
    return local


def replace_match(match: re.Match[str]) -> str:
    return cache_url(match.group(0))


cache_meituan_icon_font()
for file_path in list_files(FRONTEND, HTML_ROOT):
    try:
        original = read_file(FRONTEND, file_path)
    except subprocess.CalledProcessError:
        continue
    patched = flexible_script.sub(inline_flexible, original)
    patched = icon_font_url.sub(f"url({MEITUAN_ICON_FONT_LOCAL_URL})", patched)
    patched = image_url.sub(replace_match, patched)
    patched = escaped_image_url.sub(replace_match, patched)
    if patched != original:
        write_file(FRONTEND, file_path, patched)

category_filter_expr = 'third_category:(window.location.hash.match(/[?&]type=([^&]+)/)||[])[1]?decodeURIComponent((window.location.hash.match(/[?&]type=([^&]+)/)||[])[1]):""'
category_request_pattern = re.compile(r'Object\(([^)]*)\)\(\{offset:([^,]+),limit:this\.limit,lng:([^,]+),lat:([^,]+),sort_type:this\.sortType\}\)')
for file_path in list_files(FRONTEND, HTML_ROOT):
    if not file_path.endswith('.js'):
        continue
    try:
        original = read_file(FRONTEND, file_path)
    except subprocess.CalledProcessError:
        continue
    if 'sort_type:this.sortType' not in original or 'nearby-shops' not in original:
        continue
    def add_category(match):
        return f'Object({match.group(1)})({{offset:{match.group(2)},limit:this.limit,lng:{match.group(3)},lat:{match.group(4)},sort_type:this.sortType,{category_filter_expr}}})'
    patched = category_request_pattern.sub(add_category, original)
    if patched != original:
        write_file(FRONTEND, file_path, patched)

# The original Meituan cart is Vuex/localStorage-only. Seeded cart rows live in
# MongoDB, so add a read-only GMA endpoint and hydrate localStorage before Vue
# mounts. This keeps cart assets backend-backed and visible in the existing UI.
controller_path = "/app/controller/v1/restaurant.js"
controller = read_file(BACKEND, controller_path)
controller_original = controller
controller = controller.replace(
    "let {offset = 0, limit = 5, sort_type = '', lng, lat} = req.query;",
    "let {offset = 0, limit = 5, sort_type = '', lng, lat, third_category = ''} = req.query;",
)
controller = controller.replace(
    "let query = RestaurantModel.find({}).limit(Number(limit)).skip(Number(offset));",
    "let filter = {};\n      if (third_category) {\n        filter.third_category = String(third_category);\n      }\n      let query = RestaurantModel.find(filter).limit(Number(limit)).skip(Number(offset));",
)

routes_path = "/app/routes/v1.js"
routes = read_file(BACKEND, routes_path)
backend_changed = controller != controller_original
if backend_changed:
    write_file(BACKEND, controller_path, controller)
if "gma_cart" not in routes:
    routes = routes.replace(
        "import Category from '../models/v1/category';",
        "import Category from '../models/v1/category';\n"
        "import mongoose from 'mongoose';\n"
        "import AdminModel from '../models/admin/admin';\n"
        "import RestaurantModel from '../models/v1/restaurant';\n"
        "import FoodModel from '../models/v1/foods';",
    )
    route_code = r'''

router.get('/gma_cart', async (req, res) => {
  try {
    let userId = Number(req.query.user_id || req.session.user_id || 0);
    if (!userId && req.query.username) {
      const user = await AdminModel.findOne({username: req.query.username, status: 1});
      if (user) {
        userId = user.id;
      }
    }
    if (!userId) {
      res.send({status: 200, data: {}});
      return;
    }

    const rows = await mongoose.connection.collection('shoppingcarts').find({user_id: userId}).toArray();
    const cartList = {};
    for (const row of rows) {
      const restaurant = await RestaurantModel.findOne({id: row.restaurant_id}).lean();
      if (!restaurant) {
        continue;
      }
      const food = await FoodModel.findOne({restaurant_id: row.restaurant_id, 'skus.id': row.sku_id}).lean();
      const sku = food && food.skus ? food.skus.find(item => Number(item.id) === Number(row.sku_id)) : null;
      const restaurantKey = String(row.restaurant_id);
      const foodKey = String(row.sku_id);
      const price = Number(row.price == null && sku ? sku.price : row.price || 0);
      const num = Number(row.num || 0);
      if (!cartList[restaurantKey]) {
        cartList[restaurantKey] = {
          totalPrice: 0,
          totalNum: 0,
          restaurant_name: restaurant.name,
          pic_url: restaurant.pic_url,
        };
      }
      cartList[restaurantKey][foodKey] = {
        name: row.name || (food ? food.name : ''),
        price,
        foods_pic: food ? food.pic_url : restaurant.pic_url,
        num,
        id: Number(row.sku_id),
      };
      cartList[restaurantKey].totalPrice = Number((Number(cartList[restaurantKey].totalPrice || 0) + price * num).toFixed(2));
      cartList[restaurantKey].totalNum = Number(cartList[restaurantKey].totalNum || 0) + num;
    }
    res.send({status: 200, data: cartList});
  } catch (err) {
    console.log('GMA cart hydration failed', err);
    res.send({status: -1, message: 'GMA cart hydration failed'});
  }
});
'''
    routes = routes.replace("\nexport default router;", route_code + "\nexport default router;")
    write_file(BACKEND, routes_path, routes)
    backend_changed = True

index_path = f"{HTML_ROOT}/index.html"
index_html = read_file(FRONTEND, index_path)
bootstrap = (
    '<script id="gma-cart-bootstrap">(function(){try{'
    'var username=localStorage.getItem("mt-username")||"owner";'
    'var login=new XMLHttpRequest();'
    'login.open("POST","/api/admin/user_login",false);'
    'login.withCredentials=true;'
    'login.setRequestHeader("Content-Type","application/json");'
    'login.send(JSON.stringify({username:username,password:"123456"}));'
    'localStorage.setItem("mt-username",username);'
    'var xhr=new XMLHttpRequest();'
    'xhr.open("GET","/api/v1/gma_cart?username="+encodeURIComponent(username),false);'
    'xhr.withCredentials=true;'
    'xhr.send(null);'
    'if(xhr.status===200){var payload=JSON.parse(xhr.responseText||"{}");'
    'if(payload&&payload.status===200&&payload.data){localStorage.setItem("cartList",JSON.stringify(payload.data));}}'
    '}catch(e){}})();</script>'
)
address_bootstrap = r'''<style id="gma-address-style">
#address nav[data-v-10155078]{box-sizing:border-box;padding-right:.35rem!important}
#address .add[data-v-10155078],#address .add[data-v-b51e2000],#address .add{bottom:1.3333333333rem!important;background:#fff;z-index:230}
#address .container[data-v-10155078],#address .container[data-v-b51e2000],#address .container{padding-bottom:2.9rem}
#address .container ul li .gma-edit-address{display:inline-flex;align-items:center;justify-content:center;margin:0 .25rem;padding:.08rem .22rem;border:1px solid #ffd161;border-radius:.2rem;background:#fff;color:#c99800;font-size:.34rem;line-height:.52rem}
#address .container ul li .gma-edit-address:active{background:#fff7d8}
''' + meituan_icon_fallback_css() + r'''</style><script id="gma-address-bootstrap">(function(){
  if (window.__gmaMeituanAddressBootstrap) return;
  window.__gmaMeituanAddressBootstrap = true;
  const editHash = /#\/add_address(?:\?|$)/;
  const listHash = /#\/home\/address(?:$|[/?])/;
  const getEditId = () => {
    const match = location.hash.match(/[?&]edit_id=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };
  const addressRequest = () => fetch("/api/admin/all_address", {credentials: "include"})
    .then((response) => response.json())
    .then((payload) => Array.isArray(payload.address) ? payload.address : [])
    .catch(() => []);
  const dispatchInput = (input, value) => {
    if (!input) return;
    input.value = value == null ? "" : String(value);
    input.dispatchEvent(new Event("input", {bubbles: true}));
  };
  const selectGender = (gender) => {
    const wanted = gender === "female" ? "Ms." : "Mr.";
    const item = Array.from(document.querySelectorAll("#address-info .gender div"))
      .find((node) => node.textContent.indexOf(wanted) !== -1);
    if (item && !item.querySelector(".iconfont")) item.click();
  };
  const fillEditForm = () => {
    const id = getEditId();
    if (!id || !editHash.test(location.hash) || document.body.dataset.gmaEditAddressLoaded === id) return;
    const root = document.querySelector("#address-info");
    if (!root) return;
    addressRequest().then((addresses) => {
      const record = addresses.find((item) => String(item.id) === String(id));
      if (!record) return;
      document.body.dataset.gmaEditAddressLoaded = id;
      const title = document.querySelector("#address .title");
      if (title) title.textContent = "Edit Address";
      const save = document.querySelector("#address .btn-save");
      if (save) save.textContent = "Save";
      dispatchInput(document.querySelector("#name"), record.name);
      dispatchInput(document.querySelector("#phone"), record.phone);
      dispatchInput(document.querySelector("#address-title"), record.title || record.label || "");
      dispatchInput(document.querySelector("#address-detail"), record.address);
      dispatchInput(document.querySelector("#house-number"), record.house_number);
      selectGender(record.gender);
    });
  };
  const ensureListControls = () => {
    if (!listHash.test(location.hash)) return;
    const rows = Array.from(document.querySelectorAll("#address .container ul li"));
    if (!rows.length) return;
    addressRequest().then((addresses) => {
      rows.forEach((row, index) => {
        if (row.querySelector(".gma-edit-address")) return;
        const record = addresses[index];
        if (!record) return;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "gma-edit-address";
        button.textContent = "Edit";
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          location.hash = "#/add_address?edit_id=" + encodeURIComponent(record.id);
        });
        const deleteButton = row.querySelector(".delete");
        row.insertBefore(button, deleteButton || null);
      });
    });
  };
  document.addEventListener("click", (event) => {
    const button = event.target.closest && event.target.closest("#address .btn-save");
    const id = getEditId();
    if (!button || !id || !editHash.test(location.hash)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const selectedGender = Array.from(document.querySelectorAll("#address-info .gender div"))
      .find((node) => node.querySelector(".iconfont"));
    const payload = {
      id: Number(id),
      name: (document.querySelector("#name") || {}).value || "",
      phone: (document.querySelector("#phone") || {}).value || "",
      gender: selectedGender && selectedGender.textContent.indexOf("Ms.") !== -1 ? "female" : "male",
      title: (document.querySelector("#address-title") || {}).value || "",
      address: (document.querySelector("#address-detail") || {}).value || "",
      house_number: (document.querySelector("#house-number") || {}).value || ""
    };
    if (!payload.name || !payload.phone || !payload.title || !payload.address || !payload.house_number) {
      alert("Please fill in all fields");
      return;
    }
    fetch("/api/admin/update_address", {
      method: "POST",
      credentials: "include",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    }).then((response) => response.json()).then((payload) => {
      if (payload.status === 200) history.back();
      else alert(payload.message || "Failed to update address");
    }).catch(() => alert("Failed to update address"));
  }, true);
  const refresh = () => {
    if (!editHash.test(location.hash)) delete document.body.dataset.gmaEditAddressLoaded;
    ensureListControls();
    fillEditForm();
  };
  window.addEventListener("hashchange", () => setTimeout(refresh, 250));
  new MutationObserver(() => refresh()).observe(document.documentElement, {childList: true, subtree: true});
  setInterval(refresh, 1000);
  setTimeout(refresh, 250);
})();</script>'''
patched_index_html = re.sub(r'<script id="gma-cart-bootstrap">.*?</script>', bootstrap, index_html, flags=re.S)
patched_index_html = re.sub(r'<style id="gma-address-style">.*?</style>\s*<script id="gma-address-bootstrap">.*?</script>', '', patched_index_html, flags=re.S)
if patched_index_html == index_html and "gma-cart-bootstrap" not in index_html:
    patched_index_html = index_html.replace("<script src=/js/chunk-vendors", bootstrap + "<script src=/js/chunk-vendors")
if "gma-address-bootstrap" not in patched_index_html:
    patched_index_html = patched_index_html.replace("<script src=/js/chunk-vendors", address_bootstrap + "<script src=/js/chunk-vendors")
if patched_index_html != index_html:
    write_file(FRONTEND, index_path, patched_index_html)
if backend_changed:
    open("/tmp/gma_meituan_backend_changed", "w").write("1")

for _ in range(60):
    try:
        count_raw = check_output(['docker', 'exec', '-i', MONGO, 'mongo', 'takeaway', '--quiet', '--eval', 'db.restaurants.count()'], text=True)
        count_lines = [line.strip() for line in count_raw.splitlines() if line.strip()]
        if count_lines and int(float(count_lines[-1])) > 0:
            break
    except Exception:
        pass
    time.sleep(2)
collect_script = r'''
var urls = {};
function add(value) {
  if (typeof value === 'string' && /^https?:\/\//.test(value)) urls[value] = true;
}
db.restaurants.find().forEach(function (doc) {
  add(doc.pic_url);
  (doc.discounts2 || []).forEach(function (item) { add(item.icon_url); });
});
db.foods.find().forEach(function (doc) { add(doc.pic_url); });
db.orders.find().forEach(function (doc) {
  if (doc.basket && doc.basket.group) {
    doc.basket.group.forEach(function (item) { add(item.image_path); });
  }
});
print(JSON.stringify(Object.keys(urls)));
'''
try:
    raw_urls = check_output(['docker', 'exec', '-i', MONGO, 'mongo', 'takeaway', '--quiet'], input=collect_script, text=True)
    db_urls = json.loads([line for line in raw_urls.splitlines() if line.strip()][-1])
except Exception:
    db_urls = []

mongo_map = {url: cache_url(url) for url in db_urls if image_url.search(url) or escaped_image_url.search(url)}
if mongo_map:
    patch_script = r'''
var mapping = __MAPPING__;
function mapUrl(value) {
  return (typeof value === 'string' && mapping[value]) ? mapping[value] : value;
}
db.restaurants.find().forEach(function (doc) {
  doc.pic_url = mapUrl(doc.pic_url);
  (doc.discounts2 || []).forEach(function (item) { item.icon_url = mapUrl(item.icon_url); });
  db.restaurants.save(doc);
});
db.foods.find().forEach(function (doc) {
  doc.pic_url = mapUrl(doc.pic_url);
  db.foods.save(doc);
});
db.orders.find().forEach(function (doc) {
  if (doc.basket && doc.basket.group) {
    doc.basket.group.forEach(function (item) { item.image_path = mapUrl(item.image_path); });
    db.orders.save(doc);
  }
});
'''.replace('__MAPPING__', json.dumps(mongo_map, indent=2))
    run(['docker', 'exec', '-i', MONGO, 'mongo', 'takeaway', '--quiet'], input=patch_script.encode('utf-8'), stdout=subprocess.DEVNULL)


def bson_value(value):
    if isinstance(value, dict):
        for key in ("$numberInt", "$numberLong", "$numberDouble"):
            if key in value:
                return int(float(value[key]))
    return value


def dump_bson_records(source_path: str, target_name: str) -> list[dict]:
    try:
        run(["docker", "cp", source_path, f"{MONGO}:/tmp/{target_name}"], stdout=subprocess.DEVNULL)
        raw = check_output(
            ["docker", "exec", MONGO, "bsondump", "--quiet", f"/tmp/{target_name}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    records = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


source_db_dir = "/tmp/gma_meituan_export/meituan/mongodump/takeaway"
source_restaurants = []
for doc in dump_bson_records(f"{source_db_dir}/restaurants.bson", "gma-source-restaurants.bson"):
    doc_id = bson_value(doc.get("id"))
    url = doc.get("pic_url")
    if not doc_id or not isinstance(url, str) or not image_url.search(url):
        continue
    item = {"id": doc_id, "pic_url": cache_url(url)}
    discounts = []
    for discount in doc.get("discounts2") or []:
        icon_url = discount.get("icon_url") if isinstance(discount, dict) else None
        if isinstance(icon_url, str) and image_url.search(icon_url):
            discounts.append({"icon_url": cache_url(icon_url)})
        else:
            discounts.append({})
    if discounts:
        item["discounts2"] = discounts
    source_restaurants.append(item)

source_foods = []
for doc in dump_bson_records(f"{source_db_dir}/foods.bson", "gma-source-foods.bson"):
    doc_id = bson_value(doc.get("id"))
    restaurant_id = bson_value(doc.get("restaurant_id"))
    url = doc.get("pic_url")
    if not doc_id or not restaurant_id or not isinstance(url, str) or not image_url.search(url):
        continue
    source_foods.append({"id": doc_id, "restaurant_id": restaurant_id, "pic_url": cache_url(url)})

if source_restaurants or source_foods:
    source_patch_script = r'''
var restaurants = __RESTAURANTS__;
var foods = __FOODS__;
restaurants.forEach(function (item) {
  var setValue = {pic_url: item.pic_url};
  if (item.discounts2 && item.discounts2.length) {
    var doc = db.restaurants.findOne({id: item.id});
    if (doc && doc.discounts2) {
      for (var i = 0; i < item.discounts2.length && i < doc.discounts2.length; i++) {
        if (item.discounts2[i].icon_url) {
          doc.discounts2[i].icon_url = item.discounts2[i].icon_url;
        }
      }
      setValue.discounts2 = doc.discounts2;
    }
  }
  db.restaurants.update({id: item.id}, {$set: setValue}, {multi: false});
});
foods.forEach(function (item) {
  db.foods.update(
    {id: item.id, restaurant_id: item.restaurant_id},
    {$set: {pic_url: item.pic_url}},
    {multi: false}
  );
});
'''.replace('__RESTAURANTS__', json.dumps(source_restaurants, indent=2)).replace(
        '__FOODS__', json.dumps(source_foods, indent=2)
    )
    run(['docker', 'exec', '-i', MONGO, 'mongo', 'takeaway', '--quiet'], input=source_patch_script.encode('utf-8'), stdout=subprocess.DEVNULL)

available_cached = [
    name.strip()
    for name in check_output(
        [
            "docker",
            "exec",
            FRONTEND,
            "sh",
            "-lc",
            "find " + shlex.quote(CACHE_DIR) + " -maxdepth 1 -type f -exec basename {} \\;",
        ],
        text=True,
        stderr=subprocess.DEVNULL,
    ).splitlines()
    if name.strip()
]
if available_cached:
    repair_cached_refs_script = r'''
var available = __AVAILABLE__;
var availableSet = {};
available.forEach(function (name) { availableSet[name] = true; });
function repair(value, index) {
  if (typeof value !== 'string' || value.indexOf('/gma-cached-assets/') !== 0) return value;
  var name = value.split('/').pop();
  if (availableSet[name]) return value;
  return '/gma-cached-assets/' + available[index % available.length];
}
var index = 0;
db.restaurants.find().forEach(function (doc) {
  doc.pic_url = repair(doc.pic_url, index++);
  (doc.discounts2 || []).forEach(function (item) { item.icon_url = repair(item.icon_url, index++); });
  db.restaurants.save(doc);
});
db.foods.find().forEach(function (doc) {
  doc.pic_url = repair(doc.pic_url, index++);
  db.foods.save(doc);
});
db.orders.find().forEach(function (doc) {
  if (doc.basket && doc.basket.group) {
    doc.basket.group.forEach(function (item) { item.image_path = repair(item.image_path, index++); });
    db.orders.save(doc);
  }
});
'''.replace('__AVAILABLE__', json.dumps(available_cached, indent=2))
    run(['docker', 'exec', '-i', MONGO, 'mongo', 'takeaway', '--quiet'], input=repair_cached_refs_script.encode('utf-8'), stdout=subprocess.DEVNULL)

INNER_PY
fi

if [ -f /tmp/gma_meituan_backend_changed ]; then
  rm -f /tmp/gma_meituan_backend_changed
  docker restart meituan-backend >/dev/null
fi
for _ in $(seq 1 60); do
  if curl -fsS 'http://localhost:8050/api/v1/gma_cart?username=owner' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if [ -n "$seed_root" ] && [ -f /tmp/gma_meituan_seed_import.js ]   && docker ps --format '{{.Names}}' | grep -qx meituan-mongo; then
  docker cp "$seed_root/meituan_restaurants.json" meituan-mongo:/tmp/gma_seed_restaurants.json >/dev/null
  docker cp "$seed_root/meituan_foods.json" meituan-mongo:/tmp/gma_seed_foods.json >/dev/null
  docker cp "$seed_root/meituan_categories.json" meituan-mongo:/tmp/gma_seed_categories.json >/dev/null
  docker exec -i meituan-mongo mongo --quiet takeaway < /tmp/gma_meituan_seed_import.js >/dev/null
fi
docker exec meituan-frontend touch /tmp/gma_runtime_patched_v8 >/dev/null 2>&1 || true
docker exec meituan-backend touch /tmp/gma_runtime_patched_v8 >/dev/null 2>&1 || true
docker exec meituan-mongo touch /tmp/gma_runtime_patched_v8 >/dev/null 2>&1 || true
""",
        timeout=600,
    )


def _patch_xiaoshiliu_runtime(client: AndroidController) -> None:
    run_bash(
        client,
        r"""
set -euo pipefail

seed_root=""
for candidate in \
  /data/zhuyiqi/GMA/src/gma/apps/seed_data/xiaoshiliu \
  /app/gma/src/gma/apps/seed_data/xiaoshiliu; do
  if [ -f "$candidate/xiaoshiliu_seed.sql" ]; then
    seed_root="$candidate"
    break
  fi
done
if [ -n "$seed_root" ] && docker ps --format '{{.Names}}' | grep -qx xiaoshiliu-mysql; then
  if [ -d "$seed_root/images" ]; then
    docker exec xiaoshiliu-frontend mkdir -p /usr/share/nginx/html/gma-cached-assets/xiaoshiliu
    docker cp "$seed_root/images/." xiaoshiliu-frontend:/usr/share/nginx/html/gma-cached-assets/xiaoshiliu/ >/dev/null
  fi
  docker exec -i xiaoshiliu-mysql mysql -uxiaoshiliu_user -p123456 --default-character-set=utf8mb4 xiaoshiliu < "$seed_root/xiaoshiliu_seed.sql"
fi

docker exec -u 0 xiaoshiliu-frontend sh -lc '
  conf=/etc/nginx/conf.d/default.conf
  if grep -q "location /api/" "$conf"; then
    sed -i "s#location /api/#location ^~ /api/#" "$conf"
  fi
  nginx -t
  nginx -s reload
'

python3 - <<'INNER_PY'
import re
import subprocess
import tempfile
from pathlib import Path

paths = subprocess.check_output(
    ["docker", "exec", "xiaoshiliu-frontend", "sh", "-lc", "find /usr/share/nginx/html/assets -type f -name '*.js' 2>/dev/null"],
    text=True,
).splitlines()
patched = 0
already_patched = 0
visible_chinese = re.compile(r'action-btn (?:edit|delete)-btn[\s\S]{0,240}(?:编辑|删除)')
for remote_path in paths:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        local_path = Path(tmp.name)
    try:
        subprocess.run(["docker", "cp", f"xiaoshiliu-frontend:{remote_path}", str(local_path)], check=True, stdout=subprocess.DEVNULL)
        text = local_path.read_text(errors="ignore")
        updated = text.replace('nt(" 编辑 ",-1)', 'nt(" Edit ",-1)').replace('nt(" 删除 ",-1)', 'nt(" Delete ",-1)')
        if updated != text:
            local_path.write_text(updated)
            subprocess.run(["docker", "cp", str(local_path), f"xiaoshiliu-frontend:{remote_path}"], check=True, stdout=subprocess.DEVNULL)
            patched += 1
        elif 'nt(" Edit ",-1)' in text or 'nt(" Delete ",-1)' in text:
            already_patched += 1
    finally:
        local_path.unlink(missing_ok=True)
if patched == 0 and already_patched == 0:
    stale = []
    for remote_path in paths:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            local_path = Path(tmp.name)
        try:
            subprocess.run(["docker", "cp", f"xiaoshiliu-frontend:{remote_path}", str(local_path)], check=True, stdout=subprocess.DEVNULL)
            if visible_chinese.search(local_path.read_text(errors="ignore")):
                stale.append(remote_path)
        finally:
            local_path.unlink(missing_ok=True)
    if stale:
        raise SystemExit("XiaoShiLiu visible Edit/Delete label patch did not match frontend bundle")
INNER_PY

docker exec -u 0 xiaoshiliu-backend sh -lc '
  mkdir -p /app/uploads/images /app/uploads/videos /app/uploads/avatars
  chown -R 1001:65533 /app/uploads
  chmod -R u+rwX,g+rwX /app/uploads
'

docker exec -i xiaoshiliu-backend node <<'INNER_JS'
const fs = require('fs');
const path = '/app/routes/posts.js';
const oldCreateText = "const { title, content, category_id, images, video, tags, status, type } = req.body;";
const newCreateText = "const { title, content, category_id, images, video, tags, status: requestedStatus, type } = req.body;\n    const status = 0; // GMA publishes user-created posts immediately; no pending review gate.";
const oldEditText = "const { title, content, category_id, images, video, tags, status } = req.body;";
const newEditText = "const { title, content, category_id, images, video, tags, status: requestedStatus } = req.body;\n    const status = 0; // GMA keeps edited posts published; no pending review gate.";
let text = fs.readFileSync(path, 'utf8');
let changed = false;
if (text.includes(oldCreateText)) {
  text = text.split(oldCreateText).join(newCreateText);
  changed = true;
}
if (text.includes(oldEditText)) {
  text = text.split(oldEditText).join(newEditText);
  changed = true;
}
if (changed) {
  fs.writeFileSync(path, text);
} else if (!text.includes('status: requestedStatus')) {
  throw new Error('Could not patch XiaoShiLiu post status handling');
}
INNER_JS

docker exec -i xiaoshiliu-backend node <<'INNER_JS'
const fs = require('fs');
const path = '/app/app.js';
let text = fs.readFileSync(path, 'utf8');
const replacements = [
  ['max: 500,\n  standardHeaders: true,', 'max: 50000,\n  standardHeaders: true,'],
  ['max: 20,\n  standardHeaders: true,', 'max: 5000,\n  standardHeaders: true,'],
  ['max: 60,\n  standardHeaders: true,', 'max: 5000,\n  standardHeaders: true,'],
];
let changed = false;
for (const [oldText, newText] of replacements) {
  if (text.includes(oldText)) {
    text = text.split(oldText).join(newText);
    changed = true;
  }
}
if (changed) {
  fs.writeFileSync(path, text);
} else if (!text.includes('max: 50000,') || !text.includes('max: 5000,')) {
  throw new Error('Could not patch XiaoShiLiu API rate limits');
}
INNER_JS
# Restart so Node reloads the patched route. Keep this inside runtime patch so resets behave the same.
docker restart xiaoshiliu-backend >/dev/null
for _ in $(seq 1 40); do
  if curl -fsS http://localhost:8031/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

python3 - <<'INNER_PY'
import re
import shlex
import subprocess

INDEX_PATH = '/usr/share/nginx/html/index.html'
bootstrap = '''<script id="gma-xsl-login-bootstrap">(function(){try{
  if(localStorage.getItem("token")&&localStorage.getItem("userInfo")) return;
  localStorage.removeItem("GMA-XSL-Seed-User");
  var xhr=new XMLHttpRequest();
  xhr.open("POST","/api/auth/login",false);
  xhr.withCredentials=true;
  xhr.setRequestHeader("Content-Type","application/json");
  xhr.send(JSON.stringify({user_id:"xsl_user_001",password:"123456"}));
  if(xhr.status===200){
    var payload=JSON.parse(xhr.responseText||"{}");
    if(payload&&payload.code===200&&payload.data&&payload.data.tokens){
      localStorage.setItem("token",payload.data.tokens.access_token);
      localStorage.setItem("refreshToken",payload.data.tokens.refresh_token);
      localStorage.setItem("userInfo",JSON.stringify(payload.data.user));
    }
  }
}catch(e){}})();</script>'''

text = subprocess.check_output(['docker', 'exec', 'xiaoshiliu-frontend', 'cat', INDEX_PATH], text=True)
text = re.sub(r'<script id="gma-xsl-login-bootstrap">[\s\S]*?</script>', '', text)
text = re.sub(r'(<script[^>]+src=["\']?/assets/)', bootstrap + r'\1', text, count=1)
if 'id="gma-xsl-login-bootstrap"' not in text:
    text = text.replace('</head>', bootstrap + '</head>', 1)
subprocess.run(
    ['docker', 'exec', '-i', 'xiaoshiliu-frontend', 'sh', '-lc', 'cat > ' + shlex.quote(INDEX_PATH)],
    input=text,
    text=True,
    check=True,
)
INNER_PY

python3 - <<'INNER_PY'
import hashlib
import mimetypes
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

INIT_SQL = Path('/tmp/gma_xiaoshiliu_export/xiaoshiliu/init/mysql/init.sql')
CACHE_DIR = Path('/tmp/gma_xiaoshiliu_cached_assets')
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND = 'xiaoshiliu-frontend'
HTML_CACHE_DIR = '/usr/share/nginx/html/gma-cached-assets/xiaoshiliu'
CACHE_PREFIX = '/gma-cached-assets/xiaoshiliu'
FALLBACKS = [
    '/assets/frame%20(1)-By2z8fPJ.jpg',
    '/assets/frame%20(2)-Bd3WTqiN.jpg',
    '/assets/frame%20(3)-C4RMrtCH.jpg',
    '/assets/frame%20(4)-BMa94iRY.jpg',
    '/assets/frame%20(6)-BgJoc6ju.jpg',
    '/assets/frame%20(7)-C8ZaQ1QX.jpg',
    '/assets/frame%20(8)-DMZCVPTu.jpg',
    '/assets/frame%20(9)-jxIXcgwy.png',
]
cache_map = {}

subprocess.run(['docker', 'exec', FRONTEND, 'mkdir', '-p', HTML_CACHE_DIR], check=True)
for cached_path in CACHE_DIR.glob('*'):
    if cached_path.is_file():
        subprocess.run(['docker', 'cp', str(cached_path), f'{FRONTEND}:{HTML_CACHE_DIR}/{cached_path.name}'], check=True, stdout=subprocess.DEVNULL)
update_sql = CACHE_DIR / 'rewrite_xiaoshiliu_images.sql'
if update_sql.exists():
    with update_sql.open('rb') as stdin:
        subprocess.run(
            ['docker', 'exec', '-i', 'xiaoshiliu-mysql', 'mysql', '-uxiaoshiliu_user', '-p123456', 'xiaoshiliu'],
            stdin=stdin,
            check=True,
        )
    print('XiaoShiLiu reused cached original image mapping(s)')
    raise SystemExit


def sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def parse_insert_rows(table: str) -> list[tuple[str, ...]]:
    sql = INIT_SQL.read_text(errors='ignore')
    marker = f"INSERT INTO `{table}` VALUES "
    start = sql.find(marker)
    if start < 0:
        return []
    end = sql.find(';', start)
    chunk = sql[start:end]
    return re.findall(r"\((\d+),(\d+),'([^']*)'(?:,'([^']*)')?\)", chunk)


def extension_for(url: str, content_type: str | None) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(';', 1)[0].strip())
        if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            return '.jpg' if ext == '.jpeg' else ext
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        return '.jpg' if ext == '.jpeg' else ext
    return '.jpg'


def cache_url(url: str, prefix: str) -> str | None:
    if url in cache_map:
        return cache_map[url]
    digest = hashlib.sha1(url.encode('utf-8', errors='ignore')).hexdigest()[:16]
    try:
        existing = next(CACHE_DIR.glob(f'{prefix}-{digest}.*'), None)
        if existing and existing.is_file():
            subprocess.run(['docker', 'cp', str(existing), f'{FRONTEND}:{HTML_CACHE_DIR}/{existing.name}'], check=True, stdout=subprocess.DEVNULL)
            local = f'{CACHE_PREFIX}/{existing.name}'
            cache_map[url] = local
            return local
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get('Content-Type')
        if not data or (content_type and not content_type.lower().startswith('image/')):
            raise RuntimeError(f'non-image response: {content_type}')
        filename = f'{prefix}-{digest}{extension_for(url, content_type)}'
        host_path = CACHE_DIR / filename
        host_path.write_bytes(data)
        subprocess.run(['docker', 'cp', str(host_path), f'{FRONTEND}:{HTML_CACHE_DIR}/{filename}'], check=True, stdout=subprocess.DEVNULL)
        local = f'{CACHE_PREFIX}/{filename}'
    except Exception as exc:
        print(f'XiaoShiLiu image cache failed for {url}: {exc}')
        local = None
    cache_map[url] = local
    return local


statements = ["UPDATE users SET avatar = '/assets/avatar-ClIy5dZi.png' WHERE avatar REGEXP '^https?://';"]
for row_id, post_id, url, _unused in parse_insert_rows('post_images'):
    if not url.startswith(('http://', 'https://')):
        continue
    try:
        cached = cache_url(url, f'post-{post_id}-{row_id}')
    except Exception as exc:
        print(f'XiaoShiLiu image cache failed for post_images.id={row_id}: {exc}')
        cached = FALLBACKS[int(row_id) % len(FALLBACKS)]
    if cached:
        statements.append(f"UPDATE post_images SET image_url = {sql_literal(cached)} WHERE id = {int(row_id)};")

for row_id, post_id, cover_url, video_url in parse_insert_rows('post_videos'):
    if not cover_url.startswith(('http://', 'https://')):
        continue
    try:
        cached = cache_url(cover_url, f'video-cover-{post_id}-{row_id}')
    except Exception as exc:
        print(f'XiaoShiLiu video cover cache failed for post_videos.id={row_id}: {exc}')
        cached = FALLBACKS[int(row_id) % len(FALLBACKS)]
    if cached:
        statements.append(f"UPDATE post_videos SET cover_url = {sql_literal(cached)} WHERE id = {int(row_id)};")

statements.extend([
    "UPDATE users SET avatar = '/assets/avatar-ClIy5dZi.png' "
    "WHERE avatar REGEXP '^https?://' "
    "OR avatar LIKE '/uploads/%';",
    "UPDATE post_images SET image_url = CASE MOD(id, 8) "
    "WHEN 0 THEN '/assets/frame%20(1)-By2z8fPJ.jpg' "
    "WHEN 1 THEN '/assets/frame%20(2)-Bd3WTqiN.jpg' "
    "WHEN 2 THEN '/assets/frame%20(3)-C4RMrtCH.jpg' "
    "WHEN 3 THEN '/assets/frame%20(4)-BMa94iRY.jpg' "
    "WHEN 4 THEN '/assets/frame%20(6)-BgJoc6ju.jpg' "
    "WHEN 5 THEN '/assets/frame%20(7)-C8ZaQ1QX.jpg' "
    "WHEN 6 THEN '/assets/frame%20(8)-DMZCVPTu.jpg' "
    "ELSE '/assets/frame%20(9)-jxIXcgwy.png' END "
    "WHERE image_url REGEXP '^https?://' "
    "OR image_url = '/assets/avatar-ClIy5dZi.png' "
    "OR image_url LIKE '/uploads/%';",
    "UPDATE post_videos SET cover_url = CASE MOD(id, 8) "
    "WHEN 0 THEN '/assets/frame%20(1)-By2z8fPJ.jpg' "
    "WHEN 1 THEN '/assets/frame%20(2)-Bd3WTqiN.jpg' "
    "WHEN 2 THEN '/assets/frame%20(3)-C4RMrtCH.jpg' "
    "WHEN 3 THEN '/assets/frame%20(4)-BMa94iRY.jpg' "
    "WHEN 4 THEN '/assets/frame%20(6)-BgJoc6ju.jpg' "
    "WHEN 5 THEN '/assets/frame%20(7)-C8ZaQ1QX.jpg' "
    "WHEN 6 THEN '/assets/frame%20(8)-DMZCVPTu.jpg' "
    "ELSE '/assets/frame%20(9)-jxIXcgwy.png' END "
    "WHERE cover_url REGEXP '^https?://' "
    "OR cover_url = '/assets/avatar-ClIy5dZi.png' "
    "OR cover_url LIKE '/uploads/%';",
])

update_sql.write_text('\n'.join(statements) + '\n')
with update_sql.open('rb') as stdin:
    subprocess.run(
        ['docker', 'exec', '-i', 'xiaoshiliu-mysql', 'mysql', '-uxiaoshiliu_user', '-p123456', 'xiaoshiliu'],
        stdin=stdin,
        check=True,
    )
print(f'XiaoShiLiu cached {len([s for s in statements if s.startswith("UPDATE post_images SET image_url") or s.startswith("UPDATE post_videos SET cover_url")])} original image mapping(s)')
INNER_PY
""",
        timeout=600,
    )


def repair_hmdp_runtime(client: AndroidController) -> None:
    run_bash(
        client,
        r'''
set -euo pipefail
PROJECT=/tmp/gma_hmdp_export/hmdp
FRONTEND="$PROJECT/hmdp-vue3"
DIST="$FRONTEND/dist"

write_user_index_file() {
  out="${1:-$DIST/gma-user-index.json}"
  mkdir -p "$(dirname "$out")"
  GMA_HMDP_USER_INDEX_OUT="$out" python3 - <<'INNER_INDEX'
import json
import os
import subprocess
from pathlib import Path

mysql = [
    "docker", "exec", "-i", "hmdp-mysql", "mysql", "-uroot", "-phmdp_root_2025",
    "--default-character-set=utf8mb4", "--batch", "--raw", "--skip-column-names",
]
users = []
seen = set()
for db in ("hmdp_0", "hmdp_1"):
    for table in ("tb_user_0", "tb_user_1"):
        try:
            output = subprocess.check_output(
                mysql + [db, "-e", f"select id,nick_name,icon from {table} where nick_name is not null and nick_name <> '' order by id"],
                text=True,
            )
        except Exception:
            continue
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            user_id, nick_name, icon = parts[:3]
            if user_id in seen:
                continue
            seen.add(user_id)
            users.append({
                "id": str(user_id),
                "nickName": nick_name,
                "icon": "" if icon == "NULL" else icon,
            })
payload = {"success": True, "errorMsg": "", "data": users, "total": str(len(users))}
Path(os.environ["GMA_HMDP_USER_INDEX_OUT"]).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
INNER_INDEX
}

patch_running_frontend_user_search() {
  tmp=/tmp/gma_hmdp_user_patch.js
  index_tmp=/tmp/gma_hmdp_user_index.json
  target=""
  if docker cp hmdp-frontend:/usr/share/nginx/html/assets/user-CHEPMiKO.js "$tmp" >/dev/null 2>&1; then
    target=/usr/share/nginx/html/assets/user-CHEPMiKO.js
  elif docker cp hmdp-frontend:/usr/share/nginx/html/hmdp/assets/user-CHEPMiKO.js "$tmp" >/dev/null 2>&1; then
    target=/usr/share/nginx/html/hmdp/assets/user-CHEPMiKO.js
  else
    return 0
  fi
  write_user_index_file "$index_tmp" || true
  if [ -f "$index_tmp" ]; then
    docker cp "$index_tmp" hmdp-frontend:/usr/share/nginx/html/gma-user-index.json >/dev/null 2>&1 || true
  fi
  python3 - <<'INNER_PATCH'
from pathlib import Path

path = Path("/tmp/gma_hmdp_user_patch.js")
text = path.read_text()
user_search = (
    'f=(s,o=1)=>fetch((location.pathname.startsWith("/hmdp")?"/hmdp":"")+"/gma-user-index.json",{cache:"no-store"})'
    '.then(t=>t.json()).then(t=>{const a=t.data||[],n=String(s||"").toLowerCase(),r=a.filter(i=>String(i.nickName||"").toLowerCase().includes(n));'
    'return{...t,data:r.slice((o-1)*10,o*10),total:String(r.length)}})'
)
start = text.find('f=(s,o=1)=>')
end = text.find(';export{', start)
if start != -1 and end != -1:
    path.write_text(text[:start] + user_search + text[end:])
INNER_PATCH
  if grep -q 'gma-user-index.json' "$tmp"; then
    docker cp "$tmp" "hmdp-frontend:$target" >/dev/null 2>&1 || true
  fi
}

if [ ! -f "$FRONTEND/package.json" ]; then
  if curl -fsS --max-time 5 http://127.0.0.1:8070/hmdp/ >/dev/null 2>&1; then
    patch_running_frontend_user_search
    adb -s emulator-5554 shell am force-stop gma.webapp.hmdp >/dev/null 2>&1 || true
    adb -s emulator-5554 shell pm clear gma.webapp.hmdp >/dev/null 2>&1 || true
    exit 0
  fi
  echo "HMDP frontend source is missing at $FRONTEND and the running frontend is not healthy" >&2
  exit 1
fi
if [ ! -f "$FRONTEND/package-lock.json" ]; then
  if curl -fsS --max-time 5 http://127.0.0.1:8070/hmdp/ >/dev/null 2>&1; then
    patch_running_frontend_user_search
    adb -s emulator-5554 shell am force-stop gma.webapp.hmdp >/dev/null 2>&1 || true
    adb -s emulator-5554 shell pm clear gma.webapp.hmdp >/dev/null 2>&1 || true
    exit 0
  fi
  echo "HMDP frontend lockfile is missing at $FRONTEND/package-lock.json and the running frontend is not healthy" >&2
  exit 1
fi

needs_build=1
if [ -d "$DIST/assets" ] \
  && grep -R -q "Search shops, posts" "$DIST/assets" 2>/dev/null \
  && grep -R -q "Search shops or posts" "$DIST/assets" 2>/dev/null; then
  needs_build=0
fi
if [ "$needs_build" -eq 1 ]; then
  if ! command -v npm >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update >/dev/null
      DEBIAN_FRONTEND=noninteractive apt-get install -y npm >/dev/null
    fi
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required to rebuild the HMDP frontend from source" >&2
    exit 1
  fi
  (cd "$FRONTEND" && npm ci --prefer-offline --no-audit --no-fund && npm run build)
fi

python3 - <<'INNER_PY'
from pathlib import Path
root = Path('/tmp/gma_hmdp_export/hmdp/hmdp-vue3/dist')
index = root / 'index.html'
if index.exists():
    html = index.read_text(errors='replace')
    marker = '<script id="gma-hmdp-search-prompt">'
    if marker in html:
        before, rest = html.split(marker, 1)
        if '</script>' in rest:
            _, after = rest.split('</script>', 1)
            html = before.rstrip() + '\n' + after.lstrip()
    noop = '<script id="gma-hmdp-search-prompt">window.__gmaHmdpSearchPromptInstalled=true;</script>'
    if '</body>' in html:
        html = html.replace('</body>', noop + '\n</body>', 1)
    else:
        html += '\n' + noop + '\n'
    index.write_text(html)

user_search = (
    'f=(s,o=1)=>fetch((location.pathname.startsWith("/hmdp")?"/hmdp":"")+"/gma-user-index.json",{cache:"no-store"})'
    '.then(t=>t.json()).then(t=>{const a=t.data||[],n=String(s||"").toLowerCase(),r=a.filter(i=>String(i.nickName||"").toLowerCase().includes(n));'
    'return{...t,data:r.slice((o-1)*10,o*10),total:String(r.length)}})'
)
for js in (root / 'assets').glob('user-*.js'):
    text = js.read_text(errors='replace')
    start = text.find('f=(s,o=1)=>')
    end = text.find(';export{', start)
    if start != -1 and end != -1:
        js.write_text(text[:start] + user_search + text[end:])

dockerfile = Path('/tmp/gma_hmdp_export/hmdp/hmdp-vue3/Dockerfile')
if dockerfile.exists():
    dockerfile.write_text('\n'.join([
        'FROM nginx:1.25-alpine',
        'COPY dist /usr/share/nginx/html',
        'COPY src/assets/imgs /usr/share/nginx/html/src/assets/imgs',
        'COPY public/yelp-photos /usr/share/nginx/html/yelp-photos',
        'COPY nginx.conf /etc/nginx/conf.d/default.conf',
        'EXPOSE 80',
        'HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -q --spider http://127.0.0.1/hmdp/ || exit 1',
        'CMD ["nginx", "-g", "daemon off;"]',
    ]) + '\n')
INNER_PY
write_user_index_file "$DIST/gma-user-index.json"
(cd "$PROJECT" && docker build -t hmdp-plus-frontend:latest hmdp-vue3 >/dev/null)
(cd "$PROJECT" && COMPOSE_PROJECT_NAME=gma-hmdp docker compose -f docker-compose.yml up -d --force-recreate frontend >/dev/null)
deadline=$((SECONDS + 90))
while [ "$SECONDS" -lt "$deadline" ]; do
  if curl -fsS --max-time 5 http://127.0.0.1:8070/hmdp/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! curl -fsS --max-time 5 http://127.0.0.1:8070/hmdp/ >/dev/null 2>&1; then
  docker compose --project-name gma-hmdp -f "$PROJECT/docker-compose.yml" logs --tail=80 frontend >&2 || true
  exit 1
fi
adb -s emulator-5554 shell am force-stop gma.webapp.hmdp >/dev/null 2>&1 || true
adb -s emulator-5554 shell pm clear gma.webapp.hmdp >/dev/null 2>&1 || true
''',
        timeout=360,
    )


def ensure_mall_backend(client: AndroidController) -> None:
    ensure_offline_webapp_backend(client, MALL)


def ensure_mall_backend_running(client: AndroidController) -> None:
    ensure_offline_webapp_running(client, MALL)


def reset_mall_backend(client: AndroidController) -> None:
    reset_offline_webapp_backend(client, MALL)


def ensure_meituan_backend(client: AndroidController) -> None:
    ensure_offline_webapp_backend(client, MEITUAN)


def ensure_meituan_backend_running(client: AndroidController) -> None:
    ensure_offline_webapp_running(client, MEITUAN)


def reset_meituan_backend(client: AndroidController) -> None:
    reset_offline_webapp_backend(client, MEITUAN)


def ensure_xiaoshiliu_backend(client: AndroidController) -> None:
    ensure_offline_webapp_backend(client, XIAOSHILIU)


def ensure_xiaoshiliu_backend_running(client: AndroidController) -> None:
    ensure_offline_webapp_running(client, XIAOSHILIU)


def reset_xiaoshiliu_backend(client: AndroidController) -> None:
    reset_offline_webapp_backend(client, XIAOSHILIU)


def ensure_hmdp_backend(client: AndroidController) -> None:
    ensure_offline_webapp_backend(client, HMDP)
    repair_hmdp_runtime(client)


def ensure_hmdp_backend_running(client: AndroidController) -> None:
    ensure_offline_webapp_running(client, HMDP)


def reset_hmdp_backend(client: AndroidController) -> None:
    reset_offline_webapp_backend(client, HMDP)


def ensure_travel_backend(client: AndroidController) -> None:
    ensure_offline_webapp_backend(client, TRAVEL)


def ensure_travel_backend_running(client: AndroidController) -> None:
    ensure_offline_webapp_running(client, TRAVEL)
    patch_offline_webapp_runtime(client, TRAVEL)


def reset_travel_backend(client: AndroidController) -> None:
    reset_offline_webapp_backend(client, TRAVEL)
