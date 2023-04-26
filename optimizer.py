from qiskit import Aer
from qiskit.utils import algorithm_globals
from qiskit.algorithms import VQE, QAOA, NumPyMinimumEigensolver
from qiskit.algorithms.optimizers import COBYLA
from qiskit.circuit.library import TwoLocal
from qiskit.utils import QuantumInstance
from qiskit_finance.applications.optimization import PortfolioOptimization
from qiskit_finance.data_providers import YahooDataProvider
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.applications import OptimizationApplication
from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit_optimization import QuadraticProgram
from scipy.optimize import minimize
import numpy as np
import matplotlib.pyplot as plt
import datetime
import numpy as np
import yfinance as yf
import pandas as pd
import random


def index_to_selection(i, num_assets):
    s = "{0:b}".format(i).rjust(num_assets)
    x = np.array([1 if s[i] == "1" else 0 for i in reversed(range(num_assets))])
    return x

def portfolio_val(weights,returns):
  weights = np.array(weights)
  expected_return = np.sum((returns.mean()* weights) * 252)
  expected_vol = np.sqrt(np.dot(weights.T,np.dot(returns.cov()*252,weights)))
  sharpe_r = expected_return/expected_vol
  return np.array([expected_return,expected_vol,sharpe_r])

def sr_negate(weights,returns):
  neg_sr = portfolio_val(weights,returns)[2] * -1
  return neg_sr

def weight_check(weights):
  weights_sum = np.sum(weights)
  return weights_sum - 1
def insert_tuples(n):
    return [(0, 1) for i in range(n)]


def optimize(stocks,q,budget):
    num_assets = len(stocks)
    seed = 123

    data = YahooDataProvider(
        tickers=stocks,
        start=datetime.datetime(2018, 1, 1),
        end=datetime.datetime(2023, 12, 31)
    )
    data.run()
    mu = data.get_period_return_mean_vector()
    sigma = data.get_period_return_covariance_matrix()

    start_date = '2018-01-01'
    end_date = '2023-12-31'

    # Create placeholder for data
    data2 = pd.DataFrame(columns=stocks)

    # Fetch the data
    for ticker in stocks:
        data2[ticker] = yf.download(ticker, start_date,end_date)['Adj Close']

    penalty = num_assets  # set parameter to scale the budget penalty term

    portfolio = PortfolioOptimization(
        expected_returns=mu, covariances=sigma, risk_factor=q, budget=budget
    )
    qp = portfolio.to_quadratic_program()
    
    #VQE
    algorithm_globals.random_seed = 1234
    backend = Aer.get_backend("qasm_simulator")
    cobyla = COBYLA()
    cobyla.set_options(maxiter=500)
    ry = TwoLocal(num_assets, "ry", "cz", reps=3, entanglement="full")
    quantum_instance = QuantumInstance(backend=backend, seed_simulator=seed, seed_transpiler=seed)
    vqe_mes = VQE(ry, optimizer=cobyla, quantum_instance=quantum_instance)
    vqe = MinimumEigenOptimizer(vqe_mes)
    vqe_result = vqe.solve(qp)

    #QAOA
    algorithm_globals.random_seed = 1234
    backend = Aer.get_backend("qasm_simulator")
    cobyla = COBYLA()
    cobyla.set_options(maxiter=250)
    quantum_instance = QuantumInstance(backend=backend, seed_simulator=seed, seed_transpiler=seed)
    qaoa_mes = QAOA(optimizer=cobyla, reps=3, quantum_instance=quantum_instance)
    qaoa = MinimumEigenOptimizer(qaoa_mes)
    qaoa_result = qaoa.solve(qp)


    vqe_assets = []
    vqe = {}
    for i in range(len(vqe_result.x)):
        if(vqe_result[i] == 1):
            vqe_assets.append(stocks[i])
    data = pd.DataFrame(columns=vqe_assets)
    data[vqe_assets] = data2[vqe_assets]
    n = len(vqe_assets)
    returns=data.pct_change()
    weights = [random.random() for _ in range(n)]
    sum_weights = sum(weights)
    weights = [1*w/sum_weights for w in weights]
    constraints = ({'type':'eq','fun':weight_check})
    initial_guess = weights
    bounds=insert_tuples(n)
    results = minimize(sr_negate,weights,returns,method='SLSQP',bounds=bounds,constraints=constraints)
    optimized_metrics = portfolio_val(results.x, returns)
    vqe['Returns']=("{:.2f}%".format(optimized_metrics[0]*100))
    vqe['Volatility']=("{:.2f}%".format(optimized_metrics[1]*100))
    vqe['Sharpe Ratio']=("{:.2f}".format(optimized_metrics[2]))
    for (x,y) in zip(vqe_assets,results.x):
       vqe[x] = "{:.2f}%".format(y*100)

    
    qaoa ={}
    assets = []
    for i in range(len(qaoa_result.x)):
        if(qaoa_result[i] == 1):
            assets.append(stocks[i])
    data = pd.DataFrame(columns=assets)
    data[assets] = data2[assets]
    n = len(assets)
    returns=data.pct_change()
    weights = [random.random() for _ in range(n)]
    sum_weights = sum(weights)
    weights = [1*w/sum_weights for w in weights]
    constraints = ({'type':'eq','fun':weight_check})
    initial_guess = weights
    bounds=insert_tuples(n)
    results = minimize(sr_negate,weights,returns,method='SLSQP',bounds=bounds,constraints=constraints)
    optimized_metrics = portfolio_val(results.x, returns)
    qaoa['Returns']=("{:.2f}%".format(optimized_metrics[0]*100))
    qaoa['Volatility']=("{:.2f}%".format(optimized_metrics[1]*100))
    qaoa['Sharpe Ratio']=("{:.2f}".format(optimized_metrics[2]))
    for (x,y) in zip(assets,results.x):
       qaoa[x] = "{:.2f}%".format(y*100)


    return vqe,qaoa

