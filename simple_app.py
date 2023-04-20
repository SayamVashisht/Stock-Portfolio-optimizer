import optimizer

def main():
    tickers = "AAPL TSLA"
    minR, maxR = optimizer.optimize(tickers)
    print(minR)
    print(maxR)

main()