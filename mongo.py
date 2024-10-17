from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

# Replace with your MongoDB Atlas connection string
client = MongoClient('mongodb+srv://siddhi:kPlnsZkZWxSwFu1J@cluster0.m3kk6.mongodb.net/')
db = client['gmail_declutter']  # Database name
emails_collection = db['emails'] 

# List databases
#print(client.list_database_names())

@app.route('/find-email', methods=['GET'])
def find_email():
    data = request.json
    user_id = data.get('user_id')
    unique_id = data.get('unique_id')

    if not user_id or not unique_id:
        return jsonify({"error": "user_id and unique_id are required"}), 400

    # Dynamically select the user's email collection
    emails_collection = db[f'emails_user_{user_id}']
    
    email = emails_collection.find_one({"unique_id": unique_id})
    print(email)

    if email:
        # Convert ObjectId to string for JSON serialization
        if '_id' in email:
            email['_id'] = str(email['_id'])
        
        email['exists'] = True
        return jsonify(email), 200
    else:
        return jsonify({"exists": False}), 200


@app.route('/store-email', methods=['POST'])
def store_email():
    data = request.json
    print(data)
    
    # Get the email content from the request
    user_id = data.get('user_id')
    unique_id = data.get('unique_id')
    email_subject = data.get('email_subject')
    #email_body = data.get('body')
    classification = data.get('classification')
    labeled = data.get('labeled')
    labels = data.get('labels')
    
    if not user_id or not email_subject or not classification or not labeled or not unique_id:
        return jsonify({"error": "User Id, Email subject, classification are required"}), 400
    
    emails_collection = db[f'emails_user_{user_id}']
    
    if classification == 'Informative':
        # Generate summary for informative emails
        summary = data.get('summary')
        email_data = {
            "unique_id": unique_id,
            "subject": email_subject,
            "classification": classification,
            "labeled": labeled,
            "labels": labels,
            "summary": summary
        }
        
    elif classification == 'Actionable':
        # Generate task for actionable emails
        task = data.get('task')
        email_data = {
            "unique_id": unique_id,
            "subject": email_subject,
            "classification": classification,
            "labeled": labeled,
            "labels": labels,
            "task": task
        }
        
    elif classification == 'Respond':
        # Generate response for emails requiring response
        response = data.get('response')
        email_data = {
            "unique_id": unique_id,
            "subject": email_subject,
            "classification": classification,
            "labeled": labeled,
            "labels": labels,
        }
    
    # Insert the email data into the collection
    result = emails_collection.insert_one(email_data)
    
    return jsonify({"message": "Email processed successfully", "email_id": str(result.inserted_id)}), 200


@app.route('/get-todo-list', methods=['GET'])
def get_todo_list():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    users_collection = db['users']
    user = users_collection.find_one({"user_id": user_id})
    
    if user:
        todo_list = user.get('todo_list', [])
        return jsonify({"user_id": user_id, "todo_list": todo_list}), 200
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/update-todo-list', methods=['POST'])
def update_todo_list():
    data = request.json
    user_id = data.get('user_id')
    todo_list = data.get('todo_list')

    if not user_id or not todo_list:
        return jsonify({"error": "user_id and todo_list is required"}), 400

    users_collection = db['users']
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Update the todo_list field only if the user exists
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"todo_list": todo_list}}  # Update only the todo_list field
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "TODO list updated successfully"}), 200
    else:
        return jsonify({"message": "No changes made to TODO list"}), 200
    
@app.route('/update-labels', methods=['POST'])
def update_labels():
    data = request.json
    user_id = data.get('user_id')
    unique_id = data.get('unique_id')
    labeled = data.get('labeled')
    labels = data.get('labels')
    
    if not user_id or not unique_id or not labeled:
        return jsonify({"error": "user_id and unique_id are required"}), 400
    
    emails_collection = db[f'emails_user_{user_id}']
    email = emails_collection.find_one({"unique_id": unique_id})
    
    if not email:
        return jsonify({"error": "Emails not found"}), 404
    
    result = emails_collection.update_one(
        {"unique_id": unique_id},
        {"$set": {
            "labeled": labeled,
            "labels": labels
        }}   
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "labels updated successfully"}), 200
    else:
        return jsonify({"message": "No changes made to labels"}), 200
    

@app.route('/update-response', methods=['POST'])
def update_response():
    data = request.json
    user_id = data.get('user_id')
    unique_id = data.get('unique_id')
    response = data.get('response')
    
    if not user_id or not unique_id or not response:
        return jsonify({"error": "user_id and unique_id are required"}), 400
    
    emails_collection = db[f'emails_user_{user_id}']
    email = emails_collection.find_one({"unique_id": unique_id})
    
    if not email:
        return jsonify({"error": "Emails not found"}), 404
    
    result = emails_collection.update_one(
        {"unique_id": unique_id},
        {"$set": {"response": response}}   
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "response updated successfully"}), 200
    else:
        return jsonify({"message": "No changes made to response"}), 200

@app.route('/add-user', methods=['POST'])
def add_user():
    data = request.json
    
    user_id = data.get('user_id')  # A unique identifier for the user, such as an email or UUID
    #user_name = data.get('name')
    #user_email = data.get('email')
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    # Access the 'users' collection
    users_collection = db['users']
    
    # Check if the user already exists
    existing_user = users_collection.find_one({"user_id": user_id})
    
    if existing_user:
        last_batch_time = existing_user.get("last_batch_time")
        return jsonify({"message": "User already exists", "user_id": user_id, "last_batch_time": last_batch_time}), 200
    
    # Create a new user document
    new_user = {
        "user_id": user_id,
        "todo_list": [],  # Initialize an empty todo_list
        "emails_collection": f"emails_{user_id}",  # Link to this user's email collection
        "last_batch_time": "",
    }
    
    # Insert the new user document into the collection
    result = users_collection.insert_one(new_user)
    
    return jsonify({"message": "User created successfully", "_id": str(result.inserted_id)}), 201

@app.route('/update-user', methods=['POST'])
def update_user():
    data = request.json
    
    user_id = data.get('user_id')
    last_batch_time = data.get('last_batch_time')
    
    users_collection = db['users']
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_batch_time": last_batch_time}}  
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "response updated successfully"}), 200
    else:
        return jsonify({"message": "No changes made to response"}), 200
        

if __name__ == '__main__':
    app.run(debug=True, port=8000)