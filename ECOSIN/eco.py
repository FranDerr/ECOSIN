import random
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from flask import jsonify, request

# Inizializzazione dell'app Flask
app = Flask(__name__, static_folder='assets', template_folder='templates')

# Configura la connessione a MongoDB
app.config["MONGO_URI"] = "mongodb+srv://ECOSIN:ECOSINproject@ecosin.p1ac6.mongodb.net/ECOSIN?retryWrites=true&w=majority&ssl=true&tlsAllowInvalidCertificates=true"
mongo = PyMongo(app)

app.secret_key = 'secret_key_12345'

# Route per la pagina di login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verifica se l'utente esiste nel database
        user = mongo.db.Utenti.find_one({"username": username})

        # Confronta la password inserita con quella memorizzata
        if user and user['password'] == password:
            session['username'] = username  # Salva il nome utente nella sessione
            return redirect(url_for('portal'))  # Redirige alla pagina del portale
        else:
            flash('Invalid credentials!', 'error')  # Messaggio di errore
            return redirect(url_for('login'))

    return render_template('login.html')  # Mostra il modulo di login


# Route per il logout
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)  # Rimuove l'utente dalla sessione
    flash('You have been successfully logged out!', 'info')  # Messaggio di disconnessione
    return redirect(url_for('login'))

# Route per la pagina del portale
@app.route('/portal')
def portal():
    if 'username' in session:  # Se l'utente è loggato
        return render_template('portal.html', username=session['username'])  # Mostra la pagina del portale
    else:
        return redirect(url_for('login'))  # Se non è loggato, rimandalo al login

# Route per la pagina della mappa
@app.route('/map')
def map_page():
    return render_template('map.html')  # La pagina della mappa

# API per ottenere i dispositivi
@app.route('/api/devices')
def get_devices():
    # Recupera tutte le posizioni dei dispositivi dalla collezione Posizioni_Ecosin
    positions = mongo.db.Posizioni_Ecosin.find({}, {"_id": 0, "id_eco": 1, "latitudine": 1, "longitudine": 1, "id_ente": 1, "descrizione_ente": 1})
    devices_list = []  # Lista dei dispositivi
    for position in positions:
        device_id = position.get('id_eco')
        if not device_id:
            continue  # Salta questo documento se non ha l'id_eco

        # Recupera lo stato del dispositivo dalla collezione Stato_Ecosin
        status = mongo.db.Stato_Ecosin.find_one({"id_eco": device_id})

        # Se esiste lo stato del dispositivo, lo aggiunge alla lista
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
from datetime import datetime, timedelta

@app.route('/product/<device_id>')
def product_page(device_id):
    # Recupera le informazioni sulla posizione del dispositivo (eco)
    device = mongo.db.Posizioni_Ecosin.find_one({"id_eco": device_id})

    if device:
        # Recupera lo stato del bidone dalla collezione Stato_Ecosin
        stato = mongo.db.Stato_Ecosin.find_one({"id_eco": device_id})

        # Recupera informazioni sull'ente associato
        ente = mongo.db.Enti.find_one({"id_ente": device['id_ente']})

        # Recupera l'ultima manutenzione, ordinata per data (più recente)
        ultima_manutenzione = mongo.db.Manutenzioni.find_one({"id_eco": device_id}, sort=[("data_man", -1)])

        # Calcola la prossima manutenzione (aggiungi 30 giorni all'ultima manutenzione)
        if ultima_manutenzione:
            ultima_data = ultima_manutenzione['data_man']

            # Se la data è un oggetto datetime, convertila in stringa
            if isinstance(ultima_data, datetime):
                ultima_data_str = ultima_data.strftime("%Y-%m-%d")
            else:
                ultima_data_str = ultima_data

            # Aggiungi 30 giorni all'ultima manutenzione
            ultima_data_obj = datetime.strptime(ultima_data_str, "%Y-%m-%d")
            prossima_manutenzione = ultima_data_obj + timedelta(days=30)
            prossima_manutenzione = prossima_manutenzione.strftime("%Y-%m-%d")
        else:
            prossima_manutenzione = "Not available"

        # Calcola le percentuali per ciascun stato del bidone e della scatola
        percentuali = {
            'plastica_bidone': stato.get('plastica_bidone', 0),
            'vetro_bidone': stato.get('vetro_bidone', 0),
            'carta_bidone': stato.get('carta_bidone', 0),
            'plastica_scatola': stato.get('plastica_scatola', 0),
            'vetro_scatola': stato.get('vetro_scatola', 0),
            'carta_scatola': stato.get('carta_scatola', 0)
        }
        # Passa i dati al template della pagina del prodotto
        return render_template('product.html', device=device, stato=stato, ente=ente,
                               ultima_manutenzione=ultima_manutenzione, prossima_manutenzione=prossima_manutenzione,
                               percentuali=percentuali)
    else:
        # Se il dispositivo non esiste, restituisce un errore 404
        return "Product not found", 404

