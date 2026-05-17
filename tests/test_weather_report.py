from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.weather_report import (
    ForecastPeriod,
    build_deterministic_summary,
    find_latest_weather_report,
    load_weather_report_config,
    parse_detailed_forecast,
    render_weather_report,
    write_weather_report,
)

SAMPLE_HTML = """
<html>
  <body>
    <div id="detailed-forecast-body">
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Today</b></div>
        <div class="col-sm-10 forecast-text">Sunny, with a high near 82.</div>
      </div>
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Tonight</b></div>
        <div class="col-sm-10 forecast-text">Mostly clear, with a low around 55.</div>
      </div>
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Monday</b></div>
        <div class="col-sm-10 forecast-text">A chance of showers after 2pm.</div>
      </div>
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Monday Night</b></div>
        <div class="col-sm-10 forecast-text">Showers likely before 11pm.</div>
      </div>
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Tuesday</b></div>
        <div class="col-sm-10 forecast-text">Partly sunny, with a high near 78.</div>
      </div>
      <div class="row row-forecast">
        <div class="col-sm-2 forecast-label"><b>Tuesday Night</b></div>
        <div class="col-sm-10 forecast-text">Mostly cloudy, with a low around 60.</div>
      </div>
    </div>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self.body[:size]


def write_config(tmp_path: Path, url: str | None = None) -> Path:
    config_path = tmp_path / "weather-report.toml"
    target_url = url or (
        "https://forecast.weather.gov/MapClick.php?CityName=Westfield"
        "&state=MA&site=BOX&textField1=42.1389&textField2=-72.756&e=0"
    )
    config_path.write_text(
        "\n".join(
            [
                "[weather]",
                'name = "Westfield Weather"',
                f'url = "{target_url}"',
                "days = 3",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_load_weather_report_config(tmp_path: Path) -> None:
    config = load_weather_report_config(write_config(tmp_path))

    assert config.name == "Westfield Weather"
    assert config.days == 3
    assert config.url.startswith("https://forecast.weather.gov/MapClick.php")


def test_load_weather_report_config_rejects_non_nws_url(tmp_path: Path) -> None:
    path = write_config(tmp_path, url="https://example.com/weather")

    with pytest.raises(MarcBotError) as excinfo:
        load_weather_report_config(path)

    assert excinfo.value.code == "MBOT-WEATHER-007"


def test_parse_detailed_forecast() -> None:
    periods = parse_detailed_forecast(SAMPLE_HTML)

    assert [period.name for period in periods[:3]] == ["Today", "Tonight", "Monday"]
    assert periods[0].text == "Sunny, with a high near 82."
    assert periods[2].text == "A chance of showers after 2pm."


def test_parse_detailed_forecast_rejects_missing_section() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        parse_detailed_forecast("<html><body>No detailed forecast.</body></html>")

    assert excinfo.value.code == "MBOT-WEATHER-012"


def test_build_deterministic_summary_flags_showers() -> None:
    periods = (
        ForecastPeriod(name="Today", text="Sunny."),
        ForecastPeriod(name="Tonight", text="Chance of showers."),
    )

    summary = build_deterministic_summary(periods)

    assert summary[0] == "Temperatures look seasonable for the next few days."
    assert summary[1] == "Main watch item: rain or showers."


def test_render_weather_report_limits_to_three_days(tmp_path: Path) -> None:
    config = load_weather_report_config(write_config(tmp_path))
    periods = parse_detailed_forecast(SAMPLE_HTML)
    now = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    report = render_weather_report(config=config, periods=periods, now=now)

    assert "# Westfield Weather" in report
    assert "Generated: 2026-05-16T12:00:00+00:00" in report
    assert "## Summary" in report
    assert "### Today" in report
    assert "### Tuesday Night" in report


def test_write_weather_report_fetches_and_writes_artifact(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    reports_dir = tmp_path / "reports"

    def fake_opener(request, timeout):
        assert request.full_url.startswith("https://forecast.weather.gov/MapClick.php")
        return FakeResponse(SAMPLE_HTML.encode("utf-8"))

    result = write_weather_report(
        config_path=config_path,
        reports_dir=reports_dir,
        now=datetime(2026, 5, 16, 8, 0, tzinfo=UTC),
        opener=fake_opener,
    )

    assert result.path == reports_dir / "weather-report-2026-05-16-080000.md"
    assert result.path.exists()
    assert "Weather report written:" in result.message
    assert "### Today" in result.path.read_text(encoding="utf-8")


def test_find_latest_weather_report(tmp_path: Path) -> None:
    older = tmp_path / "weather-report-2026-05-16-080000.md"
    newer = tmp_path / "weather-report-2026-05-17-080000.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")

    assert find_latest_weather_report(tmp_path) == newer
