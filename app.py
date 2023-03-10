import logging
import os

import jinja2
import msal
from flask import render_template, session, request, redirect, url_for
from opencensus.ext.azure.log_exporter import AzureLogHandler
from sqlalchemy.dialects.postgresql import insert

from setup import app_config
from flask_session import Session
from setup import create_app, get_db_connection, Author, Article, Review, set_up_db

app = create_app()
Session(app)

from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string=os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')))

connection, engine = get_db_connection()
sql_session = set_up_db(connection, engine)


def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))


app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)


@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))

    author = get_current_author()
    articles = sql_session.query(Article, Author).filter(Article.author_id == Author.id).all()
    return render_template('index.html', author=author, articles=articles)


def get_current_author():
    author = sql_session.query(Author).filter(Author.id == session.get('user')['preferred_username']).first()
    if not author:
        stm = insert(Author).values(id=session.get('user')['preferred_username'], nickname=session.get('user')['name'])
        stm = stm.on_conflict_do_nothing(index_elements=['id'])
        sql_session.execute(stm)
        sql_session.commit()
        author = sql_session.query(Author).filter(Author.id == session.get('user')['preferred_username']).first()
    return author


@app.route("/article/<int:id>")
def article(id):
    content = sql_session.query(Article, Author).filter(Article.id == id).filter(Article.author_id == Author.id).first()
    reviews = sql_session.query(Review, Author).filter(Author.id == Review.author_id).filter(
        Review.article_id == id).all()
    try:
        return render_template('article.html', article=content, reviews=reviews)
    except jinja2.exceptions.UndefinedError as e:
        logger.exception(e)
        return redirect(url_for("index"))


@app.route("/article/<int:id>", methods=['POST'])
def add_comment(id):
    sql_session.add(Review(article_id=id, author_id=session.get('user')['preferred_username'], content=request.form['content']))
    sql_session.commit()
    logger.info(f"{get_current_author().nickname} added a review.")
    return redirect(url_for("article", id=id))


@app.route("/add_article", methods=['GET'])
def test():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("add_article.html")


@app.route("/add_article", methods=['POST'])
def add_article():
    result = request.form
    user_id = session.get('user')['preferred_username']
    sql_session.add(Article(content=result['content'], title=result['title'], author_id=user_id))
    sql_session.commit()
    logger.info(f'{get_current_author().nickname} added and article.')
    return redirect(url_for("index"))


@app.route("/login")
def login():
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
    except ValueError:
        pass
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

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


if __name__ == "__main__":
    app.run()

