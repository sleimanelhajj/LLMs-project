"""
External API Tools
Tools for integrating with external APIs for currency exchange and holiday information.
"""

from langchain_core.tools import tool
import httpx
from datetime import datetime, timedelta
from typing import Optional
import os


@tool
def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "USD") -> str:
    """
    Convert an amount from one currency to another using real-time exchange rates.
    
    Args:
        amount: The amount to convert
        from_currency: Source currency code (e.g., 'USD', 'EUR', 'GBP')
        to_currency: Target currency code (e.g., 'USD', 'EUR', 'GBP')
    
    Returns:
        Converted amount with exchange rate information
    """
    try:
        # Using ExchangeRate-API (free tier, no API key needed for basic use)
        # Alternative: https://api.exchangerate-api.com/v4/latest/{from_currency}
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        
        if to_currency.upper() not in data["rates"]:
            return f"Currency code '{to_currency}' not supported. Please use standard codes like USD, EUR, GBP, CAD, AUD, JPY, etc."
        
        rate = data["rates"][to_currency.upper()]
        converted_amount = amount * rate
        
        # Format result as HTML
        result = f"<strong>Currency Conversion</strong><br><br>"
        result += f"<strong>Amount:</strong> {amount:,.2f} {from_currency.upper()}<br>"
        result += f"<strong>Converts to:</strong> {converted_amount:,.2f} {to_currency.upper()}<br>"
        result += f"<strong>Exchange Rate:</strong> 1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()}<br>"
        result += f"<strong>Last Updated:</strong> {data.get('date', 'N/A')}"
        
        return result
        
    except httpx.HTTPError as e:
        return f"Error fetching exchange rates: {str(e)}"
    except Exception as e:
        return f"Error converting currency: {str(e)}"


@tool
def get_currency_rates(base_currency: str = "USD") -> str:
    """
    Get current exchange rates for major currencies.
    
    Args:
        base_currency: Base currency code (default: 'USD')
    
    Returns:
        List of exchange rates for major currencies
    """
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
        
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        
        # Major currencies to display
        major_currencies = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY", "INR", "MXN"]
        
        result = f"<strong>Exchange Rates (Base: {base_currency.upper()})</strong><br><br>"
        result += f"<strong>As of:</strong> {data.get('date', 'N/A')}<br><br>"
        
        for currency in major_currencies:
            if currency in data["rates"] and currency != base_currency.upper():
                rate = data["rates"][currency]
                result += f"<strong>{currency}:</strong> {rate:.4f}<br>"
        
        return result
        
    except Exception as e:
        return f"Error fetching exchange rates: {str(e)}"


@tool
def check_delivery_delays(country_code: str = "US", delivery_date: Optional[str] = None) -> str:
    """
    Check for holidays and potential delivery delays for a specific country.
    
    Args:
        country_code: Two-letter country code (e.g., 'US', 'CA', 'GB', 'MX')
        delivery_date: Expected delivery date in YYYY-MM-DD format (optional)
    
    Returns:
        Information about holidays and potential delivery delays
    """
    try:
        current_year = datetime.now().year
        
        # Using date.nager.at - free public holiday API (no key needed)
        url = f"https://date.nager.at/api/v3/publicholidays/{current_year}/{country_code.upper()}"
        
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        holidays = response.json()
        
        result = f"<strong>Holiday & Delivery Information ({country_code.upper()})</strong><br><br>"
        
        # If specific delivery date provided, check around that date
        if delivery_date:
            try:
                target_date = datetime.strptime(delivery_date, "%Y-%m-%d")
                result += f"<strong>Target Delivery Date:</strong> {target_date.strftime('%B %d, %Y')}<br><br>"
                
                # Check for holidays within 7 days of delivery date
                nearby_holidays = []
                for holiday in holidays:
                    holiday_date = datetime.strptime(holiday["date"], "%Y-%m-%d")
                    days_diff = abs((holiday_date - target_date).days)
                    if days_diff <= 7:
                        nearby_holidays.append({
                            "name": holiday["name"],
                            "date": holiday["date"],
                            "days_diff": days_diff
                        })
                
                if nearby_holidays:
                    result += "<strong>Nearby Holidays (may affect delivery):</strong><br>"
                    for h in nearby_holidays:
                        date_obj = datetime.strptime(h["date"], "%Y-%m-%d")
                        result += f"• {h['name']} - {date_obj.strftime('%B %d')} "
                        if h['days_diff'] == 0:
                            result += "(on delivery day!)<br>"
                        else:
                            result += f"({h['days_diff']} days away)<br>"
                    result += "<br><strong>Recommendation:</strong> Consider alternative delivery date to avoid delays.<br>"
                else:
                    result += "<strong>No holidays near delivery date.</strong> Delivery should proceed normally.<br>"
                    
            except ValueError:
                result += "Invalid date format. Please use YYYY-MM-DD.<br><br>"
        
        # Show upcoming holidays
        today = datetime.now()
        upcoming = [h for h in holidays if datetime.strptime(h["date"], "%Y-%m-%d") >= today][:5]
        
        if upcoming:
            result += "<br><strong>Upcoming Holidays ({} {}):</strong><br>".format(country_code.upper(), current_year)
            for holiday in upcoming:
                date_obj = datetime.strptime(holiday["date"], "%Y-%m-%d")
                result += f"• {holiday['name']} - {date_obj.strftime('%B %d, %Y')}<br>"
        
        return result
        
    except httpx.HTTPError as e:
        return f"Error fetching holiday information. Country code '{country_code}' may not be supported. Try: US, CA, GB, MX, DE, FR, etc."
    except Exception as e:
        return f"Error checking holidays: {str(e)}"


@tool
def calculate_business_days(start_date: str, business_days: int, country_code: str = "US") -> str:
    """
    Calculate a target date by adding business days (excluding weekends and holidays).
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        business_days: Number of business days to add
        country_code: Two-letter country code for holiday calendar (default: 'US')
    
    Returns:
        Target delivery date excluding weekends and holidays
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        current_year = start.year
        
        # Get holidays for the country
        url = f"https://date.nager.at/api/v3/publicholidays/{current_year}/{country_code.upper()}"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        holidays_data = response.json()
        
        # Convert to date objects
        holiday_dates = {datetime.strptime(h["date"], "%Y-%m-%d").date() for h in holidays_data}
        
        # Calculate business days
        current_date = start
        days_counted = 0
        
        while days_counted < business_days:
            current_date += timedelta(days=1)
            # Skip weekends (5=Saturday, 6=Sunday)
            if current_date.weekday() < 5 and current_date.date() not in holiday_dates:
                days_counted += 1
        
        result = f"<strong>Business Days Calculator</strong><br><br>"
        result += f"<strong>Start Date:</strong> {start.strftime('%B %d, %Y')}<br>"
        result += f"<strong>Business Days:</strong> {business_days}<br>"
        result += f"<strong>Target Date:</strong> {current_date.strftime('%B %d, %Y')}<br>"
        result += f"<strong>Country:</strong> {country_code.upper()}<br><br>"
        result += f"<em>Calculation excludes weekends and public holidays in {country_code.upper()}</em>"
        
        return result
        
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD for start_date."
    except Exception as e:
        return f"Error calculating business days: {str(e)}"
