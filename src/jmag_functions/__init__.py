"""Project-independent JMAG functions published by the capability library."""

from .session import JMAGContext
from .design_table import set_parameter, set_parameters
from .results import get_value, get_values
from .study import run_cases
from .project import (
    LoadedProject,
    ProjectSession,
    close_application,
    copy_project_bundle,
    create_application,
    dismiss_missing_result_dialog,
    find_missing_result_files,
    launch_project_in_visible_designer,
    load_project,
    load_project_copy,
    open_project,
    open_project_visible,
    open_jmag_fast,
    select_study,
    save_project,
    save_project_as,
)
from .inventory import analyze_inventory_records, export_inventory_html, inventory_design_table, render_inventory_html
from .exports import export_case_values, export_design_table, export_result_tables
from .runtime import (
    JMAGRuntimeManager,
    OperationResult,
    ProcessRecord,
    RuntimeSnapshot,
    RuntimeTarget,
    close_all_jmag_designers,
    list_running_jmag,
    save_and_close_all_jmag,
    stop_all_jmag_jobs,
)
from ._version import __version__

__all__ = [
    "JMAGContext", "get_value", "get_values", "set_parameter",
    "set_parameters", "run_cases", "LoadedProject", "ProjectSession", "create_application",
    "load_project", "load_project_copy", "open_project", "open_project_visible",
    "select_study",
    "launch_project_in_visible_designer", "save_project", "save_project_as",
    "close_application",
    "copy_project_bundle", "dismiss_missing_result_dialog", "find_missing_result_files",
    "open_jmag_fast",
    "inventory_design_table", "analyze_inventory_records", "render_inventory_html",
    "export_inventory_html", "export_case_values", "export_design_table",
    "export_result_tables", "JMAGRuntimeManager", "OperationResult",
    "ProcessRecord", "RuntimeSnapshot", "RuntimeTarget", "close_all_jmag_designers",
    "list_running_jmag",
    "save_and_close_all_jmag", "stop_all_jmag_jobs", "__version__",
]
