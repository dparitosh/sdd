"""
Simulation Data Dossier Service Layer
============================================================================
Purpose: Service layer for SDD operations (dossiers, artifacts, MOSSEC trace)
Created: February 24, 2026
Phase: Sprint 1 - Backend API Development
Related: docs/SDD_INTEGRATION_TRACKER.md
============================================================================

Features:
- Dossier CRUD operations
- Artifact queries  
- MOSSEC traceability tracking
- AP243/AP239 integration queries
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from neo4j.exceptions import Neo4jError


class SimulationService:
    """Service layer for simulation data dossier operations"""
    
    def __init__(self, neo4j_service):
        """
        Initialize simulation service
        
        Args:
            neo4j_service: Neo4jService instance for database operations
        """
        self.neo4j = neo4j_service
        logger.info("SimulationService initialized")
    
    # ========================================================================
    # DOSSIER OPERATIONS
    # ========================================================================
    
    def get_all_dossiers(
        self,
        status: Optional[str] = None,
        engineer: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get all simulation dossiers with optional filtering
        
        Args:
            status: Filter by status (IN_PROGRESS, PENDING_REVIEW, APPROVED, REJECTED)
            engineer: Filter by engineer name
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            Dictionary with count and dossiers list
        """
        where_clauses = []
        params: Dict[str, Any] = {'limit': limit, 'offset': offset}
        
        if status:
            where_clauses.append("d.status = $status")
            params['status'] = status
        
        if engineer:
            where_clauses.append("d.engineer = $engineer")
            params['engineer'] = engineer
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        MATCH (d:SimulationDossier)
        WHERE {where_clause}
        WITH d
        ORDER BY d.last_updated DESC
        SKIP $offset
        LIMIT $limit
        OPTIONAL MATCH (d)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)
        WITH d, COUNT(a) AS artifact_count
        RETURN {{
            id: d.id,
            name: d.name,
            version: d.version,
            status: d.status,
            credibility_level: d.credibility_level,
            motor_id: d.motor_id,
            project_name: d.project_name,
            engineer: d.engineer,
            last_updated: d.last_updated,            created_at: d.created_at,            artifact_count: artifact_count,
            ap_level: d.ap_level,
            ap_schema: d.ap_schema
        }} AS dossier
        """
        
        try:
            results = self.neo4j.execute_query(query, params)
            dossiers = [r['dossier'] for r in results]
            
            return {
                'count': len(dossiers),
                'dossiers': dossiers,
                'limit': limit,
                'offset': offset
            }
        
        except Neo4jError as e:
            logger.error(f"Error fetching dossiers: {e}")
            raise
    
    def get_dossier_by_id(self, dossier_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed dossier information including all artifacts and evidence categories
        
        Args:
            dossier_id: Dossier ID (e.g., 'DOS-2024-001')
        
        Returns:
            Dossier details with artifacts and evidence categories, or None if not found
        """
        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        OPTIONAL MATCH (d)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)
        OPTIONAL MATCH (d)-[:HAS_EVIDENCE_CATEGORY]->(e:EvidenceCategory)
        OPTIONAL MATCH (a)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
        WITH d, 
             COLLECT(DISTINCT {
                 id: a.id,
                 name: a.name,
                 type: a.type,
                 status: a.status,
                 timestamp: a.timestamp,
                 size: a.size,
                 checksum: a.checksum,
                 requirement: r.id
             }) AS artifacts,
             COLLECT(DISTINCT {
                 id: e.id,
                 label: e.label,
                 status: e.status,
                 type: e.type
             }) AS evidence_categories
        RETURN {
            id: d.id,
            name: d.name,
            version: d.version,
            status: d.status,
            credibility_level: d.credibility_level,
            motor_id: d.motor_id,
            project_name: d.project_name,
            engineer: d.engineer,
            last_updated: d.last_updated,
            created_at: d.created_at,
            ap_level: d.ap_level,
            ap_schema: d.ap_schema,
            artifacts: artifacts,
            evidence_categories: evidence_categories
        } AS dossier
        """
        
        try:
            results = self.neo4j.execute_query(query, {'dossier_id': dossier_id})
            if not results:
                return None
            return results[0]['dossier']
        
        except Neo4jError as e:
            logger.error(f"Error fetching dossier {dossier_id}: {e}")
            raise
    
    def create_dossier(self, dossier_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new simulation dossier
        
        Args:
            dossier_data: Dictionary with dossier properties
        
        Returns:
            Created dossier with ID
        """
        query = """
        CREATE (d:SimulationDossier {
            id: $id,
            name: $name,
            version: $version,
            status: $status,
            credibility_level: $credibility_level,
            motor_id: $motor_id,
            project_name: $project_name,
            engineer: $engineer,
            last_updated: datetime(),
            created_at: datetime(),
            ap_level: 'AP243',
            ap_schema: 'AP243'
        })
        RETURN {
            id: d.id,
            name: d.name,
            version: d.version,
            status: d.status,
            created_at: toString(d.created_at)
        } AS dossier
        """
        
        try:
            results = self.neo4j.execute_query(query, dossier_data)
            if not results:
                return None
            return results[0]['dossier']
        
        except Neo4jError as e:
            logger.error(f"Error creating dossier: {e}")
            raise
    
    def update_dossier(self, dossier_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update dossier properties
        
        Args:
            dossier_id: Dossier ID
            updates: Dictionary of properties to update
        
        Returns:
            Updated dossier or None if not found
        """
        # Build SET clause dynamically
        set_clauses = [f"d.{key} = ${key}" for key in updates.keys()]
        set_clauses.append("d.last_updated = datetime()")
        set_clause = ", ".join(set_clauses)
        
        query = f"""
        MATCH (d:SimulationDossier {{id: $dossier_id}})
        SET {set_clause}
        RETURN {{
            id: d.id,
            name: d.name,
            status: d.status,
            last_updated: toString(d.last_updated)
        }} AS dossier
        """
        
        params = {'dossier_id': dossier_id, **updates}
        
        try:
            results = self.neo4j.execute_query(query, params)
            if not results:
                return None
            return results[0]['dossier']
        
        except Neo4jError as e:
            logger.error(f"Error updating dossier {dossier_id}: {e}")
            raise
    
    # ========================================================================
    # ARTIFACT OPERATIONS
    # ========================================================================
    
    def get_artifacts(
        self,
        dossier_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get simulation artifacts with optional filtering
        
        Args:
            dossier_id: Filter by dossier ID
            artifact_type: Filter by type (Report, Certification, CSV)
            status: Filter by status (Validated, Pending)
            limit: Maximum number of results
        
        Returns:
            List of artifacts
        """
        where_clauses = []
        params: Dict[str, Any] = {'limit': limit}
        
        match_clause = "MATCH (a:SimulationArtifact)"
        
        if dossier_id:
            match_clause = "MATCH (d:SimulationDossier {id: $dossier_id})-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)"
            params['dossier_id'] = dossier_id
        
        if artifact_type:
            where_clauses.append("a.type = $artifact_type")
            params['artifact_type'] = artifact_type
        
        if status:
            where_clauses.append("a.status = $status")
            params['status'] = status
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        {match_clause}
        WHERE {where_clause}
        OPTIONAL MATCH (a)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
        RETURN {{
            id: a.id,
            name: a.name,
            type: a.type,
            status: a.status,
            timestamp: a.timestamp,
            size: a.size,
            checksum: a.checksum,
            requirement_id: r.id,
            requirement_name: r.name,
            ap_level: a.ap_level,
            ap_schema: a.ap_schema
        }} AS artifact
        LIMIT $limit
        """
        
        try:
            results = self.neo4j.execute_query(query, params)
            return [r['artifact'] for r in results]
        
        except Neo4jError as e:
            logger.error(f"Error fetching artifacts: {e}")
            raise
    
    def get_artifact_by_id(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed artifact information
        
        Args:
            artifact_id: Artifact ID (e.g., 'A1')
        
        Returns:
            Artifact details or None if not found
        """
        query = """
        MATCH (a:SimulationArtifact {id: $artifact_id})
        OPTIONAL MATCH (a)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
        OPTIONAL MATCH (d:SimulationDossier)-[:CONTAINS_ARTIFACT]->(a)
        RETURN {
            id: a.id,
            name: a.name,
            type: a.type,
            status: a.status,
            timestamp: a.timestamp,
            size: a.size,
            checksum: a.checksum,
            ap_level: a.ap_level,
            ap_schema: a.ap_schema,
            requirement: {
                id: r.id,
                name: r.name,
                description: r.description,
                priority: r.priority
            },
            dossier: {
                id: d.id,
                name: d.name,
                version: d.version
            }
        } AS artifact
        """
        
        try:
            results = self.neo4j.execute_query(query, {'artifact_id': artifact_id})
            return results[0]['artifact'] if results else None
        
        except Neo4jError as e:
            logger.error(f"Error fetching artifact {artifact_id}: {e}")
            raise
    
    # ========================================================================
    # MOSSEC TRACEABILITY
    # ========================================================================
    
    def get_mossec_trace(self, requirement_id: str, max_depth: int = 7) -> Dict[str, Any]:
        """
        Get full MOSSEC traceability chain from requirement to approval
        
        Args:
            requirement_id: Starting requirement ID (e.g., 'REQ-01')
            max_depth: Maximum relationship depth to traverse
        
        Returns:
            Dictionary with requirement, artifacts, validation cases, and trace path
        """
        query = """
        MATCH (r:Requirement {id: $requirement_id})
        OPTIONAL MATCH path = (r)-[*1..7]-(a:SimulationArtifact)
        WHERE ALL(rel in relationships(path) WHERE type(rel) IN ['LINKED_TO_REQUIREMENT', 'validates'])
        WITH r, COLLECT(DISTINCT a) AS artifacts
        RETURN {
            requirement: {
                id: r.id,
                name: r.name,
                description: r.description,
                priority: r.priority,
                standard: r.standard
            },
            artifacts: [a IN artifacts | {
                id: a.id,
                name: a.name,
                type: a.type,
                status: a.status
            }],
            trace_complete: SIZE(artifacts) > 0
        } AS trace
        """
        
        try:
            results = self.neo4j.execute_query(query, {
                'requirement_id': requirement_id,
                'max_depth': max_depth
            })
            return results[0]['trace'] if results else {
                'requirement': None,
                'artifacts': [],
                'trace_complete': False
            }
        
        except Neo4jError as e:
            logger.error(f"Error fetching MOSSEC trace for {requirement_id}: {e}")
            raise
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get simulation data statistics
        
        Returns:
            Dictionary with counts and summary stats
        """
        query = """
        MATCH (d:SimulationDossier)
        WITH COUNT(d) AS total_dossiers,
             COLLECT(DISTINCT {status: d.status}) AS statuses
        MATCH (a:SimulationArtifact)
        WITH total_dossiers, statuses, COUNT(a) AS total_artifacts
        OPTIONAL MATCH (a2:SimulationArtifact)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
        WITH total_dossiers, statuses, total_artifacts, COUNT(DISTINCT r) AS total_requirements
        MATCH (e:EvidenceCategory)
        WITH total_dossiers, statuses, total_artifacts, total_requirements, COUNT(e) AS total_evidence_categories
        RETURN {
            total_dossiers: total_dossiers,
            total_artifacts: total_artifacts,
            total_requirements: total_requirements,
            total_evidence_categories: total_evidence_categories,
            dossier_statuses: statuses
        } AS stats
        """
        
        try:
            results = self.neo4j.execute_query(query)
            return results[0]['stats'] if results else {
                'total_dossiers': 0,
                'total_artifacts': 0,
                'total_requirements': 0,
                'total_evidence_categories': 0,
                'dossiers_by_status': []
            }
        
        except Neo4jError as e:
            logger.error(f"Error fetching statistics: {e}")
            raise    
    # ========================================================================
    # SIMULATION RUN OPERATIONS (Sprint 2)
    # ========================================================================
    
    def get_simulation_runs(
        self,
        dossier_id: Optional[str] = None,
        status: Optional[str] = None,
        sim_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get simulation runs with optional filtering
        
        Args:
            dossier_id: Filter by dossier ID
            status: Filter by run status (Complete, Running, Failed)
            sim_type: Filter by simulation type
            limit: Maximum number of results
        
        Returns:
            List of simulation runs
        """
        where_clauses = []
        params: Dict[str, Any] = {'limit': limit}
        
        if status:
            where_clauses.append("sr.status = $status")
            params['status'] = status
        
        if sim_type:
            where_clauses.append("sr.sim_type = $sim_type")
            params['sim_type'] = sim_type
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Add dossier filter if provided
        dossier_match = ""
        if dossier_id:
            dossier_match = """
            MATCH (d:SimulationDossier {id: $dossier_id})-[:HAS_SIMULATION_RUN]->(sr)
            """
            params['dossier_id'] = dossier_id
        else:
            dossier_match = "MATCH (sr:SimulationRun)"
        
        query = f"""
        {dossier_match}
        WHERE {where_clause}
        OPTIONAL MATCH (sr)-[:GENERATED]->(a:SimulationArtifact)
        WITH sr, COLLECT(a.id) AS generated_artifacts
        RETURN {{
            id: sr.id,
            sim_type: sr.sim_type,
            start_time: sr.start_time,
            end_time: sr.end_time,
            status: sr.status,
            solver_version: sr.solver_version,
            credibility_level: sr.credibility_level,
            mesh_elements: sr.mesh_elements,
            cpu_hours: sr.cpu_hours,
            generated_artifacts: generated_artifacts,
            ap_level: sr.ap_level
        }} AS run
        ORDER BY sr.start_time DESC
        LIMIT $limit
        """
        
        try:
            results = self.neo4j.execute_query(query, params)
            return [r['run'] for r in results]
        
        except Neo4jError as e:
            logger.error(f"Error fetching simulation runs: {e}")
            raise
    
    def get_simulation_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed simulation run information
        
        Args:
            run_id: SimulationRun ID
        
        Returns:
            Simulation run details or None
        """
        query = """
        MATCH (sr:SimulationRun {id: $run_id})
        OPTIONAL MATCH (d:SimulationDossier)-[:HAS_SIMULATION_RUN]->(sr)
        OPTIONAL MATCH (sr)-[:GENERATED]->(a:SimulationArtifact)
        WITH sr, d,
             COLLECT({
                 id: a.id,
                 name: a.name,
                 type: a.type,
                 status: a.status,
                 size: a.size
             }) AS artifacts
        RETURN {
            id: sr.id,
            sim_type: sr.sim_type,
            start_time: sr.start_time,
            end_time: sr.end_time,
            timestamp: sr.timestamp,
            status: sr.status,
            solver_version: sr.solver_version,
            credibility_level: sr.credibility_level,
            mesh_elements: sr.mesh_elements,
            convergence_tolerance: sr.convergence_tolerance,
            cpu_hours: sr.cpu_hours,
            dossier_id: d.id,
            dossier_name: d.name,
            generated_artifacts: artifacts,
            ap_level: sr.ap_level,
            ap_schema: sr.ap_schema
        } AS run
        """
        
        try:
            results = self.neo4j.execute_query(query, {'run_id': run_id})
            if not results:
                return None
            return results[0]['run']
        
        except Neo4jError as e:
            logger.error(f"Error fetching simulation run {run_id}: {e}")
            raise
    
    def create_simulation_run(self, run_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new simulation run
        
        Args:
            run_data: Dictionary containing run properties
                Required: id, sim_type, timestamp
                Optional: solver_version, credibility_level, etc.
        
        Returns:
            Created simulation run
        """
        query = """
        CREATE (sr:SimulationRun {
            id: $id,
            sim_type: $sim_type,
            timestamp: $timestamp,
            start_time: $start_time,
            status: COALESCE($status, 'Running'),
            end_time: $end_time,
            cpu_hours: $cpu_hours,
            solver_version: $solver_version,
            credibility_level: COALESCE($credibility_level, 'PC2'),
            mesh_elements: $mesh_elements,
            convergence_tolerance: $convergence_tolerance,
            ap_level: 'AP243',
            ap_schema: 'AP243',
            created_at: datetime()
        })
        WITH sr
        OPTIONAL MATCH (d:SimulationDossier {id: $dossier_id})
        FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
            MERGE (d)-[:HAS_SIMULATION_RUN]->(sr)
        )
        RETURN {
            id: sr.id,
            sim_type: sr.sim_type,
            status: sr.status,
            timestamp: sr.timestamp
        } AS run
        """
        
        params = {
            'id': run_data['id'],
            'sim_type': run_data['sim_type'],
            'timestamp': run_data['timestamp'],
            'start_time': run_data.get('start_time', run_data['timestamp']),
            'end_time': run_data.get('end_time'),
            'status': run_data.get('status'),
            'cpu_hours': run_data.get('cpu_hours'),
            'solver_version': run_data.get('solver_version'),
            'credibility_level': run_data.get('credibility_level'),
            'mesh_elements': run_data.get('mesh_elements'),
            'convergence_tolerance': run_data.get('convergence_tolerance'),
            'dossier_id': run_data.get('dossier_id')
        }
        
        try:
            results = self.neo4j.execute_query(query, params)
            if not results:
                return None
            return results[0]['run']
        
        except Neo4jError as e:
            logger.error(f"Error creating simulation run: {e}")
            raise