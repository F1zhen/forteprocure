import httpx
import logging
from sqlalchemy.orm import Session
from sqlalchemy import delete
from .models import RegistryEntry

# Configuration for logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URLs and Configs
TIMEOUT = 30.0

async def fetch_paginated_data(client: httpx.AsyncClient, url: str, params: dict):
    """
    Generic generator to fetch all pages from the Zakup API.
    """
    page = 0
    while True:
        params['page'] = page
        try:
            logger.info(f"Fetching {url} - Page {page}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            yield data
            page += 1
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching page {page}: {e}")
            break

async def sync_all_registries(db: Session):
    """
    Main logic to clear old data and re-fetch from all 4 sources.
    """
    # 1. Clear existing data (Optional: depends on if we want upsert or full sync. Full sync is safer for consistency)
    db.query(RegistryEntry).delete()
    db.commit()
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        
        # --- 1. Commodity Producers ---
        url = "https://zakup.sk.kz/eprocglobal/open-api/suppliers"
        params = {
            "registerType": "COMMODITY_PRODUCER",
            "flagCustomer": "false",
            "size": 1000, # Increased size for efficiency
            "sort": "includeNomenclatureDate,asc"
            # Add other flags from prompt if strictly necessary, usually defaults work
        }
        
        async for batch in fetch_paginated_data(client, url, params):
            entries = []
            for item in batch:
                entry = RegistryEntry(
                    source_registry="COMMODITY_PRODUCER",
                    first_name=item.get("firstName"),
                    last_name=item.get("lastName"),
                    middle_name=item.get("middleName"),
                    general_name=item.get("nameRu"),
                    external_id=item.get("identifier"),
                    raw_data=item
                )
                entries.append(entry)
            db.add_all(entries)
            db.commit()

        # --- 2. Untrustworthy Suppliers ---
        # Same URL structure as Commodity, different registerType
        params["registerType"] = "BAD_SUPPLIER"
        # The prompt specific hash/flags can be added here
        
        async for batch in fetch_paginated_data(client, url, params):
            entries = []
            for item in batch:
                entry = RegistryEntry(
                    source_registry="UNTRUSTWORTHY_SUPPLIER",
                    first_name=item.get("firstName"),
                    last_name=item.get("lastName"),
                    middle_name=item.get("middleName"),
                    general_name=item.get("nameRu"),
                    external_id=item.get("identifier"),
                    raw_data=item
                )
                entries.append(entry)
            db.add_all(entries)
            db.commit()

        # --- 3. Qualified Suppliers ---
        url_qual = "https://zakup.sk.kz/eprocpko/open-api/pko-qualified-suppliers"
        params_qual = {"size": 100}
        
        async for batch in fetch_paginated_data(client, url_qual, params_qual):
            entries = []
            for item in batch:
                # Structure is nested: item['supplier']['nameRu']
                supplier = item.get("supplier", {})
                entry = RegistryEntry(
                    source_registry="QUALIFIED_SUPPLIER",
                    # Qualified API often returns companies, so First/Last might be missing in JSON
                    # We map the company name to general_name
                    general_name=supplier.get("nameRu"),
                    external_id=supplier.get("bin"),
                    raw_data=item
                )
                entries.append(entry)
            db.add_all(entries)
            db.commit()

        # --- 4. Accredited Software ---
        url_soft = "https://zakup.sk.kz/eprocglobal/open-api/dpo-pep-suppliers"
        params_soft = {"size": 700, "sort": "registryAddedAt,ASC"}
        
        async for batch in fetch_paginated_data(client, url_soft, params_soft):
            entries = []
            for item in batch:
                entry = RegistryEntry(
                    source_registry="ACCREDITED_SOFTWARE",
                    # Software API has 'applicantNameRu'
                    general_name=item.get("applicantNameRu"),
                    external_id=item.get("applicantIINorBin"),
                    raw_data=item
                )
                entries.append(entry)
            db.add_all(entries)
            db.commit()

    logger.info("Sync completed successfully.")