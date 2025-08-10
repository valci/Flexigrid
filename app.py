import json
import requests
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
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

# --- Funções de Simulação de Investimento ---

def calculate_traditional_investment(months):
    """Calcula o valor futuro de um investimento tradicional (juros compostos)."""
    monthly_rate = (1 + TRADITIONAL_ANNUAL_RATE)**(1/12) - 1
    final_value = 0
    for _ in range(months):
        final_value = (final_value + INVESTMENT_AMOUNT) * (1 + monthly_rate)
    return final_value

def calculate_bitcoin_investment(months):
    """Calcula o valor de um investimento em Bitcoin usando a API da CoinGecko."""
    total_btc_purchased = 0
    today = datetime.now()

    # 1. Obter o preço atual do BTC em BRL
    try:
        current_price_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=brl"
        response = requests.get(current_price_url)
        response.raise_for_status()
        current_price_brl = response.json()['bitcoin']['brl']
    except requests.exceptions.RequestException as e:
        return f"Erro ao buscar preço atual do Bitcoin: {e}"

    # 2. Iterar pelos meses anteriores para simular a compra
    for i in range(months):
        past_date = today - relativedelta(months=i)
        date_str = past_date.strftime('%d-%m-%Y')

        try:
            # Aumentamos o delay para evitar o rate limiting da API
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
            # Se uma chamada falhar, podemos decidir se paramos ou continuamos.
            # Por enquanto, vamos continuar para obter uma estimativa parcial.
            continue

    # 3. Calcular o valor final
    final_value = total_btc_purchased * current_price_brl
    return final_value


# --- Rotas da Aplicação ---

@app.route('/', methods=['GET', 'POST'])
def index():
    transactions = load_transactions()

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

    simulation_results = None
    if request.method == 'POST':
        try:
            months_to_simulate = int(request.form.get('months', 12))
            if months_to_simulate > 0:
                traditional_result = calculate_traditional_investment(months_to_simulate)
                bitcoin_result = calculate_bitcoin_investment(months_to_simulate)
                simulation_results = {
                    "months": months_to_simulate,
                    "traditional": traditional_result,
                    "bitcoin": bitcoin_result
                }
        except (ValueError, TypeError):
            pass

    return render_template(
        'index.html',
        transactions=transactions,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        simulation_results=simulation_results,
        TRADITIONAL_ANNUAL_RATE=TRADITIONAL_ANNUAL_RATE
    )

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        trans_type = request.form['type']
        category = request.form['category']
        amount = float(request.form['amount'])
        date = request.form['date']
        transactions = load_transactions()
        new_transaction = {'type': trans_type, 'category': category, 'amount': amount, 'date': date}
        transactions.append(new_transaction)
        save_transactions(transactions)
        return redirect(url_for('index'))
    return render_template('add_transaction.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
