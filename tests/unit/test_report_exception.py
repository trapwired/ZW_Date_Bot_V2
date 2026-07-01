"""Observability: TelegramService.report_exception logs every unhandled exception
(so failures are visible in the logs, not only in a maintainer DM) and best-effort
alerts the maintainer without letting a failed alert swallow the original error.
"""
import logging


async def test_report_exception_logs_at_error_and_alerts_maintainer(services, bot, caplog):
    telegram_service = services["telegram_service"]

    with caplog.at_level(logging.ERROR):
        await telegram_service.report_exception("Exception in the flow", ValueError("boom"))

    # Logged at ERROR with a traceback (exc_info), independent of the alert.
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert any("Exception in the flow" in r.getMessage() for r in error_records)
    assert any(r.exc_info for r in error_records)

    # Maintainer was alerted.
    assert any("Exception in the flow" in m.text for m in bot.sent)


async def test_report_exception_survives_a_failing_alert(services, monkeypatch, caplog):
    telegram_service = services["telegram_service"]

    async def failing_alert(*args, **kwargs):
        raise RuntimeError("telegram unreachable")

    monkeypatch.setattr(telegram_service, "send_maintainer_message", failing_alert)

    with caplog.at_level(logging.ERROR):
        # Must not raise even though the maintainer alert fails.
        await telegram_service.report_exception("Exception in the flow", ValueError("boom"))

    messages = [r.getMessage() for r in caplog.records]
    assert any("Exception in the flow" in m for m in messages)          # original error logged
    assert any("Failed to send maintainer alert" in m for m in messages)  # alert failure logged too
