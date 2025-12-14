/**
 * Neo4j Client for MBSE Knowledge Graph
 * Provides typed query methods for accessing UML/SysML model data
 */

import neo4j, { Driver, Session, Result, SessionMode } from 'neo4j-driver';

export interface Neo4jConfig {
  uri: string;
  user: string;
  password: string;
}

export interface Class {
  id: string;
  name: string;
  comment?: string;
  visibility?: string;
  isAbstract?: boolean;
}

export interface Package {
  id: string;
  name: string;
  comment?: string;
  child_count?: number;
}

export interface Property {
  id: string;
  name: string;
  type?: string;
  multiplicity?: string;
  visibility?: string;
  owner?: string;
}

export interface Association {
  id: string;
  name: string;
  display_name?: string;
  member_ends?: string;
  end_types?: string;
}

export interface Relationship {
  type: string;
  from: string;
  to: string;
  properties?: Record<string, any>;
}

export class Neo4jClient {
  private driver: Driver;

  constructor(config: Neo4jConfig) {
    this.driver = neo4j.driver(
      config.uri,
      neo4j.auth.basic(config.user, config.password)
    );
  }

  async connect(): Promise<void> {
    try {
      await this.driver.verifyConnectivity();
      console.log('✅ Connected to Neo4j');
    } catch (error) {
      console.error('❌ Failed to connect to Neo4j:', error);
      throw error;
    }
  }

  async close(): Promise<void> {
    await this.driver.close();
  }

  private async executeQuery<T = any>(
    query: string,
    params: Record<string, any> = {},
    accessMode: SessionMode = neo4j.session.READ
  ): Promise<T[]> {
    const session: Session = this.driver.session({ defaultAccessMode: accessMode });
    try {
      const result = await session.run(query, params);
      return result.records.map((record: any) => record.toObject() as T);
    } finally {
      await session.close();
    }
  }

  // ==================== Statistics ====================

  async getStatistics(): Promise<{
    totalNodes: number;
    totalRelationships: number;
    nodesByType: Array<{ label: string; count: number }>;
    relationshipsByType: Array<{ type: string; count: number }>;
  }> {
    const nodeQuery = `
      MATCH (n)
      RETURN labels(n)[0] AS label, count(n) AS count
      ORDER BY count DESC
    `;
    
    const relQuery = `
      MATCH ()-[r]->()
      RETURN type(r) AS type, count(r) AS count
      ORDER BY count DESC
    `;

    const [nodes, rels] = await Promise.all([
      this.executeQuery(nodeQuery, {}, neo4j.session.READ),
      this.executeQuery(relQuery, {}, neo4j.session.READ)
    ]);

    return {
      totalNodes: nodes.reduce((sum: number, n: any) => sum + n.count, 0),
      totalRelationships: rels.reduce((sum: number, r: any) => sum + r.count, 0),
      nodesByType: nodes,
      relationshipsByType: rels
    };
  }

  // ==================== Packages ====================

  async getPackages(search?: string, limit: number = 100): Promise<Package[]> {
    const query = `
      MATCH (p:Package)
      ${search ? 'WHERE p.name CONTAINS $search' : ''}
      OPTIONAL MATCH (p)-[:CONTAINS]->(child)
      RETURN p.id AS id,
             p.name AS name,
             p.comment AS comment,
             count(child) AS child_count
      ORDER BY p.name
      LIMIT $limit
    `;
    return this.executeQuery<Package>(query, { search, limit }, neo4j.session.READ);
  }

  async getPackageById(id: string): Promise<any> {
    const query = `
      MATCH (p:Package {id: $id})
      OPTIONAL MATCH (p)-[:CONTAINS]->(child)
      RETURN p,
             collect(DISTINCT {
               id: child.id,
               name: child.name,
               type: labels(child)[0]
             }) AS contents
    `;
    const result = await this.executeQuery(query, { id }, neo4j.session.READ);
    return result[0] || null;
  }

  async getPackageContents(id: string): Promise<any[]> {
    const query = `
      MATCH (p:Package {id: $id})-[:CONTAINS]->(child)
      RETURN child.id AS id,
             child.name AS name,
             labels(child)[0] AS type,
             child.comment AS comment
      ORDER BY type, child.name
    `;
    return this.executeQuery(query, { id }, neo4j.session.READ);
  }

  // ==================== Classes ====================

  async getClasses(search?: string, packageId?: string, limit: number = 100): Promise<Class[]> {
    let query = `MATCH (c:Class)`;
    
    if (packageId) {
      query += ` MATCH (p:Package {id: $packageId})-[:CONTAINS]->(c)`;
    }
    
    if (search) {
      query += ` WHERE c.name CONTAINS $search`;
    }
    
    query += `
      RETURN c.id AS id,
             c.name AS name,
             c.comment AS comment,
             c.visibility AS visibility,
             c.isAbstract AS isAbstract
      ORDER BY c.name
      LIMIT $limit
    `;
    
    return this.executeQuery<Class>(query, { search, packageId, limit }, neo4j.session.READ);
  }

