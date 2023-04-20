from distutils.log import debug
from sys import flags
from flask import Flask, request, render_template, url_for, redirect, flash, get_flashed_messages
from flask_restful import Resource, Api
from flask_cors import CORS
import optimizer
import pandas as pd
import sqlite3
import pymysql

def create_app():
	app = Flask(__name__)
	return app

app = create_app()
api = Api(app)
CORS(app)

TICKERS = {"Bonds": ["^FVX", "^IRX", "^TNX", "^TYX"],
"Commodities": ["CL=F", "GC=F", "KC=F"],
"Cryptos": ["BNB-USD", "BTC-USD", "ETH-USD", "USDC-USD", "USDT-USD"],
"Indices": ["^GDAXI", "^GSPC", "^N225", "^RUT"],
"Stocks": ["AAPL", "AMZN", "F", "GOOGL", "META", "NFLX", "TSLA"]}

BONDS = TICKERS["Bonds"] + TICKERS["Commodities"]
STOCKS = TICKERS["Cryptos"] + TICKERS["Indices"] + TICKERS["Stocks"]

conn = sqlite3.connect('./datadb/database.db')
conn.row_factory = sqlite3.Row
with open("./datadb/schema.sql") as f:
    conn.executescript(f.read())
conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect('./datadb/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data = cur.execute('SELECT * FROM portfolios')
    
    portfolios = list()

    for portfolio in data:
        print(dict(portfolio))
        portfolios.append(dict(portfolio))

    conn.commit()

    return render_template("index.html", portfolios=portfolios)

@app.route("/add_portfolio")
def add_portfolio():
    conn = sqlite3.connect('./datadb/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    title = request.args.get("title")
    assets = request.args.get("assets")
    budget = request.args.get("budget" , type =int)
    riskfactor = request.args.get("riskfactor" , type = float)

    print(f"Insert: {title} {assets} {budget} {riskfactor}")

    cur.execute("INSERT INTO portfolios (title, assets, budget, riskfactor) VALUES (?, ?, ?, ?)",
            (str(title), str(assets), int(budget), float(riskfactor)))
    conn.commit()

    flash("Portfolio added successfully!")
    return redirect(url_for("index"))

@app.route("/edit_portfolio/<id>")
def edit_portfolio(id):
    conn = sqlite3.connect('./datadb/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(f"SELECT * FROM portfolios WHERE id={id}")
    data = cur.fetchall()
    cur.close()
    print(f"Edit Record {id}: {dict(data[0])}")

    return render_template("edit.html", portfolio=dict(data[0]))

@app.route("/update_portfolio/<id>")
def update_portfolio(id):
    title = request.args.get("title")
    assets = request.args.get("assets")
    budget = request.args.get("budget" , type = int)
    riskfactor = request.args.get("riskfactor" , type = float)

    conn = sqlite3.connect('./datadb/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"Update: {title} {assets} {budget} {riskfactor}")

    cur.execute("UPDATE portfolios SET title=?, assets=?, budget=?, riskfactor=? WHERE id=?", (str(title), str(assets),int(budget), float(riskfactor), int(id)))
    flash("Portfolio update successfully!")
    
    conn.commit()
    cur.close()
    return redirect(url_for('index'))

@app.route("/delete_portfolio/<string:id>")
def delete_portfolio(id):
    conn = sqlite3.connect('./datadb/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('DELETE FROM portfolios WHERE id= {0}'.format(id))
    conn.commit()
    cur.close()

    flash("Portfolio deleted successfully!")
    return redirect(url_for("index"))

@app.route("/portfolio_optimizer")
@app.route("/portfolio_optimizer/<string:assets>")
def portfolio_optimizer(assets=None):

    #ticker_list = "AAPL TSLA"
    data = dict()
    if assets:
        print(assets)
        print(f"assets: {assets} {type(assets)}")
        app.logger.info(assets.split())
        minRisk, maxReturn = optimizer.optimize(assets)
        data["minRisk"] = minRisk
        data["maxReturn"] = maxReturn
    elif request.args.get("tickers") and len(request.args.get("tickers").split()) >= 2:
        ticker_list = request.args.get("tickers")
        app.logger.info(ticker_list.split())
        minRisk, maxReturn = optimizer.optimize(ticker_list)
        data["minRisk"] = minRisk
        data["maxReturn"] = maxReturn
    else:
        data["Error"] = "No portfolio provided"
    app.logger.info(data)

    new_data = list()
    minRisk_data = list()
    maxReturn_data = list()

    for k, v in data["minRisk"].items():
        for key, val in v.items():
            minRisk_data.append(tuple([k, val]))

    for k, v in data["maxReturn"].items():
        for key, val in v.items():
            maxReturn_data.append(tuple([k, val]))
        
    new_data = [minRisk_data, maxReturn_data]

    return render_template("portfolio_optimizer.html", data=new_data)

if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=8090)
    app.secret_key = 'nive'
    app.run(host="0.0.0.0", port=8090, debug=True)
