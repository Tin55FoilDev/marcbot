# Deterministic weather report workflow for MarcBot.

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from marcbot import __version__
from marcbot.errors import MarcBotError
from marcbot.paths import WORKSPACE_DIR

DEFAULT_WEATHER_CONFIG_PATH = Path("/srv/marcbot/config/weather-report.toml")
WEATHER_REPORTS_DIR = WORKSPACE_DIR / "weather" / "reports"
WEATHER_REPORT_GLOB = "weather-report-*.md"
FETCH_TIMEOUT_SECONDS = 20
MAX_FETCH_BYTES = 400_000
USER_AGENT = f"MarcBot/{__version__} weather-report"


class UrlOpenLike(Protocol):
    def __call__(self, request: Request, timeout: int):
        pass


@dataclass(frozen=True)
class WeatherReportConfig:
    name: str
    url: str
    days: int = 3
    config_path: Path = DEFAULT_WEATHER_CONFIG_PATH


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    text: str


@dataclass(frozen=True)
class WeatherReportResult:
    path: Path
    message: str


class DetailedForecastParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._div_stack: list[dict[str, object]] = []
        self._in_detailed = False
        self._capture_kind: str | None = None
        self._capture_chunks: list[str] = []
        self._pending_label: str | None = None
        self.periods: list[ForecastPeriod] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return

        attr_map = {name: value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        div_id = attr_map.get("id", "")

        frame = {
            "was_detailed_start": div_id == "detailed-forecast-body",
            "capture_kind": None,
        }
        self._div_stack.append(frame)

        if div_id == "detailed-forecast-body":
            self._in_detailed = True

        if not self._in_detailed:
            return

        if "forecast-label" in classes:
            self._start_capture("label")
            frame["capture_kind"] = "label"
        elif "forecast-text" in classes:
            self._start_capture("text")
            frame["capture_kind"] = "text"

    def handle_endtag(self, tag: str) -> None:
        if tag != "div":
            return

        frame = self._div_stack.pop() if self._div_stack else {}

        capture_kind = frame.get("capture_kind")
        if capture_kind:
            self._finish_capture(str(capture_kind))

        if frame.get("was_detailed_start"):
            self._in_detailed = False

    def handle_data(self, data: str) -> None:
        if self._capture_kind is not None:
            self._capture_chunks.append(data)

    def _start_capture(self, kind: str) -> None:
        self._capture_kind = kind
        self._capture_chunks = []

    def _finish_capture(self, kind: str) -> None:
        text = _normalize_space(" ".join(self._capture_chunks))
        self._capture_kind = None
        self._capture_chunks = []

        if not text:
            return

        if kind == "label":
            self._pending_label = text
            return

        if kind == "text" and self._pending_label is not None:
            self.periods.append(ForecastPeriod(name=self._pending_label, text=text))
            self._pending_label = None


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_weather_report_config(
    path: Path = DEFAULT_WEATHER_CONFIG_PATH,
) -> WeatherReportConfig:
    if not path.exists():
        raise MarcBotError(
            "MBOT-WEATHER-001",
            f"Weather report config is missing: {path}",
        )

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    weather = data.get("weather")
    if not isinstance(weather, dict):
        raise MarcBotError(
            "MBOT-WEATHER-002",
            "Weather report config must define [weather]",
        )

    name = weather.get("name", "Weather report")
    if not isinstance(name, str) or not name.strip():
        raise MarcBotError(
            "MBOT-WEATHER-003",
            "weather.name must be a non-empty string",
        )

    url = weather.get("url")
    if not isinstance(url, str) or not url.strip():
        raise MarcBotError(
            "MBOT-WEATHER-004",
            "weather.url must be a non-empty string",
        )
    _validate_weather_url(url.strip())

    days = weather.get("days", 3)
    if not isinstance(days, int) or days < 1 or days > 7:
        raise MarcBotError(
            "MBOT-WEATHER-005",
            "weather.days must be an integer from 1 to 7",
        )

    return WeatherReportConfig(
        name=name.strip(),
        url=url.strip(),
        days=days,
        config_path=path,
    )


def _validate_weather_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise MarcBotError(
            "MBOT-WEATHER-006",
            "Weather report URL must use https",
        )
    if parsed.netloc != "forecast.weather.gov":
        raise MarcBotError(
            "MBOT-WEATHER-007",
            "Weather report URL must use forecast.weather.gov",
        )
    if not parsed.path.endswith("/MapClick.php"):
        raise MarcBotError(
            "MBOT-WEATHER-008",
            "Weather report URL must be a forecast.weather.gov MapClick.php URL",
        )


def fetch_weather_html(
    config: WeatherReportConfig,
    opener: UrlOpenLike = urlopen,
) -> str:
    request = Request(
        config.url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    try:
        with opener(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_FETCH_BYTES + 1)
    except HTTPError as exc:
        raise MarcBotError(
            "MBOT-WEATHER-009",
            f"Weather fetch returned HTTP {exc.code}",
        ) from exc
    except URLError as exc:
        raise MarcBotError(
            "MBOT-WEATHER-010",
            f"Weather fetch failed: {exc.reason}",
        ) from exc

    if len(raw) > MAX_FETCH_BYTES:
        raise MarcBotError(
            "MBOT-WEATHER-011",
            f"Weather fetch exceeded {MAX_FETCH_BYTES} bytes",
        )

    return raw.decode("utf-8", errors="replace")


def parse_detailed_forecast(html: str) -> tuple[ForecastPeriod, ...]:
    parser = DetailedForecastParser()
    parser.feed(html)

    if not parser.periods:
        raise MarcBotError(
            "MBOT-WEATHER-012",
            "Detailed Forecast section was not found or had no periods",
        )

    return tuple(parser.periods)


def select_next_periods(
    periods: tuple[ForecastPeriod, ...],
    days: int,
) -> tuple[ForecastPeriod, ...]:
    max_periods = days * 2
    return periods[:max_periods]


def build_deterministic_summary(periods: tuple[ForecastPeriod, ...]) -> tuple[str, str]:
    combined = " ".join(period.text.lower() for period in periods)

    temp_sentence = "Temperatures look seasonable for the next few days."
    if "hot" in combined or re.search(r"\b9\d\b", combined):
        temp_sentence = "The next few days may run hot, so plan for warm conditions."
    elif "cold" in combined or "frost" in combined or "freeze" in combined:
        temp_sentence = "The next few days may run cold, so plan for chilly conditions."

    watch_items: list[str] = []
    if "thunder" in combined:
        watch_items.append("thunderstorms")
    if "showers" in combined or "rain" in combined:
        watch_items.append("rain or showers")
    if "snow" in combined:
        watch_items.append("snow")
    if "wind" in combined or "gust" in combined:
        watch_items.append("gusty winds")

    if watch_items:
        watch_sentence = "Main watch item: " + ", ".join(watch_items) + "."
    else:
        watch_sentence = "No major precipitation or wind signal stands out in this forecast."

    return temp_sentence, watch_sentence


def render_weather_report(
    *,
    config: WeatherReportConfig,
    periods: tuple[ForecastPeriod, ...],
    now: datetime,
) -> str:
    selected = select_next_periods(periods, config.days)
    summary = build_deterministic_summary(selected)

    lines = [
        f"# {config.name}",
        "",
        f"Generated: {now.isoformat()}",
        f"Source: {config.url}",
        f"Days requested: {config.days}",
        "",
        "## Summary",
        "",
        f"- {summary[0]}",
        f"- {summary[1]}",
        "",
        "## Detailed forecast",
        "",
    ]

    for period in selected:
        lines.extend(
            [
                f"### {period.name}",
                "",
                period.text,
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write_weather_report(
    *,
    config_path: Path = DEFAULT_WEATHER_CONFIG_PATH,
    reports_dir: Path = WEATHER_REPORTS_DIR,
    now: datetime | None = None,
    opener: UrlOpenLike = urlopen,
) -> WeatherReportResult:
    current_time = now or datetime.now(UTC)
    config = load_weather_report_config(config_path)
    html = fetch_weather_html(config, opener=opener)
    periods = parse_detailed_forecast(html)
    report = render_weather_report(config=config, periods=periods, now=current_time)

    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = current_time.strftime("%Y-%m-%d-%H%M%S")
    path = reports_dir / f"weather-report-{timestamp}.md"
    path.write_text(report, encoding="utf-8")

    return WeatherReportResult(
        path=path,
        message=f"Weather report written: {path}",
    )


def find_latest_weather_report(
    reports_dir: Path = WEATHER_REPORTS_DIR,
) -> Path | None:
    if not reports_dir.is_dir():
        return None

    candidates = [
        path
        for path in reports_dir.glob(WEATHER_REPORT_GLOB)
        if path.is_file()
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)
