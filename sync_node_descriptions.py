import logging
from neo4j_db import Neo4jDBManager
from qdrant_db import QdrantDBManager
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_descriptions():
    # Initialize database managers
    logger.info("Connecting to databases...")
    neo4j_db = Neo4jDBManager(uri="bolt://localhost:7687")
    qdrant_db = QdrantDBManager(location=":localhost:", port=6333)
    
    COLLECTION_NAME = 'test'
    
    # 1. Fetch node IDs, descriptions, and names from Neo4j
    logger.info("Fetching nodes from Neo4j...")
    query = "MATCH (n) RETURN elementId(n) AS id, n.description AS description, n.name AS name"
    try:
        results = neo4j_db.execute_cypher(query)
    except Exception as e:
        logger.error(f"Failed to fetch from Neo4j: {e}")
        return

    node_data = {}
    for record in results:
        node_id = record.get('id')
        description = record.get('description')
        name = record.get('name')
        if node_id:
            node_data[node_id] = {'description': description, 'name': name}
            
    logger.info(f"Found {len(node_data)} nodes in Neo4j.")

    # 2. Update Qdrant payloads
    logger.info("Updating Qdrant payloads...")
    updated_count = 0
    
    # We'll retrieve points from Qdrant by filtering for point_type="node"
    # To do this efficiently, we can use the scroll API
    
    query_filter = Filter(
        must=[
            FieldCondition(
                key="type",
                match=MatchValue(value="node")
            )
        ]
    )
    
    # Track the scroll offset
    offset = None
    
    while True:
        try:
            points, next_offset = qdrant_db.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=query_filter,
                limit=100,
                with_payload=True,
                offset=offset
            )
            
            if not points:
                break
                
            for point in points:
                # Assuming the neo4j node_id is stored in the Qdrant payload under '_id'
                # (as seen in the get_similar_node_function implementation)
                neo4j_id = point.payload.get('_id')
                
                if neo4j_id and neo4j_id in node_data:
                    neo4j_info = node_data[neo4j_id]
                    new_description = neo4j_info['description']
                    new_name = neo4j_info['name']
                    
                    # Only update if the description or name is different/missing
                    needs_update = False
                    payload_update = {}
                    
                    if new_description is not None and point.payload.get('description') != new_description:
                        payload_update['description'] = new_description
                        needs_update = True
                        
                    if new_name is not None and point.payload.get('name') != new_name:
                        payload_update['name'] = new_name
                        needs_update = True
                        
                    if needs_update:
                        qdrant_db.client.set_payload(
                            collection_name=COLLECTION_NAME,
                            payload=payload_update,
                            points=[point.id]
                        )
                        updated_count += 1
                        
            offset = next_offset
            if offset is None:
                break
                
        except Exception as e:
            logger.error(f"Error updating Qdrant: {e}")
            break

    logger.info(f"Sync complete. Updated descriptions for {updated_count} nodes in Qdrant.")
    
    neo4j_db.close()

if __name__ == "__main__":
    sync_descriptions()
