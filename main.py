from flask import Flask, jsonify, request
import os
import ibm_db_dbi as dbi
import pandas as pd
from dotenv import load_dotenv
import json, logging, traceback, random, requests



logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
load_dotenv()


DB2___PERSONAS_DSN = 'DATABASE={database};HOSTNAME={hostname};PORT={port};PROTOCOL=TCPIP;UID={username};PWD={password};SECURITY=SSL'.format(
    database=os.environ.get("DB2_DATABASE",""),
    hostname= os.environ.get("DB2_HOST",""),
    port=os.environ.get("DB2_PORT",""),
    username=os.environ.get("DB2_USERNAME",""),
    password=os.environ.get("DB2_PASSWORD","")
)

MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY","")

ui2name_index = './user_index.json'

def get_user_uid(user_uid):
    global user_index
    return user_index[user_uid]["user_uid"]

def make_db2_connection():
    return dbi.connect(DB2___PERSONAS_DSN)

def query_data(customer_id):
    global db2_connection
    query = f"""
    SELECT * FROM "CUSTOMER"."CUSTOMER_DATA" WHERE USER_ID ='{customer_id}'
    """
    try :
        result = pd.read_sql_query(query, con=db2_connection)
        result = result.iloc[0].to_dict()
        return result
    except Exception as e:
        logging.error("Failed to call the model", str(e))
        traceback.print_exc()
        result = None
    return result

def get_db_ids():
    global db2_connection
    query = f"""
    SELECT NAME, USER_ID FROM "CUSTOMER"."CUSTOMER_DATA"
    """
    try :
        result = pd.read_sql_query(query, con=db2_connection)
        result = result.set_index('NAME').to_dict()['USER_ID']
    except Exception as e:
        logging.error("Failed to call the model", str(e))
        traceback.print_exc()
        result = None
    return result

def update_index(wa_user_id, persona_name):
    global user_index
    logging.info(f"updating index with {wa_user_id}")
    # existing = set(user_index.keys())
    # if wa_user_id in existing:
    #     logging.info(f"{wa_user_id} already assigned")
    #     return 'pass'
    db_ids = get_db_ids()
    if isinstance(db_ids, dict):
        if persona_name is not None:
            new_id = db_ids[persona_name]
        else:
            new_id = random.sample(list(db_ids.values()), 1)[0]
        logging.info(f"assigning {new_id} to {wa_user_id}")
        user_index[wa_user_id]={"user_uid":new_id}
        with open(ui2name_index, 'w') as index_file:
            index_file.write(json.dumps(user_index))
        return new_id
    else :
        logging.info(f"failed to retrieve ids in database, db_ids:", str(db_ids))
        return None

@app.route('/send_email', methods=['POST']) 
def send_email(): 
    logging.info("send_email") 
    data = request.get_json(force=True) 
    email_message = data['email_message'] 
    email_subject = data['email_subject']
    email_to = data['email_to']
    mailgun_endpoint = data['mailgun_endpoint'] # "https://api.mailgun.net/v3/sandbox87573be681cf489f90506a55814df346.mailgun.org/messages"
    mailgun_address = data['mailgun_address'] # "Mailgun Sandbox postmaster@sandbox87573be681cf489f90506a55814df346.mailgun.org>"
    if MAILGUN_API_KEY != "":
        resp = requests.post( 
            mailgun_endpoint, 
            auth=("api", MAILGUN_API_KEY), 
            data={"from": mailgun_address, 
                "to": email_to, 
                "subject": email_subject, 
                "text": email_message}) 
        if resp.status_code == 200: 
            logging.info(f"{email_message} succesffuly sent to {email_to}") 
            return jsonify({'response': 'succes'}), 200 
        else : 
            return jsonify({'error': 'Bad request'}), 400
    else:
       return jsonify({'error': 'No API Key provided for MAILGUN'}), 400

@app.route('/assign_id', methods=['POST'])
def assign_id():
    logging.info("assign_id")
    data = request.get_json(force=True)
    wa_user_id = data['user_id']
    persona_name = data.get('persona_name', None)
    assigned_id = update_index(wa_user_id, persona_name)
    if isinstance(assigned_id, str):
        logging.info(f"{wa_user_id} succesffuly assigned to {assigned_id}")
        return jsonify({'response': 'succes'}), 200
    else :
        return jsonify({'error': 'Bad request'}), 400

@app.route('/get_user_data', methods=['POST'])
def get_user_data():
    logging.info("get_user_data")
    data = request.get_json(force=True)
    user_id = data['user_id']
    customer_id = get_user_uid(user_id)
    user_data = query_data(customer_id)
    logging.info(str(user_data))
    if isinstance(user_data, dict):
        return jsonify({'NAME': user_data['NAME'],
                        'AGE': user_data['AGE'],
                        'GENDER': user_data['GENDER'],
                        'MARITAL': user_data['MARITAL'],
                        'EDUCATION': user_data['EDUCATION'],
                        'CURRENT_INCOME': user_data['CURRENT_INCOME'],
                        'TOTAL_401K_SAVINGS': user_data['TOTAL_401K_SAVINGS'],
                        'TOTAL_HSA_SAVINGS': user_data['TOTAL_HSA_SAVINGS'],
                        'TOTAL_DEBT': user_data['TOTAL_DEBT'],
                        'TOTAL_NET_WORTH': user_data['TOTAL_NET_WORTH'],
                        'STATE': user_data['STATE'],
                        'USER_ID': user_data['USER_ID'],
                        'PERSONADESC':user_data['PERSONADESC']}), 200
    else :
        return jsonify({'error': 'Bad request'}), 400

if __name__ == '__main__':
    logging.info("STARTING MAIN")
    logging.info("get user index")
    with open(ui2name_index, 'r') as file:
        user_index = json.load(file)
    logging.info("Connect to db2")
    db2_connection = make_db2_connection()
    logging.info("STARTING THE APP")
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False)