# Route per la pagina delle manutenzioni
@app.route('/manutenzioni', methods=['GET', 'POST'])
def maintenance_page():
    # Recupera gli enti dal database
    enti = mongo.db.Enti.find()  # Ottenere tutti gli enti

    # Calcola la data di domani
    tomorrow = (datetime.today() + timedelta(days=1)).date()  # Domani

    if request.method == 'POST':
        # Recupera i dati dal form (ente, azione, data e materiale)
        id_ente = request.form.get('ente')
        azione = request.form.get('azione')
        data_str = request.form.get('data')
        materiale = request.form.get('materiale')  # Tipo di materiale per ritiro (solo se necessario)

        # Verifica che tutti i campi necessari siano compilati
        if not id_ente or not azione or not data_str or (azione == 'ritiro' and not materiale):
            flash('Please fill in all fields!', 'error')
            return redirect(url_for('maintenance_page'))

        # Converte la data dal formato stringa a un oggetto datetime
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()

            # Verifica che la data sia almeno domani
            if data < tomorrow:
                flash('The date must be after or equal to tomorrow.', 'error')
                return redirect(url_for('maintenance_page'))

        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('maintenance_page'))

        # Verifica che l'ente esista nel database
        ente = mongo.db.Enti.find_one({'id_ente': id_ente})
        if not ente:
            flash(f"The entity with ID  {id_ente} not exists.", "error")
            return redirect(url_for('maintenance_page'))

        # Ottieni l'ID Eco associato all'ente
        posizione_eco = mongo.db.Posizioni_Ecosin.find_one({'id_ente': id_ente})
        if not posizione_eco:
            flash(f"No ecosin positions found for the entity {id_ente}.", "error")
            return redirect(url_for('maintenance_page'))

        id_eco = posizione_eco['id_eco']  # L'ID Eco corrispondente all'ente

        # Recupera un manutentore disponibile
        manutentori = list(mongo.db.Manutentori.find())
        if not manutentori:
            flash("No maintainers found in the database.", "error")
            return redirect(url_for('maintenance_page'))

        # Seleziona un manutentore casuale
        manutentore = random.choice(manutentori)
        cf_man = manutentore['cf_man']

        # Funzione per generare un codice unico per manutenzione o ritiro
        def get_next_code(action):
            if action == 'manutenzione':
                # Trova l'ultimo codice manutenzione nel database
                last_code = mongo.db.Manutenzioni.find().sort('cod_man', -1).limit(1)
                if last_code:
                    last_code = last_code[0]['cod_man']
                    number = int(last_code[3:])
                    new_code = f"MAN{str(number + 1).zfill(2)}"
                else:
                    new_code = "MAN01"
            elif action == 'ritiro':
                # Trova l'ultimo codice ritiro nel database
                last_code = mongo.db.Ritiri.find().sort('cod_r', -1).limit(1)
                if last_code:
                    last_code = last_code[0]['cod_r']
                    number = int(last_code[3:])
                    new_code = f"RIT{str(number + 1).zfill(2)}"
                else:
                    new_code = "RIT01"
            return new_code

        # Genera il codice univoco per manutenzione o ritiro
        codice_univoco = get_next_code(azione)

        # A seconda dell'azione (manutenzione o ritiro), salva i dati nel database
        if azione == 'manutenzione':
            manutenzione_data = {
                'cod_man': codice_univoco,
                'id_eco': id_eco,
                'data_man': data_str,
                'cf_man': cf_man,
                'id_ente': id_ente
            }
            mongo.db.Manutenzioni.insert_one(manutenzione_data)
            flash('Maintenance successfully recorded!', 'success')
            # Crea la comunicazione per manutenzione
            create_communication(id_ente, azione, data_str,materiale=None)

        elif azione == 'ritiro':
            # Recupera lo stato del dispositivo dal database
            stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})
            if not stato:
                flash(f"No status found for the id {id_eco}.", "error")
                return redirect(url_for('maintenance_page'))

            # Verifica che la percentuale di materiale nella scatola sia almeno 90%
            if materiale == "PLASTIC":
                scatola = stato.get('plastica_scatola', 0)
            elif materiale == "GLASS":
                scatola = stato.get('vetro_scatola', 0)
            elif materiale == "PAPER":
                scatola = stato.get('carta_scatola', 0)
            else:
                flash("Invalid material type", "error")
                return redirect(url_for('maintenance_page'))

            if scatola < 90:
                flash('The box must be at least 90% full to start the withdraw', 'error')
                return redirect(url_for('maintenance_page'))
            ritiro_data = {
                'cod_r': codice_univoco,
                'id_eco': id_eco,
                'data_r': data_str,
                'cf_man': cf_man,
                'id_ente': id_ente,
                'materiale': materiale
            }
            mongo.db.Ritiri.insert_one(ritiro_data)
            flash('Withdrawal successfully registered!', 'success')
            # Crea la comunicazione per ritiro
            create_communication(id_ente, azione, data_str,materiale)

            # Svuota la scatola dopo il ritiro
            if materiale == "PLASTIC":
                stato['plastica_scatola'] = 0
            elif materiale == "GLASS":
                stato['vetro_scatola'] = 0
            elif materiale == "PAPER":
                stato['carta_scatola'] = 0

            # Salva lo stato aggiornato nel database
            mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})

        return redirect(url_for('maintenance_page'))
    # Passa gli enti e la data di domani al template
    return render_template('maintenance.html', enti=enti, tomorrow=tomorrow)

