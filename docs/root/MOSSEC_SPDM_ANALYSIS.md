# MoSSEC (ISO 10303-243) & SPDM Architecture Analysis

## 1. Domain Context: The MoSSEC Gap
Current implementation treats "AP243" merely as a bucket for "Reference Data" (Units, Ontologies). This is a **Level 3 implementation** view but misses the core business logic of ISO 10303-243 (MoSSEC).

**MoSSEC is about:**
- **Collaborative SE Context**: Who (Organization) did what (Activity) to what (Study/Model) and why (Requirement).
- **SPDM (Simulation Process Data Management)**: Managing the lifecycle of a simulation *study*, not just the file storage.

The current system has `SimulationAgent` but lacks the formal MoSSEC data structures to make its actions "standard-compliant".

## 2. Agent-as-a-Resource in MoSSEC
In a proper MoSSEC architecture, an "AI Agent" is not an external "user" but a **first-class participant**.

### 2.1 Mapping Agents to MoSSEC Entities
| MoSSEC Entity | AI Agent Equivalent |
|:---|:---|
| `Organization` / `Person` | **The Agent Identity**. Each specific agent (e.g., "FEA_Solver_Agent") should be registered as a `Person` or `Organization` in the Graph. |
| `Activity` | **The Agent's Execution**. When `SimulationAgent.run_simulation()` is called, it must create a MoSSEC `Activity` node. |
| `Study` | **The Agent's Workflow**. A chain of Agent reasoning steps = A MoSSEC `Study`. |
| `Context` | **The LangGraph State**. The memory of the agent *is* the MoSSEC `Context`. |

## 3. SPDM Integration Architecture

### 3.1 The "Wrapper" Pattern
The `SimulationAgent` currently mocks execution. To support real SPDM, we must implement the **Tool Wrapper** pattern:
1.  **Input Definition**: Agent reads `Requirement` (AP239) and `GeometricModel` (AP242).
2.  **Context Creation**: Agent creates a MoSSEC `Study` node.
3.  **Tool Execution**: Agent generates the input deck for the solver (Nastran, Ansys, OpenFOAM).
4.  **Result Capture**: Agent parses the result file and creates a MoSSEC `AnalysisResult` node linked to the `Study`.

### 3.2 Traceability (The "Why")
MoSSEC excels at linking the *Result* back to the *Requirement*.
- **Current Linker**: Links `Analysis` -> `Geometry`.
- **MoSSEC Linker**: Must link `AnalysisResult` (SPDM) -> `Activity` (Agent) -> `Requirement` (AP239).

## 4. Revised Phase 2 Plan (MoSSEC-First)

### 4.1 Data Model Extensions
We need to extend the Neo4j schema to support these MoSSEC specifics:
- `(:MoSSEC_Study)`
- `(:MoSSEC_Activity)`
- `(:MoSSEC_Context)`

### 4.2 Agent Refactoring
The `SimulationAgent` needs to be upgraded from a simple function caller to a **MoSSEC-aware actor**:
- **Before Run**: Create `Activity` node (Status: Started).
- **During Run**: Update `Context`.
- **After Run**: Link `AnalysisResult` to `Activity` and `GeometricModel`.

## 5. OSLC Integration for SPDM
SPDM tools often lack native OSLC. The Agent acts as the **OSLC Adapter**:
- External Client requests: "Run Analysis X".
- Agent (acting as OSLC Server) accepts the request.
- Agent runs the legacy CLI tool.
- Agent exposes the result as an RDF Resource.

This "Agent-as-Adapter" approach leverages the AI to bridge the gap between modern Linked Data and legacy Simulation Tools.
