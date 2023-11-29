from flask import Flask, jsonify, request
import os
import ibm_db_dbi as dbi
import pandas as pd
from dotenv import load_dotenv
import json, logging, traceback, random



logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
load_dotenv()


DB2___PERSONAS_DSN = 'DATABASE={database};HOSTNAME={hostname};PORT={port};PROTOCOL=TCPIP;UID={username};PWD={password};SECURITY=SSL'.format(
    database=os.environ.get("DB2_DATABASE",""),
    hostname= os.environ.get("DB2_HOST",""),
    port=os.environ.get("DB2_PORT",""),
    username=os.environ.get("DB2_USERNAME",""),
    password=os.environ.get("DB2_PASTWORD","")
)

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
    SELECT USER_ID FROM "CUSTOMER"."CUSTOMER_DATA"
    """
    try :
        result = pd.read_sql_query(query, con=db2_connection)
        result = list(result['USER_ID'])
    except Exception as e:
        logging.error("Failed to call the model", str(e))
        traceback.print_exc()
        result = None
    return result

def update_index(wa_user_id):
    global user_index
    logging.info(f"updating index with {wa_user_id}")
    existing = set(user_index.keys())
    if wa_user_id in existing:
        logging.info(f"{wa_user_id} already assigned")
        return 'pass'
    db_ids = get_db_ids()
    if isinstance(db_ids, list):
        new_id = random.sample(db_ids ,1)[0]
        logging.info(f"assigning {new_id} to {wa_user_id}")
        user_index[wa_user_id]={"user_uid":new_id}
        with open(ui2name_index, 'w') as index_file:
            index_file.write(json.dumps(user_index))
        return new_id
    else :
        logging.info(f"failed to retrieve ids in database, db_ids:", str(db_ids))
        return None

@app.route('/assign_id', methods=['POST'])
def assign_id():
    logging.info("assign_id")
    data = request.get_json(force=True)
    wa_user_id = data['user_id']
    assigned_id = update_index(wa_user_id)
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
    logging.info("STARTING THE APP")
    logging.info("get user index")
    with open(ui2name_index, 'r') as file:
        user_index = json.load(file)
    logging.info("Connect to db2")
    db2_connection = make_db2_connection()
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False)