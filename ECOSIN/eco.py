import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, redirect, url_for, session, flash
from flask_pymongo import PyMongo

app = Flask(__name__, static_folder='assets', template_folder='templates')

# Configura la connessione a MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/ECOSIN"  # Sostituisci con il tuo URI MongoDB
mongo = PyMongo(app)

app.secret_key = 'secret_key_12345'

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
            return redirect(url_for('portal'))  # Redirige alla mappa dopo il login
        else:
            flash('Credenziali non valide!', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# Route per il logout
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    flash('Sei stato disconnesso con successo!', 'info')  # Messaggio di disconnessione
    return redirect(url_for('login'))

# Route per la pagina del portale
@app.route('/portal')
def portal():
    if 'username' in session:  # Se l'utente è loggato
        return render_template('portal.html', username=session['username'])  # Mostra la pagina del portale
    else:
        return redirect(url_for('login'))  # Se non è loggato, rimandalo al login

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

from datetime import datetime, timedelta

@app.route('/product/<device_id>')
def product_page(device_id):
    # Recupera le informazioni sulla posizione del dispositivo (eco)
    device = mongo.db.Posizioni_Ecosin.find_one({"id_eco": device_id})

    if device:
        # Recupera lo stato del bidone dalla tabella Stato_Ecosin
        stato = mongo.db.Stato_Ecosin.find_one({"id_eco": device_id})

        # Recupera informazioni sull'ente associato
        ente = mongo.db.Enti.find_one({"id_ente": device['id_ente']})

        # Recupera l'ultima manutenzione
        ultima_manutenzione = mongo.db.Manutenzioni.find_one({"id_eco": device_id}, sort=[("data_man", -1)])

        # Calcola la prossima manutenzione (aggiungi 30 giorni all'ultima manutenzione)
        if ultima_manutenzione:
            # Controlla se la data di manutenzione è una stringa o un oggetto datetime
            ultima_data = ultima_manutenzione['data_man']

            if isinstance(ultima_data, datetime):
                # Se è un oggetto datetime, convertilo in stringa
                ultima_data_str = ultima_data.strftime("%Y-%m-%d")
            else:
                # Se è già una stringa, usa direttamente
                ultima_data_str = ultima_data

            # Aggiungi 30 giorni alla data (simulato senza conversione a datetime)
            ultima_data_obj = datetime.strptime(ultima_data_str, "%Y-%m-%d")
            prossima_manutenzione = ultima_data_obj + timedelta(days=30)
            prossima_manutenzione = prossima_manutenzione.strftime("%Y-%m-%d")
        else:
            prossima_manutenzione = "Non disponibile"

        # Calcola le percentuali per ciascun stato del bidone e della scatola
        percentuali = {
            'plastica_bidone': stato.get('plastica_bidone', 0),
            'vetro_bidone': stato.get('vetro_bidone', 0),
            'carta_bidone': stato.get('carta_bidone', 0),
            'plastica_scatola': stato.get('plastica_scatola', 0),
            'vetro_scatola': stato.get('vetro_scatola', 0),
            'carta_scatola': stato.get('carta_scatola', 0)
        }

        # Passa tutti i dati al template
        return render_template('product.html', device=device, stato=stato, ente=ente,
                               ultima_manutenzione=ultima_manutenzione, prossima_manutenzione=prossima_manutenzione,
                               percentuali=percentuali)
    else:
        return "Prodotto non trovato", 404




#----------------------------------------------------------------------------------------------------------------
# Route per la pagina delle manutenzioni
@app.route('/manutenzioni',methods=['GET', 'POST'])
def maintenance_page():
    # Recupero gli enti dal database
    enti = mongo.db.Enti.find()  # Ottenere tutti gli enti

    # Calcola la data di domani
    tomorrow = (datetime.today() + timedelta(days=1)).date()

    if request.method == 'POST':
        # Recupera i dati dal form
        id_ente = request.form.get('ente')  # L'utente seleziona l'id_ente direttamente
        azione = request.form.get('azione')
        data_str = request.form.get('data')  # La data che l'utente inserisce

        # Verifica che tutti i dati siano stati inviati
        if not id_ente or not azione or not data_str:
            flash('Per favore, compila tutti i campi!', 'error')
            return redirect(url_for('maintenance_page'))  # Ritorna alla stessa pagina

        # Converti la data dal formato stringa a un oggetto datetime
        try:
            # Usa solo la parte di data (giorno, mese, anno), senza orario
            data = datetime.strptime(data_str, "%Y-%m-%d").date()  # .date() esclude l'orario

            # Verifica che la data inserita sia maggiore di domani
            if data < tomorrow:
                flash('La data deve essere successiva o uguale a domani.', 'error')
                return redirect(url_for('maintenance_page'))

        except ValueError:
            flash('Formato data non valido.', 'error')
            return redirect(url_for('maintenance_page'))

        # Verifica che l'ente esista nel database
        ente = mongo.db.Enti.find_one({'id_ente': id_ente})
        if not ente:
            flash(f"L'ente con id {id_ente} non esiste.", "error")
            return redirect(url_for('maintenance_page'))

        # Ottieni l'ID Eco corrispondente all'ente selezionato (id_ente <-> id_eco)
        posizione_eco = mongo.db.Posizioni_Ecosin.find_one({'id_ente': id_ente})
        if not posizione_eco:
            flash(f"Nessuna posizione ecosin trovata per l'ente {id_ente}.", "error")
            return redirect(url_for('maintenance_page'))

        id_eco = posizione_eco['id_eco']  # L'ID Eco corrispondente all'ente

        # Recupera un manutentore esistente dalla collezione Manutentori
        manutentori = list(mongo.db.Manutentori.find())  # Otteniamo tutti i manutentori

        if not manutentori:
            flash("Nessun manutentore trovato nel database.", "error")
            return redirect(url_for('maintenance_page'))

        # Seleziona un manutentore casuale
        manutentore = random.choice(manutentori)
        cf_man = manutentore['cf_man']  # Estrai il codice fiscale del manutentore

        # Funzione per ottenere il prossimo codice per manutenzione o ritiro
        def get_next_code(action):
            if action == 'manutenzione':
                # Trova l'ultimo codice manutenzione nel database
                last_code = mongo.db.Manutenzioni.find().sort('cod_man', -1).limit(1)
                if last_code:
                    last_code = last_code[0]['cod_man']
                    number = int(last_code[3:])  # Estrai il numero dal codice
                    new_code = f"MAN{str(number + 1).zfill(2)}"
                else:
                    new_code = "MAN01"  # Se non ci sono manutenzioni, iniziamo da MAN01
            elif action == 'ritiro':
                # Trova l'ultimo codice ritiro nel database
                last_code = mongo.db.Ritiri.find().sort('cod_r', -1).limit(1)
                if last_code:
                    last_code = last_code[0]['cod_r']
                    number = int(last_code[3:])  # Estrai il numero dal codice
                    new_code = f"RIT{str(number + 1).zfill(2)}"
                else:
                    new_code = "RIT01"  # Se non ci sono ritiri, iniziamo da RIT01
            return new_code

        # Genera il codice univoco per manutenzione o ritiro
        codice_univoco = get_next_code(azione)

        # A seconda dell'azione (manutenzione o ritiro), salva i dati nel database
        if azione == 'manutenzione':
            manutenzione_data = {
                'cod_man': codice_univoco,  # Codice univoco per la manutenzione
                'id_eco': id_eco,  # ID Eco recuperato
                'data_man': data_str,  # Memorizza la data come stringa nel formato YYYY-MM-DD
                'cf_man': cf_man,  # Codice fiscale del manutentore
                'id_ente': id_ente  # L'ente selezionato
            }

            # Inserimento nel database
            mongo.db.Manutenzioni.insert_one(manutenzione_data)
            flash('Manutenzione registrata con successo!', 'success')

            # Crea la comunicazione per manutenzione
            create_communication(id_ente, azione, data_str)

        elif azione == 'ritiro':
            ritiro_data = {
                'cod_r': codice_univoco,  # Codice univoco per il ritiro
                'id_eco': id_eco,  # ID Eco recuperato
                'data_r': data_str,  # Memorizza la data come stringa nel formato YYYY-MM-DD
                'cf_man': cf_man,  # Codice fiscale del manutentore
                'id_ente': id_ente  # L'ente selezionato
            }

            # Inserimento nel database
            mongo.db.Ritiri.insert_one(ritiro_data)
            flash('Ritiro registrato con successo!', 'success')
            # Crea la comunicazione per ritiro
            create_communication(id_ente, azione, data_str)

        return redirect(url_for('maintenance_page'))  # Rimanda alla pagina dopo aver inserito i dati

    return render_template('maintenance.html', enti=enti)  # Visualizza la pagina con gli enti


# Route per la pagina di manutenzioni da fare
@app.route('/maintenance_todo')
def maintenance_todo():
    if 'username' in session:
        # Ottieni la data odierna come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query per unire Manutenzioni con Enti e Manutentori, e filtrare le date
        maintenances = mongo.db.Manutenzioni.aggregate([
            {
                "$match": {
                    "data_man": {"$gte": today}  # Filtra le date maggiori o uguali a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",  # Nome della collezione Enti
                    "localField": "id_ente",  # Campo in Manutenzioni che fa riferimento a Enti
                    "foreignField": "id_ente",  # Campo in Enti che corrisponde
                    "as": "ente_info"  # Nome del campo di output per i dati uniti
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
                    "from": "Manutentori",  # Nome della collezione Manutentori
                    "localField": "cf_man",  # Campo in Manutenzioni che fa riferimento a Manutentori
                    "foreignField": "cf_man",  # Campo in Manutentori che corrisponde
                    "as": "manutentore_info"  # Nome del campo di output per i dati uniti
                }
            },
            {
                "$unwind": "$manutentore_info"  # Separa i dati uniti (uno per ogni manutentore)
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
        return render_template('maintenance_todo.html', maintenances=maintenances)
    else:
        return redirect(url_for('login'))


# Route per la pagina di ritiri da fare (corretto il nome del file)
@app.route('/withdrawals_todo')
def withdrawals_todo():
    if 'username' in session:
        # Ottieni la data odierna come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query per unire Ritiri con Enti e Manutentori, e filtrare le date
        withdrawals = mongo.db.Ritiri.aggregate([
            {
                "$match": {
                    "data_r": {"$gte": today}  # Filtra le date maggiori o uguali a oggi
                }
            },
            {
                "$lookup": {
                    "from": "Enti",  # Nome della collezione Enti
                    "localField": "id_ente",  # Campo in Ritiri che fa riferimento a Enti
                    "foreignField": "id_ente",  # Campo in Enti che corrisponde
                    "as": "ente_info"  # Nome del campo di output per i dati uniti
                }
            },
            {
                "$unwind": "$ente_info"  # Separa i dati uniti (uno per ogni ente)
            },
            {
                "$sort": {
                    "data_r": 1  # Ordina per data_m in ordine crescente (imminenti in cima)
                }
            },
            {
                "$lookup": {
                    "from": "Manutentori",  # Nome della collezione Manutentori
                    "localField": "cf_man",  # Campo in Ritiri che fa riferimento a Manutentori
                    "foreignField": "cf_man",  # Campo in Manutentori che corrisponde
                    "as": "manutentore_info"  # Nome del campo di output per i dati uniti
                }
            },
            {
                "$unwind": "$manutentore_info"  # Separa i dati uniti (uno per ogni manutentore)
            },
            {
                "$project": {
                    "_id": 0,                 # Escludi il campo _id
                    "cod_r": 1,               # Includi il codice ritiro
                    "data_r": 1,              # Includi la data del ritiro
                    "ente_nome": "$ente_info.nome_d",  # Nome dell'ente
                    "manutentore_nome": "$manutentore_info.nome_m",  # Nome del manutentore
                    "manutentore_cognome": "$manutentore_info.cognome_m"  # Cognome del manutentore
                }
            }
        ])

        # Passa i dati al template
        return render_template('withdrawals_todo.html', withdrawals=withdrawals)
    else:
        return redirect(url_for('login'))

#----------------------------------------------------------------------------------------------------------------

#bozza sull'aggiornamento delle percentuali penso ufficiale
def aggiorna_percentuali_bidone():
    dispositivi = mongo.db.Posizioni_Ecosin.find()

    for dispositivo in dispositivi:
        id_eco = dispositivo['id_eco']
        stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

        if stato:
            # Randomizza quale parte del bidone deve essere aggiornata (plastica, vetro o carta)
            stato_bidone = random.choice(['plastica_bidone', 'vetro_bidone', 'carta_bidone'])

            # Incremento casuale tra 1 e 2 percento
            incremento_bidone = random.randint(1, 2)

            stato_update = {}

            # Incremento per lo stato selezionato del bidone (solo se non è già al 100%)
            if stato[stato_bidone] < 100:
                stato_update[stato_bidone] = min(100, stato.get(stato_bidone, 0) + incremento_bidone)

            # Aggiorna il database con il nuovo stato del bidone
            if stato_update:
                mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato_update})
                print(f"Percentuale del bidone aggiornata per {id_eco}: {stato_update}")
        else:
            print(f"Dispositivo {id_eco} non trovato.")

def start_scheduler():
    # Scheduler
    scheduler = BackgroundScheduler()

    # Aggiorna il bidone in modo casuale
    scheduler.add_job(func=aggiorna_percentuali_bidone, trigger="interval", minutes=10)

    scheduler.start()

#bozza route dello sminuzzamento
@app.route('/product/sminuzza/<id_eco>/<tipo>', methods=['POST'])
def sminuzza(id_eco, tipo):
    # Recupera lo stato del dispositivo dal database
    stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

    if stato:
        incremento_scatola = 0  # Variabile che conterrà il valore da aggiungere alla scatola

        # Gestisci il tipo di materiale (plastica, vetro, carta)
        if tipo == "plastica":
            plastica_bidone = stato['plastica_bidone']
            if plastica_bidone >= 80:
                if plastica_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se la plastica è tra 80% e 90%
                elif plastica_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se la plastica è tra 90% e 100%
                stato['plastica_bidone'] = 0  # Svuota il bidone
                stato['plastica_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Sminuzzamento non consentito, la plastica deve essere almeno al 80%"}), 400

        elif tipo == "vetro":
            vetro_bidone = stato['vetro_bidone']
            if vetro_bidone >= 80:
                if vetro_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se il vetro è tra 80% e 90%
                elif vetro_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se il vetro è tra 90% e 100%
                stato['vetro_bidone'] = 0  # Svuota il bidone
                stato['vetro_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Sminuzzamento non consentito, il vetro deve essere almeno al 80%"}), 400

        elif tipo == "carta":
            carta_bidone = stato['carta_bidone']
            if carta_bidone >= 80:
                if carta_bidone < 90:
                    incremento_scatola = 5  # Aggiungi 5 alla scatola se la carta è tra 80% e 90%
                elif carta_bidone >= 90:
                    incremento_scatola = 10  # Aggiungi 10 alla scatola se la carta è tra 90% e 100%
                stato['carta_bidone'] = 0  # Svuota il bidone
                stato['carta_scatola'] += incremento_scatola  # Aggiungi il valore calcolato alla scatola
            else:
                return jsonify({"status": "error", "message": "Sminuzzamento non consentito, la carta deve essere almeno al 80%"}), 400

        # Salva le modifiche nel database
        mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})

        # Restituisci una risposta di successo
        return jsonify({"status": "success", "message": f"Sminuzzamento completato per {tipo}. Aggiunto {incremento_scatola}% alla scatola."}), 200

    # Se lo stato del dispositivo non viene trovato
    return jsonify({"status": "error", "message": "Dispositivo non trovato"}), 404



#bozza route aggiornamento percentuali forse ufficiale
from flask import jsonify, request

@app.route('/product/percentuali/<id_eco>', methods=['GET'])
def get_percentuali(id_eco):
    # Cerca lo stato del dispositivo specificato tramite id_eco
    stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

    if stato:
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
        # Se il dispositivo non esiste, restituisci un errore
        return jsonify({"error": "Dispositivo non trovato"}), 404

#se è possibile aggiugere il messaggio a schermo quando non puoi sminuzzare

#bozza route ritiro e manutenzione

@app.route('/product/avvia_ritiro/<id_eco>', methods=['POST'])
def avvia_ritiro(id_eco):
    if 'username' in session:
        try:
            # Recupera il tipo di materiale dal body della richiesta
            data = request.get_json()
            tipo_materiale = data.get('tipo')

            if not tipo_materiale:
                return jsonify({'success': False, 'error': 'Tipo di materiale non fornito'}), 400

            # Recupera lo stato del dispositivo dal database
            stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})
            if not stato:
                return jsonify({'success': False, 'error': f"Nessun stato trovato per l'id {id_eco}."}), 404

            # Gestione del tipo di materiale e verifica se il materiale è almeno al 90% nella scatola
            if tipo_materiale == "plastica":
                scatola = stato.get('plastica_scatola', 0)
            elif tipo_materiale == "vetro":
                scatola = stato.get('vetro_scatola', 0)
            elif tipo_materiale == "carta":
                scatola = stato.get('carta_scatola', 0)
            else:
                return jsonify({'success': False, 'error': 'Tipo di materiale non valido'}), 400

            # Verifica che la percentuale nella scatola sia almeno 90%
            if scatola < 90:
                return jsonify({'success': False, 'error': 'La scatola deve essere almeno al 90% per avviare il ritiro'}), 400

            # Logica per avviare il ritiro
            posizione_eco = mongo.db.Posizioni_Ecosin.find_one({'id_eco': id_eco})
            if not posizione_eco:
                return jsonify({'success': False, 'error': f"Nessuna posizione ecosin trovata per l'id {id_eco}."}), 404

            id_ente = posizione_eco['id_ente']
            ente = mongo.db.Enti.find_one({'id_ente': id_ente})
            if not ente:
                return jsonify({'success': False, 'error': f"L'ente con id {id_ente} non esiste."}), 404

            def next_workday(date):
                while date.weekday() >= 5:  # Sabato=5, Domenica=6
                    date += timedelta(days=1)
                return date

            next_day = datetime.now() + timedelta(days=1)
            data_ritiro = next_workday(next_day).strftime("%Y-%m-%d")

            # Seleziona un manutentore casuale
            manutentori = list(mongo.db.Manutentori.find())
            if not manutentori:
                return jsonify({'success': False, 'error': "Nessun manutentore trovato nel database."}), 500
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
            }
            mongo.db.Ritiri.insert_one(ritiro_data)

            # Crea comunicazione di ritiro
            create_communication(id_ente, azione='ritiro', data_str=data_ritiro)

            # Svuota la scatola dopo il ritiro (senza modificare il bidone)
            if tipo_materiale == "plastica":
                stato['plastica_scatola'] = 0
            elif tipo_materiale == "vetro":
                stato['vetro_scatola'] = 0
            elif tipo_materiale == "carta":
                stato['carta_scatola'] = 0

            # Salva lo stato aggiornato nel database
            mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})

            return jsonify({'success': True})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Utente non autenticato'}), 401


