from flask import Flask, render_template, request, redirect, url_for, session
from flask_babel import Babel
import pandas as pd
import re
import os
import unicodedata
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error as mysqlError


app = Flask(__name__)

# Define the function to get the current locale
def get_locale():
    return request.args.get('lang') or session.get('lang') or 'en'

# Babel configuration
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

# Initialize Babel
babel = Babel()
babel.init_app(app, locale_selector=get_locale)

bcrypt = Bcrypt(app)

# Database connection parameters (the authentification database)

db_params = {
    'database': 'comprix$user_auth_db',
    'user': 'comprix',
    #'password': os.environ.get('DATABASE_PASSWORD'),
    'password': 'testingout',
    'host': 'comprix.mysql.eu.pythonanywhere-services.com'
}

# Establish a database connection using MySQL connector
try:
    conn = mysql.connector.connect(**db_params)
    cur = conn.cursor(dictionary=True)  # Use dictionary=True to get dict cursor
except mysql.connector.Error as error:
    print("Error: ", error)
    
# Normalising French characters
def normalize_string(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

# Function to extract shop name from URL
def extract_shop_from_url(url):
    if not isinstance(url, str):
        return 'Unknown'  # Handle non-string URLs

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

#this function builds the mapping across all elements in category and those in Description
def build_relationship_map(df):
    # Preprocess the columns
    df['category'] = df['category'].str.replace('-', ' ', regex=False)
    df['Description'] = df['Description'].str.replace('-', ' ', regex=False)

    # Create the brand_cat column
    df['brand_cat'] = df['Brand'] + ' > in ' + df['category']

    category_to_descriptions = {}
    description_to_categories = {}
    brand_cat_to_descriptions = {}

    # Create initial mappings
    for _, row in df.iterrows():
        category = row['category']
        description = row['Description']
        brand_cat = row['brand_cat']

        # Add to category_to_descriptions
        category_to_descriptions.setdefault(category, set()).add(description)

        # Add to description_to_categories
        description_to_categories.setdefault(description, set()).add(category)

        # Add to brand_cat_to_descriptions
        brand_cat_to_descriptions.setdefault(brand_cat, set()).add(description)

    # Handle missing values in a general function
    def clean_mapping(mapping):
        return {k: {v for v in values if v and not pd.isna(v)} for k, values in mapping.items() if k and not pd.isna(k)}

    category_to_descriptions = clean_mapping(category_to_descriptions)
    description_to_categories = clean_mapping(description_to_categories)
    brand_cat_to_descriptions = clean_mapping(brand_cat_to_descriptions)

    return category_to_descriptions, description_to_categories, brand_cat_to_descriptions



def load_data(file_path):
    df = pd.read_csv(file_path)
    # Remove special characters and diacritics from all string columns except the URL column
    for col in df.columns:
        if col != 'URL' and df[col].dtype == object:
            df[col] = df[col].str.replace('[^\w\s]', '', regex=True)
            #df[col] = df[col].apply(remove_diacritics)
    df['Shop'] = df['URL'].apply(extract_shop_from_url)
    #df['DescBrand'] = df['Brand'].astype(str) + ' ' + df['Description'].astype(str)
    return df

def save_mappings_to_csv(category_to_descriptions, description_to_categories, brand_cat_to_descriptions):
    # Convert mappings to DataFrame
    cat_to_desc_df = pd.DataFrame(list(category_to_descriptions.items()), columns=['category', 'Description']).explode('Description')
    desc_to_cat_df = pd.DataFrame(list(description_to_categories.items()), columns=['Description', 'category']).explode('category')
    brand_cat_to_desc_df = pd.DataFrame(list(brand_cat_to_descriptions.items()), columns=['brand_cat', 'Description']).explode('Description')

    # Save to CSV
    cat_to_desc_df.to_csv('category_to_descriptions.csv', index=False)
    desc_to_cat_df.to_csv('description_to_categories.csv', index=False)
    brand_cat_to_desc_df.to_csv('brand_cat_to_descriptions.csv', index=False)

    print("Mappings saved to CSV files.")



# Load data from price_comprix_cleaned.csv
df = pd.read_csv('price_comprix_cleaned.csv')  # Adjust the path if needed

# Build the mappings
category_to_descriptions, description_to_categories, brand_cat_to_descriptions = build_relationship_map(df)

# Save the mappings to CSV
save_mappings_to_csv(category_to_descriptions, description_to_categories, brand_cat_to_descriptions)


def load_data(file_path):
    df = pd.read_csv(file_path)

# Remove rows with missing information Prices

    df = df.dropna(subset=['Price'])
###################################### FM: we may decide to reinstate this, but not sure
    
    # Remove special characters and diacritics from all string columns except the URL column
    for col in df.columns:
        if col != 'URL' and df[col].dtype == object:
            df[col] = df[col].str.replace('[^\w\s]', '', regex=True)
            #df[col] = df[col].apply(remove_diacritics)
    df['Shop'] = df['URL'].apply(extract_shop_from_url)
    df['DescBrand'] = df['Brand'].astype(str) + ' ' + df['Description'].astype(str)

    # Create the brand_cat column
    df['brand_cat'] = df['Brand'] + ' > in ' + df['category']
    return df


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


@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    session['lang'] = lang_code
    return redirect(request.referrer or url_for('landing'))


# shopping list with a sophisticated autocompletion
@app.route('/shopping_list', methods=['GET', 'POST'])
def shopping_list():
    # Load data from price_comprix_cleaned.csv
    df = pd.read_csv('price_comprix_cleaned.csv')  # Adjust the path if needed

    # Create the brand_cat column
    df['brand_cat'] = df['Brand'] + ' > in ' + df['category']

    # Assuming df is your DataFrame
    print(df.columns)  # To check if 'Core Identity' is in the columns
    print(df.head())   # To see the first few rows of the DataFrame

    # Extracting the necessary columns
    descriptions = df['Description'].dropna().unique().tolist()
    brands = df['Brand'].dropna().unique().tolist()
    category = df['category'].dropna().unique().tolist()
    brand_cats = df['brand_cat'].dropna().unique().tolist()

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
    
    # Sending the data to the frontend (note the difference: categories are the aisles, category comes into the serach bar and price comparison)
    return render_template('shopping_list.html', 
                           descriptions=descriptions, 
                           brands=brands,
                           category=category,
                           brand_cats=brand_cats,
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



#PRICE COMPARISON

@app.route('/compare_prices', methods=['GET'])
def compare_prices():
    main_file_path = 'price_comprix_cleaned.csv'  # Adjust the path for the main data
    mapping_file_path = 'category_to_descriptions.csv'  # Path for the category-to-description mapping
    
    # Load the image URLs> they need to be treated differently due to formatting
    df_images = pd.read_csv(main_file_path, usecols=['URL', 'image_small_url'], escapechar=None)
    df_images['image_small_url'] = df_images['image_small_url'].fillna('N/A').astype(str)

    # Load the brand_cat_to_desc mapping
    brand_cat_to_desc_df = pd.read_csv('brand_cat_to_descriptions.csv')  # Adjust the path if needed
    df = load_data(main_file_path)
    df.drop('image_small_url', axis=1, inplace=True)  # Remove the image_small_url column
    cat_to_desc_df = pd.read_csv(mapping_file_path)

    df_images = pd.read_csv(main_file_path, usecols=['URL', 'image_small_url'], escapechar=None)
    df_images['image_small_url'] = df_images['image_small_url'].fillna('N/A').astype(str)

    print(df_images['image_small_url'].head())  # Print first few URLs to check after loading

    # Extract shop information and drop rows where shop is 'Unknown'
    df['Shop'] = df['URL'].apply(lambda url: extract_shop_from_url(url))
    df = df[df['Shop'] != 'Unknown']

    shopping_list_text = request.args.get('shopping_list', '')
    shopping_list = re.split(',|\n', shopping_list_text.lower())
    shopping_list = [item.strip() for item in shopping_list if item.strip()]

    category_column = 'category'
    all_cheapest_items = pd.DataFrame()

    for keyword in shopping_list:
        for shop in df['Shop'].unique():
            direct_match = True  # Assume a direct match initially
            df_shop = df[df['Shop'] == shop]
            df_shop = df_shop[pd.to_numeric(df_shop['Price'], errors='coerce').notna()]

            # Check if keyword contains ' >' and search in 'brand_cat' if it does
            if ' >' in keyword:
                df_keyword = df_shop[df_shop['brand_cat'].str.contains(keyword, case=False, na=False)]
                cheapest_item = df_keyword.nsmallest(1, 'Price') if not df_keyword.empty else pd.DataFrame()

                if cheapest_item.empty:
                    direct_match = False
                    associated_descriptions = brand_cat_to_desc_df[brand_cat_to_desc_df['brand_cat'].str.lower().str.contains(keyword.lower())]['Description'].tolist()
                    df_associated_items = df_shop[df_shop['Description'].isin(associated_descriptions)]
                    df_associated_items = df_associated_items[pd.to_numeric(df_associated_items['Price'], errors='coerce').notna()]
                    cheapest_item = df_associated_items.nsmallest(1, 'Price') if not df_associated_items.empty else pd.DataFrame()

            else:
                # Search in 'category'
                df_keyword = df_shop[df_shop[category_column].str.lower() == keyword.lower()]
                if not df_keyword.empty:
                    cheapest_item = df_keyword.nsmallest(1, 'Price')
                else:
                    direct_match = False  # Not a direct match
                    # Search in 'Description'
                    df_keyword = df_shop[df_shop['Description'].str.contains(keyword, case=False, na=False)]
                    cheapest_item = df_keyword.nsmallest(1, 'Price') if not df_keyword.empty else pd.DataFrame()

                    # If not found, use category_to_description mapping
                    if cheapest_item.empty:
                        associated_descriptions = cat_to_desc_df[cat_to_desc_df['category'].str.lower() == keyword.lower()]['Description'].tolist()
                        df_associated_items = df_shop[df_shop['Description'].isin(associated_descriptions)]
                        df_associated_items = df_associated_items[pd.to_numeric(df_associated_items['Price'], errors='coerce').notna()]
                        cheapest_item = df_associated_items.nsmallest(1, 'Price') if not df_associated_items.empty else pd.DataFrame()

                    # Add the cheapest item or a placeholder for no match
            if not cheapest_item.empty:
                cheapest_item['Keyword'] = keyword
                cheapest_item['Shop'] = shop
                cheapest_item['Is Direct Match'] = direct_match
                cheapest_item['Nutriscore Grade'] = cheapest_item['nutriscore_grade']
                all_cheapest_items = pd.concat([all_cheapest_items, cheapest_item], ignore_index=True)
            else:
                no_match_item = pd.DataFrame({'Shop': [shop], 'Keyword': [keyword], 'Price': ['N/A'], 'URL': ['N/A'], 'Is Direct Match': [direct_match], 'Nutriscore Grade': ['N/A']})
                all_cheapest_items = pd.concat([all_cheapest_items, no_match_item], ignore_index=True)

    pivot_prices_dict = {}
    pivot_urls_dict = {}
    pivot_direct_match_dict = {}
    pivot_nutriscore_dict = {}
    pivot_image_url_dict = {}
    store_names = []

    if not all_cheapest_items.empty:
        grouped = all_cheapest_items.groupby(['Keyword', 'Shop']).agg({
            'Price': 'min', 
            'URL': 'first', 
            'Is Direct Match': 'first', 
            'Nutriscore Grade': 'first',
            'label_item': 'first',
            #'image_small_url': 'first'  # Include image_small_url  # Add label_item here
        }).reset_index()
        grouped['Shop'] = grouped['URL'].apply(lambda url: extract_shop_from_url(url))

        all_cheapest_items = all_cheapest_items.merge(df_images, on='URL', how='left')
        # Check columns after merge to confirm 'image_small_url' is present
        print("Columns in all_cheapest_items after merge:", all_cheapest_items.columns)


        pivot_prices = grouped.pivot(index='Keyword', columns='Shop', values='Price')
        pivot_urls = grouped.pivot(index='Keyword', columns='Shop', values='URL')
        pivot_direct_match_dict = grouped.pivot(index='Keyword', columns='Shop', values='Is Direct Match').fillna(True).to_dict(orient='index')
        pivot_nutriscore_dict = grouped.pivot(index='Keyword', columns='Shop', values='Nutriscore Grade').fillna('default').to_dict(orient='index')
        pivot_label_item_dict = grouped.pivot(index='Keyword', columns='Shop', values='label_item').fillna('N/A').to_dict(orient='index')

        #adding images to the table sent to html.
        # Now, create the pivot table for image_small_url from all_cheapest_items
        pivot_image_url_dict = all_cheapest_items.pivot(index='Keyword', columns='Shop', values='image_small_url').fillna('N/A').to_dict(orient='index')

        

        pivot_prices.drop(columns=['Unknown'], errors='ignore', inplace=True)
        pivot_urls.drop(columns=['Unknown'], errors='ignore', inplace=True)

        total_prices = pivot_prices.apply(pd.to_numeric, errors='coerce').sum().round(2)
        total_prices = total_prices.apply(lambda x: f"€{x}" if pd.notna(x) else x).rename('Total')
        pivot_prices = pd.concat([pivot_prices, total_prices.to_frame().T])

        pivot_prices_dict = pivot_prices.fillna('N/A').to_dict(orient='index')
        pivot_urls_dict = pivot_urls.to_dict(orient='index')
        store_names = list(pivot_prices.columns)

    output_csv_file = 'comparison_results.csv'
    all_cheapest_items.to_csv(output_csv_file, index=False)
    
    #debugging
    #print(pivot_nutriscore_dict)
    print(next(iter(pivot_image_url_dict.values())))  # Print first entry for check

    return render_template('compare_results.html', 
                           pivot_prices_dict=pivot_prices_dict,
                           pivot_urls_dict=pivot_urls_dict,
                           pivot_direct_match_dict=pivot_direct_match_dict,
                           pivot_nutriscore_dict=pivot_nutriscore_dict,
                           pivot_label_item_dict=pivot_label_item_dict,  # Add this
                           pivot_image_url_dict=pivot_image_url_dict, # Add this for sending the images
                           store_names=store_names,
                           total_prices=total_prices)



#RECIPES
@app.route('/recipes')
def recipes():
    return render_template('recipes.html')

#BLOG
@app.route('/blog')
def blog():
    return render_template('blog.html')

#BADGES
@app.route('/badges')
def badges():
    return render_template('sustainability_health_badges.html')

# Render the login page
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# Handle the login form submission
@app.route('/login', methods=['POST'])
def login_action():
    username = request.form.get('username')
    password = request.form.get('password')

    try:
        # Establish a database connection using MySQL
        conn = mysql.connector.connect(**db_params)
        cur = conn.cursor(dictionary=True)
        
        # Check user credentials
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            # Successful login
            session['username'] = username  # Start a session for the logged-in user
            return redirect(url_for('dashboard'))  # Redirect to the dashboard view function
        else:
            # Invalid credentials
            return 'Invalid username or password', 401

    except mysql.connector.Error as error:
        print(f"An error occurred: {error}")
        return 'Database connection error', 500
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


# Render the signup page
@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

# Handle the signup form submission
@app.route('/signup', methods=['POST'])
def signup_action():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')

    # Hash the password
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        # Establish a database connection using MySQL
        conn = mysql.connector.connect(**db_params)
        cur = conn.cursor()

        # Insert new user into the database
        cur.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                    (username, pw_hash, email))
        conn.commit()

        # After successful signup
        session['username'] = username  # Start a session for the logged-in user
        return redirect(url_for('dashboard'))  # Redirect to the dashboard view function

    except mysql.connector.Error as error:
        print(f"An error occurred: {error}")
        conn.rollback()
        if error.errno == mysql.connector.errorcode.ER_DUP_ENTRY:
            # Handle username or email already exists error
            return 'Username or email already exists', 409
        else:
            return 'Database error during signup', 500

    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


    # Redirect user to login page or dashboard after successful signup
    # For now, just returning a success message
    # return 'Sign-up successful', 200
# After successful signup
    session['username'] = username  # Start a session for the logged-in user
    return redirect(url_for('dashboard'))  # Redirect to the dashboard view function

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        # Fetch additional data as needed to display on the dashboard
        return render_template('dashboard.html')  # Render a dashboard template
    else:
        return redirect(url_for('login_page'))  # If not logged in, redirect to login
    

@app.route('/faq')
def faq():
    return render_template('faq.html')


## NEWSLETTER 
@app.route('/subscribe_newsletter', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if not email:
        return 'No email provided', 400

    try:
        conn = mysql.connector.connect(**db_params)
        cur = conn.cursor()

        # Insert the email into the newsletter_subscribers table
        cur.execute('INSERT INTO newsletter_subscribers (email) VALUES (%s)', (email,))
        conn.commit()
        return 'Subscription successful', 200
    except mysql.connector.Error as error:
        print(f"An error occurred: {error}")
        conn.rollback()
        return 'Database error', 500
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()

    

# Make sure to add a secret key for sessions to work
# app.secret_key = os.environ.get('SECRET_KEY')  # Replace with a real secret key
app.secret_key = 'testingout'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)