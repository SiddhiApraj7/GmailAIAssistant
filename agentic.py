import openai
import os
from transformers import GPT2Tokenizer

openai.api_key = os.environ.get("OPENAI_API_KEY","")

def trim_content(body, max_tokens=4000):
    # Tokenize both subject and body
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    body_tokens = tokenizer.encode(body)

    # If total tokens exceed max_tokens, prioritize body trimming
    if len(body_tokens) > max_tokens:
        body_tokens = body_tokens[:max_tokens]
        trimmed_body = tokenizer.decode(body_tokens, skip_special_tokens=True)
        return trimmed_body

    return body

class EmailClassificationAgent:
    def classify_email(self, email_subject, email_body):
        prompt = f"Classify this email with the subject: '{email_subject}' and body: '{email_body}' as one of the following: 'Informative', 'Actionable', or 'Respond'. Only respond with the classification label and no other text. Make sure the label has only first letter in uppercase. If the reply needs a response, do not classify it as actionable. Instead classify it as 'Respond'."
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=10
        )
        print(response.choices[0].text)
        return response.choices[0].text.strip()

class SummarizationAgent:
    def summarize_email(self, email_body):
        prompt = f"Summarize the following email in upto 10 sentences:\n\n{email_body}\n Note that your summary should simply be a smaller version of the email. It should serve as a quick read to understand the purpose of the email and its most important info."
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=900
        )
        return response.choices[0].text.strip()
    
class TaskCreationAgent:
    def generate_task(self, email_subject, email_body):
        prompt = f"Generate a task from this email that can be added to a to-do list:\n\nSubject: {email_subject}\nBody: {email_body}"
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=25
        )
        return response.choices[0].text.strip()
    
class ResponseAssistantAgent:
    def generate_possible_responses(self, email_subject, email_body):
        prompt = f"""EXAMPLE:
        Subject: Request for recommendation letter\n
        Body: I hope this message finds you well. I am reaching out to kindly request your recommendation for my applications to several master's programs. I am applying to Carnegie Mellon University’s Master of Science in Artificial Intelligence(MSAII) as well as Data Science programs at University of Pennsylvania and Boston University. 
        Your guidance and mentorship throughout my academic journey in courses like Theory of Computation, Graph Theory and Analysis and Design of Algorithms, have greatly influenced my passion for learning and pursuing higher education. I believe your insight into my academic strengths, research aptitude, and commitment to the field would significantly enhance my application. 
        I have attached my resume, highlighting my progress thus far, for your reference. The recommendation letters are an essential component of my application, and your support would mean a great deal to me at this crucial stage.
        Thank you again for your support.\n
        Options: 1. Agree to send a recommendation letter 2. Politely refuse the request 3. Inquire further regarding details \n\n
        Similar to the above example, generate a list of possible responses to the following email. I want the list to be numbered and contain short 4-5 word phrases giving a general idea of what the response can contain.\n
        This is the email:\n\nSubject: {email_subject}\nBody: {email_body}"""
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=25
        )
        return response.choices[0].text.strip()
    
    def first_response(self, email_subject, email_body, instruction):
        prompt = f"""Generate a response to the following email based on the instruction provided: \n\n Subject: {email_subject}\n Body: {email_body}\n Instruction: {instruction}"""
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=500
        )
        return response.choices[0].text.strip()
    
    def customize_response(self, prev_response, instruction):
        prompt = f"""Modify the response below according to the instruction provided: \n\n Response: {prev_response}\n Instruction: {instruction}"""
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=500
        )
        return response.choices[0].text.strip()
    
class EmailProcessingController:
    def __init__(self):
        self.classification_agent = EmailClassificationAgent()
        self.summarization_agent = SummarizationAgent()
        self.task_creation_agent = TaskCreationAgent()
        self.response_assistant_agent = ResponseAssistantAgent()
    
    def process_email(self, email_subject, email_body):
        body = trim_content(email_body, 3000)
        # Classify the email
        classification = self.classification_agent.classify_email(email_subject, body)
        print(email_subject)
        print(classification)
        
        if classification == 'Informative':
            # Generate summary for informative emails
            summary = self.summarization_agent.summarize_email(body)
            return {"email_subject": email_subject, "classification": classification, "summary": summary}
        
        elif classification == 'Actionable':
            # Generate task for actionable emails
            task = self.task_creation_agent.generate_task(email_subject, body)
            return {"email_subject": email_subject, "classification": classification, "task": task}
        
        elif classification == 'Respond':
            # Generate response for emails requiring response
            #options = self.response_assistant_agent.generate_possible_responses(email_subject, body)
            #options_list = [option.strip() for option in options.split("\n") if option.strip()]
            return {"email_subject": email_subject, "classification": classification, "response": ""}
        
        return {"email_subject": email_subject, "classification": classification}
    
    def get_first_response(self, email_subject, email_body, instruction):
        body = trim_content(email_body, 3000)
        response = self.response_assistant_agent.first_response(email_subject, body, instruction)
        return {"instruction": instruction, "email_subject": email_subject, "response": response}
    
    def get_customized_response(self, prev_response, instruction):
        new_response = self.response_assistant_agent.customize_response(prev_response, instruction)
        return {"response": new_response}
        

