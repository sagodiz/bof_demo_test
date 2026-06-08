from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import psycopg2
import subprocess
import os
import uuid
import bcrypt
from pathlib import Path
import mimetypes

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Everything before 'yield' runs on STARTUP ---
    flag_content = os.getenv('FLAG')

    if flag_content:
        try:
            # Note: Ensure the container has permissions for /etc/
            with open('/etc/flag', 'w') as f:
                f.write(flag_content)
            print("Successfully initialized /etc/flag")
        except Exception as e:
            print(f"Startup Error writing flag: {e}")
    else:
        print("Warning: FLAG environment variable not found at startup.")

    yield
    # --- Everything after 'yield' runs on SHUTDOWN ---
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "bofdb"),
    "user": os.getenv("DB_USER", "bofuser"),
    "password": os.getenv("DB_PASSWORD", "bofpass"),
}


#origins = [
#    "http://localhost:3001",  # your frontend
#    "http://127.0.0.1:3001",
#    "http://sz-docker.inf.u-szeged.hu:3001",
#    "http://sz-docker:3001"
#]

app.add_middleware(
    CORSMiddleware,
 #   allow_origins=origins,  # allow specific origins
    allow_credentials=True,
    allow_methods=["*"],    # allow all HTTP methods
    allow_headers=["*"],    # allow all headers
)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


@app.post("/register")
def register(name: str = Form(...), pwd: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    hashed_pwd = hash_password( pwd )

    try:
        cur.execute(
            "INSERT INTO users (name, pwd, freetier) VALUES (%s, %s, TRUE)",
            (name, hashed_pwd),
        )
        conn.commit()
        return {"user": name}

    except Exception as e:
        conn.rollback()
        return {"error": "user already exists"}

    finally:
        cur.close()
        conn.close()


@app.post("/login")
def login(name: str = Form(...), pwd: str = Form(...)):



    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT pwd FROM users WHERE name = %s",
        (name,),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row and verify_password(pwd, row[0]):
        return {"user": name}

    return {"error": "invalid credentials"}


@app.post("/perform/{user_name}")
async def perform(user_name: str, file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    input_path = f"/tmp/{uuid.uuid4().hex}_{file.filename}"

    ext = Path(file.filename).suffix.lower()
    output_path = f"/tmp/{uuid.uuid4().hex}{ext}"

    # Save uploaded file
    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())
    except:
        pass # TODO: handle later.

    # Call binary: it should WRITE to output_path
    result = subprocess.run(
        f"./vuln_app {user_name} {input_path} {output_path}",
        shell=True,
        capture_output=True,
        timeout=10,
    )

    if result.returncode != 0 or not os.path.exists(output_path):
        return {"error": f"processing failed: {result.stderr}"}


    background_tasks.add_task(os.remove, output_path)
    return FileResponse(
        output_path,
        filename=f"result.{ext}",   # what user downloads
        media_type=mimetypes.guess_type(output_path)[0] or "application/octet-stream"
    )
