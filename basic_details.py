import pandas as pd

def convert_csv_to_excel(csv_file, excel_file):
    """
    Converts a CSV file into an Excel file.
    
    :param csv_file: Path to the input CSV file.
    :param excel_file: Path to the output Excel file.
    """
    try:
        # Read the CSV file
        data = pd.read_csv(csv_file)
        
        # Write to an Excel file
        data.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"Successfully converted '{csv_file}' to '{excel_file}'.")
    except Exception as e:
        print(f"Error converting file: {e}")

# Example usage
convert_csv_to_excel('new_data_.csv', 'basic_details.xlsx')
