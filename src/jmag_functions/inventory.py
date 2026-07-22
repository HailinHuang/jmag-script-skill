"""Inspect JMAG Design Table parameters without project-specific semantics."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .session import JMAGContext


def _serializable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def _read_method(obj: Any, method: str, *args: Any) -> Any:
    return _serializable(getattr(obj, method)(*args))


_EXPRESSION_KEYWORDS = {
    "abs", "acos", "asin", "atan", "ceil", "cos", "e", "exp", "floor",
    "log", "max", "min", "pi", "pow", "sin", "sqrt", "tan",
}


def _referenced_equations(expression: Any, equation_names: set[str], own: str) -> list[str]:
    if not isinstance(expression, str):
        return []
    symbols = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression))
    return sorted((symbols & equation_names) - {own} - _EXPRESSION_KEYWORDS)


def _inferred_purpose(record: dict[str, Any]) -> dict[str, str]:
    """Return a non-authoritative purpose inferred from names and expressions."""
    equation = record.get("equation", {})
    name = str(equation.get("name") or record["name"])
    expression = str(equation.get("expression") or "")
    text = f"{name} {expression}".lower()
    if any(token in text for token in ("step", "div", "period", "mesh")):
        return {"category": "simulation", "summary": "Simulation/discretization control or derived step quantity."}
    if any(token in text for token in ("speed", "fre", "phase", "current", "irms", "torque", "vline", "voltage")):
        return {"category": "operating", "summary": "Operating-point input, limit, or derived electrical quantity."}
    if any(token in text for token in ("resistivity", "conductivity", "tem_", "temperature", "magnet")):
        return {"category": "material", "summary": "Material or temperature-dependent property."}
    if any(token in text for token in ("loss", "cost", "mass", "area", "fill", "ratio", "limit", "margin", "obj")):
        return {"category": "performance", "summary": "Derived performance, constraint, or objective quantity."}
    if record["name"].startswith("CAD parameters:"):
        return {"category": "geometry", "summary": "CAD geometry input synchronized through the Design Table."}
    if record["type"] == "Equation" and expression:
        return {"category": "derived", "summary": "Equation-defined parameter; inspect its relationships for dependencies."}
    return {"category": "input", "summary": "Direct Design Table input or study property."}


def _enrich_relationships(records: list[dict[str, Any]]) -> None:
    equation_records = [record for record in records if "equation" in record]
    equation_names = {
        str(record["equation"]["name"])
        for record in equation_records
        if record["equation"].get("name")
    }
    dependents: dict[str, list[str]] = {name: [] for name in equation_names}
    for record in records:
        equation = record.get("equation", {})
        own = str(equation.get("name") or "")
        references = _referenced_equations(equation.get("expression"), equation_names, own)
        for reference in references:
            dependents[reference].append(own)
        record["relationships"] = {
            "references": references,
            "dependents": [],
            "related_parameters": [],
            "basis": "Equation expression token analysis",
        }
        record["inferred_purpose"] = _inferred_purpose(record)
    for record in records:
        own = str(record.get("equation", {}).get("name") or "")
        record["relationships"]["dependents"] = sorted(dependents.get(own, []))


def analyze_inventory_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add expression relationships and non-authoritative purpose inference.

    This pure post-processing function also supports inventories loaded from a
    saved JSON report, without reconnecting to JMAG.
    """
    _enrich_relationships(records)
    return records


