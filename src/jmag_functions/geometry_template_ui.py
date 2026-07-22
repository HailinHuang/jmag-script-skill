"""Fail-closed UI orchestration for Geometry Library registration.

The concrete UI driver deliberately lives outside this module so normal imports
remain independent of Windows UI Automation and JMAG.
"""

from __future__ import annotations

from typing import Protocol

from .geometry_templates import GeometryTemplateSpec


class UiControlNotFound(RuntimeError):
    """Raised before any state-changing UI action when the expected UI is absent."""


class GeometryRegistrationUi(Protocol):
    def ensure_editor_visible(self) -> None: ...
    def find_command(self, name: str) -> object | None: ...
    def invoke(self, control: object) -> None: ...
    def wait_for_dialog(self, title: str) -> object | None: ...
    def set_text(self, dialog: object, field: str, value: str) -> None: ...
    def set_checked(self, dialog: object, field: str, value: bool) -> None: ...
    def confirm(self, dialog: object) -> None: ...
    def has_library_item(self, library_key: str) -> bool: ...
    def capture(self, label: str) -> None: ...


def register_template_via_ui(ui: GeometryRegistrationUi, spec: GeometryTemplateSpec) -> None:
    """Register exactly one template, stopping before unsafe or ambiguous actions."""
    ui.ensure_editor_visible()
    ui.capture("geometry_editor_ready")
    command = ui.find_command("Register in Geometry Library")
    if command is None:
        raise UiControlNotFound("JMAG command 'Register in Geometry Library' was not found")
    ui.invoke(command)
    dialog = ui.wait_for_dialog("Register Geometry Library")
    if dialog is None:
        raise UiControlNotFound("JMAG registration dialog was not found")
    ui.set_text(dialog, "Name", spec.template_id)
    ui.set_text(dialog, "Folder", spec.library_folder)
    ui.set_checked(dialog, "Registered Geometry", True)
    ui.capture("registration_dialog_ready")
    ui.confirm(dialog)
    if not ui.has_library_item(spec.library_key):
        raise UiControlNotFound(f"Registered library item was not found: {spec.library_key}")
    ui.capture("library_item_verified")
