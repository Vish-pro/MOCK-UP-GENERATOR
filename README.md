# One-Click E-Commerce Studio

A "One-Click E-Commerce Studio" app that automates the creation of 4K website assets. It analyzes uploaded product images and generates high-fidelity mockups.

## Features
- **Auto-Analysis**: Detects Garment Type and Dominant Color.
- **Batch Generation**: Creates 12 4K mockups (Humans and Ghost Mannequin views).
- **Download**: Download generated assets individually or all at once.

## Prerequisites
- Python 3.8+
- Node.js 16+
- npm

## Setup & Running

### 1. Backend (FastAPI)

Navigate to the `backend` directory:
```bash
cd backend
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Start the server:
```bash
python main.py
```
The backend will run at `http://localhost:8000`.

### 2. Frontend (React + Vite)

Open a new terminal and navigate to the `frontend` directory:
```bash
cd frontend
```

Install Node dependencies:
```bash
npm install
```

Start the development server:
```bash
npm run dev
```
The frontend will run at `http://localhost:5173`.

## Testing

### Backend Tests
To run the backend unit tests (ensuring API endpoints work correctly):

```bash
# From the root directory
pytest backend/test_main.py
```

## Usage
1. Open the frontend URL (`http://localhost:5173`).
2. Upload a product image (e.g., a T-Shirt).
3. Click "Start Studio Workflow".
4. Wait for the analysis and generation to complete.
5. View the mockups in the gallery and download them.