# Route per la pagina delle manutenzioni da fare
@app.route('/maintenance_todo')
def maintenance_todo():
    if 'username' in session:
        today = datetime.now().strftime("%Y-%m-%d")

        # Recupera manutenzioni future unendo con Enti e Manutentori
        maintenances = mongo.db.Manutenzioni.aggregate([
            {
                "$match": {
                    "data_man": {"$gte": today}  # Filtra le date maggiori o uguali a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",
                    "localField": "id_ente",
                    "foreignField": "id_ente",
                    "as": "ente_info"
                }
            },
            {
                "$unwind": "$ente_info"  # Separa i dati uniti (uno per ogni ente)
            },
            {
                "$sort": {
                    "data_man": 1  # Ordina per data_m in ordine crescente (imminenti in cima)
                }
            },
            {
                "$lookup": {
                    "from": "Manutentori",
                    "localField": "cf_man",
                    "foreignField": "cf_man",
                    "as": "manutentore_info"
                }
            },
            {
                "$unwind": "$manutentore_info"  # Separa i dati uniti (uno per ogni manutentore)
            },
            {
                "$project": {
                    "_id": 0,
                    "cod_man": 1,
                    "data_man": 1,
                    "ente_nome": "$ente_info.nome_d",
                    "manutentore_nome": "$manutentore_info.nome_m",
                    "manutentore_cognome": "$manutentore_info.cognome_m"
                }
            }
        ])

        # Passa le manutenzioni al template
        return render_template('maintenance_todo.html', maintenances=maintenances)
    else:
        return redirect(url_for('login'))

