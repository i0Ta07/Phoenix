import psycopg,os,uuid
from psycopg.rows import dict_row

def get_conn():
    try:
        conn = psycopg.connect(
            os.getenv("DB_URL"),
            autocommit=True
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

def init_schema():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Users Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)

                # Initialize Local User
                cur.execute("""
                    INSERT INTO users (id,email)
                    VALUES (
                        '00000000-0000-0000-0000-000000000001',
                        'bot@phoenix.app'
                    )
                    ON CONFLICT (id) DO NOTHING;
                """)
                # Thread table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS threads (
                            thread_id UUID PRIMARY KEY,
                            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            thread_name TEXT NOT NULL,
                            file_name TEXT,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                """)
                # Threads User index
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
                """)
    except Exception as e:
        raise RuntimeError(f"Runtime Error on creating schema; Error: {e}") from e 

def create_thread(thread_id:uuid.UUID, thread_name: str, user_id : uuid.UUID ):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO threads (thread_id, user_id, thread_name) VALUES (%s,%s,%s)",
                    (thread_id, user_id, thread_name)
                )
    except Exception as e:
        raise RuntimeError(f"Runtime Error on creating thread; Error: {e}") from e 

def update_file_name(file_name:str, thread_id:uuid.UUID,user_id:uuid.UUID):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE threads SET file_name = %s WHERE thread_id = %s AND user_id = %s",(file_name,thread_id,user_id))

    except Exception as e:
        raise RuntimeError(f"Runtime Error on updating filename; Error: {e}") from e

def get_threads(user_id:uuid.UUID): # either user_id =  (UUID obj or None) and default = None for Optional usecases 
    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT thread_id, thread_name,file_name FROM threads WHERE user_id = %s ORDER BY created_at DESC",(user_id,))
                return cur.fetchall()

    except Exception as e:
        raise RuntimeError(f"Cannot fetch threads for the current user; Error: {e}") from e
    
