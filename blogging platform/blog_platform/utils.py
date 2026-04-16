from blog_platform.db import get_connection

def is_premium_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM subscriptions
        WHERE user_id=%s AND end_date >= CURRENT_DATE
    """, (user_id,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None