# Route per la pagina dei ritiri da fare
@app.route('/withdrawals_todo')
def withdrawals_todo():
    if 'username' in session:
        today = datetime.now().strftime("%Y-%m-%d")

        # Recupera i ritiri futuri unendo con Enti e Manutentori
        withdrawals = mongo.db.Ritiri.aggregate([
            {
                "$match": {
                    "data_r": {"$gte": today}
                }
            },
            {
                "$lookup": {
                    "from": "Enti",
                    "localField": "id_ente",
                    "foreignField": "id_ente",
                    "as": "ente_info"
                }
            },
            {
                "$unwind": "$ente_info"
            },
            {
                "$sort": {
                    "data_r": 1 # Ordina per data di ritiro
                }
            },
            {
                "$lookup": {
                    "from": "Manutentori",
                    "localField": "cf_man",
                    "foreignField": "cf_man",
                    "as": "manutentore_info"
                }
            },
            {
                "$unwind": "$manutentore_info"
            },
            {
                "$project": {
                    "_id": 0,
                    "cod_r": 1,
                    "data_r": 1,
                    "ente_nome": "$ente_info.nome_d",
                    "manutentore_nome": "$manutentore_info.nome_m",
                    "manutentore_cognome": "$manutentore_info.cognome_m",
                    "materiale": 1
                }
            }
        ])

        return render_template('withdrawals_todo.html', withdrawals=withdrawals)
    else:
        return redirect(url_for('login'))

# Funzione per aggiornare le percentuali dei bidoni
def aggiorna_percentuali_bidone():
    dispositivi = mongo.db.Posizioni_Ecosin.find()

    for dispositivo in dispositivi:
        id_eco = dispositivo['id_eco']
        stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

        if stato:
            # Seleziona casualmente quale stato del bidone aggiornare
            stato_bidone = random.choice(['plastica_bidone', 'vetro_bidone', 'carta_bidone'])

            # Incremento casuale tra 1 e 2 percento
            incremento_bidone = random.randint(1, 2)

            stato_update = {}

            # Aggiorna solo se il valore nel bidone non è già al 100%
            if stato[stato_bidone] < 100:
                stato_update[stato_bidone] = min(100, stato.get(stato_bidone, 0) + incremento_bidone)

            # Aggiorna il database con il nuovo stato del bidone
            if stato_update:
                mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato_update})
                print(f"Updated bin percentage for {id_eco}: {stato_update}")
        else:
            print(f"Device {id_eco} not found.")

# Funzione per avviare lo scheduler e aggiornare le percentuali
def start_scheduler():
    scheduler = BackgroundScheduler()

    # Aggiorna il bidone in modo casuale ogni 10 minuti
    scheduler.add_job(func=aggiorna_percentuali_bidone, trigger="interval", minutes=10)

    scheduler.start()

