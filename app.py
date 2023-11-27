from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import re
import os
import unicodedata

app = Flask(__name__)

# Normalising French characters
def normalize_string(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


# Function to check if all words in a keyword are in a text (case insensitive)
def all_words_present(text, keyword):
    if isinstance(text, str):
        text_lower = text.lower()
        return all(word.lower() in text_lower for word in keyword.split())
    else:
        return False

# Function to check if all words in a keyword are fully present in a text (case insensitive)
def all_words_fully_present(text, keyword):
    if isinstance(text, str):
        text_lower = text.lower().split()
        return all(word.lower() in text_lower for word in keyword.split())
    else:
        return False

# Function to find exact match in a DataFrame column
def find_exact_match(df, column, keyword):
    return df[df[column].apply(lambda x: all_words_present(x, keyword))]

# Function to find partial match in a DataFrame column
def find_partial_match(df, column, keyword):
    return df[df[column].apply(lambda x: all_words_fully_present(x, keyword))]

# Function to extract shop name from URL
def extract_shop_from_url(url):
    if 'auchan' in url:
        return 'Auchan'
    elif 'monoprix' in url:
        return 'Monoprix'
    elif 'franprix' in url:
        return 'Franprix'
    elif 'carrefour' in url:
        return 'Carrefour'
    else:
        return 'Unknown'

def load_data(file_path):
    df = pd.read_csv(file_path)
    # Remove special characters and diacritics from all string columns except the URL column
    for col in df.columns:
        if col != 'URL' and df[col].dtype == object:
            df[col] = df[col].str.replace('[^\w\s]', '', regex=True)
            #df[col] = df[col].apply(remove_diacritics)
    df['Shop'] = df['URL'].apply(extract_shop_from_url)
    df['DescBrand'] = df['Brand'].astype(str) + ' ' + df['Description'].astype(str)
    return df

# Read data from Excel file
# df = pd.read_excel('./unique_supermarket_prices.xlsx')

# Convert the DataFrame to a dictionary
# products = df.to_dict(orient="index")
# products = {str(k).lower(): v for k, v in products.items()}
# products = {k.lower(): v for k, v in products.items()}

@app.route('/', methods=['GET'])
def landing():
    try:
        # Load data from Excel file
        df = pd.read_excel('./arrondissements.xlsx')
        
        # Check if 'ZIP_code' column exists
        if 'ZIP_code' not in df.columns:
            raise ValueError("Column 'ZIP_code' not found in Excel file")

        # Combine columns
        arrondissements = [f"{row['Arrondissement']} ({row['ZIP_code']})" for _, row in df.iterrows()]
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        arrondissements = []  # Return an empty list in case of error

    # Pass the arrondissements data to the landing.html template
    return render_template('landing.html', arrondissements=arrondissements)



# shopping list with a sophisticated autocompletion
@app.route('/shopping_list', methods=['GET', 'POST'])
def shopping_list():
    # Load data from price_comprix.csv
    df = pd.read_csv('price_comprix.csv')  # Adjust the path if needed

    # Assuming df is your DataFrame
    print(df.columns)  # To check if 'Core Identity' is in the columns
    print(df.head())   # To see the first few rows of the DataFrame

    # Extracting the necessary columns
    descriptions = df['Description'].dropna().unique().tolist()
    brands = df['Brand'].dropna().unique().tolist()
    category = df['category'].dropna().unique().tolist()

    # Read categories from Excel (this is for the aisles)
    df_categories = pd.read_excel('categories.xlsx')
    # categories = [{'name': cat, 'image': cat.lower().replace(' ', '_') + '.jpg'} for cat in df_categories['category'].dropna().unique()]
    # categories = [{'name': cat, 'image': cat.lower().replace(' ', '_').replace('&', 'and').replace('è', 'e') + '.jpg'} for cat in df_categories['category'].dropna().unique()]
    categories = [
    {
        'name': cat, 
        'image': normalize_string(cat).lower().replace(' ', '_').replace('&', 'and') + '.jpg'
    } 
    for cat in df_categories['category'].dropna().unique()
]
    
    # Sending the data to the frontend (noe the difference: categories are the aisles, category comes into the serach bar and price comparison)
    return render_template('shopping_list.html', 
                           descriptions=descriptions, 
                           brands=brands,
                           category=category,
                            categories=categories)


# SUBCATEGORIES PAGE (Different Fruits) (Subcategories of a given Category, browsing through the subcategories.xlxs)
@app.route('/category/<category_name>')
def category_page(category_name):
    # Read the Excel file
    df = pd.read_excel('./subcategories.xlsx')

    # Get the subcategories for the specified category
    raw_subcategories = df[category_name].dropna().tolist()

    # Create a list of dictionaries for subcategories with name and image
    subcategories = [
        {
            'name': subcategory, 
            'image': normalize_string(subcategory).lower().replace(' ', '_') + '.png'
        } 
        for subcategory in raw_subcategories
    ]

    return render_template('category_page.html', 
                           subcategories=subcategories, 
                           category_name=category_name)


# SUBCATEGORIES2 PAGE (Different Dried fruits) (Subcategories2 of a given Subcategory, browsing through the subcategories2.xlxs)

@app.route('/subcategory/<subcategory_name>')
def subcategory_page(subcategory_name):
    try:
        # Read the Excel file
        df = pd.read_excel('./subcategories2.xlsx')

        # Normalize the subcategory_name for case-insensitive matching
        normalized_subcategory_name = normalize_string(subcategory_name).lower()

        # Check if the normalized subcategory name is in the DataFrame's columns
        if normalized_subcategory_name not in [normalize_string(col).lower() for col in df.columns]:
            raise ValueError(f"Subcategory {subcategory_name} not found")

        # Get the index of the subcategory column after normalization
        subcategory_col_index = [normalize_string(col).lower() for col in df.columns].index(normalized_subcategory_name)

        # Select the column corresponding to the subcategory
        subcategory_column = df.iloc[:, subcategory_col_index]

        # Get the items and images for the specified subcategory, skipping the header row
        subcategory2_items = []
        for i in range(1, len(subcategory_column)):  # Skip the header
            item_name = subcategory_column.iloc[i]
            if pd.notna(item_name):  # Check if the item name is not NaN
                image_filename = normalize_string(item_name).lower().replace(' ', '_') + '.png'
                # Append a dictionary with the item name and image filename
                subcategory2_items.append({
                    'name': item_name,
                    'image': image_filename
                })

    except Exception as e:
        print(f"An error occurred: {e}")
        subcategory2_items = []

    return render_template('subcategory_page.html',
                           subcategory2_items=subcategory2_items,
                           subcategory_name=subcategory_name)




#RECIPES

@app.route('/recipes')

def recipes():
    product_names = [str(name).lower() for name in df.index.tolist()]
    return render_template('recipes.html', product_names=product_names)



@app.route('/compare_prices', methods=['GET'])
def compare_prices():
    file_path = 'price_comprix.csv'  # Adjust the path if needed
    df = load_data(file_path)

    shopping_list_text = request.args.get('shopping_list', '')
    shopping_list = re.split(',|\n', shopping_list_text.lower())
    shopping_list = [item.strip() for item in shopping_list if item.strip()]

    category_column = 'category'
    descbrand_column = 'DescBrand'
    all_cheapest_items = pd.DataFrame()

    for keyword in shopping_list:
        match_source = None
        df_keyword = find_exact_match(df, category_column, keyword)
        if not df_keyword.empty:
            match_source = 'category'
        if df_keyword.empty:
            df_keyword = find_partial_match(df, descbrand_column, keyword)
            if not df_keyword.empty:
                match_source = 'descbrand'

        if not df_keyword.empty:
            df_keyword['Shop'] = df_keyword['URL'].apply(extract_shop_from_url)
            cheapest_items = df_keyword.loc[df_keyword.groupby('Shop')['Price'].idxmin()]
            label = keyword if match_source == 'descbrand' else df_keyword[category_column].iloc[0]
            cheapest_items[category_column] = label
            cheapest_items['Keyword'] = keyword
            all_cheapest_items = pd.concat([all_cheapest_items, cheapest_items], ignore_index=True)

    # Initialize pivot_prices and pivot_urls
    pivot_prices = pd.DataFrame()
    pivot_urls = pd.DataFrame()

    if not all_cheapest_items.empty:
        all_cheapest_items['Shop'] = all_cheapest_items['URL'].apply(extract_shop_from_url)
        pivot_prices = all_cheapest_items.pivot(index='Keyword', columns='Shop', values='Price')
        pivot_urls = all_cheapest_items.pivot(index='Keyword', columns='Shop', values='URL')

        for index, row in pivot_prices.iterrows():
            empty_shops = row[row.isna()].index.tolist()
            if empty_shops:
                cheapest_shop = row.idxmin()
                cheapest_item_url = pivot_urls.at[index, cheapest_shop]
                category_of_cheapest = df[df['URL'] == cheapest_item_url][category_column].iloc[0]

                for shop in empty_shops:
                    cheapest_in_category = df[(df['Shop'] == shop) & (df[category_column] == category_of_cheapest)].nsmallest(1, 'Price')
                    if not cheapest_in_category.empty:
                        pivot_prices.at[index, shop] = cheapest_in_category.iloc[0]['Price']
                        pivot_urls.at[index, shop] = cheapest_in_category.iloc[0]['URL']
         
        
        # Check if pivot_prices is not empty before calculating totals
        if not pivot_prices.empty:
            total_prices = pivot_prices.sum().to_dict()
        else:
            total_prices = {}

    # Export the results to a CSV file
    output_csv_file = 'comparison_results.csv'  # You can change this file name and path as needed
    all_cheapest_items.to_csv(output_csv_file, index=False)

    # Convert pivot_prices to a dictionary format for Jinja2
    pivot_prices_dict = {}
    if not pivot_prices.empty:
        pivot_prices_dict = pivot_prices.fillna('N/A').to_dict(orient='index')

    store_names = list(pivot_prices.columns) if not pivot_prices.empty else []
    
    # Convert pivot_urls to a dictionary format for Jinja2
    pivot_urls_dict = pivot_urls.to_dict(orient='index') if not pivot_urls.empty else {}


    return render_template('compare_results.html', 
                           pivot_prices_html=pivot_prices.to_html(classes='pivot-table', border=0) if not pivot_prices.empty else "",
                           pivot_urls_html=pivot_urls.to_html(classes='pivot-table', border=0) if not pivot_urls.empty else "",
                           pivot_prices_dict=pivot_prices_dict,
                           store_names=store_names,
                           total_prices=total_prices,
                           pivot_urls_dict=pivot_urls_dict)



@app.route('/blog')
def blog():
    return render_template('blog.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)