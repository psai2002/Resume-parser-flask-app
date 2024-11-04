import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from pypdf import PdfReader
import psycopg2
from sqlalchemy import create_engine
import google.generativeai as genai
import json

app = Flask(__name__)
# app.secret_key = 'your_secret_key'

# Configure database connection
conn_string = "postgresql://postgres:postgres@localhost/newdb"
db = create_engine(conn_string)

# Configure GenAI (Google API)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file:
        file.save(file.filename)
        parsed_data, raw_text = process_pdf(file.filename)
        insert_data_into_db(parsed_data)
        return jsonify({'parsed_data': parsed_data, 'raw_text': raw_text})

def process_pdf(pdf_file):
    text = ''
    with open(pdf_file, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + '\n'
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
    response = model.generate_content(f"from {text} extract name, email, phone, college, skills, job title, company, duration. in skills remove colon. in skills remove text before colon. give json data.")

    raw_text = text
    data = response.text
    dictionary = json.loads(data)
    
    return dictionary, raw_text

def insert_data_into_db(dictionary):
    # Connect to the database and insert parsed data
    conn = psycopg2.connect(conn_string)
    conn.autocommit = True
    cur = conn.cursor()

    # Insert data into details, skills, and experience tables
    query1 = "INSERT INTO details (name, email, phone, college) VALUES (%s, %s, %s, %s)"
    values1 = (dictionary.get('name'), dictionary.get('email'), dictionary.get('phone'), dictionary.get('college'))

    query2 = "INSERT INTO skills (skill, email) VALUES (%s, %s)"
    values2 = (dictionary.get('skills'), dictionary.get('email'))

    query3 = "INSERT INTO experience (title, company, duration, email) VALUES (%s, %s, %s, %s)"
    values3 = (dictionary.get('job_title'), dictionary.get('company'), dictionary.get('duration'), dictionary.get('email'))

    query4 = "INSERT INTO candidate (name, email, phone, college, skills, job_title, company, duration) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    values4 = (
        dictionary.get('name'),
        dictionary.get('email'),
        dictionary.get('phone'),
        dictionary.get('college'),
        dictionary.get('skills'),
        dictionary.get('job_title'),
        dictionary.get('company'),
        dictionary.get('duration')
    )

    cur.execute(query1, values1)
    cur.execute(query2, values2)
    cur.execute(query3, values3)
    cur.execute(query4, values4)

    cur.close()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)

