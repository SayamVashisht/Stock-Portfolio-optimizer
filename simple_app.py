import optimizer

def main():
    tickers = ['AAPL', 'MSFT','TSLA']
    minR, maxR = optimizer.optimize(tickers, 0.5,3)
    print(minR)
    print(maxR)

main()
