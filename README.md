# IRONHUB Sivagangai

Python Flask website for **IRONHUB**, a gym in Sivagangai, Tamil Nadu.

## Run locally

```powershell
cd C:\Users\yoghan\ironhub-sivagangai
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Membership enquiries from `/contact` are stored in `ironhub.db` (SQLite).

## Admin CMS

Open [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login).

Default local login:

- Username: `admin`
- Password: `ironhub-admin`

Change these with environment variables before going live:

- `IRONHUB_ADMIN_USER`
- `IRONHUB_ADMIN_PASSWORD`
- `IRONHUB_SECRET_KEY`

If the admin user was already created, updating the password env var will not rewrite the stored hash. Delete the `admins` row in SQLite or recreate `ironhub.db` after changing credentials.

The CMS lets you edit contact details, hours, plan prices, and review Join-form enquiries. It is not linked from the public navigation.
