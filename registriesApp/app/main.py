from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from . import models, schemas, database, service

# Initialize DB tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Zakup Registry Aggregator")

@app.post("/sync-registries", response_model=schemas.SyncStatus)
async def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    """
    Triggers a background task to scrape all 4 APIs and populate the local database.
    """
    background_tasks.add_task(service.sync_all_registries, db)
    return {"message": "Sync started in background", "status": "processing"}

@app.get("/persons", response_model=List[schemas.RegistryEntryResponse])
def search_persons(
    full_name: str = Query(..., description="Full Name in format: LastName FirstName MiddleName"),
    db: Session = Depends(database.get_db)
):
    """
    Accepts full name and responds with records from all registries with the same full name.
    Strictly matches: lastName + ' ' + firstName + ' ' + middleName
    """
    # Sanitize input
    search_term = full_name.strip()
    
    # We construct the query to concat DB columns and compare with input
    # Note: Qualified and Software registries might not appear here if they lack
    # structured first/last/middle name fields in their source JSON.
    
    query = text("""
        SELECT * FROM registry_entries 
        WHERE CONCAT(last_name, ' ', first_name, ' ', middle_name) = :name
        OR general_name = :name
    """)
    
    results = db.execute(query, {"name": search_term}).fetchall()
    
    return results

@app.get("/stats")
def get_stats(db: Session = Depends(database.get_db)):
    """Helper to see how many records we have"""
    count = db.query(models.RegistryEntry).count()
    return {"total_records": count}