  async getClassById(id: string): Promise<any> {
    const query = `
      MATCH (c:Class {id: $id})
      OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
      OPTIONAL MATCH (c)-[:GENERALIZES]->(parent:Class)
      OPTIONAL MATCH (child:Class)-[:GENERALIZES]->(c)
      OPTIONAL MATCH (c)-[a:ASSOCIATION]-(other:Class)
      RETURN c,
             collect(DISTINCT p) AS properties,
             collect(DISTINCT parent) AS parents,
             collect(DISTINCT child) AS children,
             collect(DISTINCT {
               type: type(a),
               target: other.name,
               targetId: other.id
             }) AS associations
    `;
    const result = await this.executeQuery(query, { id }, neo4j.session.READ);
    return result[0] || null;
  }

  async getClassHierarchy(id: string): Promise<any> {
    const query = `
      MATCH path = (c:Class {id: $id})-[:GENERALIZES*0..]->(ancestor:Class)
      RETURN ancestor.id AS id,
             ancestor.name AS name,
             length(path) AS depth
      ORDER BY depth
    `;
    return this.executeQuery(query, { id }, neo4j.session.READ);
  }

  // ==================== Properties ====================

  async getProperties(ownerId?: string, search?: string, limit: number = 100): Promise<Property[]> {
    let query = `MATCH (p:Property)`;
    
    if (ownerId) {
      query += ` MATCH (owner {id: $ownerId})-[:HAS_ATTRIBUTE]->(p)`;
    }
    
    if (search) {
      query += ` WHERE p.name CONTAINS $search`;
    }
    
    query += `
      RETURN p.id AS id,
             p.name AS name,
             p.type AS type,
             p.multiplicity AS multiplicity,
             p.visibility AS visibility
      ORDER BY p.name
      LIMIT $limit
    `;
    
    return this.executeQuery<Property>(query, { ownerId, search, limit }, neo4j.session.READ);
  }

  // ==================== Associations ====================

  async getAssociations(limit: number = 100): Promise<Association[]> {
    const query = `
      MATCH (a:Association)
      RETURN a.id AS id,
             a.name AS name,
             a.display_name AS display_name,
             a.member_ends AS member_ends,
             a.end_types AS end_types
      ORDER BY a.display_name
      LIMIT $limit
    `;
    return this.executeQuery<Association>(query, { limit });
  }

  // ==================== Search ====================

  async search(query: string, types?: string[], limit: number = 50): Promise<any[]> {
    let cypherQuery = `MATCH (n)`;
    
    if (types && types.length > 0) {
      const labels = types.map(t => `n:${t}`).join(' OR ');
      cypherQuery += ` WHERE (${labels}) AND n.name CONTAINS $query`;
    } else {
      cypherQuery += ` WHERE n.name CONTAINS $query`;
    }
    
    cypherQuery += `
      RETURN n.id AS id,
             n.name AS name,
             labels(n)[0] AS type,
             n.comment AS comment
      ORDER BY n.name
      LIMIT $limit
    `;
    
    return this.executeQuery(cypherQuery, { query, limit });
  }

  // ==================== Relationships ====================

  async getRelationships(nodeId: string): Promise<Relationship[]> {
    const query = `
      MATCH (n {id: $nodeId})-[r]-(other)
      RETURN type(r) AS type,
             n.id AS from,
             other.id AS to,
             other.name AS toName,
             labels(other)[0] AS toType,
             properties(r) AS properties
      LIMIT 100
    `;
    return this.executeQuery<Relationship>(query, { nodeId });
  }

  // ==================== Graph Visualization ====================

  async getSubgraph(nodeId: string, depth: number = 2): Promise<any> {
    const query = `
      MATCH path = (n {id: $nodeId})-[*0..${depth}]-(connected)
      WITH nodes(path) AS nodes, relationships(path) AS rels
      UNWIND nodes AS node
      WITH collect(DISTINCT {
        id: node.id,
        name: node.name,
        type: labels(node)[0]
      }) AS nodes, rels
      UNWIND rels AS rel
      RETURN nodes,
             collect(DISTINCT {
               type: type(rel),
               from: startNode(rel).id,
               to: endNode(rel).id
             }) AS relationships
    `;
    const result = await this.executeQuery(query, { nodeId, depth });
    return result[0] || { nodes: [], relationships: [] };
  }

  // ==================== Custom Cypher ====================

  async executeCypher(cypher: string, params: Record<string, any> = {}): Promise<any[]> {
    return this.executeQuery(cypher, params);
  }
}