def render_inventory_html(records: list[dict[str, Any]], *, title: str = "JMAG Parameter Inventory") -> str:
    """Render an interactive, self-contained HTML fragment for inventory records.

    The table is presentation-only: purpose categories are explicitly labelled
    as inferred, while expression-derived references and inverse dependents are
    shown separately.
    """
    safe_records = json.dumps(
        analyze_inventory_records(records), ensure_ascii=False
    ).replace("</", "<\\/")
    safe_title = html.escape(title)
    return f'''<section id="jmag-inventory-table" aria-label="{safe_title}">
  <style>
    #jmag-inventory-table {{ color: var(--foreground, #1f2937); font-family: system-ui, sans-serif; }}
    #jmag-inventory-table .controls {{ display: flex; gap: .75rem; flex-wrap: wrap; margin-bottom: .75rem; }}
    #jmag-inventory-table input, #jmag-inventory-table select {{ padding: .45rem .6rem; border: 1px solid var(--border, #cbd5e1); border-radius: .35rem; background: var(--background, transparent); color: inherit; }}
    #jmag-inventory-table table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
    #jmag-inventory-table th, #jmag-inventory-table td {{ text-align: left; vertical-align: top; padding: .45rem; border-bottom: 1px solid var(--border, #cbd5e1); }}
    #jmag-inventory-table th {{ position: sticky; top: 0; background: var(--card, #f8fafc); }}
    #jmag-inventory-table tbody tr {{ cursor: pointer; }}
    #jmag-inventory-table tbody tr:hover, #jmag-inventory-table tbody tr[data-selected="true"] {{ background: var(--accent, #e2e8f0); }}
    #jmag-inventory-table .detail {{ margin-top: .75rem; padding: .75rem; border: 1px solid var(--border, #cbd5e1); border-radius: .35rem; }}
    #jmag-inventory-table .muted {{ color: var(--muted-foreground, #64748b); }}
    #jmag-inventory-table code {{ white-space: pre-wrap; word-break: break-word; }}
    @media (max-width: 640px) {{ #jmag-inventory-table th:nth-child(4), #jmag-inventory-table td:nth-child(4) {{ display: none; }} }}
  </style>
  <div class="controls">
    <label>Search <input id="jmag-inventory-search" type="search" placeholder="name, expression, purpose"></label>
    <label>Category <select id="jmag-inventory-category"><option value="">All categories</option></select></label>
    <span id="jmag-inventory-count" class="muted"></span>
  </div>
  <table>
    <thead><tr><th>#</th><th>Parameter</th><th>Type</th><th>Value / expression</th><th>Inferred purpose</th><th>Relationship</th></tr></thead>
    <tbody id="jmag-inventory-rows"></tbody>
  </table>
  <div id="jmag-inventory-detail" class="detail" aria-live="polite">Select a parameter to inspect its relationships.</div>
  <script>
    (() => {{
      const root = document.getElementById('jmag-inventory-table');
      const records = {safe_records};
      const search = root.querySelector('#jmag-inventory-search');
      const category = root.querySelector('#jmag-inventory-category');
      const rows = root.querySelector('#jmag-inventory-rows');
      const count = root.querySelector('#jmag-inventory-count');
      const detail = root.querySelector('#jmag-inventory-detail');
      const esc = (value) => String(value ?? '').replace(/[&<>"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
      [...new Set(records.map(record => record.inferred_purpose?.category || 'input'))].sort().forEach(value => {{
        const option = document.createElement('option'); option.value = value; option.textContent = value; category.appendChild(option);
      }});
      const filtered = () => {{
        const needle = search.value.toLowerCase();
        return records.filter(record => {{
          const relationship = record.relationships || {{}};
          const text = [record.name, record.type, record.value, record.equation?.expression, record.inferred_purpose?.summary, ...(relationship.references || []), ...(relationship.dependents || [])].join(' ').toLowerCase();
          return (!needle || text.includes(needle)) && (!category.value || record.inferred_purpose?.category === category.value);
        }});
      }};
      const showDetail = record => {{
        const relation = record.relationships || {{}};
        const equation = record.equation || {{}};
        detail.innerHTML = `<strong>${{esc(record.name)}}</strong><br><span class="muted">${{esc(record.inferred_purpose?.category || 'input')}} · inferred purpose</span><p>${{esc(record.inferred_purpose?.summary || '')}}</p><div><strong>Expression:</strong> <code>${{esc(equation.expression || record.value)}}</code></div><div><strong>References:</strong> ${{esc((relation.references || []).join(', ') || 'none')}}</div><div><strong>Dependents:</strong> ${{esc((relation.dependents || []).join(', ') || 'none')}}</div><div><strong>Relationship basis:</strong> ${{esc(relation.basis || 'none')}}</div>`;
      }};
      const render = () => {{
        const visible = filtered(); rows.innerHTML = ''; count.textContent = `${{visible.length}} / ${{records.length}} parameters`;
        visible.forEach(record => {{
          const relation = record.relationships || {{}};
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>${{esc(record.index)}}</td><td><code>${{esc(record.name)}}</code></td><td>${{esc(record.type)}}</td><td><code>${{esc(record.equation?.expression || record.value)}}</code></td><td>${{esc(record.inferred_purpose?.category || 'input')}}<br><span class="muted">${{esc(record.inferred_purpose?.summary || '')}}</span></td><td>→ ${{esc((relation.references || []).join(', ') || '—')}}<br>← ${{esc((relation.dependents || []).join(', ') || '—')}}</td>`;
          tr.addEventListener('click', () => {{ rows.querySelectorAll('tr').forEach(row => row.removeAttribute('data-selected')); tr.dataset.selected = 'true'; showDetail(record); }});
          rows.appendChild(tr);
        }});
      }};
      search.addEventListener('input', render); category.addEventListener('change', render); render();
    }})();
  </script>
</section>'''


