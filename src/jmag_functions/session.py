"""Explicit JMAG session ownership and bound-study context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass
class JMAGContext:
    app: Any
    model: Any
    study: Any
    table: Any
    owns_application: bool = False
    _closed: bool = False

    @classmethod
    def from_current(cls, app: Any | None = None, *, study: str | int | None = None) -> Self:
        if app is None:
            from jmag.designer import designer
            app = designer.GetApplication()
        if app is None:
            raise RuntimeError("No JMAG application is available")
        model = app.GetCurrentModel()
        if model is None:
            raise RuntimeError("No current JMAG model is available")
        bound_study = app.GetCurrentStudy() if study is None else model.GetStudy(study)
        if bound_study is None:
            raise RuntimeError(f"JMAG study not found: {study!r}")
        if study is not None:
            app.SetStudyAsCurrent(bound_study)
        table = bound_study.GetDesignTable()
        if table is None:
            raise RuntimeError("The selected study has no design table")
        # GetApplication may attach or create; ownership cannot be inferred safely.
        return cls(app, model, bound_study, table, owns_application=False)

    @classmethod
    def create(cls, options: list[str] | None = None) -> Self:
        from jmag.designer import designer
        app = designer.CreateApplication(options or ["-g"])
        try:
            context = cls.from_current(app)
        except Exception:
            app.Quit()
            raise
        context.owns_application = True
        return context

    def activate(self) -> None:
        self._ensure_open()
        self.app.SetStudyAsCurrent(self.study)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.owns_application:
            self.app.Quit()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("JMAGContext is closed")

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def case_index(self, case: int) -> int:
        if isinstance(case, bool) or not isinstance(case, int):
            raise TypeError("case must be a 1-based integer")
        count = int(self.table.NumCases())
        if case < 1 or case > count:
            raise ValueError(f"case must be between 1 and {count}; got {case}")
        return case - 1

    def parameter_index(self, name: str) -> int:
        expected = f"Equation parameters: {name}"
        for index in range(int(self.table.NumParameters())):
            if (self.table.ParameterTypeName(index) == "Equation"
                    and self.table.ParameterName(index) == expected):
                return index
        raise KeyError(f"JMAG equation parameter not found: {name}")

    def has_parameter(self, name: str) -> bool:
        try:
            self.parameter_index(name)
        except KeyError:
            return False
        return True
