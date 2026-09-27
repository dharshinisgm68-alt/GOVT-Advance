import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

UPLOAD_FOLDER = "documents"
VECTOR_DIR = "faiss_index"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
vector_store = None

def load_documents():
    documents = []
    for filename in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if filename.lower().endswith(".pdf"):
                documents.extend(PyPDFLoader(path).load())
            elif filename.lower().endswith(".txt"):
                documents.extend(TextLoader(path, encoding="utf-8").load())
        except Exception as error:
            print(f"Could not load {filename}: {error}")
    return documents

def rebuild_index():
    global vector_store
    documents = load_documents()
    if not documents:
        vector_store = None
        return 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(VECTOR_DIR)
    return len(chunks)

def load_index():
    global vector_store
    if not os.path.exists(VECTOR_DIR):
        return
    try:
        vector_store = FAISS.load_local(
            VECTOR_DIR, embeddings, allow_dangerous_deserialization=True
        )
        print("FAISS database loaded successfully.")
    except Exception as error:
        print(f"Could not load FAISS database: {error}")
        vector_store = None

load_index()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template("admin_login.html", error="Incorrect admin password.")
    if not session.get("admin_logged_in"):
        return render_template("admin_login.html")
    return render_template("admin.html")

@app.route("/admin/upload", methods=["POST"])
def admin_upload():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Admin login required."}), 401
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Please select a PDF or TXT file."}), 400
    filename = secure_filename(file.filename)
    if not filename.lower().endswith((".pdf", ".txt")):
        return jsonify({"error": "Only PDF and TXT files are supported."}), 400
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    try:
        count = rebuild_index()
        return jsonify({"message": f"Uploaded successfully. Indexed {count} chunks."})
    except Exception as error:
        return jsonify({"error": f"Indexing failed: {str(error)}"}), 500

@app.route("/admin/rebuild", methods=["POST"])
def admin_rebuild():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Admin login required."}), 401
    try:
        count = rebuild_index()
        return jsonify({"message": f"Knowledge base rebuilt successfully: {count} chunks."})
    except Exception as error:
        return jsonify({"error": f"Rebuild failed: {str(error)}"}), 500

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("home"))

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if vector_store is None:
        return jsonify({"error": "No government scheme documents are available yet."}), 400

    try:
        results = vector_store.similarity_search(question, k=4)
        if not results:
            return jsonify({"answer": "I could not find relevant information in the government scheme documents.", "sources": []})

        context_parts = []
        for doc in results:
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            context_parts.append(
                f"[Source: {os.path.basename(source)} | Page: {page}]\n{doc.page_content}"
            )
        context = "\n\n".join(context_parts)

        prompt = ChatPromptTemplate.from_template("""
You are a Government Scheme Information Assistant for India.
Answer using ONLY the retrieved document context.
Do not invent eligibility, benefits, deadlines, procedures, or URLs.
If information is unavailable, clearly say it was not found in the available documents.
Keep the answer simple. Remind the user to verify current information on the official government website.

USER QUESTION:
{question}

RETRIEVED DOCUMENT CONTEXT:
{context}

ANSWER:
""")
        response = llm.invoke(prompt.format_messages(question=question, context=context))
        answer = response.content

        if isinstance(answer, list):
            answer = "\n".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in answer
            )
        elif isinstance(answer, dict):
            answer = str(answer.get("text") or answer.get("content") or answer)
        else:
            answer = str(answer)

        sources = [
            {"source": os.path.basename(doc.metadata.get("source", "Unknown")),
             "page": doc.metadata.get("page", "N/A")}
            for doc in results
        ]
        return jsonify({"answer": answer, "sources": sources})
    except Exception as error:
        print("ERROR WHILE ANSWERING:", error)
        return jsonify({"error": f"Could not generate answer: {str(error)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