def export_inventory_html(
    records: list[dict[str, Any]], path: str | Path, *, title: str = "JMAG Parameter Inventory", overwrite: bool = False
) -> Path:
    """Write the visual inventory table to a new or explicitly replaceable HTML file."""
    output = Path(path).resolve()
    if output.suffix.lower() != ".html":
        raise ValueError("inventory visualization output must use .html")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    output.write_text(render_inventory_html(records, title=title), encoding="utf-8")
    return output


def inventory_design_table(
    context: JMAGContext, case: int = 1, *, include_equation_metadata: bool = False
) -> list[dict[str, Any]]:
    """Return every parameter plus available equation metadata for one case.

    Public case numbers are one-based. The default uses only safe Design Table
    methods; Equation values are retained as expressions. Set
    ``include_equation_metadata=True`` to request additional wrapper metadata,
    which may be unavailable for malformed project entries.
    """
    case_index = context.case_index(case)
    context.activate()
    records: list[dict[str, Any]] = []
    for index in range(int(context.table.NumParameters())):
        name = str(context.table.ParameterName(index))
        parameter_type = str(context.table.ParameterTypeName(index))
        record: dict[str, Any] = {
            "index": index,
            "name": name,
            "type": parameter_type,
            "value": _read_method(context.table, "GetValue", case_index, index),
        }
        if parameter_type == "Equation":
            equation_name = name.removeprefix("Equation parameters: ")
            record["equation"] = {
                "name": equation_name,
                "display_name": "",
                "description": "",
                "expression": record["value"] if isinstance(record["value"], str) else "",
                "evaluated_value": record["value"] if not isinstance(record["value"], str) else None,
            }
            if not equation_name:
                record.pop("equation")
                record["equation_error"] = "Equation parameter has no name"
            elif include_equation_metadata:
                try:
                    equation = context.table.GetEquation(equation_name)
                    record["equation"].update(
                        {
                            "display_name": _read_method(equation, "GetDisplayName"),
                            "description": _read_method(equation, "GetDescription"),
                            "expression": _read_method(equation, "GetExpression"),
                            "evaluated_value": _read_method(equation, "GetValue", case_index),
                        }
                    )
                except Exception as exc:
                    record["equation_error"] = f"{type(exc).__name__}: {exc}"
                    record["equation_error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
    return analyze_inventory_records(records)
