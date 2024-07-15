"""Run this file to analyse the league results."""
import matplotlib.pyplot as plt
import pandas as pd

from gsheets import get_gsheet_worksheet


def main():
    """Run the analysis."""
    # import the match results and person data from Google sheets
    match_results_df = import_results("Match Results")
    match_results_processed_df = process_match_results(match_results_df)

    players_df = import_results("Players")
    players_df = process_player_results(players_df)

    print(match_results_df.head(5).to_markdown())
    print(match_results_processed_df.head(5).to_markdown())
    print(players_df.to_markdown())
    players_df.to_csv("players.csv")

    print(f"Unique Player {players_df['Player'].nunique()}")
    print(f"Unique Clubs {match_results_processed_df['Club'].nunique()}")
    print(f"Unique Matches {match_results_processed_df['Match ID'].nunique()}")
    print(f"Rubbers Played {match_results_processed_df['Score'].sum()}")

    create_division_charts(match_results_processed_df)

    # Process data to extract the match results and person data

    # Create a visual for each division of league on standings over time

    # identify the Top individuals for each division

    # Get Top level KPIS
    # Number of games played
    # Number of points played
    # Number of different players


def process_match_results(df: pd.DataFrame) -> pd.DataFrame:
    """Process the match results data.

    Give each match an ID
    split the score field into two columns,
    Align the home and away scores into a single column,
    Calculate the accumulative score for each team over time.
    """
    df["Match ID"] = df.index
    df[["Home Score", "Away Score"]] = (
        df["Score"].str.split("-", expand=True).astype(int).rename({"Score": "Score Text"})
    )
    df["Match Date"] = pd.to_datetime(df["Match Date"])
    shared_columns = [
        "Division",
        "Status",
        "Match Date",
        "Time",
        "Courts",
        "Team",
        "Score",
        "Match ID",
    ]
    home_columns = {"Home Team": "Team", "Home Score": "Score"}
    away_columns = {"Away Team": "Team", "Away Score": "Score"}
    df = pd.concat(
        [
            df.rename(columns=home_columns)[shared_columns],
            df.rename(columns=away_columns)[shared_columns],
        ]
    )
    df = df.sort_values(by=["Match Date", "Time"])
    df["Running Total"] = df.groupby(["Division", "Team"])[["Score"]].cumsum()
    df["Matches Played"] = df.groupby(["Division", "Team"])[["Score"]].cumcount() + 1

    df["Current Rank"] = df.groupby(["Division", "Matches Played"])["Running Total"].rank(
        ascending=True, method="max"
    )

    # Get club from team by removing the division strings "Ladies, Open, Mixed" and anything after
    df["Club"] = df["Team"].str.replace(r"\s*(Ladies|Open|Mixed).*", "", regex=True)

    print("Processed Match Results")
    print(df.head(25).to_markdown())
    return df


def process_player_results(df: pd.DataFrame) -> pd.DataFrame:
    """Take the player raw data and prepares for analysis.

    Split Rubbers Won/Lost/Drawn into separate columns
    Convert Rating from Text to Numeric
    Split Matches Played into separate columns
    """
    # Split the 'Rubbers' column into 'Rubbers Won', 'Rubbers Lost', and 'Rubbers Drawn'
    df[["Rubbers Won", "Rubbers Lost", "Rubbers Drawn"]] = (
        df["Rubbers"].str.split("/", expand=True).astype(int)
    )

    # Convert the 'Rating' column from percentage string to numeric
    df["Rating"] = df["Rating"].str.rstrip("%").astype(float)

    # Split the 'Matches Played' column into 'Matches Played' and 'Fixtures'
    df[["Matches Played", "Potential Fixtures"]] = (
        df["Matches Played"].str.split("/", expand=True).astype(int)
    )

    df["Played Percentage"] = df["Matches Played"] / df["Potential Fixtures"]

    df_sorted = df.sort_values(by=["Rating", "Played Percentage"], ascending=False)

    # Drop the original 'Rubbers' and 'Matches Played / Fixtures' columns
    df_sorted = df.drop(columns=["Rubbers"])

    return df_sorted


def create_division_charts(match_results_df: pd.DataFrame) -> pd.DataFrame:
    """Create a chart for each division."""
    # Identify the different divisions
    divisions = match_results_df["Division"].unique()
    for division in divisions:
        create_division_chart(
            match_results_df, division, x_axis="Match Date", y_axis="Running Total"
        )
        create_division_chart(
            match_results_df, division, x_axis="Matches Played", y_axis="Current Rank"
        )


def create_division_chart(
    match_results_df: pd.DataFrame,
    division: str,
    x_axis: str = "Match Date",
    y_axis: str = "Running Total",
) -> None:
    """Create a chart for a single division for given X & Y axis."""
    # Create a chart for each division
    df = match_results_df[match_results_df["Division"] == division]
    fig, ax = plt.subplots(figsize=(10, 6))

    for team in df["Team"].unique():
        team_data = df[df["Team"] == team]
        final_result = team_data.iloc[-1]
        ax.plot(
            team_data[x_axis],
            team_data[y_axis],
            label=team,
            marker="o",
            markersize=5,
        )
        ax.text(
            team_data[x_axis].values[-1],
            team_data[y_axis].values[-1],
            f"{team} {final_result[y_axis]}",
            ha="left",
            va="center",
        )

    ax.set_xlabel(x_axis)
    ax.set_ylabel(y_axis)
    ax.set_title(f"{division} Standings: {y_axis} by {x_axis}")

    # Place the legend outside the chart to the right
    ax.legend(bbox_to_anchor=(1.2, 1), loc="upper left")

    # Save the chart to a file
    plt.savefig(f"{division}_Standings_{y_axis}_by_{x_axis}.png", bbox_inches="tight")

    # create a chart that shows the current score for each team over time.


def import_results(sheet_name: str) -> pd.DataFrame:
    """Import the results from the Google Sheet."""
    # File shared with digooglesheetsapi@wise-analyst-275114.iam.gserviceaccount.com
    file_location = (
        "https://docs.google.com/spreadsheets/d/1cAm73JBscnqmmTybAUzMX5TWStrbwFYlmt9BOv7lnJ0"
    )
    worksheet = get_gsheet_worksheet(file_location, sheet_name)
    return pd.DataFrame(worksheet.get_all_records())


if __name__ == "__main__":
    main()
