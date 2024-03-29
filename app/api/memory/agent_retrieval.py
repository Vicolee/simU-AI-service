import psycopg2
from ..models import AgentInfo
from .lru_cache import LRUCache

agent_info_cache = LRUCache(128)
user_info_cache = LRUCache(128)

async def get_agent_info(agentID, isUser, game_db_name, game_db_user, game_db_pass, game_db_url) -> AgentInfo:
    """
    This asynchronous function retrieves information about an agent from a PostgreSQL database.
    
    Parameters:
    agentID (str): The ID of the agent whose information needs to be retrieved.
    isUser (bool): A boolean value indicating whether the agent is a user or not.
    game_db_name (str): The name of the game database.
    game_db_user (str): The username for the game database.
    game_db_pass (str): The password for the game database.
    game_db_url (str): The URL of the game database.
    
    Returns:
    AgentInfo: An instance of the AgentInfo model containing the first name, last name, and description of the agent.
    """
    res = agent_info_cache.get(agentID)
    if res != -1:
        return res
    # Connect to the DB
    results = None
    conn = psycopg2.connect(
        dbname=game_db_name,
        user=game_db_user,
        password=game_db_pass,
        host=game_db_url
        )
    try:
        # Build and execute the query
        cursor = conn.cursor()     
        query = ""
        if isUser:
            query = f"""
            SELECT "Username", "Summary"
            FROM "Users"
            WHERE "Id" = '{agentID}'
            """
        else:
            query = f"""
            SELECT "Username", "Summary"
            FROM "Agents"
            WHERE "Id" = '{agentID}'
            """ 
        # query = f"""
        # SELECT "Username", "Description"
        # FROM {"\"Users\"" if isUser else "\"Agents\""}
        # WHERE "Id" = '{agentID}'
        # """
        cursor.execute(query)
        results = cursor.fetchall()
        if not results:
            print("No results for agent id: ", agentID)
            return None
        else:
            results = results[0]
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print("no success", error)
    finally:
        if cursor:
            cursor.close()
        if results:
            agent_info_cache.put(agentID, AgentInfo(results[0], results[1]))
            return AgentInfo(results[0], results[1])

def update_user_summary(userID, summary): 
    if user_info_cache.get(userID) != -1:
        curr_agent_info = user_info_cache.get(userID)
        user_info_cache.put(userID, AgentInfo(username=curr_agent_info.username, summary=summary))