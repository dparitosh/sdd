# Installation Scripts & Documentation — Detailed Audit Report

**Date:** 2025-07-14  
**Scope:** All installation scripts (`scripts/`, `deployment/scripts/`), start/stop/health-check scripts, and installation/deployment markdown files (`INSTALL.md`, `README.md`, `deployment/*.md`).

---

## Executive Summary

The project has a **well-structured installation toolchain** centered on `scripts/install.ps1` and `scripts/service_manager.ps1`, with good `.env`-driven configuration and port-conflict resolution. However, the audit identified **19 issues** across 4 severity levels:

| Severity | Count |
|----------|-------|
| **CRITICAL**  | 4 |
| **HIGH**      | 5 |
| **MEDIUM**    | 6 |
| **LOW**       | 4 |

The most impactful problems are: (1) stale deployment docs referencing non-existent paths/scripts, (2) dead code in deprecated wrappers, (3) missing OpenSearch/Ollama installation guidance, and (4) `.env.example` defaulting to Aura cloud URI while the project uses local Neo4j.

---

## 1. CRITICAL Issues

### 1.1 — `.env.example` defaults to Aura cloud URI; project uses local Neo4j

**File:** `.env.example` line 3  
**Problem:** `NEO4J_URI=neo4j+s://your-neo4j-uri.databases.neo4j.io` — the `neo4j+s://` scheme is for Neo4j Aura (cloud, TLS-required). The actual deployment uses `neo4j://127.0.0.1:7687` (local, plain Bolt). A new developer copying `.env.example` will get connection errors and may not understand why.  
**Fix:** Change default to `neo4j://127.0.0.1:7687` with a comment explaining Aura alternative.

### 1.2 — No installation docs or scripts for OpenSearch

**Files:** `INSTALL.md`, `scripts/install.ps1`  
**Problem:** OpenSearch is required for vector search, RAG, and AI Insights — yet:
- `install.ps1` does not install or configure OpenSearch
- `INSTALL.md` mentions OpenSearch zero times
- `start_opensearch.ps1` hardcodes `D:\Software\opensearch-3.3.1` as the default path with no guidance on how to get there

**Fix:** Add an "OpenSearch Setup" section to `INSTALL.md` (download link, `opensearch.yml` config, security plugin disable, test command). Either auto-detect or require `OPENSEARCH_HOME` in `.env`.

### 1.3 — No installation docs or scripts for Ollama

**Files:** `INSTALL.md`, `scripts/install.ps1`  
**Problem:** Ollama is the local LLM/embedding provider used in production (`LLM_PROVIDER=ollama`). Neither the installer nor INSTALL.md mention:
- How to install Ollama
- Which models to pull (`nomic-embed-text:latest`, `llama3:latest`)
- How to verify Ollama is running (`http://localhost:11434`)

`.env.example` lists `OLLAMA_BASE_URL` but INSTALL.md provides no context.

**Fix:** Add "Ollama Setup" section: install link, `ollama pull` commands, verification step.

### 1.4 — `deployment/README.md` file tree is entirely fictional

**File:** `deployment/README.md`  
**Problem:** The "What's Included" tree claims these files exist:
| Claimed File | Actual Status |
|---|---|
| `deployment/scripts/install.ps1` | Exists — but it's a deprecated 22-line wrapper |
| `deployment/scripts/install.bat` | Exists — but it's a standalone 269-line old installer with hardcoded `C:\MBSE` paths |
| `deployment/scripts/cleanup.ps1` | **Does NOT exist** — actual file is `scripts/cleanup.ps1` |
| `deployment/scripts/cleanup.bat` | **Does NOT exist** |
| `deployment/scripts/service_manager.ps1` | Exists — but it's a deprecated wrapper |
| `deployment/scripts/service_manager.bat` | Exists — fully standalone old version |
| `deployment/diagnostics/test_database.ps1` | Exists |

The README directs users to run `deployment\scripts\install.ps1` "as Administrator" — but the actual installer (`scripts/install.ps1`) explicitly states it does NOT require Administrator privileges.

**Fix:** Rewrite `deployment/README.md` to point to `scripts/` as the canonical location. Mark `deployment/scripts/` as legacy/deprecated.

---

## 2. HIGH Issues

### 2.1 — `deployment/scripts/install.ps1`: 320 lines of dead code

**File:** `deployment/scripts/install.ps1` (341 lines)  
**Problem:** Lines 1-22 are a deprecation wrapper that forwards to `scripts/install.ps1` and then calls `exit`. Lines 23-341 (~320 lines) contain an entire old installer that **will never execute** — including its own prerequisite checks, file copying to `C:\MBSE`, venv creation, and dynamic script generation.  
**Fix:** Delete lines 23-341. Keep only the 22-line forwarding wrapper (or delete the file entirely and update references).

### 2.2 — `deployment/scripts/service_manager.ps1`: same dead-code pattern

**File:** `deployment/scripts/service_manager.ps1` (419 lines)  
**Problem:** Lines 1-35 forward to `scripts/service_manager.ps1` and exit. Lines 36-419 (~384 lines) are unreachable dead code containing an old service manager implementation.  
**Fix:** Delete the dead code. Keep only the forwarding wrapper.

### 2.3 — `README.md` project structure is completely stale

**File:** `README.md`  
**Problem:** The "Project Structure" section shows:
```
├── src/web/app.py           ← Flask – doesn't exist (now FastAPI: backend/src/web/app_fastapi.py)
├── src/parsers/              ← doesn't exist (now backend/src/parsers/)
├── src/graph/                ← doesn't exist (now backend/src/graph/)
├── frontend/                 ← partially correct
├── deployment/scripts/       ← deprecated location
```
Also references `venv` instead of `.venv`, and shows old repo name (`mbse-neo4j-graph-rep`).

**Fix:** Update to reflect actual `backend/src/` structure and correct venv path.

### 2.4 — `README.md` has duplicate "Quick Start" sections

**File:** `README.md`  
**Problem:** Two different "Quick Start" headings exist — one at the top (brief) and one further down (detailed). Both reference `deployment/scripts/install.ps1` (deprecated path). The brief one says "Run as Administrator" contradicting the installer.

**Fix:** Merge into one Quick Start section pointing to `scripts/install.ps1`.

### 2.5 — `reinstall_clean.ps1` uses old repo URL

**File:** `scripts/reinstall_clean.ps1`  
**Problem:** Default `-RepoUrl` is `https://github.com/dparitosh/mbse-neo4j-graph-rep.git`. The current repo is `dparitosh/sdd`.  
**Fix:** Update default URL to current repo.

---

## 3. MEDIUM Issues

### 3.1 — `deployment/DEPLOYMENT_CHECKLIST.md` contradicts installer on admin requirements

**File:** `deployment/DEPLOYMENT_CHECKLIST.md`  
**Problem:** Step 2 says "Run installer (Administrator)" — but `scripts/install.ps1` line 3 explicitly states: "Does NOT require Administrator privileges."  
**Fix:** Remove the Administrator requirement from the checklist.

### 3.2 — `deployment/DEPLOYMENT_CHECKLIST.md` hardcodes install path

**File:** `deployment/DEPLOYMENT_CHECKLIST.md`  
**Problem:** Multiple references to `C:\MBSE\mbse-neo4j-graph-rep` as the install directory. This path comes from the dead code in the old `deployment/scripts/install.ps1`, which no longer runs. Current `scripts/install.ps1` installs in-place (no copy).  
**Fix:** Update to reference repo root directory (e.g., `$PWD` or user-chosen path).

### 3.3 — `deployment/scripts/install.bat` is a full standalone installer with hardcoded paths

**File:** `deployment/scripts/install.bat` (269 lines)  
**Problem:** Unlike its `.ps1` counterpart (which was updated to a forwarding wrapper), the `.bat` version is still a full standalone installer. It:
- Requires Administrator (`net session` check)
- Copies files to `C:\MBSE\mbse-neo4j-graph-rep`
- Generates `start_all.bat` / `stop_all.bat` dynamically
- Has its own venv creation, npm install, `.env` generation
- References old directory structure

This will produce a broken installation if run by a user following `deployment/README.md`.

**Fix:** Either convert to a forwarding wrapper (like the `.ps1`) or delete entirely.

### 3.4 — `install_oslc.ps1` seeds only 2 of 5 TTL files

**File:** `scripts/install_oslc.ps1`  
**Problem:** The script seeds `oslc-core.ttl` and `oslc-rm.ttl`, but there are 5 TTL files mentioned in the codebase (`oslc-core.ttl`, `oslc-rm.ttl`, `oslc-cm.ttl`, `oslc-qm.ttl`, `oslc-am.ttl`). The core + requirements-management ontologies are loaded, but change-management, quality-management, and architecture-management may be needed.  
**Fix:** Confirm which ontologies are required and update the script accordingly.

### 3.5 — `INSTALL.md` Section 6 references two different `reload_database.py`

**File:** `INSTALL.md`  
**Problem:** Section 6 references both:
- `scripts/reload_database.py` (root-level — exists, 116 lines, full pipeline)
- `backend/scripts/reload_database.py` (not directly referenced but exists with different behavior)

These are two different scripts with different functionality. A user could run the wrong one.

**Fix:** Clarify which script to use and explain the difference, or consolidate into one.

### 3.6 — Duplicated `Import-DotEnvIfPresent` function across 5+ scripts

**Files:** `start_backend.ps1`, `start_ui.ps1`, `stop_backend.ps1`, `stop_ui.ps1`, `service_manager.ps1`  
**Problem:** Each script contains its own copy of the `.env` parser function (15-25 lines each). The implementations differ slightly:
- `start_backend.ps1` has a `-Force` parameter
- `stop_backend.ps1` uses a simpler split-based parser
- `service_manager.ps1` has additional multi-line/continuation support

Bug fixes or improvements must be applied to all copies independently.

**Fix:** Extract to a shared module (e.g., `scripts/lib/env-utils.ps1`) and dot-source it from each script.

---

## 4. LOW Issues

### 4.1 — `health_check.ps1` uses `$env:API_KEY` inconsistently

**File:** `scripts/health_check.ps1`  
**Problem:** The script reads `$env:API_KEY` for the `X-API-Key` header, which is correct. However, it doesn't load `.env` first — so if the user hasn't exported `API_KEY` to their shell environment, the health check will send requests without authentication, potentially getting 401 errors.  
**Fix:** Add `.env` loading at the top (like other scripts do).

### 4.2 — `start_opensearch.ps1` hardcodes default path

**File:** `scripts/start_opensearch.ps1` line 48  
**Problem:** `$defaultHome = "D:\Software\opensearch-3.3.1"` is machine-specific.  
**Fix:** Either require `OPENSEARCH_HOME` in `.env` or use a more portable default like `$env:LOCALAPPDATA\opensearch`.

### 4.3 — `stop_all.ps1` doesn't stop OpenSearch

**File:** `scripts/stop_all.ps1`  
**Problem:** Calls `stop_ui.ps1` and `stop_backend.ps1` but does NOT stop OpenSearch. A user running `stop_all.ps1` would expect everything to stop.  
**Fix:** Add OpenSearch stop call: `& (Join-Path $repoRoot "scripts\start_opensearch.ps1") -Stop`

### 4.4 — `INSTALL.md` missing script reference table entries

**File:** `INSTALL.md` Section 8 (Scripts Reference)  
**Problem:** The scripts reference table doesn't include:
- `start_opensearch.ps1`
- `install_oslc.ps1`  
- `reinstall.ps1` / `reinstall_clean.ps1`

**Fix:** Add missing entries to the table.

---

## 5. Cross-Reference Matrix

| Doc/Script Reference | Target | Status |
|---|---|---|
| `README.md` → `deployment/scripts/install.ps1` | Deprecated wrapper | **Stale** |
| `README.md` → `src/web/app.py` | Doesn't exist | **Stale** |
| `INSTALL.md` → `scripts/install.ps1` | Main installer | **Correct** |
| `INSTALL.md` → `scripts/service_manager.ps1` | Service manager | **Correct** |
| `INSTALL.md` → `scripts/health_check.ps1` | Health checker | **Correct** |
| `INSTALL.md` → `scripts/reload_database.py` | Database loader | **Correct** |
| `deployment/README.md` → `deployment/scripts/install.ps1` | Deprecated wrapper | **Stale** |
| `deployment/README.md` → `deployment/scripts/cleanup.ps1` | Doesn't exist | **Broken** |
| `deployment/README.md` → `deployment/scripts/cleanup.bat` | Doesn't exist | **Broken** |
| `deployment/DEPLOYMENT_CHECKLIST.md` → `deployment\scripts\install.ps1` | Deprecated | **Stale** |
| `deployment/DEPLOYMENT_CHECKLIST.md` → `start_all.ps1` | Doesn't exist | **Broken** |
| `deployment/DEPLOYMENT_SUMMARY.md` → `deployment/scripts/install.bat` | Standalone old installer | **Misleading** |
| `reinstall_clean.ps1` → `mbse-neo4j-graph-rep.git` | Old repo URL | **Stale** |
| `.env.example` → `neo4j+s://` scheme | Aura cloud URI | **Misleading** |

