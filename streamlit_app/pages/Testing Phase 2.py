import requests
from lxml import html

def get_performance_data(tradingview_url):
    try:
        response = requests.get(tradingview_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)

            # Example of finding data using specific classes or identifiers
            one_day = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "1D")]/following-sibling::span/text()')[0]
            five_days = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "5D")]/following-sibling::span/text()')[0]
            one_month = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "1M")]/following-sibling::span/text()')[0]
            six_months = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "6M")]/following-sibling::span/text()')[0]
            ytd = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "YTD")]/following-sibling::span/text()')[0]
            one_year = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "1Y")]/following-sibling::span/text()')[0]
            five_years = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "5Y")]/following-sibling::span/text()')[0]
            all_time = tree.xpath('//div[@class="some-unique-class"]//span[contains(text(), "All")]/following-sibling::span/text()')[0]

            return {
                "1 Day": one_day,
                "5 Days": five_days,
                "1 Month": one_month,
                "6 Month": six_months,
                "YTD": ytd,
                "1 Year": one_year,
                "5 Year": five_years,
                "All Time": all_time
            }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {
            "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A",
            "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"
        }

# Example URL
tradingview_url = "https://www.tradingview.com/symbols/NYSE-SCM/"
performance_data = get_performance_data(tradingview_url)
print(performance_data)
