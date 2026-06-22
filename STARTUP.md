# Manual Startup (if start.ps1 fails)

## Backend (Terminal 1)
cd backend
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m uvicorn main:app --reload --port 8000

## Frontend (Terminal 2)
cd frontend
npm install
npm run dev

Then open http://localhost:5173
