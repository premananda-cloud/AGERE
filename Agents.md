# AGENTS.md - Project Context & Rules

## 1. Project Root
The absolute root directory for this project is:
`C:\Users\Public\Premananda\model\AGERE`

## 2. Source Code Location
All actual source code lives in:
`C:\Users\Public\Premananda\model\AGERE\src`

**RULE:** When asked to read or edit code, **ONLY** look inside the `src/` folder and its subfolders. Do not attempt to read files outside of this path unless explicitly told to.

## 3. Strict Ignore Rules (DO NOT READ)
The following directories and files are **build artifacts, caches, or libraries**. They are binary, massive, or auto-generated. 
**NEVER read or search these folders** to answer a question. Ignore them completely:

- `C:\Users\Public\Premananda\model\AGERE\target\`
- `C:\Users\Public\Premananda\model\AGERE\node_modules\`
- `C:\Users\Public\Premananda\model\AGERE\.git\`
- `C:\Users\Public\Premananda\model\AGERE\dist\`
- `C:\Users\Public\Premananda\model\AGERE\build\`
- Any file ending in `.log`, `.lock`, `.tmp`, or `.DS_Store`

## 4. Absolute Paths (CRITICAL - NO GUESSING)
This is a **Windows machine**. 
- **DO NOT** guess paths like `/a/b/` or `/home/user/`.
- **DO NOT** use relative paths like `./src/main.rs` without specifying the absolute root.
- **ALWAYS** use the full Windows path: `C:\Users\Public\Premananda\model\AGERE\src\...` when listing or accessing a file.

## 5. Operational Modes
- **If I ask "Where is X?":** First, use `list_directory` on `C:\Users\Public\Premananda\model\AGERE\src` to find the actual file name. Do not invent file names.
- **If I ask "Fix a bug":** Show me the specific file path you intend to edit before making the change.
- **If I ask "Explain code":** Read the specific file I mention using the absolute path.

## 6. Project Type
Treat this as a compiled application project (Rust, Go, or C++ based on the `src` structure). If you see `Cargo.toml`, use `cargo` commands. If you see a `Makefile`, use `make`. **Do not suggest Node.js or Python fixes unless you see a `package.json` or `requirements.txt` in the root.**
