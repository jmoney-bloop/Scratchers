import requests
from bs4 import BeautifulSoup
import pandas as pd


def format_currency(value):
    """Format a number as currency with commas and dollar sign"""
    if pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def format_large_number(value):
    """Format large numbers with commas"""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def all_urls():
    start_url = 'https://www.mslottery.com/gamestatus/active/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    # Fetch the page content
    response = requests.get(start_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    all_links = [a['href'] for a in soup.find_all('a', href=True)]

    # Optional: Filter to unique links
    unique_links = list(set(all_links))

    # Display as DataFrame
    df = pd.DataFrame(unique_links, columns=['URL'])
    return game_urls(df)


def game_urls(df):
    game_url = []
    for game in df['URL']:
        if "instantgames" in game:
            game_url.append(game)
    return game_url


def calculate_expected_value(current_df, current_tickets, ticket_price_num):
    """
    Calculate expected value for a lottery game.

    Expected Value = (Sum of all prize values * their probabilities) - ticket cost
    Probability of winning each prize = remaining_count / total_remaining_tickets
    """
    if current_tickets == 0:
        return -ticket_price_num  # If no tickets left, you lose your money

    # Calculate expected value from prizes using vectorized operations
    prize_values = current_df['Prize Value'].values
    remaining_counts = current_df['Remaining Prize Count'].values

    # Calculate probabilities for each prize tier
    probabilities = remaining_counts / current_tickets

    # Calculate contribution from each prize tier
    prize_contributions = prize_values * probabilities

    # Sum all contributions
    expected_prize_value = prize_contributions.sum()

    # Expected value = expected prize value - cost of ticket
    expected_value = expected_prize_value - ticket_price_num

    return expected_value


def calculate_ev_details(current_df, current_tickets, ticket_price_num):
    """
    Calculate detailed EV breakdown for analysis
    """
    ev_breakdown = []

    if current_tickets == 0:
        return ev_breakdown, -ticket_price_num

    total_ev = 0

    for _, row in current_df.iterrows():
        prize_value = row['Prize Value']
        remaining_count = row['Remaining Prize Count']

        probability = remaining_count / current_tickets
        contribution = prize_value * probability
        total_ev += contribution

        ev_breakdown.append({
            'Prize Value': prize_value,
            'Remaining Count': remaining_count,
            'Probability': probability,
            'EV Contribution': contribution
        })

    # Subtract ticket cost
    final_ev = total_ev - ticket_price_num

    return ev_breakdown, final_ev


# Main processing
urls = all_urls()
games_data = []

for item in urls:
    try:
        name = item.replace('https://www.mslottery.com/instantgames/', '')
        name = name.replace('/', '')

        data = pd.read_html(item)
        launch_df = data[0]
        current_df = data[1]

        # Debug: Print column names to understand structure
        print(f"Processing {name}")
        print(f"Launch DF columns: {launch_df.columns.tolist()}")
        print(f"Current DF columns: {current_df.columns.tolist()}")
        print(f"Current DF shape: {current_df.shape}")

        # Extract basic info with better error handling
        try:
            ticket_price = launch_df.loc[launch_df[0] == "Ticket Price", 1].values[0]
        except:
            print(f"Could not find Ticket Price for {name}")
            continue

        try:
            top_prize = launch_df.loc[launch_df[0] == "Top Prize", 1].values[0]
        except:
            print(f"Could not find Top Prize for {name}")
            continue

        try:
            odds = launch_df.loc[launch_df[0] == "Overall Odds", 1].values[0]
        except:
            print(f"Could not find Overall Odds for {name}")
            continue

        # Validate current_df has required columns
        required_columns = ['Prize Value', 'Remaining Prize Count', 'Original Prize Count']
        missing_columns = [col for col in required_columns if col not in current_df.columns]

        if missing_columns:
            print(f"Missing required columns for {name}: {missing_columns}")
            print(f"Available columns: {current_df.columns.tolist()}")
            continue

        # Clean and convert prize values with validation
        try:
            current_df['Prize Value'] = current_df['Prize Value'].replace('[\$,]', '', regex=True).astype(float)
        except Exception as e:
            print(f"Error converting Prize Value for {name}: {e}")
            continue

        # Calculate remaining prize amount safely
        try:
            current_df['Remaining Prize Amount'] = current_df['Prize Value'].values * current_df[
                'Remaining Prize Count'].values
        except Exception as e:
            print(f"Error calculating Remaining Prize Amount for {name}: {e}")
            continue

        # Calculate ticket counts with validation
        try:
            odd_calculator = float(odds.split(":")[1])
            total_original_prizes = current_df["Original Prize Count"].sum()
            total_remaining_prizes = current_df['Remaining Prize Count'].sum()

            original_tickets = float(total_original_prizes * odd_calculator)
            current_tickets = float(total_remaining_prizes * odd_calculator)

            ticket_price_num = float(ticket_price.replace("$", ''))
        except Exception as e:
            print(f"Error calculating ticket counts for {name}: {e}")
            continue

        # Calculate expected value
        try:
            # Debug: Show the current_df structure
            print(f"Current DF for {name}:")
            print(current_df[['Prize Value', 'Remaining Prize Count']].head())
            print(f"Total remaining tickets: {current_tickets}")

            expected_value = calculate_expected_value(current_df, current_tickets, ticket_price_num)

            # Calculate detailed breakdown (optional - for analysis)
            ev_breakdown, ev_check = calculate_ev_details(current_df, current_tickets, ticket_price_num)

            print(f"Expected Value: {expected_value}")
            print(f"EV Check (should match): {ev_check}")

            # Calculate additional metrics
            current_df['Money Back'] = current_df['Prize Value'] >= ticket_price_num
            money_back_prizes = current_df[current_df['Money Back']]['Remaining Prize Count'].sum()

            # ROI calculation
            roi = (expected_value / ticket_price_num) * 100 if ticket_price_num > 0 else 0

        except Exception as e:
            print(f"Error calculating EV for {name}: {e}")
            continue

        game_data = {
            "Name": name,
            "Ticket Price": ticket_price_num,
            "Top Prize": top_prize,
            "Odds": odds,
            "Original Tickets": original_tickets,
            "Current Tickets": current_tickets,
            "Expected Value": expected_value,
            "ROI Percentage": roi,
            "Money Back Prizes Remaining": money_back_prizes,
            "Total Prize Pool Remaining": current_df['Remaining Prize Amount'].sum(),
            "EV Breakdown": ev_breakdown  # Store detailed breakdown
        }

        games_data.append(game_data)

    except Exception as e:
        print(f"Error processing {name}: {str(e)}")
        continue

# Create DataFrame and save
df = pd.DataFrame(games_data)

# Sort by expected value (best games first)
df_sorted = df.sort_values('Expected Value', ascending=False)

# Create a formatted version for display
df_display = df_sorted.copy()

# Format currency columns
currency_columns = ['Ticket Price', 'Expected Value', 'Total Prize Pool Remaining']
for col in currency_columns:
    if col in df_display.columns:
        df_display[f'{col} (Formatted)'] = df_display[col].apply(format_currency)

# Format large number columns
df_display['Original Tickets (Formatted)'] = df_display['Original Tickets'].apply(format_large_number)
df_display['Current Tickets (Formatted)'] = df_display['Current Tickets'].apply(format_large_number)
df_display['Money Back Prizes Remaining (Formatted)'] = df_display['Money Back Prizes Remaining'].apply(
    format_large_number)

# Format ROI as percentage
df_display['ROI (Formatted)'] = df_display['ROI Percentage'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")

# Save to CSV (original unformatted data)
df_csv = df_sorted.drop('EV Breakdown', axis=1, errors='ignore')
df_csv.to_csv("Lottodata.csv", index=False)

# Display top games with formatting
print("Top 10 Games by Expected Value:")
display_columns = ['Name', 'Ticket Price (Formatted)', 'Expected Value (Formatted)', 'ROI (Formatted)']
print(df_display[display_columns].head(10).to_string(index=False))

# Display games with positive expected value
positive_ev = df_sorted[df_sorted['Expected Value'] > 0]
if not positive_ev.empty:
    print(f"\n🎉 Games with Positive Expected Value ({len(positive_ev)} found):")
    positive_display = positive_ev.copy()
    for col in currency_columns:
        if col in positive_display.columns:
            positive_display[f'{col} (Formatted)'] = positive_display[col].apply(format_currency)
    positive_display['ROI (Formatted)'] = positive_display['ROI Percentage'].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    print(positive_display[display_columns].to_string(index=False))
else:
    print("\n❌ No games with positive expected value found.")

# Summary statistics
print(f"\n📊 Summary Statistics:")
print(f"Total games analyzed: {len(df_sorted)}")
print(f"Best Expected Value: {format_currency(df_sorted['Expected Value'].max())}")
print(f"Worst Expected Value: {format_currency(df_sorted['Expected Value'].min())}")
print(f"Average Expected Value: {format_currency(df_sorted['Expected Value'].mean())}")
print(f"Best ROI: {df_sorted['ROI Percentage'].max():.2f}%")
print(f"Average ROI: {df_sorted['ROI Percentage'].mean():.2f}%")