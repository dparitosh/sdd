# Git-Integrated MBSE Knowledge Graph Synchronization

## 📊 CI/CD Pipeline Review

### Current Implementation Status

**✅ Strengths:**
1. **Comprehensive Git Validation** - Branch naming, conventional commits, merge conflict detection
2. **Multi-Stage Pipeline** - git-validation → lint → test → build → security → deploy
3. **Multiple Triggers** - Push, PR, tags, releases, manual dispatch
4. **Security Scanning** - Trivy vulnerability scanning integrated
5. **Dual Deployment** - Staging (develop) and Production (main) environments

**⚠️ Gaps Identified:**
1. **No XMI/Model File Tracking** - Git changes don't trigger knowledge graph updates
2. **No Artifact Versioning** - MBSE artifacts (models, requirements, simulations) not versioned in Neo4j
3. **No Graph Synchronization** - Changes to XMI files don't automatically sync to graph database
4. **No Model Validation** - No validation of MBSE model integrity on commit
5. **No Digital Thread Tracking** - No traceability between Git commits and graph nodes

---

## 🎯 Solution: Git-Synchronized MBSE Knowledge Graph

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Developer Workflow                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Git Repository (GitHub/GitLab/Azure DevOps)                    │
│  ├── data/raw/*.xmi          (SysML/UML models)                 │
│  ├── simulations/*.slx       (Simulink models)                  │
│  ├── requirements/*.json     (Requirements data)                │
│  └── artifacts/*.yaml        (Metadata)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               CI/CD Pipeline (GitHub Actions)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Detect Changed Files                                   │  │
│  │    - Track *.xmi, *.slx, *.json, *.yaml                  │  │
│  │    - Calculate diff from previous commit                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │ 2. Validate Models                                        │  │
│  │    - XMI schema validation                                │  │
│  │    - ISO SMRL compliance check                            │  │
│  │    - Requirement ID collision check                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │ 3. Parse & Transform                                      │  │
│  │    - SemanticXMILoader.load_xmi_file()                    │  │
│  │    - Extract nodes & relationships                        │  │
│  │    - Add Git metadata (commit SHA, author, timestamp)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │ 4. Sync to Neo4j Knowledge Graph                          │  │
│  │    - Incremental update (delta only)                      │  │
│  │    - Version tagging with Git SHA                         │  │
│  │    - Create GitCommit nodes                               │  │
│  │    - Link artifacts to commits                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │ 5. Post-Sync Actions                                      │  │
│  │    - Run traceability analysis                            │  │
│  │    - Generate change impact report                        │  │
│  │    - Notify stakeholders                                  │  │
│  │    - Trigger simulation validation (if needed)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│         Neo4j MBSE Knowledge Graph (Versioned)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Nodes:                                                    │  │
│  │   - GitCommit {sha, author, timestamp, branch}            │  │
│  │   - Class {id, version, git_sha, modified_at}             │  │
│  │   - Requirement {id, version, git_sha}                    │  │
│  │   - SimulationModel {id, version, git_sha}                │  │
│  │                                                           │  │
│  │ Relationships:                                            │  │
│  │   - (GitCommit)-[:MODIFIED]->(Class)                      │  │
│  │   - (Class)-[:VERSION_OF {from_sha, to_sha}]->(Class)     │  │
│  │   - (Requirement)-[:TRACED_IN {git_sha}]->(Class)         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Components

### 1. Git Change Detection Job

Add to `.github/workflows/ci-cd.yml`:

```yaml
jobs:
  # ... existing jobs ...

  # ============================================================================
  # MBSE MODEL SYNCHRONIZATION
  # ============================================================================
  sync-mbse-models:
    name: Sync MBSE Models to Knowledge Graph
    runs-on: ubuntu-latest
    needs: [git-validation, lint]
    if: |
      (github.event_name == 'push' && 
       (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')) ||
      github.event_name == 'workflow_dispatch'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 2  # Need previous commit for diff

      - name: Detect changed MBSE files
        id: detect-changes
        run: |
          echo "Detecting changed MBSE artifacts..."
          
          # Get list of changed files
          CHANGED_FILES=$(git diff --name-only HEAD^ HEAD)
          
          # Filter for MBSE-relevant files
          XMI_FILES=$(echo "$CHANGED_FILES" | grep '\.xmi$' || true)
          SIMULINK_FILES=$(echo "$CHANGED_FILES" | grep '\.slx$' || true)
          REQUIREMENT_FILES=$(echo "$CHANGED_FILES" | grep 'requirements/.*\.json$' || true)
          
          echo "Changed XMI files:"
          echo "$XMI_FILES"
          echo "Changed Simulink files:"
          echo "$SIMULINK_FILES"
          echo "Changed Requirement files:"
          echo "$REQUIREMENT_FILES"
          
          # Export to outputs
          echo "xmi_files<<EOF" >> $GITHUB_OUTPUT
          echo "$XMI_FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          
          echo "simulink_files<<EOF" >> $GITHUB_OUTPUT
          echo "$SIMULINK_FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          
          echo "requirement_files<<EOF" >> $GITHUB_OUTPUT
          echo "$REQUIREMENT_FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          
          # Check if any MBSE files changed
          if [ -n "$XMI_FILES" ] || [ -n "$SIMULINK_FILES" ] || [ -n "$REQUIREMENT_FILES" ]; then
            echo "has_changes=true" >> $GITHUB_OUTPUT
            echo "✓ MBSE artifacts changed - sync required"
          else
            echo "has_changes=false" >> $GITHUB_OUTPUT
            echo "ℹ No MBSE artifacts changed - skipping sync"
          fi

      - name: Set up Python
        if: steps.detect-changes.outputs.has_changes == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        if: steps.detect-changes.outputs.has_changes == 'true'
        run: |
          pip install -r requirements.txt

      - name: Validate XMI files
        if: steps.detect-changes.outputs.has_changes == 'true'
        env:
          XMI_FILES: ${{ steps.detect-changes.outputs.xmi_files }}
        run: |
          echo "Validating XMI files..."
          python scripts/validate_xmi.py $XMI_FILES
          echo "✓ XMI validation passed"

      - name: Sync models to Neo4j
        if: steps.detect-changes.outputs.has_changes == 'true'
        env:
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
          GIT_SHA: ${{ github.sha }}
          GIT_AUTHOR: ${{ github.actor }}
          GIT_BRANCH: ${{ github.ref_name }}
          XMI_FILES: ${{ steps.detect-changes.outputs.xmi_files }}
        run: |
          echo "Syncing MBSE models to knowledge graph..."
          python scripts/sync_models_to_graph.py \
            --git-sha $GIT_SHA \
            --git-author $GIT_AUTHOR \
            --git-branch $GIT_BRANCH \
            --files $XMI_FILES
          echo "✓ Sync complete"

      - name: Generate change impact report
        if: steps.detect-changes.outputs.has_changes == 'true'
        env:
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
          GIT_SHA: ${{ github.sha }}
        run: |
          echo "Generating change impact analysis..."
          python scripts/analyze_change_impact.py --git-sha $GIT_SHA > impact_report.md
          echo "✓ Impact report generated"

      - name: Upload impact report
        if: steps.detect-changes.outputs.has_changes == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: impact-report-${{ github.sha }}
          path: impact_report.md

      - name: Comment on PR with impact analysis
        if: steps.detect-changes.outputs.has_changes == 'true' && github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('impact_report.md', 'utf8');
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🔄 MBSE Model Change Impact Analysis\n\n${report}`
            });
```

---

### 2. Model Synchronization Script

Create `scripts/sync_models_to_graph.py`:

```python
"""
Sync MBSE models from Git to Neo4j Knowledge Graph
Tracks versions using Git commit metadata
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.graph.connection import Neo4jConnection
from src.parsers.semantic_loader import SemanticXMILoader
from src.utils.config import Config


class GitIntegratedModelSync:
    """Synchronize MBSE models with Git version tracking"""

    def __init__(self, neo4j_conn: Neo4jConnection, git_sha: str, git_author: str, git_branch: str):
        self.conn = neo4j_conn
        self.git_sha = git_sha
        self.git_author = git_author
        self.git_branch = git_branch
        self.loader = SemanticXMILoader(neo4j_conn, enable_versioning=True)

    def create_git_commit_node(self) -> None:
        """Create a GitCommit node for version tracking"""
        logger.info(f"Creating GitCommit node for {self.git_sha}")

        query = """
        MERGE (gc:GitCommit {sha: $sha})
        SET gc.author = $author,
            gc.branch = $branch,
            gc.timestamp = datetime(),
            gc.synced_at = datetime()
        RETURN gc
        """

        self.conn.execute_query(
            query,
            {"sha": self.git_sha, "author": self.git_author, "branch": self.git_branch},
        )

        logger.info("✓ GitCommit node created")

    def sync_xmi_file(self, xmi_path: Path) -> dict:
        """
        Sync XMI file to graph with Git metadata
        Returns sync statistics
        """
        logger.info(f"Syncing {xmi_path} to knowledge graph...")

        # Load XMI with git metadata
        stats = self.loader.load_xmi_file(
            str(xmi_path),
            metadata={
                "git_sha": self.git_sha,
                "git_author": self.git_author,
                "git_branch": self.git_branch,
                "load_timestamp": datetime.now().isoformat(),
            },
        )

        # Link all modified nodes to GitCommit
        self.link_artifacts_to_commit(xmi_path.stem)

        logger.info(f"✓ Synced {xmi_path.name}")
        return stats

    def link_artifacts_to_commit(self, model_name: str) -> None:
        """Create relationships between artifacts and GitCommit"""
        logger.info(f"Linking artifacts from {model_name} to commit {self.git_sha}")

        query = """
        MATCH (gc:GitCommit {sha: $git_sha})
        MATCH (n)
        WHERE n.git_sha = $git_sha
          AND n.loadSource CONTAINS $model_name
        MERGE (gc)-[:MODIFIED {timestamp: datetime()}]->(n)
        RETURN count(n) as linked_count
        """

        result = self.conn.execute_query(
            query, {"git_sha": self.git_sha, "model_name": model_name}
        )

        linked_count = result[0]["linked_count"] if result else 0
        logger.info(f"✓ Linked {linked_count} artifacts to GitCommit")

    def create_version_links(self) -> None:
        """
        Create VERSION_OF relationships between old and new versions
        Tracks evolution of artifacts across commits
        """
        logger.info("Creating version relationships...")

        query = """
        // Find nodes with same ID but different git_sha
        MATCH (old)
        WHERE old.git_sha IS NOT NULL
        WITH old.id as artifact_id, old.git_sha as old_sha
        MATCH (new)
        WHERE new.id = artifact_id
          AND new.git_sha = $current_sha
          AND new.git_sha <> old_sha
        MATCH (old_node {id: artifact_id, git_sha: old_sha})
        MERGE (old_node)-[v:VERSION_OF]->(new)
        SET v.from_sha = old_sha,
            v.to_sha = $current_sha,
            v.created_at = datetime()
        RETURN count(v) as version_links
        """

        result = self.conn.execute_query(query, {"current_sha": self.git_sha})
        version_links = result[0]["version_links"] if result else 0

        logger.info(f"✓ Created {version_links} version relationships")

    def sync_all(self, xmi_files: list[Path]) -> dict:
        """Sync all XMI files and create version tracking"""
        logger.info(f"Starting sync of {len(xmi_files)} XMI files...")

        # Create GitCommit node
        self.create_git_commit_node()

        # Sync each file
        total_stats = {
            "files_synced": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": [],
        }

        for xmi_file in xmi_files:
            try:
                stats = self.sync_xmi_file(xmi_file)
                total_stats["files_synced"] += 1
                total_stats["nodes_created"] += stats.get("nodes_created", 0)
                total_stats["relationships_created"] += (
                    stats.get("containment_relationships", 0)
                    + stats.get("semantic_relationships", 0)
                    + stats.get("type_relationships", 0)
                )
            except Exception as e:
                logger.error(f"Failed to sync {xmi_file}: {e}")
                total_stats["errors"].append({"file": str(xmi_file), "error": str(e)})

        # Create version links
        self.create_version_links()

        logger.info("✓ Sync complete!")
        return total_stats


def main():
    parser = argparse.ArgumentParser(description="Sync MBSE models to Neo4j with Git tracking")
    parser.add_argument("--git-sha", required=True, help="Git commit SHA")
    parser.add_argument("--git-author", required=True, help="Git commit author")
    parser.add_argument("--git-branch", required=True, help="Git branch name")
    parser.add_argument("--files", nargs="+", required=True, help="XMI files to sync")

    args = parser.parse_args()

    # Convert file paths to Path objects
    xmi_files = [Path(f) for f in args.files if f.strip()]

    if not xmi_files:
        logger.info("No XMI files to sync")
        return

    # Connect to Neo4j
    config = Config()
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()

        # Run sync
        syncer = GitIntegratedModelSync(
            conn, args.git_sha, args.git_author, args.git_branch
        )
        stats = syncer.sync_all(xmi_files)

        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("SYNC STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Files synced: {stats['files_synced']}")
        logger.info(f"Nodes created: {stats['nodes_created']}")
        logger.info(f"Relationships created: {stats['relationships_created']}")
        logger.info(f"Errors: {len(stats['errors'])}")

        if stats["errors"]:
            logger.error("\nErrors encountered:")
            for error in stats["errors"]:
                logger.error(f"  {error['file']}: {error['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### 3. Change Impact Analysis Script

Create `scripts/analyze_change_impact.py`:

```python
"""
Analyze impact of model changes using Neo4j graph queries
Generates markdown report for PR comments
"""

import argparse
from datetime import datetime

from loguru import logger

from src.graph.connection import Neo4jConnection
from src.utils.config import Config


class ChangeImpactAnalyzer:
    """Analyze impact of Git commit on MBSE knowledge graph"""

    def __init__(self, neo4j_conn: Neo4jConnection, git_sha: str):
        self.conn = neo4j_conn
        self.git_sha = git_sha

    def get_modified_artifacts(self) -> list[dict]:
        """Get all artifacts modified in this commit"""
        query = """
        MATCH (gc:GitCommit {sha: $git_sha})-[:MODIFIED]->(n)
        RETURN 
            n.id as id,
            n.name as name,
            labels(n) as types,
            n.type as xmi_type
        ORDER BY n.name
        """
        return self.conn.execute_query(query, {"git_sha": self.git_sha})

    def get_downstream_impact(self, artifact_id: str) -> list[dict]:
        """Find all artifacts affected by changes to this artifact"""
        query = """
        MATCH path = (modified {id: $artifact_id})<-[*1..3]-(affected)
        WHERE modified.git_sha = $git_sha
        RETURN DISTINCT
            affected.id as id,
            affected.name as name,
            labels(affected)[0] as type,
            length(path) as distance
        ORDER BY distance, affected.name
        LIMIT 50
        """
        return self.conn.execute_query(
            query, {"artifact_id": artifact_id, "git_sha": self.git_sha}
        )

    def get_requirement_traceability(self, artifact_id: str) -> list[dict]:
        """Check if modified artifact affects requirements"""
        query = """
        MATCH (modified {id: $artifact_id})
        MATCH path = (req:Requirement)-[*]-(modified)
        WHERE modified.git_sha = $git_sha
        RETURN DISTINCT
            req.id as req_id,
            req.name as req_name,
            length(path) as hops
        ORDER BY hops
        LIMIT 20
        """
        return self.conn.execute_query(
            query, {"artifact_id": artifact_id, "git_sha": self.git_sha}
        )

    def generate_report(self) -> str:
        """Generate markdown report of change impact"""
        modified = self.get_modified_artifacts()

        if not modified:
            return "No MBSE artifacts modified in this commit."

        report = []
        report.append(f"**Commit:** `{self.git_sha[:8]}`")
        report.append(f"**Modified Artifacts:** {len(modified)}")
        report.append("")
        report.append("### 📝 Modified Artifacts")
        report.append("")
        report.append("| Artifact | Type | ID |")
        report.append("|----------|------|-----|")

        for artifact in modified:
            name = artifact.get("name", "N/A")
            types = ", ".join(artifact.get("types", []))
            artifact_id = artifact.get("id", "N/A")
            report.append(f"| {name} | {types} | `{artifact_id}` |")

        report.append("")
        report.append("### 🔗 Downstream Impact Analysis")
        report.append("")

        total_affected = 0
        for artifact in modified[:5]:  # Limit to 5 most important
            artifact_id = artifact["id"]
            downstream = self.get_downstream_impact(artifact_id)

            if downstream:
                total_affected += len(downstream)
                report.append(f"**{artifact['name']}** affects {len(downstream)} artifact(s):")
                report.append("")
                for item in downstream[:10]:  # Show top 10
                    report.append(
                        f"- `{item['id']}` ({item['type']}) - {item['distance']} hop(s) away"
                    )
                report.append("")

        report.append(f"**Total Downstream Artifacts:** {total_affected}")
        report.append("")
        report.append("### ✅ Requirements Traceability")
        report.append("")

        requirements_affected = set()
        for artifact in modified:
            reqs = self.get_requirement_traceability(artifact["id"])
            for req in reqs:
                requirements_affected.add(req["req_id"])

        if requirements_affected:
            report.append(
                f"**{len(requirements_affected)} Requirement(s) potentially affected:**"
            )
            report.append("")
            for req_id in list(requirements_affected)[:10]:
                report.append(f"- `{req_id}`")
        else:
            report.append("No direct requirement impacts detected.")

        report.append("")
        report.append("---")
        report.append(f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Analyze change impact of Git commit")
    parser.add_argument("--git-sha", required=True, help="Git commit SHA")
    args = parser.parse_args()

    config = Config()
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()

        analyzer = ChangeImpactAnalyzer(conn, args.git_sha)
        report = analyzer.generate_report()

        print(report)


if __name__ == "__main__":
    main()
```

---

### 4. XMI Validation Script

Create `scripts/validate_xmi.py`:

```python
"""
Validate XMI files for ISO SMRL compliance before syncing to graph
"""

import argparse
import sys
from pathlib import Path

from loguru import logger
from lxml import etree


class XMIValidator:
    """Validate XMI files against ISO SMRL schema"""

    def __init__(self):
        self.errors = []

    def validate_file(self, xmi_path: Path) -> bool:
        """
        Validate XMI file structure and content
        Returns True if valid, False otherwise
        """
        logger.info(f"Validating {xmi_path}")

        try:
            # Parse XML
            tree = etree.parse(str(xmi_path))
            root = tree.getroot()

            # Check root element
            if root.tag not in ["{http://www.omg.org/spec/XMI/20131001}XMI", "xmi:XMI"]:
                self.errors.append(f"{xmi_path}: Invalid root element {root.tag}")
                return False

            # Check for required namespaces
            required_ns = ["xmi", "uml"]
            for ns in required_ns:
                if not any(ns in key for key in root.nsmap.keys()):
                    self.errors.append(f"{xmi_path}: Missing namespace {ns}")
                    return False

            # Check for model elements
            model_elements = root.findall(".//*[@xmi:id]", root.nsmap)
            if not model_elements:
                self.errors.append(f"{xmi_path}: No model elements with xmi:id found")
                return False

            # Check for duplicate IDs
            ids = [elem.get("{http://www.omg.org/spec/XMI/20131001}id") for elem in model_elements]
            duplicates = [id for id in ids if ids.count(id) > 1]
            if duplicates:
                self.errors.append(
                    f"{xmi_path}: Duplicate xmi:id found: {set(duplicates)}"
                )
                return False

            logger.info(f"✓ {xmi_path.name} is valid")
            return True

        except etree.XMLSyntaxError as e:
            self.errors.append(f"{xmi_path}: XML syntax error - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{xmi_path}: Validation error - {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Validate XMI files")
    parser.add_argument("files", nargs="+", help="XMI files to validate")
    args = parser.parse_args()

    validator = XMIValidator()
    all_valid = True

    for file_path in args.files:
        path = Path(file_path)
        if path.exists():
            if not validator.validate_file(path):
                all_valid = False
        else:
            logger.warning(f"File not found: {file_path}")

    if not all_valid:
        logger.error("\n❌ Validation failed:")
        for error in validator.errors:
            logger.error(f"  {error}")
        sys.exit(1)

    logger.info("\n✓ All XMI files are valid")


if __name__ == "__main__":
    main()
```

---

## 📊 Graph Schema Extension for Git Integration

Add these node types and relationships:

```cypher
// Create GitCommit nodes
CREATE CONSTRAINT git_commit_sha IF NOT EXISTS
FOR (gc:GitCommit) REQUIRE gc.sha IS UNIQUE;

// Create index for git_sha on artifacts
CREATE INDEX artifact_git_sha IF NOT EXISTS
FOR (n:Class) ON (n.git_sha);

// Example GitCommit node
CREATE (gc:GitCommit {
  sha: 'a1b2c3d4e5f6',
  author: 'john.doe',
  branch: 'feature/brake-system',
  timestamp: datetime(),
  message: 'feat(brakes): update brake caliper material',
  synced_at: datetime()
})

// Link to modified artifacts
MATCH (gc:GitCommit {sha: 'a1b2c3d4e5f6'})
MATCH (c:Class {git_sha: 'a1b2c3d4e5f6'})
MERGE (gc)-[:MODIFIED {timestamp: datetime()}]->(c)

// Create version history
MATCH (old:Class {id: 'BrakeCaliper'})-[:VERSION_OF*0..]->(current:Class {id: 'BrakeCaliper'})
WHERE current.git_sha = 'a1b2c3d4e5f6'
RETURN old, current
```

---

## 🎯 Benefits

### 1. **Complete Digital Thread**
- Every artifact version linked to Git commit
- Full audit trail from requirements → design → implementation
- Bi-directional traceability (code ↔ models)

### 2. **Automated Change Management**
- Automatic impact analysis on every commit
- Requirements validation before merge
- Stakeholder notifications on affected artifacts

### 3. **Version Control for MBSE**
- Time-travel queries ("show me the system as of commit X")
- Diff between model versions
- Rollback capability

### 4. **Continuous Integration**
- Model validation on every PR
- Automated testing of system architecture
- Simulation triggers on design changes

### 5. **Collaboration Enhancement**
- Clear ownership via Git authors
- Change history visible in knowledge graph
- Conflict detection before merge

---

## 📈 Example Queries

### Get all changes in last 10 commits
```cypher
MATCH (gc:GitCommit)
WITH gc ORDER BY gc.timestamp DESC LIMIT 10
MATCH (gc)-[:MODIFIED]->(artifact)
RETURN gc.sha, gc.author, gc.timestamp, 
       collect({name: artifact.name, type: labels(artifact)}) as changes
```

### Find requirements affected by commit
```cypher
MATCH (gc:GitCommit {sha: 'abc123'})-[:MODIFIED]->(modified)
MATCH path = (req:Requirement)-[*]-(modified)
RETURN DISTINCT req.id, req.name, length(path) as distance
ORDER BY distance
```

### Get version history of artifact
```cypher
MATCH path = (old:Class {id: 'BrakeCaliper'})-[:VERSION_OF*]->(current:Class)
RETURN [node IN nodes(path) | {
  version: node.git_sha,
  modified_at: node.modifiedAt,
  author: node.git_author
}] as version_history
ORDER BY current.modifiedAt DESC
```

---

## ✅ Implementation Checklist

- [ ] Add `sync-mbse-models` job to CI/CD pipeline
- [ ] Create `scripts/sync_models_to_graph.py`
- [ ] Create `scripts/analyze_change_impact.py`
- [ ] Create `scripts/validate_xmi.py`
- [ ] Add GitCommit constraint to Neo4j
- [ ] Update SemanticXMILoader to accept git metadata
- [ ] Configure GitHub secrets (NEO4J_URI, NEO4J_PASSWORD)
- [ ] Test with sample XMI file change
- [ ] Document workflow for developers
- [ ] Train team on Git-integrated MBSE workflow

---

**Status**: Ready for implementation - All components designed and integration points identified.