@app.route('/product/manutenzione/<id_eco>', methods=['POST'])
def avvia_manutenzione(id_eco):
    if 'username' in session:  # Verifica se l'utente è autenticato
        try:
            # Recupera i dati del dispositivo (eco) dal database
            dispositivo = mongo.db.Posizioni_Ecosin.find_one({"id_eco": id_eco})
            if not dispositivo:
                return jsonify({"success": False, "error": "Dispositivo non trovato"}), 404

            # Recupera l'ente associato al dispositivo
            id_ente = dispositivo['id_ente']
            ente = mongo.db.Enti.find_one({"id_ente": id_ente})
            if not ente:
                return jsonify({"success": False, "error": "Ente non trovato"}), 404

            manutentori = list(mongo.db.Manutentori.find())
            if not manutentori:
                return jsonify({'success': False, 'error': "Nessun manutentore trovato nel database."}), 500
            manutentore = random.choice(manutentori)
            cf_man = manutentore['cf_man']

            def next_workday(date):
                while date.weekday() >= 5:  # Sabato=5, Domenica=6
                    date += timedelta(days=1)
                return date

            next_day = datetime.now() + timedelta(days=1)
            data_manutenzione = next_workday(next_day).strftime("%Y-%m-%d")

            # Genera il codice di manutenzione incrementando l'ultimo codice
            last_code = mongo.db.Manutenzioni.find().sort('cod_man', -1).limit(1)
            if last_code:
                last_code = last_code[0]['cod_man']
                number = int(last_code[3:])  # Estrai la parte numerica del codice
                codice_univoco = f"MAN{str(number + 1).zfill(2)}"  # Incrementa il numero e riformatta
            else:
                codice_univoco = "MAN01"  # Se è la prima manutenzione

            # Inserisci i dati di manutenzione nel database
            manutenzione_data = {
                'cod_man': codice_univoco,
                'id_eco': id_eco,
                'data_man': data_manutenzione,
                'cf_man': cf_man,
                'id_ente': id_ente,
            }
            mongo.db.Manutenzioni.insert_one(manutenzione_data)

            create_communication(id_ente, azione='manutenzione', data_str=data_manutenzione)


        # Restituisce una risposta di successo
            return jsonify({"success": True}), 200
        except Exception as e:
            print(f"Errore durante l'avvio della manutenzione: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return jsonify({"success": False, "error": "Utente non autenticato"}), 401



#bozze route per comunicazioni,manutenzioni e archivio
# Route per la pagina delle comunicazioni
@app.route('/comunicazioni', methods=['GET', 'POST'])
def communication_page():
    if 'username' in session:
        # Ottieni la data odierna come stringa
        today = datetime.now().strftime("%Y-%m-%d")

        # Query per unire Comunicazioni con Enti e filtrare per data
        communications = mongo.db.Comunicazioni.aggregate([
            {
                "$match": {
                    "data_m": {"$gte": today}  # Filtra le date minori rispetto a oggi
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
                    "data_m": 1  # Ordina per data_m in ordine crescente (imminenti in cima)
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
        return render_template('communications.html', communications=communications)
    else:
        return redirect(url_for('login'))

# Funzione per creare una comunicazione nel database
def create_communication(id_ente, azione, data_str):
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
            message = f"PASSERA' IL GIORNO {data_str} UN NOSTRO INCARICATO PER LA MANUTENZIONE."
        elif azione == 'ritiro':
            message = f"IL GIORNO {data_str} SI EFFETTUA IL RITIRO."

        # Mostra i dati che stai cercando di inserire
        print(f"Comunicazione da inserire: Codice: {new_code}, Ente: {id_ente}, Data: {data_str}, Messaggio: {message}")

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
            print(f"Comunicazione inserita con successo: {communication_data}")
        else:
            print("Errore durante l'inserimento della comunicazione.")

    except Exception as e:
        print(f"Errore durante la creazione della comunicazione: {e}")


# Route per la pagina dell'archivio
@app.route('/archivio')
def archive_page():
    if 'username' in session:
        return render_template('archive.html')  # La pagina dell'archivio
    else:
        return redirect(url_for('login'))

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
