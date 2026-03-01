from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase

class Neo4jDBManager:
    """
    A class to manage a Neo4j database with basic CRUD operations.
    """
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        """
        Initializes the Neo4j DB Manager.
        
        Args:
            uri (str): The URI for the Neo4j instance.
            user (str): The username for authentication.
            password (str): The password for authentication.
        """
        # Connect to the Neo4j instance
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """
        Close the Neo4j driver connection.
        """
        if self.driver:
            self.driver.close()

    def create_node(self, label: str, properties: Dict[str, Any]) -> int:
        """
        Create a new node with a specific label and properties.
        
        Args:
            label (str): The label for the node (e.g., 'Person').
            properties (Dict[str, Any]): The properties for the node.

        Returns:
            int: The Neo4j internal ID of the created node.
        """
        query = (
            f"MERGE (n:{label} {{name: $name, description: $description}}) "
            "SET n += $properties "
            "RETURN elementId(n) AS node_id"
        )
        
        def _execute_create(tx):
            result = tx.run(query, properties=properties, name=properties['name'], description=properties['description'])
            record = result.single()
            return record["node_id"] if record else None

        with self.driver.session() as session:
            node_id = session.execute_write(_execute_create)
            return node_id

    def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        """
        Read / Retrieve a specific node by its Neo4j internal ID.
        
        Args:
            node_id (int): The Neo4j internal ID of the node.

        Returns:
            Optional[Dict[str, Any]]: The node properties if found, else None.
        """
        query = (
            "MATCH (n) "
            "WHERE elementId(n) = $node_id "
            "RETURN properties(n) AS properties"
        )

        def _execute_get(tx):
            result = tx.run(query, node_id=node_id)
            record = result.single()
            return record["properties"] if record else None

        with self.driver.session() as session:
            return session.execute_read(_execute_get)

    def search_nodes(self, label: str, property_key: str, property_value: Any) -> List[Dict[str, Any]]:
        """
        Read / Search for nodes by a specific label and property match.
        
        Args:
            label (str): The label of the nodes to find.
            property_key (str): The property key to match.
            property_value (Any): The property value to match.

        Returns:
            List[Dict[str, Any]]: A list of node properties that match the criteria.
        """
        query = (
            f"MATCH (n:{label} {{{property_key}: $property_value}}) "
            "RETURN properties(n) AS properties, elementId(n) as node_id"
        )

        def _execute_search(tx):
            result = tx.run(query, property_value=property_value)
            return [{"id": record["node_id"], **record["properties"]} for record in result]

        with self.driver.session() as session:
            return session.execute_read(_execute_search)

    def update_node_properties(self, node_id: int, properties: Dict[str, Any]) -> bool:
        """
        Update properties of an existing node by its internal ID.
        
        Args:
            node_id (int): The Neo4j internal ID of the node.
            properties (Dict[str, Any]): The new properties to set / update.

        Returns:
            bool: True if the node was found and updated, False otherwise.
        """
        query = (
            "MATCH (n) "
            "WHERE elementId(n) = $node_id "
            "SET n += $properties "
            "RETURN elementId(n) AS node_id"
        )

        def _execute_update(tx):
            result = tx.run(query, node_id=node_id, properties=properties)
            return result.single() is not None

        with self.driver.session() as session:
            return session.execute_write(_execute_update)

    def delete_node(self, node_id: int, detach: bool = True) -> bool:
        """
        Delete a specific node by its internal ID.
        
        Args:
            node_id (int): The Neo4j internal ID of the node.
            detach (bool): If True, also delete all relationships connected to the node (DETACH DELETE).

        Returns:
            bool: True if the node was found and deleted, False otherwise.
        """
        delete_clause = "DETACH DELETE n" if detach else "DELETE n"
        query = (
            "MATCH (n) "
            "WHERE elementId(n) = $node_id "
            f"{delete_clause} "
            "RETURN COUNT(n) as deleted_count"
        )

        def _execute_delete(tx):
            result = tx.run(query, node_id=node_id)
            record = result.single()
            return record and record["deleted_count"] > 0

        with self.driver.session() as session:
            return session.execute_write(_execute_delete)

    def create_relationship(self, start_node_id: int, end_node_id: int, rel_type: str, properties: Dict[str, Any] = None) -> bool:
        """
        Create a directed relationship between two existing nodes.
        
        Args:
            start_node_id (int): Internal ID of the starting node.
            end_node_id (int): Internal ID of the ending node.
            rel_type (str): The type of the relationship (e.g., 'KNOWS').
            properties (Dict[str, Any], optional): Properties for the relationship.

        Returns:
            bool: True if the relationship was successfully created.
        """
        properties = properties or {}
        query = (
            "MATCH (a), (b) "
            "WHERE elementId(a) = $start_node_id AND elementId(b) = $end_node_id "
            f"MERGE (a)-[r:`{rel_type}`]->(b) "
            "SET r += $properties "
            "RETURN type(r) AS rel_type"
        )

        def _execute_rel_create(tx):
            result = tx.run(query, start_node_id=start_node_id, end_node_id=end_node_id, properties=properties)
            return result.single() is not None

        with self.driver.session() as session:
            return session.execute_write(_execute_rel_create)
