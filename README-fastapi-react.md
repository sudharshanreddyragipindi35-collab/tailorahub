# TailoraHub FastAPI + React

New separated stack:

- `backend/` - Python FastAPI API, PostgreSQL, email OTP, admin audit logs
- `frontend/` - React role-based app for customers, tailors and admin

The old Node/static files are left untouched, but the new app should be run from these two folders.

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default DB URL in `backend/.env.example`:

```text
postgresql+psycopg://tailorahub:devpassword123@localhost:5432/tailorahub_dev
```

On startup, FastAPI runs `backend/app/schema.sql` and creates/updates only the admin account. It does not insert dummy customers, tailors, orders, payments, reviews or complaints.

Admin credentials:

```text
backend/admin-credentials.txt
```

## Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

`npm run dev` builds and serves the React app locally on port `5173`.

Open:

```text
http://127.0.0.1:5173
```

## Role Logins

The first screen asks for a role:

- Customer: register/login, browse approved tailors, send booking requests, track orders, pay and review.
- Tailor: register/login, wait for admin approval, update availability, accept/reject requests and manage own orders.
- Admin: login with `admin / admin@123`, approve tailors and manage platform data.

Customer and tailor accounts are created from the Register tab. Tailors stay `PENDING_APPROVAL` until admin approves them.

## Email OTP

Customer, tailor and delivery auth uses email OTP. Configure SMTP in `backend/.env`. If SMTP is blank, OTP emails are written to `backend/email-outbox.log`.

## Admin Rights

Admin APIs validate the `admin` role on the backend. Customer/tailor users cannot access admin endpoints by changing URLs. Suspend, block, cancel and delete actions ask for confirmation in the React UI and write audit log records on the backend. Customer/tailor delete is blocked while active orders or pending payments exist.
