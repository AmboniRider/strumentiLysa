"""Fixture condivise per la suite di test pytest."""

import customtkinter as ctk
import pytest


@pytest.fixture(scope="session")
def ctk_root():
    """Fixture di sessione per condividere una singola istanza Tk/CTk tra tutti i test GUI."""
    root = ctk.CTk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass
