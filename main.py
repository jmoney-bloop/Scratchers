import requests
from bs4 import BeautifulSoup
import pandas as pd

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
            "Ticket Price": f"${ticket_price_num}",
            "Top Prize": top_prize,
            "Odds": odds,
            "Original Tickets": f"{original_tickets:,}",
            "Current Tickets": f"{current_tickets:,}",
            "Expected Value": f"${expected_value:.2f}",
            "ROI Percentage": roi,
            "Total Prize Pool Remaining": f"${current_df['Remaining Prize Amount'].sum():,.2f}",
        }

        games_data.append(game_data)

    except Exception as e:
        print(f"Error processing {name}: {str(e)}")
        continue

# Create DataFrame and save
df = pd.DataFrame(games_data)

# Sort by expected value (best games first)
df = df.sort_values('ROI Percentage', ascending=False)

df.to_csv("Lottodata.csv", index=False)