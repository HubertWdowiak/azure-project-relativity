import msal
import requests
from flask import Flask, render_template, session, request, redirect, url_for
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler, AzureEventHandler
import app_config
from flask_session import Session

app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=53cb6ec7-11ad-4eb7-b29a-75d260de8cdc;IngestionEndpoint=https://northeurope-2.in.applicationinsights.azure.com/;LiveEndpoint=https://northeurope.livediagnostics.monitor.azure.com/'))

import psycopg2
from psycopg2 import pool

# NOTE: fill in these variables for your own cluster
host = "c.sg4b6c3796be05442f855b5f0f5f9158f7.postgres.database.azure.com"
dbname = "citus"
user = "citus"
password = "nLDP8EvM!K7ksQX"
sslmode = "require"

# Build a connection string from the variables
conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)

postgreSQL_pool = psycopg2.pool.SimpleConnectionPool(1, 20,conn_string)
if (postgreSQL_pool):
    print("Connection pool created successfully")

conn = postgreSQL_pool.getconn()
cursor = conn.cursor()

# Drop previous table of same name if one exists
cursor.execute("DROP TABLE IF EXISTS pharmacy;")
print("Finished dropping table (if existed)")

# Create a table
cursor.execute("CREATE TABLE pharmacy (pharmacy_id integer, pharmacy_name text, city text, state text, zip_code integer);")
print("Finished creating table")

# Create a index
cursor.execute("CREATE INDEX idx_pharmacy_id ON pharmacy(pharmacy_id);")
print("Finished creating index")

# Insert some data into the table
cursor.execute("INSERT INTO pharmacy  (pharmacy_id,pharmacy_name,city,state,zip_code) VALUES (%s, %s, %s, %s,%s);", (1,"Target","Sunnyvale","California",94001))
cursor.execute("INSERT INTO pharmacy (pharmacy_id,pharmacy_name,city,state,zip_code) VALUES (%s, %s, %s, %s,%s);", (2,"CVS","San Francisco","California",94002))
print("Inserted 2 rows of data")

# Clean up
conn.commit()
cursor.close()
conn.close()



@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))

    ###############
    try:
        result = 1 / 0  # generate a ZeroDivisionError
    except Exception:
        logger.exception('Captured an exception.',
                         extra={'custom_dimensions': {'key_1': 'value_1', 'key_2': 'value_2'}})
    ###############
    return render_template('index.html', user=session["user"], version=msal.__version__)


@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__)


@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))


@app.route("/graphcall")
def graphcall():
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    graph_data = requests.get(  # Use token to call downstream service
        app_config.ENDPOINT,
        headers={'Authorization': 'Bearer ' + token['access_token']},
    ).json()
    return render_template('display.html', result=graph_data)


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)


def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))


def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

if __name__ == "__main__":
    app.run()
