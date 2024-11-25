from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_pymongo import PyMongo

app = Flask(__name__, static_folder='assets', template_folder='templates')

# Configura la connessione a MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/ECOSIN"  # Sostituisci con il tuo URI MongoDB
mongo = PyMongo(app)

app.secret_key = 'secret_key_12'

# Route per la pagina di login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Cerca l'utente nel database
        user = mongo.db.Utenti.find_one({"username": username})

        # Verifica che l'utente esista e che la password corrisponda
        if user and user['password'] == password:
            session['username'] = username  # Salva l'utente nella sessione
            return redirect(url_for('portal_page'))  # Redirige alla mappa dopo il login
        else:
            flash('Credenziali non valide!', 'error')

    return render_template('login.html')

# Route per il logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Route per il portale
@app.route('/portal')
def portal_page():
    if 'username' in session:
        return render_template('portal.html')  # La pagina del portale che conterrà i bottoni
    else:
        flash('Devi essere loggato per accedere al portale!', 'error')
        return redirect(url_for('login'))

@app.route('/map')
def map_page():
    return render_template('map.html')  # La pagina della mappa

@app.route('/api/devices')
def get_devices():
    # Recupera tutte le posizioni dalla collezione Posizioni_Ecosin
    positions = mongo.db.Posizioni_Ecosin.find({}, {"_id": 0, "id_eco": 1, "latitudine": 1, "longitudine": 1, "id_ente": 1, "descrizione_ente": 1})

    # Crea una lista dei dispositivi da restituire
    devices_list = []
    for position in positions:
        device_id = position.get('id_eco')
        if not device_id:
            continue  # Salta questo documento se non ha l'id_eco

        # Recupera lo stato del dispositivo dalla collezione Stato_Ecosin
        status = mongo.db.Stato_Ecosin.find_one({"id_eco": device_id})

        # Se esiste uno stato per questo dispositivo, lo aggiungiamo
        if status:
            devices_list.append({
                "_id": device_id,  # Identificativo del dispositivo (id_eco)
                "nome": device_id,  # Nome del dispositivo (id_eco)
                "lat": position.get('latitudine'),  # Latitudine
                "lng": position.get('longitudine'),  # Longitudine
                "descrizione_ente": position.get('descrizione_ente', ''),  # Descrizione dell'ente
                "stato": {
                    "PLASTICA_BIDONE": status.get('plastica_bidone', 'N/A'),
                    "VETRO_BIDONE": status.get('vetro_bidone', 'N/A'),
                    "CARTA_BIDONE": status.get('carta_bidone', 'N/A'),
                    "PLASTICA_SCATOLA": status.get('plastica_scatola', 'N/A'),
                    "VETRO_SCATOLA": status.get('vetro_scatola', 'N/A'),
                    "CARTA_SCATOLA": status.get('carta_scatola', 'N/A'),
                }
            })

    return jsonify({"devices": devices_list})


if __name__ == '__main__':
    app.run(debug=True)
