# ADR-0003: Python stdlib only, fully offline

The build uses only the Python standard library: no third-party packages, no network, no secrets, no evaluation of data files. This guarantees it runs anywhere, including an offline hackathon laptop, and keeps the verification tool itself dependency-free. Data inputs (scenario declarations) are parsed, never executed.