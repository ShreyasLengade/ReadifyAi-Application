from parameter import OpenAI_API_KEY, conn_params
from datetime import datetime, timezone
import psycopg2


def insert_conversation_history(userid, speaker, app_section, book_or_material,
                                chapter_or_page, conversation_content):
    """
    Insert the conversation history into the database.
    """

    # Connect to the database
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    conversation_timestamp = datetime.now(timezone.utc).isoformat()
    # Insert the conversation history
    cur.execute('''
            INSERT INTO chat_conversation_history (userid, speaker, app_section, book_or_material, chapter_or_page, conversation_content, conversation_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (userid, speaker, app_section, book_or_material, chapter_or_page, conversation_content, conversation_timestamp))

    # Commit the transaction
    conn.commit()

    # Close the cursor and connection
    cur.close()
    conn.close()
