# FlicksMix

FlicksMix is a responsive DJ mix download website where users can browse mixes, listen to previews, upload new mixes, register as members, contact the DJ, and access an admin dashboard.

## Features
- Responsive landing page
- Audio preview player for mixes
- Mix upload form
- Download links for uploaded audio files
- Member registration and login
- Admin dashboard for managing mixes
- Contact form for booking requests

## Tech Stack
- Python
- Flask
- SQLite
- HTML/CSS/JavaScript

## Run Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the app:
   ```bash
   python app.py
   ```
3. Open:
   ```text
   http://localhost:8000/
   ```

## Admin Access
- Username: admin
- Password: password123

## Deployment
This app is ready for deployment on platforms such as Render or Railway.
Use the following start command:
```bash
gunicorn app:app
```
