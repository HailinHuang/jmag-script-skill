# Frontend Status

The PySide6 design frontend is planned—not present in this commit. There is no
`run_frontend.cmd`, frontend package, or frontend requirements file to install
or run.

The existing runtime frontend is a separate dependency-free Tkinter tool:

```text
jmag_user_py/jmag_runtime_frontend.py
```

Its `--help` path is presentation-only and does not start a JMAG session. It
does not make the planned PySide6 design frontend available.
