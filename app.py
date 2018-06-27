# Flask Sample
#https://gist.github.com/kemitche/9749639

# Flask Debugging
#https://code.visualstudio.com/docs/python/tutorial-flask

#!/usr/bin/env python
from flask import Flask, abort, request
from uuid import uuid4
import requests
import requests.auth
import urllib
CLIENT_ID = 'Q0pe6YvYiaUjA2Yv1CqS1wJkEHqNr3paQSNxlo9gRicpkf3W09'
CLIENT_SECRET = '9Z2W4t81Vr8mTxLM04av9MOAyOsJBUVCYBR1JbnU'
REDIRECT_URI = "http://localhost:8000/qbo_callback"

app = Flask(__name__)
@app.route('/')
def homepage():
    text = '<a href="%s">Authenticate with qbo</a>'
    return text % make_authorization_url()

def make_authorization_url():

    import requests
    # https://github.com/sidecars/python-quickbooks
    from quickbooks import Oauth2SessionManager

    session_manager = Oauth2SessionManager(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        base_url='http://localhost:8000/qbo_callback',
    )

    callback_url = 'http://localhost:8000/qbo_callback'  # Quickbooks will send the response to this url
    authorize_url = session_manager.get_authorize_url(callback_url)

    requests.get(authorize_url)

    return authorize_url


# Left as an exercise to the reader.
# You may want to store valid states in a database or memcache.
def save_created_state(state):
    pass
def is_valid_state(state):
    return True

@app.route('/qbo_callback')
def qbo_callback():

    # https://github.com/sidecars/python-quickbooks
    from quickbooks import Oauth2SessionManager
    from quickbooks import QuickBooks

    error = request.args.get('error', '')
    if error:
        return "Error: " + error
    state = request.args.get('state', '')
    if not is_valid_state(state):
        # Uh-oh, this request wasn't started by us!
        abort(403)
    authorization_code = request.args.get('code')
    realm_id = request.args.get('realmId')

    session_manager = Oauth2SessionManager(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        base_url='http://localhost:8000/qbo_callback',
    )

    session_manager.get_access_tokens(authorization_code)
    access_token = session_manager.access_token

    session_manager = Oauth2SessionManager(
    client_id=realm_id,
    client_secret=CLIENT_SECRET,
    access_token=access_token,
    )

    client = QuickBooks(
        sandbox=True,
        session_manager=session_manager,
        company_id=realm_id
    )
    
    from quickbooks.objects.customer import Customer
    customers = Customer.all(qb=client)

    import_googlesheets(customers)

    client.disconnect_account()

    # Note: In most cases, you'll want to store the access token, in, say,
    # a session for use in other parts of your web app.
    return "Your qbo authorization_code is %s realm_id is: %s customers: %s" % (authorization_code, realm_id, customers)

def import_googlesheets(customers):
    """Import into Google Sheets"""

    import datasheets

    # Create a data set to upload
    import pandas as pd
    customer_slicer = []
    for customer in customers:
        customer_row = []
        customer_row.append(customer.DisplayName)
        customer_row.append(customer.Balance)
        customer_slicer.append(customer_row)

    df = pd.DataFrame(customer_slicer, columns=['DisplayName', 'Balance'])

    try:
        client = datasheets.Client()
        workbook = client.fetch_workbook('QuickBooksSample')
        if workbook is None:
            workbook = client.create_workbook('QuickBooksSample')
        
        tab_names = workbook.fetch_tab_names()
        if not 'QuickBooks-Export' in tab_names.values:
            tab = workbook.create_tab('QuickBooks-Export')
        else:
            tab = workbook.fetch_tab('QuickBooks-Export')
            tab.clear_data()

        # Upload data to sheet
        tab.insert_data(df, index=False)

    except Exception as ex:
        print str(ex)
    return "Worked"

if __name__ == '__main__':
    app.run(debug=True, port=8000)