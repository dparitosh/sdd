# Phase 2 Gap Analysis: Semantic Web & MoSSEC Integration

**Date**: January 22, 2026
**Status**: Architecture Defined, Implementation Pending

## 1. Critical Infrastructure Gaps (The "Plumbing")

### 1.1 SMRL Data Ingestion Pipeline
**Status**: 🔴 **CRITICAL MISSING**
- **Issue**: We have the `smrlv12` folder (raw schemas), but no mechanism to load it into the system.
- **Impact**: The "Semantic Foundation" is theoretical. The Graph doesn't actually know what a `ThermalAnalysis` is according to ISO 10303.
- **Requirement**: `scripts/ingest_smrl.py`
    - Must parse standard EXPRESS schemas or mapped XSDs.
    - Must populate the "TBox" (Ontology) in Neo4j or an RDF Store.
    - Must populate a SKOS vocabulary for "Reference Data" lookup.

### 1.2 OSLC Server Implementation
**Status**: 🔴 **MISSING**
- **Issue**: No actual API endpoints exist to expose data as OSLC Resources.
- **Impact**: External tools (DOORS, Cameo) cannot connect to us.
- **Requirement**: `backend/src/web/routes/oslc.py` + `backend/src/web/services/oslc_service.py`
    - `/oslc/rootservices` (Entry point)
    - `/oslc/catalog` (Service Provider Catalog)
    - Content Negotiation logic (`application/rdf+xml`, `application/ld+json`).

### 1.3 TRS (Tracked Resource Set) Service
**Status**: 🟠 **PARTIAL**
- **Issue**: `link_ap_hierarchy.py` is a standalone batch script, not a "Live Feed".
- **Impact**: "Smart Linking" is static. Changes in Requirements aren't propagated to the Graph in real-time.
- **Requirement**: Transform script into `OSLC_TRS_Service` that maintains a persistent `ChangeLog` in Redis/Neo4j.

## 2. MoSSEC Agent Gaps (The "Behavior")

### 2.1 Agent State vs. MoSSEC Context
**Status**: 🟠 **CONCEPTUAL ONLY**
- **Issue**: Agents store state in LangGraph memory (ephemeral).
- **Impact**: We lose the "Why" (Context) of a simulation run. Traceability is broken.
- **Requirement**: Agents must persist their "Run Context" as a `(:MoSSEC_Context)` node in Neo4j *before* execution.

### 2.2 SPDM Tool Wrappers
**Status**: 🔴 **MISSING**
- **Issue**: `SimulationAgent` mocks execution.
- **Impact**: No real connection to industry tools (HDF5 results, Mesh files).
- **Requirement**: `backend/src/integrations/spdm/`
    - `hdf5_parser.py`: Extract results from standard binary files.
    - `mesh_parser.py`: Extract geometry metadata.

## 3. Frontend Gaps (The "Experience")

### 3.1 Delegated UI
**Status**: 🔴 **MISSING**
- **Issue**: No React components to support OSLC "Picker" or "Creation" dialogs.
- **Impact**: External tools cannot "pop up" a window to select a Requirement from our system.
- **Requirement**: `frontend/src/components/oslc/DelegatedUI.jsx`.

### 3.2 Semantic Search
**Status**: 🔴 **MISSING**
- **Issue**: Search is currently text-based (Lucene).
- **Impact**: Searching for "Heat" misses "Thermal" (synonyms).
- **Requirement**: Integrate SKOS-based expansion into the search API (`/api/search/semantic`).

## 4. Reference Data Gaps

### 4.1 Unit Management
**Status**: 🟠 **PARTIAL** (Basic endpoints exist)
- **Issue**: Units are isolated.
- **Impact**: Cannot automatically convert "50 kg" to "110 lbs" during validation.
- **Requirement**: Integrate `QUDT` or `OM` (Ontology of Units of Measure) mapping into the `smrlv12` ingestor.

## 5. Security Gaps

### 5.1 OSLC OAuth
**Status**: 🔴 **MISSING**
- **Issue**: No OAuth 1.0a implementation.
- **Impact**: Cannot act as an OSLC Client to legacy tools (IBM ELM requires OAuth 1.0a).
- **Requirement**: `OSLCClient` service with `requests-oauthlib` for proper 3-legged auth.
