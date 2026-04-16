import psycopg2

#xLY4X84kwfq9hLjK
'''
def get_connection():
    conn = psycopg2.connect(
        host="db.ugrukquepbotedvxklfh.supabase.co",
        database="postgres",
        user="postgres",
        password="xLY4X84kwfq9hLjK",
        port="5432"
    )
    return conn
'''

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="blogs_DB",
        user="postgres",
        password="vignasri",
        port="5432"
    )

# ── The Context Manager Class ──
class DBConnection:
    def __enter__(self):
        # Automatically opens the connection using your existing details
        self.conn = get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Automatically commits or rolls back, and ALWAYS closes the connection safely
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()