# Route per lo sminuzzamento del materiale
@app.route('/product/sminuzza/<id_eco>/<tipo>', methods=['POST'])
def sminuzza(id_eco, tipo):
    stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

    if stato:
        incremento_scatola = 0  # Valore da aggiungere alla scatola

        # Gestione sminuzzamento per plastica, vetro e carta
        if tipo == "plastic":
            plastica_bidone = stato['plastica_bidone']
            if plastica_bidone >= 80:
                if plastica_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se la plastica è tra 80% e 90%
                elif plastica_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se la plastica è tra 90% e 100%
                stato['plastica_bidone'] = 0  # Svuota il bidone
                stato['plastica_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Shredding not allowed, plastic must be at least 80%"}), 400

        elif tipo == "glass":
            vetro_bidone = stato['vetro_bidone']
            if vetro_bidone >= 80:
                if vetro_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se il vetro è tra 80% e 90%
                elif vetro_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se il vetro è tra 90% e 100%
                stato['vetro_bidone'] = 0  # Svuota il bidone
                stato['vetro_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Shredding not allowed, glass must be at least 80%"}), 400

        elif tipo == "paper":
            carta_bidone = stato['carta_bidone']
            if carta_bidone >= 80:
                if carta_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se la carta è tra 80% e 90%
                elif carta_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se la carta è tra 90% e 100%
                stato['carta_bidone'] = 0  # Svuota il bidone
                stato['carta_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Shredding not allowed, paper must be at least 80%"}), 400

        # Salva le modifiche nel database
        mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})

        return jsonify({"status": "success", "message": f"Shredding completed for {tipo}. Added {incremento_scatola}% at box."}), 200

    return jsonify({"status": "error", "message": "Device not found"}), 404


#Route per le percentuali del dispositivo
@app.route('/product/percentuali/<id_eco>', methods=['GET'])
def get_percentuali(id_eco):
    # Cerca lo stato del dispositivo specificato tramite id_eco
    stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

    if stato:
        # Recupera le percentuali di plastica, vetro e carta nei bidoni e nelle scatole
        percentuali = {
            'plastica_bidone': stato.get('plastica_bidone', 0),
            'vetro_bidone': stato.get('vetro_bidone', 0),
            'carta_bidone': stato.get('carta_bidone', 0),
            'plastica_scatola': stato.get('plastica_scatola', 0),
            'vetro_scatola': stato.get('vetro_scatola', 0),
            'carta_scatola': stato.get('carta_scatola', 0),
        }
        return jsonify(percentuali)
    else:
        return jsonify({"error": "Device not found"}), 404


#Route per avviare il ritiro di una scatola
@app.route('/product/avvia_ritiro/<id_eco>', methods=['POST'])
def avvia_ritiro(id_eco):
    if 'username' in session:
        try:
            # Estrai il tipo di materiale dal body della richiesta
            data = request.get_json()
            tipo_materiale = data.get('tipo')

            if not tipo_materiale:
                return jsonify({'success': False, 'error': 'Type of material not supplied'}), 400

            # Recupera lo stato del dispositivo dal database
            stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})
            if not stato:
                return jsonify({'success': False, 'error': f"No status found for the id {id_eco}."}), 404

            # Gestione del tipo di materiale e verifica se il materiale è almeno al 90% nella scatola
            if tipo_materiale == "plastic":
                scatola = stato.get('plastica_scatola', 0)
            elif tipo_materiale == "glass":
                scatola = stato.get('vetro_scatola', 0)
            elif tipo_materiale == "paper":
                scatola = stato.get('carta_scatola', 0)
            else:
                return jsonify({'success': False, 'error': 'Invalid material type'}), 400

            # Verifica che la percentuale nella scatola sia almeno 90%
            if scatola < 90:
                return jsonify({'success': False, 'error': 'The box must be at least 90% full to start the collection'}), 400

            # Recupera la posizione ecosin ed ente associato
            posizione_eco = mongo.db.Posizioni_Ecosin.find_one({'id_eco': id_eco})
            if not posizione_eco:
                return jsonify({'success': False, 'error': f"No ecosin positions found for the id {id_eco}."}), 404

            id_ente = posizione_eco['id_ente']
            ente = mongo.db.Enti.find_one({'id_ente': id_ente})
            if not ente:
                return jsonify({'success': False, 'error': f"The entity with id {id_ente} doesn't exist."}), 404

            # Determina il prossimo giorno lavorativo
            def next_workday(date):
                while date.weekday() >= 5:  # Sabato=5, Domenica=6
                    date += timedelta(days=1)
                return date

            next_day = datetime.now() + timedelta(days=1)
            data_ritiro = next_workday(next_day).strftime("%Y-%m-%d")

            # Seleziona un manutentore casuale
            manutentori = list(mongo.db.Manutentori.find())
            if not manutentori:
                return jsonify({'success': False, 'error': "No maintainers found in the database."}), 500
            manutentore = random.choice(manutentori)
            cf_man = manutentore['cf_man']

            # Genera il codice del ritiro
            last_code = mongo.db.Ritiri.find().sort('cod_r', -1).limit(1)
            if last_code:
                last_code = last_code[0]['cod_r']
                number = int(last_code[3:])  # Estrai la parte numerica del codice
                codice_univoco = f"RIT{str(number + 1).zfill(2)}"
            else:
                codice_univoco = "RIT01"

            # Dati del ritiro
            ritiro_data = {
                'cod_r': codice_univoco,
                'id_eco': id_eco,
                'data_r': data_ritiro,
                'cf_man': cf_man,
                'id_ente': id_ente,
                'materiale': tipo_materiale  # Aggiungi il materiale al ritiro
            }
            mongo.db.Ritiri.insert_one(ritiro_data)

            # Crea comunicazione di ritiro
            create_communication(id_ente, azione='ritiro', data_str=data_ritiro, materiale=tipo_materiale)

            # Svuota la scatola dopo il ritiro (senza modificare il bidone)
            if tipo_materiale == "plastic":
                stato['plastica_scatola'] = 0
            elif tipo_materiale == "glass":
                stato['vetro_scatola'] = 0
            elif tipo_materiale == "paper":
                stato['carta_scatola'] = 0

            # Salva lo stato aggiornato nel database
            mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})

            return jsonify({'success': True})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401


