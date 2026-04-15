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
