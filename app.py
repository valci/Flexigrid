import json
import requests
import uuid
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

app = Flask(__name__)

DATA_FILE = 'data.json'
INVESTMENT_AMOUNT = 100.0
TRADITIONAL_ANNUAL_RATE = 0.10

def load_transactions():
    """Carrega as transações do arquivo JSON."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_transactions(transactions):
    """Salva as transações no arquivo JSON."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, indent=4, ensure_ascii=False)

# --- Investment Simulation Functions (unchanged for now) ---
def calculate_traditional_investment(months):
    monthly_rate = (1 + TRADITIONAL_ANNUAL_RATE)**(1/12) - 1
    final_value = 0
    for _ in range(months):
        final_value = (final_value + INVESTMENT_AMOUNT) * (1 + monthly_rate)
    return final_value

def calculate_bitcoin_investment(months):
    # This function remains the same as before
    total_btc_purchased = 0
    today = datetime.now()
    try:
        current_price_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=brl"
        response = requests.get(current_price_url)
        response.raise_for_status()
        current_price_brl = response.json()['bitcoin']['brl']
    except requests.exceptions.RequestException as e:
        return f"Erro ao buscar preço atual do Bitcoin: {e}"
    for i in range(months):
        past_date = today - relativedelta(months=i)
        date_str = past_date.strftime('%d-%m-%Y')
        try:
            time.sleep(1.5)
            historical_price_url = f"https://api.coingecko.com/api/v3/coins/bitcoin/history?date={date_str}"
            response = requests.get(historical_price_url)
            response.raise_for_status()
            data = response.json()
            if 'market_data' in data and 'current_price' in data['market_data']:
                past_price_brl = data['market_data']['current_price']['brl']
                if past_price_brl > 0:
                    btc_bought = INVESTMENT_AMOUNT / past_price_brl
                    total_btc_purchased += btc_bought
        except requests.exceptions.RequestException as e:
            print(f"Aviso: Não foi possível buscar o preço do Bitcoin para {date_str}. Erro: {e}")
            continue
    final_value = total_btc_purchased * current_price_brl
    return final_value

# --- Main Application Routes ---

@app.route('/')
def index():
    # This route logic remains the same for now, but will be updated
    # to show the new edit/delete buttons
    transactions = load_transactions()
    transactions.sort(key=lambda x: x['date'], reverse=True) # Sort by date

    total_receitas = sum(t['amount'] for t in transactions if t['type'] == 'receita')
    total_despesas = sum(t['amount'] for t in transactions if t['type'] == 'despesa')

    for t in transactions:
        if t['type'] == 'despesa':
            t['percentage_of_income'] = (t['amount'] / total_receitas) * 100 if total_receitas > 0 else 0

    despesas_por_categoria = {}
    for t in transactions:
        if t['type'] == 'despesa':
            categoria = t['category']
            despesas_por_categoria[categoria] = despesas_por_categoria.get(categoria, 0) + t['amount']

    chart_labels = list(despesas_por_categoria.keys())
    chart_data = list(despesas_por_categoria.values())

    return render_template(
        'index.html',
        transactions=transactions,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        simulation_results=None, # Reset simulation on page load
        TRADITIONAL_ANNUAL_RATE=TRADITIONAL_ANNUAL_RATE
    )

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        transactions = load_transactions()

        trans_type = request.form['type']
        category = request.form['category']
        total_amount = float(request.form['amount'])
        date_str = request.form['date']
        installments = int(request.form.get('installments', 1) or 1)

        start_date = datetime.strptime(date_str, '%Y-%m-%d')

        if installments > 1 and trans_type == 'despesa':
            amount_per_installment = total_amount / installments
            for i in range(installments):
                installment_date = start_date + relativedelta(months=i)
                new_transaction = {
                    'id': str(uuid.uuid4()),
                    'type': trans_type,
                    'category': f"{category} ({i+1}/{installments})",
                    'amount': amount_per_installment,
                    'date': installment_date.strftime('%Y-%m-%d')
                }
                transactions.append(new_transaction)
        else:
            new_transaction = {
                'id': str(uuid.uuid4()),
                'type': trans_type,
                'category': category,
                'amount': total_amount,
                'date': date_str
            }
            transactions.append(new_transaction)

        save_transactions(transactions)
        return redirect(url_for('index'))

    return render_template('add_transaction.html')

@app.route('/edit/<transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    transactions = load_transactions()
    transaction_to_edit = next((t for t in transactions if t.get('id') == transaction_id), None)

    if transaction_to_edit is None:
        # Adicionar uma mensagem de erro ou redirecionar
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Atualiza os dados da transação
        transaction_to_edit['type'] = request.form['type']
        transaction_to_edit['category'] = request.form['category']
        transaction_to_edit['amount'] = float(request.form['amount'])
        transaction_to_edit['date'] = request.form['date']

        save_transactions(transactions)
        return redirect(url_for('index'))

    # Método GET: mostra o formulário de edição
    return render_template('edit_transaction.html', transaction=transaction_to_edit)

@app.route('/delete/<transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    transactions = load_transactions()
    transactions = [t for t in transactions if t.get('id') != transaction_id]
    save_transactions(transactions)
    return redirect(url_for('index'))

# Placeholder for investment simulation route, which is now separate
@app.route('/simulate', methods=['POST'])
def simulate():
    # This logic is moved from index() to its own route
    # to avoid re-running on every page load.
    # The implementation can be done in a later step if needed.
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
