# CampusTrace

CampusTrace is an institutional health monitoring, contact tracing, and outbreak prevention system built with Flask (Python), MySQL, and React (Vite).

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** & `npm`
- **MySQL Server** (running locally on port `3306`)

---

## 1. Database Setup

Create the MySQL database:
```sql
CREATE DATABASE campustrace;
```

Import the initial schema:
```bash
mysql -u root -p campustrace < database/schema.sql
```

---

## 2. Backend Setup & Execution

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install flask flask-sqlalchemy flask-jwt-extended flask-cors flask-bcrypt pymysql requests pytest
   ```

4. Set environment variables (if your MySQL username/password differs from `root:password`):
   ```bash
   # Windows PowerShell:
   $env:DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/campustrace"
   
   # Linux/macOS:
   export DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/campustrace"
   ```

5. Run the Flask API server:
   ```bash
   python -m flask --app app run --port 5000
   ```
   The backend API will start at `http://localhost:5000/api`.

---

## 3. Seed Development Data (Optional)

With the Flask backend running on `http://localhost:5000/api`, open a new terminal and run:

```bash
python scripts/dev_populate.py --base-url http://localhost:5000/api
```

This populates the local database with:
- **Bootstrap Institute Admin**: `admin@campustrace.edu` (Password: `AdminPassword123!`)
- **Division**: Second Year CS-C
- **Rooms**: Lab 101, LH 201
- **Courses & Batches**: Data Structures (`CS201`), DSA Lab (`CS202L`), Maths Tutorial (`CS203T`)
- **Timetable Slots**: Mon–Fri lecture & lab schedule
- **Faculty Accounts**: `turing@campustrace.edu` & `hopper@campustrace.edu` (Password: `FacultyPass123!`)
- **Student Accounts**: `alice@campustrace.edu`, `bob@campustrace.edu` (Password: `StudentPass123!`)

---

## 4. Frontend Setup & Execution

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite React development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5173
   ```

---

## 5. Running Tests & Validation

- **Run Backend Test Suite** (141 tests):
  ```bash
  cd backend
  pytest app/tests/ -v
  ```

- **Run Frontend Test Suite** (Vitest):
  ```bash
  cd frontend
  npm test
  ```

- **Production Frontend Build**:
  ```bash
  cd frontend
  npx vite build
  ```