import yfinance as yf
from rich.console import Console
from rich.table import Table

console = Console()

def display_put_options_all_dates(ticker_symbol):
    try:
        # Fetch Ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch available expiration dates
        expiration_dates = ticker.options
        if not expiration_dates:
            return f"No options data available for ticker {ticker_symbol}."
        
        # Loop through all expiration dates
        for chosen_date in expiration_dates:
            console.print(f"\n[bold magenta]Processing expiration date: {chosen_date}[/bold magenta]")
            
            # Fetch put options for the current expiration date
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                console.print(f"[yellow]No puts available for expiration date {chosen_date}.[/yellow]")
                continue
            
            # Prepare put options table with only required columns:
            # Contract, Strike, Last Price, Bid Price, Ask Price
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid Price", "Ask Price"]
            
            # Create a rich table for display with the selected columns
            table = Table(title=f"Put Options ({chosen_date})", show_header=True, header_style="bold magenta")
            table.add_column("Contract", style="cyan", justify="left")
            table.add_column("Strike", justify="right")
            table.add_column("Bid Price", justify="right")
            table.add_column("Ask Price", justify="right")
            table.add_column("Last Price", justify="right")
            
            # Populate the table
            for _, row in puts_table.iterrows():
                table.add_row(
                    row["Contract"],
                    f"{row['Strike']:.2f}",
                    f"{row['Bid Price']:.2f}",
                    f"{row['Ask Price']:.2f}",
                    f"{row['Last Price']:.2f}"
                )
            
            # Display the table
            console.print(table)
        
        return "All expiration dates processed successfully."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    ticker_symbol = input("Enter the ticker symbol: ").strip().upper()
    result = display_put_options_all_dates(ticker_symbol)
    if result != "All expiration dates processed successfully.":
        console.print(f"[bold red]{result}[/bold red]")
