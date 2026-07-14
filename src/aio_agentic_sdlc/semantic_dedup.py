import os
import sqlite3
import sqlite_vec
import glob
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

# Lazy load sentence_transformers to speed up CLI for other commands
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2 is small and fast, output dim = 384
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def get_db(project_path: str) -> sqlite3.Connection:
    db_path = os.path.join(project_path, ".agents", "semantic_cache.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    
    # Initialize schema
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS prd_embeddings USING vec0(
            embedding float[384]
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS prd_metadata (
            rowid INTEGER PRIMARY KEY,
            filepath TEXT UNIQUE,
            last_modified REAL
        )
    """)
    db.commit()
    return db

def sync_documents(project_path: str, db: sqlite3.Connection):
    """Scan inbox/ and archive/ and update embeddings for new/modified .md files."""
    inbox_path = os.path.join(project_path, "inbox", "*.md")
    archive_path = os.path.join(project_path, "archive", "*.md")
    
    files = glob.glob(inbox_path) + glob.glob(archive_path)
    
    cursor = db.cursor()
    # Get existing metadata
    cursor.execute("SELECT rowid, filepath, last_modified FROM prd_metadata")
    existing = {row[1]: {"rowid": row[0], "last_modified": row[2]} for row in cursor.fetchall()}
    
    to_insert = []
    to_update = []
    
    for filepath in files:
        stat = os.stat(filepath)
        mtime = stat.st_mtime
        
        # Check if file needs embedding
        rel_path = os.path.relpath(filepath, project_path)
        if rel_path not in existing:
            to_insert.append((rel_path, filepath, mtime))
        elif mtime > existing[rel_path]["last_modified"]:
            to_update.append((existing[rel_path]["rowid"], rel_path, filepath, mtime))
            
    if not to_insert and not to_update:
        return
        
    model = get_model()
    
    # Process insertions
    for rel_path, filepath, mtime in to_insert:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        embedding = model.encode([content])[0]
        
        # Insert metadata to get rowid
        cursor.execute("INSERT INTO prd_metadata (filepath, last_modified) VALUES (?, ?)", (rel_path, mtime))
        rowid = cursor.lastrowid
        # Insert embedding
        cursor.execute("INSERT INTO prd_embeddings (rowid, embedding) VALUES (?, ?)", (rowid, embedding.tobytes()))
        
    # Process updates
    for rowid, rel_path, filepath, mtime in to_update:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        embedding = model.encode([content])[0]
        
        cursor.execute("UPDATE prd_metadata SET last_modified = ? WHERE rowid = ?", (mtime, rowid))
        # sqlite-vec virtual table update (delete and re-insert is safer for virtual tables)
        cursor.execute("DELETE FROM prd_embeddings WHERE rowid = ?", (rowid,))
        cursor.execute("INSERT INTO prd_embeddings (rowid, embedding) VALUES (?, ?)", (rowid, embedding.tobytes()))
        
    db.commit()

def find_duplicate_prds(proposed_text: str, project_path: str = ".", threshold: float = 0.2) -> List[Dict[str, Any]]:
    """
    Search for similar PRDs.
    Returns a list of matching documents.
    Note: threshold is cosine distance (0 to 2). Smaller is more similar.
    Distance of 0.2 means 0.8 cosine similarity.
    """
    db = get_db(project_path)
    sync_documents(project_path, db)
    
    model = get_model()
    query_embedding = model.encode([proposed_text])[0]
    
    cursor = db.cursor()
    
    # Query sqlite-vec
    cursor.execute("""
        SELECT m.filepath, e.distance
        FROM prd_embeddings e
        JOIN prd_metadata m ON m.rowid = e.rowid
        WHERE e.embedding MATCH ? AND k = 3
        ORDER BY e.distance ASC
    """, (query_embedding.tobytes(),))
    
    results = []
    for row in cursor.fetchall():
        filepath, distance = row
        if distance <= threshold:
            results.append({
                "filepath": filepath,
                "distance": distance,
                "similarity_score": 1.0 - distance
            })
            
    db.close()
    return results