#Route per avviare la manutenzione
@app.route('/product/manutenzione/<id_eco>', methods=['POST'])
def avvia_manutenzione(id_eco):
    if 'username' in session:
        try:
            # Recupera i dati del dispositivo (eco)
            dispositivo = mongo.db.Posizioni_Ecosin.find_one({"id_eco": id_eco})
            if not dispositivo:
                return jsonify({"success": False, "error": "Device not found"}), 404

            # Recupera l'ente associato al dispositivo
            id_ente = dispositivo['id_ente']
            ente = mongo.db.Enti.find_one({"id_ente": id_ente})
            if not ente:
                return jsonify({"success": False, "error": "Entity not found"}), 404

            manutentori = list(mongo.db.Manutentori.find())
            if not manutentori:
                return jsonify({'success': False, 'error': "No maintainers found in the database."}), 500
            manutentore = random.choice(manutentori)
            cf_man = manutentore['cf_man']

            def next_workday(date):
                while date.weekday() >= 5:  # Sabato=5, Domenica=6
                    date += timedelta(days=1)
                return date

            next_day = datetime.now() + timedelta(days=1)
            data_manutenzione = next_workday(next_day).strftime("%Y-%m-%d")

            last_code = mongo.db.Manutenzioni.find().sort('cod_man', -1).limit(1)
            if last_code:
                last_code = last_code[0]['cod_man']
                number = int(last_code[3:])
                codice_univoco = f"MAN{str(number + 1).zfill(2)}"
            else:
                codice_univoco = "MAN01"

            # Inserisci i dati di manutenzione nel database
            manutenzione_data = {
                'cod_man': codice_univoco,
                'id_eco': id_eco,
                'data_man': data_manutenzione,
                'cf_man': cf_man,
                'id_ente': id_ente,
            }
            mongo.db.Manutenzioni.insert_one(manutenzione_data)

            create_communication(id_ente, azione='manutenzione', data_str=data_manutenzione, materiale = None)

            return jsonify({"success": True}), 200
        except Exception as e:
            print(f"Error starting maintenance: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return jsonify({"success": False, "error": "User not authenticated"}), 401

# Route per la pagina delle comunicazioni
@app.route('/comunicazioni', methods=['GET', 'POST'])
def communication_page():
    if 'username' in session:
        today = datetime.now().strftime("%Y-%m-%d")

        # Query aggregata per ottenere comunicazioni future con i dettagli dell'ente
        communications = mongo.db.Comunicazioni.aggregate([
            {
                "$match": {
                    "data_m": {"$gte": today}  # Filtra le date minori rispetto a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",
                    "localField": "id_ente",
                    "foreignField": "id_ente",
                    "as": "ente_info"
                }
            },
            {
                "$unwind": "$ente_info"
            },
            {
                "$sort": {
                    "data_m": 1  # Ordina per data_m in ordine crescente (imminenti in cima)
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "cod_m": 1,
                    "data_m": 1,
                    "messaggio": 1,
                    "ente_nome": "$ente_info.nome_d"
                }
            }
        ])

        return render_template('communications.html', communications=communications, logged_in=True)
    else:
        return redirect(url_for('login'))

# Funzione per creare una comunicazione nel database
def create_communication(id_ente, azione, data_str, materiale):
    try:
        # Genera il codice univoco per la comunicazione
        last_communication = mongo.db.Comunicazioni.find().sort('cod_m', -1).limit(1)
        if last_communication:
            last_code = last_communication[0]['cod_m']
            number = int(last_code[3:])
            new_code = f"COM{str(number + 1).zfill(2)}"
        else:
            new_code = "COM01"

        # Costruisci il messaggio
        if azione == 'manutenzione':
            message = f"ONE OF OUR MAINTENANCE STAFF WILL COME BY THE DAY {data_str}."
        elif azione == 'ritiro':
            message = f"ON {data_str} THE {materiale.upper()} WILL BE COLLECTED."

        print(f"Communication to be inserted: Code: {new_code}, Entity: {id_ente}, Date: {data_str}, Message: {message}")

        # Crea il documento per la comunicazione
        communication_data = {
            'cod_m': new_code,
            'id_ente': id_ente,
            'data_m': data_str,
            'messaggio': message,
        }

        # Inserimento nel database
        result = mongo.db.Comunicazioni.insert_one(communication_data)

        # Verifica se l'inserimento ha avuto successo
        if result.acknowledged:
            print(f"Message successfully inserted: {communication_data}")
        else:
            print("Error while entering communication.")

    except Exception as e:
        print(f"Error creating communication: {e}")

# Route per la pagina dell'archivio
@app.route('/archivio')
def archive_page():
    if 'username' in session:
        return render_template('archive.html')  # La pagina dell'archivio
    else:
        return redirect(url_for('login'))

# Route per visualizzare gli archivi dei ritiri passati
@app.route('/withdrawals_archive')
def withdrawals_archive():
    if 'username' in session:
        # Ottieni la data corrente come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query aggregata per unire Ritiri con Enti e Manutentori
        withdrawals = mongo.db.Ritiri.aggregate([
            {
                "$match": {
                    "data_r": {"$lt": today}  # Filtra date string inferiori a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",  # Unione con la collezione Enti
                    "localField": "id_ente",  # Campo in Ritiri
                    "foreignField": "id_ente",  # Campo in Enti
                    "as": "ente_info"  # Campo unito
                }
            },
            {
                "$unwind": "$ente_info"  # Separa i dati uniti
            },
            {
                "$sort": {
                    "data_r": -1  # Ordina per data_m in ordine decrescente (più recente in cima)
                }
            },
            {
                "$lookup": {
                    "from": "Manutentori",  # Unione con la collezione Manutentori
                    "localField": "cf_man",  # Campo in Ritiri
                    "foreignField": "cf_man",  # Campo in Manutentori
                    "as": "manutentore_info"  # Campo unito
                }
            },
            {
                "$unwind": "$manutentore_info"  # Separa i dati uniti
            },
            {
                "$project": {
                    "_id": 0,                 # Escludi il campo _id
                    "cod_r": 1,               # Includi il codice ritiro
                    "data_r": 1,              # Includi la data del ritiro
                    "materiale": 1,           # Includi il materiale
                    "ente_nome": "$ente_info.nome_d",  # Nome dell'ente
                    "manutentore_nome": "$manutentore_info.nome_m",  # Nome del manutentore
                    "manutentore_cognome": "$manutentore_info.cognome_m"  # Cognome del manutentore
                }
            }
        ])

        # Passa i dati al template
        return render_template('withdrawals_archive.html', withdrawals=withdrawals)
    else:
        return redirect(url_for('login'))

# Route per l'archivio delle comunicazioni
@app.route('/communications_archive')
def communications_archive():
    if 'username' in session:
        # Ottieni la data odierna come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query per unire Comunicazioni con Enti e filtrare per data
        communications = mongo.db.Comunicazioni.aggregate([
            {
                "$match": {
                    "data_m": {"$lt": today}  # Filtra le date minori rispetto a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",  # Nome della collezione Enti
                    "localField": "id_ente",  # Campo in Comunicazioni che fa riferimento a Enti
                    "foreignField": "id_ente",  # Campo in Enti che corrisponde
                    "as": "ente_info"  # Nome del campo di output per i dati uniti
                }
            },
            {
                "$unwind": "$ente_info"  # Separa i dati uniti (uno per ogni ente)
            },
            {
                "$sort": {
                    "data_m": -1  # Ordina per data_m in ordine decrescente (più recente in cima)
                }
            },
            {
                "$project": {
                    "_id": 0,               # Escludi il campo _id
                    "cod_m": 1,             # Includi il codice comunicazione
                    "data_m": 1,            # Includi la data
                    "messaggio": 1,         # Includi il messaggio
                    "ente_nome": "$ente_info.nome_d"  # Nome dell'ente
                }
            }
        ])

        # Passa i dati al template
        return render_template('communications_archive.html', communications=communications)
    else:
        return redirect(url_for('login'))

# Route per l'archivio delle manutenzioni
@app.route('/maintenance_archive')
def maintenance_archive():
    if 'username' in session:
        # Ottieni la data odierna come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query aggregata per unire Manutenzioni con Enti e Manutentori e filtrare per data
        maintenances = mongo.db.Manutenzioni.aggregate([
            {
                "$match": {
                    "data_man": {"$lt": today}  # Filtra le date minori rispetto a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",  # Unione con la collezione Enti
                    "localField": "id_ente",  # Campo in Manutenzioni
                    "foreignField": "id_ente",  # Campo in Enti
                    "as": "ente_info"  # Campo unito
                }
            },
            {
                "$unwind": "$ente_info"  # Separa i dati uniti
            },
            {
                "$sort": {
                    "data_man": -1  # Ordina per data_m in ordine decrescente (più recente in cima)
                }
            },
            {
                "$lookup": {
                    "from": "Manutentori",  # Unione con la collezione Manutentori
                    "localField": "cf_man",  # Campo in Manutenzioni
                    "foreignField": "cf_man",  # Campo in Manutentori
                    "as": "manutentore_info"  # Campo unito
                }
            },
            {
                "$unwind": "$manutentore_info"  # Separa i dati uniti
            },
            {
                "$project": {
                    "_id": 0,                 # Escludi il campo _id
                    "cod_man": 1,             # Includi il codice manutenzione
                    "data_man": 1,            # Includi la data della manutenzione
                    "ente_nome": "$ente_info.nome_d",  # Nome dell'ente
                    "manutentore_nome": "$manutentore_info.nome_m",  # Nome del manutentore
                    "manutentore_cognome": "$manutentore_info.cognome_m"  # Cognome del manutentore
                }
            }
        ])
        # Passa i dati al template
        return render_template('maintenance_archive.html', maintenances=maintenances)
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    start_scheduler()
    app.run(debug=True)

# Copyright (c) 2024 ECOSIN
# This file is part of a project licensed under the MIT License.
# See the LICENSE file in the project root for more information.