from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import re
import os

app = Flask(__name__)

# Read data from Excel file
df = pd.read_excel('./unique_supermarket_prices.xlsx', index_col="Goods")

# Convert the DataFrame to a dictionary
products = df.to_dict(orient="index")
products = {k.lower(): v for k, v in products.items()}

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/shopping_list', methods=['GET', 'POST'])
def shopping_list():
    product_names = [name.lower() for name in df.index.tolist()]
    return render_template('shopping_list.html', product_names=product_names)


@app.route('/recipes')
def recipes():
    product_names = [name.lower() for name in df.index.tolist()]
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

