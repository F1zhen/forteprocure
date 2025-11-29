# How to Run

### 1. Connect the Database:
Add registriesApp/.env file with enviroment variable:

```
DB_CONN=postgresql://[username]:[password]@[address]:5432/[db name]
```
### 2. Install Dependencies: (Ideally in a virtual environment)

```
pip install -r requirements.txt
```
### 3. Run the API:

```
uvicorn app.main:app --reload
```

### Usage Steps:

Step 1: Go to http://127.0.0.1:8000/docs.

Step 2: Call the POST `/sync-registries` endpoint. This will start downloading data from the Kazakhstan procurement APIs in the background. Wait a moment (check logs or the `/stats` endpoint).

Step 3: Use GET `/persons` with a name found in the registry (e.g., КАРШИГИНА АЙГУЛЬ БУЛЕКБАЕВНА).