---

## 6. Script Quality Assessment

### Well-Implemented (Strengths)

| Script | Quality Notes |
|---|---|
| `scripts/install.ps1` | Clean parameter handling, Python/Node version validation, React 19 lockfile guardrail, optional Phase 2 deps, connectivity verification |
| `scripts/service_manager.ps1` | Comprehensive 710-line manager with port conflict resolution, PID tracking, process tree killing, preflight inspection, legacy env var compatibility |
| `scripts/start_opensearch.ps1` | Robust lifecycle management: start/stop/restart/status, stale lock cleanup, health wait loop with timeout, process identification by command-line (avoids killing unrelated Java) |
| `scripts/start_all_interactive.ps1` | Good UX: prerequisite checks with warnings (not failures), delegates to service_manager |
| `scripts/start_backend.ps1` / `start_ui.ps1` | Port auto-selection, .env loading, legacy variable normalization, detach mode |

### Needs Improvement

| Script | Issues |
|---|---|
| `scripts/stop_all.ps1` | Doesn't stop OpenSearch, no .env loading |
| `scripts/health_check.ps1` | No .env loading, may fail auth without exported API_KEY |
| `scripts/install_oslc.ps1` | Incomplete ontology seeding (2/5 TTL files) |
| `deployment/scripts/install.bat` | Fully standalone, hardcoded paths, out-of-sync with current architecture |
| `deployment/scripts/*.ps1` | Dead code after forwarding wrappers |

---

## 7. Documentation Quality Assessment

### `INSTALL.md` — Grade: B+
- **Strengths:** Comprehensive 9-section guide, covers data loading pipeline (6 subsections), Azure VM deployment, troubleshooting tips
- **Gaps:** Missing OpenSearch setup, missing Ollama setup, incomplete scripts reference table, ambiguous dual `reload_database.py` references

### `README.md` — Grade: C
- **Strengths:** Good API endpoint documentation, feature overview
- **Problems:** Stale project structure, duplicate Quick Start sections, deprecated path references, old repo name

### `deployment/README.md` — Grade: D
- **Problems:** Fictional file tree, contradicts installer on admin requirements, references non-existent files, hardcoded install paths

### `deployment/DEPLOYMENT_CHECKLIST.md` — Grade: C-
- **Problems:** Admin requirement contradiction, hardcoded paths, references deprecated scripts and non-existent `start_all.ps1`

### `deployment/DEPLOYMENT_SUMMARY.md` — Grade: C-
- **Problems:** References deprecated/non-existent deployment script paths

### `.env.example` — Grade: B
- **Strengths:** Well-commented, covers all configuration areas (Neo4j, Ollama, Azure, Redis, JWT)
- **Problem:** Aura cloud URI default is misleading for local development

---

## 8. Recommended Action Plan

### Priority 1 — Fix immediately (blocking new-user onboarding)

1. Update `.env.example` NEO4J_URI default to `neo4j://127.0.0.1:7687`
2. Add OpenSearch installation section to `INSTALL.md`
3. Add Ollama installation section to `INSTALL.md`
4. Update `README.md` project structure and Quick Start to use `scripts/install.ps1`

### Priority 2 — Fix soon (causes confusion)

5. Delete dead code from `deployment/scripts/install.ps1` (lines 23-341)
6. Delete dead code from `deployment/scripts/service_manager.ps1` (lines 36-419)
7. Rewrite `deployment/README.md` with correct file tree and paths
8. Update `deployment/DEPLOYMENT_CHECKLIST.md` — remove admin requirement, fix paths
9. Fix `reinstall_clean.ps1` repo URL

### Priority 3 — Improve when convenient

10. Add OpenSearch stop to `stop_all.ps1`
11. Add `.env` loading to `health_check.ps1`
12. Extract shared `Import-DotEnvIfPresent` to module
13. Update `INSTALL.md` scripts reference table
14. Review `deployment/scripts/install.bat` — convert to wrapper or delete
