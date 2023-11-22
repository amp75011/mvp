from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import re
import os
import unicodedata


app = Flask(__name__)

#normalising french characters
def normalize_string(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


# Read data from Excel file
df = pd.read_excel('./unique_supermarket_prices.xlsx')

# Convert the DataFrame to a dictionary
products = df.to_dict(orient="index")
products = {str(k).lower(): v for k, v in products.items()}
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
    # Assuming df is your DataFrame
    print(df.columns)  # To check if 'Core Identity' is in the columns
    print(df.head())   # To see the first few rows of the DataFrame

    # Extracting the necessary columns
    core_identity = df['Core Identity'].dropna().unique().tolist()
    extended_core_identity = df['Extended Core Identity'].dropna().unique().tolist()
    cleaned_description = df['Cleaned Description'].dropna().unique().tolist()

    # Read categories from Excel
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
    
    # Sending the data to the frontend
    return render_template('shopping_list.html', 
                           core_identity=core_identity, 
                           extended_core_identity=extended_core_identity, 
                           cleaned_description=cleaned_description,
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





#RECIPES

@app.route('/recipes')

def recipes():
    product_names = [str(name).lower() for name in df.index.tolist()]
    return render_template('recipes.html', product_names=product_names)



@app.route('/compare_prices', methods=['GET'])
def compare_prices():
    shopping_list_text = request.args.get('shopping_list', '')
    shopping_list = re.split(',|\n', shopping_list_text.lower())
    shopping_list = [item.strip() for item in shopping_list if item.strip()]
    
    results = []
    total_prices = {store: 0 for store in df.columns}
    
    for item in shopping_list:
        prices = products.get(item, {store: None for store in df.columns})
        results.append((item, prices))
        for store, price in prices.items():
            if price is not None:
                total_prices[store] += price

    min_total_price = min(total_prices.values())

    return render_template('compare_results.html', results=results, total_prices=total_prices, min_total_price=min_total_price)

@app.route('/blog')
def blog():
    return render_template('blog.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

