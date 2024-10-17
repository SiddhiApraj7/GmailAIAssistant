from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import openai
import os
from agentic import EmailProcessingController
from gmail_api import gmail_authenticate, fetch_emails, batch_process_emails
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

openai.api_key = os.environ.get("OPENAI_API_KEY","")

email_processor = EmailProcessingController()

@app.route('/hello', methods=['GET'])
def hello():
    return "hello world"

@app.route('/process-email',  methods=['POST'])
def process_email():
    data = request.json
    
    search_email_url = 'http://127.0.0.1:8000/find-email'
    store_email_url = 'http://127.0.0.1:8000/store-email'
    
    # Get the email content from the request
    email_subject = data.get('subject')
    email_body = data.get('body')
    unique_id = data.get('uniqueId')
    print(unique_id)
    
    if not email_subject or not email_body or not unique_id:
        return jsonify({"error": "Email subject and body are required"}), 400
    
    
    try:
        service = gmail_authenticate()
        profile = service.users().getProfile(userId='me').execute()
        user_id = profile.get('emailAddress')
        
        payload = {
            "user_id": user_id,
            "unique_id": unique_id
        }
        search_response = requests.get(search_email_url, json=payload)
        if search_response.status_code == 200:
            data = search_response.json()
            print(data)
            
            if data.get('exists'):
                print(f"Email with unique_id {unique_id} already exists. Fetching...")
                return data, 200
            
            else:
                result = email_processor.process_email(email_subject, email_body)
                result["user_id"] = user_id
                result["unique_id"] = unique_id
                result["labeled"] = "False"
                result["labels"] = []
                store_response = requests.post(store_email_url, json=result)
                result["body"] = email_body
                
                if store_response.status_code == 200:
                    print(f"Email with unique_id {unique_id} stored successfully.")
                else:
                    print(f"Failed to store email with unique_id {unique_id}. Status code: {store_response.status_code}")
                    
                return jsonify(result), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    

@app.route('/batch-process-emails', methods=['POST'])
def fetch_and_batch_process():
    try:
        service = gmail_authenticate()
        profile = service.users().getProfile(userId='me').execute()
        user_id = profile.get('emailAddress')
        fetch_emails(service, user_id)
        batch_process_emails(user_id)
        return jsonify({"message": "Emails fetched and processed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-response', methods=['POST'])
def first_draft():
    print("generate response")
    data = request.json
    user_id = data.get('user_id')
    unique_id = data.get('unique_id')
    email_subject = data.get('subject')
    email_body = data.get('body')
    labeled = data.get('labeled')
    labels = data.get('labels')
    instruction = data.get('userInstruction')
    
    print(email_subject)
    print(email_body)
    print(instruction)
    
    update_response_url = 'http://127.0.0.1:8000/update-response'
    
    result = email_processor.get_first_response(email_subject, email_body, instruction)
    result["user_id"] = user_id
    result["unique_id"] = unique_id
    result["labeled"] = labeled
    result["labels"] = labels
    
    print(result)
    
    update_response = requests.post(update_response_url, json=result)
    if update_response.status_code == 200:
        print(f"Email with unique_id {unique_id} update successfully.")
    else:
        print(f"Failed to update email with unique_id {unique_id}. Status code: {update_response.status_code}")
    
    return jsonify(result), 200

"""@app.route('/modify-response', methods=['POST'])
def first_draft():
    data = request.json
    unique_id = data.get('unique_id')
    prev_response = data.get('prevResponse')
    instruction = data.get('instruction')
    
    result = email_processor.get_first_response(prev_response, instruction)
    return jsonify(result), 200
"""
"""
@app.route('/classify-email', methods=['POST'])
def classify_email():
    data = request.json
    
    # Get the email content from the request
    email_subject = data.get('subject')
    email_body = data.get('body')
    
    if not email_subject or not email_body:
        return jsonify({"error": "Email subject and body are required"}), 400
    
    # Create the prompt for the AI model
    prompt = f"Classify this email with the subject: '{email_subject}' and body: '{email_body}' as one of the following: 'informative', 'actionable', or 'respond'. Only respond with the classification label and no other text."
    
    # Set up the payload for the AI model
    payload = {
        "model": "gpt-4",  # You can change the model if necessary
        "prompt": prompt,
        "max_tokens": 10  # Just enough for the classification response
    }
    
    #headers = {
    #    "Authorization": f"Bearer {API_KEY}",
    #    "Content-Type": "application/json"
    #}
    
    completion = openai.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt=prompt,
    max_tokens=10
    )
    response_str = completion.choices[0].text
    print(response_str)
    
    
    # Send request to the AI model API
    #response = requests.post(AI_MODEL_ENDPOINT, headers=headers, json=payload)
    #response_str = response.text
    #print(response_str)
    
    # Parse the response
    #ai_response = response.json()
    #classification = ai_response['choices'][0]['text'].strip()

    # Return the classification result
    return response_str#jsonify({"classification": classification})"""

if __name__ == '__main__':
    app.run(debug=True, port=5000)
