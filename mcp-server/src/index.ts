#!/usr/bin/env node

/**
 * MBSE Knowledge Graph MCP Server
 * 
 * Model Context Protocol server that exposes MBSE Neo4j knowledge graph
 * to AI assistants like Claude Desktop.
 * 
 * Capabilities:
 * - Query packages, classes, properties, associations
 * - Search across the model
 * - Navigate relationships and hierarchies
 * - Execute custom Cypher queries
 * - Get graph statistics and visualizations
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { config } from 'dotenv';
import { Neo4jClient } from './neo4j-client.js';

// Load environment variables
config({ path: '../.env' }); // Try parent directory first
config(); // Then current directory

// Initialize Neo4j client
const neo4jClient = new Neo4jClient({
  uri: process.env.NEO4J_URI || '',
  user: process.env.NEO4J_USER || 'neo4j',
  password: process.env.NEO4J_PASSWORD || '',
});

// Define available tools
const TOOLS: Tool[] = [
  {
    name: 'get_statistics',
    description: 'Get overall statistics about the MBSE knowledge graph including node counts, relationship counts, and breakdown by type',
    inputSchema: {
      type: 'object',
      properties: {},
      required: [],
    },
  },
  {
    name: 'list_packages',
    description: 'List all packages in the model with optional search filter. Packages organize the model into logical groupings.',
    inputSchema: {
      type: 'object',
      properties: {
        search: {
          type: 'string',
          description: 'Optional search term to filter packages by name',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 100)',
          default: 100,
        },
      },
      required: [],
    },
  },
  {
    name: 'get_package',
    description: 'Get detailed information about a specific package including its contents',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Unique identifier of the package (e.g., _18_4_1_...)',
        },
      },
      required: ['id'],
    },
  },
  {
    name: 'list_classes',
    description: 'List all classes (system components) with optional filters. Classes represent the core building blocks of the system.',
    inputSchema: {
      type: 'object',
      properties: {
        search: {
          type: 'string',
          description: 'Optional search term to filter classes by name',
        },
        packageId: {
          type: 'string',
          description: 'Optional package ID to filter classes within a specific package',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 100)',
          default: 100,
        },
      },
      required: [],
    },
  },
  {
    name: 'get_class',
    description: 'Get detailed information about a specific class including properties, parent classes, child classes, and associations',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Unique identifier of the class',
        },
      },
      required: ['id'],
    },
  },
  {
    name: 'get_class_hierarchy',
    description: 'Get the inheritance hierarchy for a class, showing all ancestor classes',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Unique identifier of the class',
        },
      },
      required: ['id'],
    },
  },
  {
    name: 'list_properties',
    description: 'List properties (attributes) with optional filters. Properties define the characteristics of classes.',
    inputSchema: {
      type: 'object',
      properties: {
        ownerId: {
          type: 'string',
          description: 'Optional owner ID to get properties of a specific class',
        },
        search: {
          type: 'string',
          description: 'Optional search term to filter properties by name',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 100)',
          default: 100,
        },
      },
      required: [],
    },
  },
  {
    name: 'list_associations',
    description: 'List all associations (relationships between classes) in the model',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 100)',
          default: 100,
        },
      },
      required: [],
    },
  },
  {
    name: 'search_model',
    description: 'Search across the entire model by name with optional type filters',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search term to find in node names',
        },
        types: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['Class', 'Package', 'Property', 'Association', 'Constraint', 'Port'],
          },
          description: 'Optional array of node types to filter by',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50)',
          default: 50,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_relationships',
    description: 'Get all relationships (connections) for a specific node',
    inputSchema: {
      type: 'object',
      properties: {
        nodeId: {
          type: 'string',
          description: 'Unique identifier of the node',
        },
      },
      required: ['nodeId'],
    },
  },
  {
    name: 'get_subgraph',
    description: 'Get a subgraph centered on a specific node, including connected nodes up to a specified depth',
    inputSchema: {
      type: 'object',
      properties: {
        nodeId: {
          type: 'string',
          description: 'Unique identifier of the central node',
        },
        depth: {
          type: 'number',
          description: 'How many relationship hops to include (default: 2)',
          default: 2,
        },
      },
      required: ['nodeId'],
    },
  },
  {
    name: 'execute_cypher',
    description: 'Execute a custom Cypher query against the Neo4j database. Use for advanced queries not covered by other tools.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Cypher query to execute',
        },
        params: {
          type: 'object',
          description: 'Optional parameters for the query',
          additionalProperties: true,
        },
      },
      required: ['query'],
    },
  },
];

// Create MCP server
const server = new Server(
  {
    name: process.env.MCP_SERVER_NAME || 'mbse-knowledge-graph',
    version: process.env.MCP_SERVER_VERSION || '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS,
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'get_statistics': {
        const stats = await neo4jClient.getStatistics();
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(stats, null, 2),
            },
          ],
        };
      }

      case 'list_packages': {
        const packages = await neo4jClient.getPackages(
          args?.search as string,
          (args?.limit as number) || 100
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(packages, null, 2),
            },
          ],
        };
      }

      case 'get_package': {
        if (!args?.id) {
          throw new Error('Package ID is required');
        }
        const pkg = await neo4jClient.getPackageById(args.id as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(pkg, null, 2),
            },
          ],
        };
      }

      case 'list_classes': {
        const classes = await neo4jClient.getClasses(
          args?.search as string,
          args?.packageId as string,
          (args?.limit as number) || 100
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(classes, null, 2),
            },
          ],
        };
      }

      case 'get_class': {
        if (!args?.id) {
          throw new Error('Class ID is required');
        }
        const cls = await neo4jClient.getClassById(args.id as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(cls, null, 2),
            },
          ],
        };
      }

      case 'get_class_hierarchy': {
        if (!args?.id) {
          throw new Error('Class ID is required');
        }
        const hierarchy = await neo4jClient.getClassHierarchy(args.id as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(hierarchy, null, 2),
            },
          ],
        };
      }

      case 'list_properties': {
        const properties = await neo4jClient.getProperties(
          args?.ownerId as string,
          args?.search as string,
          (args?.limit as number) || 100
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(properties, null, 2),
            },
          ],
        };
      }

      case 'list_associations': {
        const associations = await neo4jClient.getAssociations(
          (args?.limit as number) || 100
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(associations, null, 2),
            },
          ],
        };
      }

      case 'search_model': {
        if (!args?.query) {
          throw new Error('Search query is required');
        }
        const results = await neo4jClient.search(
          args.query as string,
          args?.types as string[],
          (args?.limit as number) || 50
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(results, null, 2),
            },
          ],
        };
      }

      case 'get_relationships': {
        if (!args?.nodeId) {
          throw new Error('Node ID is required');
        }
        const relationships = await neo4jClient.getRelationships(args.nodeId as string);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(relationships, null, 2),
            },
          ],
        };
      }

      case 'get_subgraph': {
        if (!args?.nodeId) {
          throw new Error('Node ID is required');
        }
        const subgraph = await neo4jClient.getSubgraph(
          args.nodeId as string,
          (args?.depth as number) || 2
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(subgraph, null, 2),
            },
          ],
        };
      }

      case 'execute_cypher': {
        if (!args?.query) {
          throw new Error('Cypher query is required');
        }

        const query = String(args.query);
        const allowWrite = String(process.env.MCP_ALLOW_WRITE_CYPHER || '').toLowerCase() === 'true';

        // Default-safe posture: block write / privileged operations.
        // MCP servers are commonly used from desktop assistants; treat them as high-trust but not unlimited.
        const upper = query.toUpperCase();
        const blockedPatterns: RegExp[] = [
          /\bCREATE\b/, /\bMERGE\b/, /\bSET\b/, /\bDELETE\b/, /\bDETACH\b/, /\bREMOVE\b/, /\bDROP\b/, /\bFOREACH\b/,
          /\bLOAD\s+CSV\b/, /\bCALL\s+DBMS\b/, /\bCALL\s+APOC\b/, /\bAPOC\b/, /\bDBMS\b/
        ];

        if (!allowWrite && blockedPatterns.some((re) => re.test(upper))) {
          throw new Error(
            'Refusing to execute potentially mutating/privileged Cypher. Set MCP_ALLOW_WRITE_CYPHER=true to override.'
          );
        }

        const results = await neo4jClient.executeCypher(
          query,
          (args?.params as Record<string, any>) || {}
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(results, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  try {
    // Connect to Neo4j
    await neo4jClient.connect();

    // Create transport
    const transport = new StdioServerTransport();
    
    // Connect server to transport
    await server.connect(transport);

    console.error('🚀 MBSE MCP Server running on stdio');
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Handle shutdown
process.on('SIGINT', async () => {
  console.error('\n⏸️  Shutting down...');
  await neo4jClient.close();
  process.exit(0);
});

main();
