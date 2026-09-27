Government Scheme RAG Chatbot - Admin Upload + Public User Chat

Public page:
- Users can only ask questions.
- No document upload is shown.

Admin page:
- Open /admin
- Login with ADMIN_PASSWORD
- Upload official government scheme PDF/TXT files.
- Rebuild the FAISS knowledge base.
- Logout.

Setup:
1. python -m venv venv
2. .\venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. Copy .env.example to .env
5. Add GOOGLE_API_KEY, ADMIN_PASSWORD and FLASK_SECRET_KEY.
6. python app.py
7. Public: http://127.0.0.1:5000/
8. Admin: http://127.0.0.1:5000/admin

Never upload .env to GitHub.
Use official government documents and verify current scheme information on official government websites.
