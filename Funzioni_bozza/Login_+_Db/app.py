from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo

app = Flask(__name__)

# Configura la connessione a MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp"  # Sostituisci con il tuo URI MongoDB
mongo = PyMongo(app)

app.secret_key = 'secret_key_12345'

# Route per la pagina di login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Cerca l'utente nel database
        user = mongo.db.users.find_one({"username": username})

        # Verifica che l'utente esista e che la password sia corretta
        if user and user['password'] == password:
            session['username'] = username  # Salva l'utente nella sessione
            return redirect(url_for('portal'))
        else:
            flash('Credenziali non valide!', 'error')

    return render_template('login.html')

# Route per il portale principale
@app.route('/portal')
def portal():
    if 'username' not in session:
        flash('Devi accedere prima di vedere il portale.', 'error')
        return redirect(url_for('login'))

    username = session['username']
    return render_template('portal.html', username=username)

# Route per la mappa
@app.route('/map')
def map_page():
    return render_template('map.html')

# Route per il logout
@app.route('/logout')
def logout():
    session.pop('username', None)  # Rimuovi l'utente dalla sessione
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))

# Pagina di dettaglio per un singolo dispositivo
@app.route("/product/<int:product_id>")
def product(product_id):
    prodotto = mongo.db.devices.find_one({"_id": product_id})
    if prodotto:
        return render_template("product.html", prodotto=prodotto)
    else:
        return "Dispositivo non trovato", 404

# API per fornire i dati dei dispositivi
@app.route("/api/devices")
def api_devices():
    devices = list(mongo.db.devices.find({}, {"_id": 1, "nome": 1, "lat": 1, "lng": 1, "stato": 1}))
    for device in devices:
        device["_id"] = int(device["_id"])
    return {"devices": devices}

if __name__ == '__main__':
    app.run(debug=True)
