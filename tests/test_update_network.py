"""Regressioni del trasporto HTTPS: fiducia nativa, diagnostica e timeout."""

from io import BytesIO
import ssl
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

import src.update_service as service


def test_windows_tls_uses_native_verification():
    """Il contesto di produzione mantiene verifiche native e hostname attive."""
    if service.sys.platform != "win32":
        pytest.skip("Contesto nativo riservato a Windows")
    import truststore
    context = service.create_tls_context()
    assert isinstance(context, truststore.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("wrapped", [False, True])
def test_certificate_failure_reaches_user_with_original_cause(monkeypatch, wrapped):
    """Riproduce l'errore remoto sia diretto sia incapsulato da urllib."""
    certificate_error = ssl.SSLCertVerificationError(
        1, "certificate verify failed: unable to get local issuer certificate")
    original = URLError(certificate_error) if wrapped else certificate_error
    monkeypatch.setattr(service, "urlopen", Mock(side_effect=original))
    with pytest.raises(service.UpdateError, match="errore del certificato") as caught:
        service.check_release("2.0.0")
    assert "unable to get local issuer certificate" in str(caught.value)
    assert caught.value.__cause__ is original


@pytest.mark.parametrize("code", [403, 404, 429])
def test_http_failure_shows_status_without_exposing_url(monkeypatch, code):
    """La diagnostica riporta il codice HTTP senza URL o token del server."""
    error = HTTPError("https://example.invalid/?token=non-esporre", code, "Denied", {}, None)
    monkeypatch.setattr(service, "urlopen", Mock(side_effect=error))
    with pytest.raises(service.UpdateError, match=f"HTTP {code}") as caught:
        service.check_release()
    assert "non-esporre" not in str(caught.value)


def test_package_download_can_continue_beyond_ten_seconds(monkeypatch):
    """Un trasferimento attivo oltre 10s resta ammesso nel budget del pacchetto."""
    ticks = iter((0.0, 1.0, 11.0, 12.0))
    chunks = iter((b"prima parte", b"seconda parte", b""))
    context = service.create_tls_context()
    response = BytesIO()
    response.read = Mock(side_effect=lambda size: next(chunks))
    opened = Mock(return_value=response)
    monkeypatch.setattr(service, "create_tls_context", lambda: context)
    monkeypatch.setattr(service.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(service, "urlopen", opened)
    assert service.download("https://github.com/package.zip") == b"prima parteseconda parte"
    assert opened.call_args.kwargs["context"] is context
    assert opened.call_args.kwargs["timeout"] == service.SOCKET_TIMEOUT


@pytest.mark.parametrize("budget", [service.CHECK_TIMEOUT, service.PACKAGE_TIMEOUT])
def test_total_download_deadline_stays_finite(monkeypatch, budget):
    """Sia i metadati sia lo ZIP si interrompono al rispettivo limite totale."""
    ticks = iter((0.0, budget + 1.0))
    monkeypatch.setattr(service.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(service, "urlopen", Mock(return_value=BytesIO(b"payload")))
    with pytest.raises(service.UpdateError, match="Tempo massimo"):
        service.download("https://github.com/package.zip", timeout=budget)


def test_download_still_enforces_size_limit(monkeypatch):
    """Il nuovo budget non permette di aggirare il massimo numero di bytes."""
    monkeypatch.setattr(service, "urlopen", Mock(return_value=BytesIO(b"troppo grande")))
    with pytest.raises(service.UpdateError, match="limite consentito"):
        service.download("https://github.com/package.zip", maximum=3)


def test_failed_check_is_logged_and_delivered_to_panel(monkeypatch, caplog):
    """L'errore prima silenzioso raggiunge sia la console sia il polling Tk."""
    import src.gui.update_dialog as gui
    message = "Connessione HTTPS a GitHub non verificabile: errore del certificato."
    monkeypatch.setattr(gui, "check_release", Mock(side_effect=service.UpdateError(message)))
    # Esegue lo stesso worker senza un thread reale: la prova non dipende
    # dall'ordine di scheduling e non costruisce finestre o database.
    monkeypatch.setattr(gui.threading, "Thread", lambda target, daemon: SimpleNamespace(start=target))
    controller = gui.UpdateController(SimpleNamespace(after=Mock(return_value="timer")))
    controller.check()
    assert controller.events.get_nowait() == (None, message)
    assert message in caplog.text
