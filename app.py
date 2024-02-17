from flask import Flask, render_template, request, redirect, session
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import json
import bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'authentication_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Secret key for session management
app.secret_key = 'your_secret_key'

# Initialize MySQL
mysql = MySQL(app)

# Global array to store responses
responses = []

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Fetch form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')  # Encode password

        # Hash password
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        # Create cursor
        cur = mysql.connection.cursor()

        # Check if user already exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            return "User already exists!"

        # Insert new user into database
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password))

        # Commit to database
        mysql.connection.commit()

        # Close connection
        cur.close()

        # Store username in session
        session['username'] = username

        return redirect('/')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Fetch form data
        username = request.form['username']
        password = request.form['password'].encode('utf-8')  # Encode password

        # Create cursor
        cur = mysql.connection.cursor()

        # Fetch user from database
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        # Close connection
        cur.close()

        # Check if user exists and password is correct
        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            # Store username in session
            session['username'] = username
            return redirect('/')
        else:
            return "Invalid username or password"

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear session data
    session.pop('username', None)
    return redirect('/login')

@app.route("/process_pdf", methods=["POST"])
def process_pdf():
    pdf_files = request.files.getlist("pdf_files")
    raw_text = get_pdf_text(pdf_files)
    text_chunks = get_text_chunks(raw_text)
    get_vector_store(text_chunks)
    return render_template("response_succ.html")

@app.route("/ask_question", methods=["POST"])
def ask_question():
    number = request.form.get("number")  # Retrieve the 'number' from the form data
    response = user_input(number)
    # Append response to global array
    responses.append(response)
    # Render response
    return render_response(response)

def render_response(response):
    response = remove_newlines(response)
    # Save response to a file
    save_to_file(response)
    return render_template("response.html", response=response)

def remove_newlines(response):
    if isinstance(response, str):
        return response.replace('\n', ' ')
    elif isinstance(response, dict):
        return {key: value.replace('\n', '') if isinstance(value, str) else value for key, value in response.items()}
    else:
        return response

def save_to_file(response):
    filename = "response.md"  # You can customize the filename if needed
    with open(filename, "w") as file:
        if isinstance(response, dict):
            response_str = json.dumps(response, indent=4)  # Convert dictionary to JSON string
        else:
            response_str = response
        file.write(response_str)

def get_pdf_text(pdf_files):
    text = ""
    for pdf_file in pdf_files:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def get_conversational_chain():
    prompt_template = """
    generate {number} of markdown mcq from the given text in markdown format 
    Context:{context}?
    
    "example : question:questions sentence 1\n option1\n option2\n option3\n option4\n"
    
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, google_api_key=os.getenv("GOOGLE_API_KEY"))
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "number"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(number):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings)
    docs = new_db.similarity_search(number)
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "number": number}, return_only_outputs=True)
    return response

if __name__ == "__main__":
    load_dotenv()
    app.run(debug=True)
