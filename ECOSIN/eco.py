import random
from datetime import datetime, timedelta
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_pymongo import PyMongo

app = Flask(_name_, static_folder='assets', template_folder='templates')

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

    return render_template('login.html')

# Route per il logout
@app.route('/logout')
def logout():
    session.pop('username', None)
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
        ultima_manutenzione = mongo.db.Manutenzioni.find_one(
            {"id_eco": device_id}, sort=[("data_man", -1)]
        )

        # Calcola la prossima manutenzione (aggiungi 30 giorni all'ultima manutenzione)
        from datetime import datetime, timedelta
        if ultima_manutenzione:
            ultima_data = datetime.strptime(ultima_manutenzione['data_man'], "%Y-%m-%d")
            prossima_manutenzione = ultima_data + timedelta(days=30)
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

    if request.method == 'POST':
        # Recupera i dati dal form
        id_ente = request.form.get('ente')  # L'utente seleziona l'id_ente direttamente
        azione = request.form.get('azione')
        data_str = request.form.get('data')  # La data che l'utente inserisce

        # Verifica che tutti i dati siano stati inviati
        if not id_ente or not azione or not data_str:
            flash("Per favore, compila tutti i campi!", "error")
            return redirect(url_for('maintenance_page'))  # Ritorna alla stessa pagina

        # Converti la data dal formato stringa a un oggetto datetime
        try:
            # Usa solo la parte di data (giorno, mese, anno), senza orario
            data = datetime.strptime(data_str, "%Y-%m-%d").date()  # .date() esclude l'orario
        except ValueError:
            flash("Formato data non valido.", "error")
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
            flash("Manutenzione registrata con successo!", "success")

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
            flash("Ritiro registrato con successo!", "success")

        return redirect(url_for('maintenance_page'))  # Rimanda alla pagina dopo aver inserito i dati

    return render_template('maintenance.html', enti=enti)  # Visualizza la pagina con gli enti





# Route per la pagina di manutenzioni da fare
@app.route('/maintenance_todo')
def maintenance_todo():
    if 'username' in session:
        today = datetime.now()
        # Recupera tutte le manutenzioni future dalla collezione Manutenzioni
        manutenzioni_future = mongo.db.Manutenzioni.find({"data_man": {"$gte": today}})

        # Aggiungi le informazioni dell'ente e del manutentore per ogni manutenzione
        for manutenzione in manutenzioni_future:
            ente = mongo.db.Enti.find_one({'id_ente': manutenzione['id_ente']})
            manutentore = mongo.db.Manutentori.find_one({'cf_man': manutenzione['cf_man']})
            manutenzione['ente_nome'] = ente['nome_d'] if ente else "N/A"
            manutenzione['manutentore_nome'] = manutentore['nome_m'] if manutentore else "N/A"
            manutenzione['manutentore_cognome'] = manutentore['cognome_m'] if manutentore else "N/A"

        return render_template('maintenance_todo.html', manutenzioni=manutenzioni_future)
    else:
        return redirect(url_for('login'))  # Se non loggato, redirect alla pagina di login



# Route per la pagina di ritiri da fare (corretto il nome del file)
@app.route('/withdrawals_todo')
def withdrawals_todo():
    if 'username' in session:
        today = datetime.now()
        # Recupera tutti i ritiri futuri dalla collezione Ritiri
        ritiri_future = mongo.db.Ritiri.find({"data_r": {"$gte": today}})

        # Aggiungi le informazioni dell'ente e del manutentore per ogni ritiro
        for ritiro in ritiri_future:
            ente = mongo.db.Enti.find_one({'id_ente': ritiro['id_ente']})
            manutentore = mongo.db.Manutentori.find_one({'cf_man': ritiro['cf_man']})
            ritiro['ente_nome'] = ente['nome_d'] if ente else "N/A"
            ritiro['manutentore_nome'] = manutentore['nome_m'] if manutentore else "N/A"
            ritiro['manutentore_cognome'] = manutentore['cognome_m'] if manutentore else "N/A"

        return render_template('withdrawals_todo.html', ritiri=ritiri_future)
    else:
        return redirect(url_for('login'))  # Se non loggato, redirect alla pagina di login


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
    # Scheduler per eseguire i job ogni 10 secondi
    scheduler = BackgroundScheduler()

    # Aggiorna il bidone in modo casuale ogni 10 secondi
    scheduler.add_job(func=aggiorna_percentuali_bidone, trigger="interval", minutes=10)

    scheduler.start()

#bozza route dello sminuzzamento
@app.route('/product/sminuzza/<id_eco>/<tipo>', methods=['POST'])
def sminuzza(id_eco, tipo):
    # Recupera lo stato del dispositivo
    stato = mongo.db.Stato_Ecosin.find_one({"id_eco": id_eco})

    if stato:
        if tipo == "plastica":
            stato['plastica_bidone'] = 0
            stato['plastica_scatola'] += 10  # Aggiungi il valore alla scatola
        elif tipo == "vetro":
            stato['vetro_bidone'] = 0
            stato['vetro_scatola'] += 10  # Aggiungi il valore alla scatola
        elif tipo == "carta":
            stato['carta_bidone'] = 0
            stato['carta_scatola'] += 10  # Aggiungi il valore alla scatola

        # Salva le modifiche nel database
        mongo.db.Stato_Ecosin.update_one({"id_eco": id_eco}, {"$set": stato})
        return jsonify({"status": "success", "message": "Sminuzzamento completato"}), 200
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




@app.route('/product/avvia_ritiro', methods=['POST'])
def avvia_ritiro():
    id_eco = request.form['id_eco']  # id del prodotto
    materiale = request.form['materiale']  # plastica, vetro o carta
    cf_man = request.form['cf_man']  # codice fiscale del manutentore
    id_ente = request.form['id_ente']  # id dell'ente

    # Registra un nuovo ritiro
    ritiro_data = {
        "id_eco": id_eco,
        "data_r": datetime.now(),
        "cf_man": cf_man,
        "id_ente": id_ente
    }

    mongo.db.Ritiri.insert_one(ritiro_data)

    return jsonify({"success": True, "message": f"Ritiro di {materiale} avviato!"})





#bozze route per comunicazioni,manutenzioni e archivio
# Route per la pagina delle comunicazioni
@app.route('/comunicazioni')
def communication_page():
    if 'username' in session:
        return render_template('communications.html')  # La pagina delle comunicazioni
    else:
        return redirect(url_for('login'))


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
        # Query aggregata per unire Ritiri con Enti e Manutentori
        withdrawals = mongo.db.Ritiri.aggregate([
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
        # Esegui una query aggregata per unire Comunicazioni con Enti
        communications = mongo.db.Comunicazioni.aggregate([
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
        # Query aggregata per unire Manutenzioni con Enti e Manutentori
        maintenances = mongo.db.Manutenzioni.aggregate([
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










if _name_ == '_main_':
    start_scheduler()
    app.run(debug=True)
