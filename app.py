from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from datetime import datetime
import os

app = Flask(__name__)

# --- CONFIG: editar según tu instalación ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'AnnaKarenina2925',   # ← REEMPLAZA CON TU CONTRASEÑA REAL
    'database': 'juego_seguro',
    'autocommit': True
}
# -----------------------------------------

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play', methods=['GET', 'POST'])
def play():
    nombre = request.form.get('nombre', 'Anonimo')
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM preguntas ORDER BY id ASC;")
    preguntas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('play.html', nombre=nombre, preguntas=preguntas)

@app.route('/submit', methods=['POST'])
def submit():
    # === DEBUG: Ver qué está llegando ===
    print("🔍 DEBUG /submit: Se recibió una petición")
    try:
        data = request.get_json()
        print(f"📦 Datos recibidos: {data}")
    except Exception as e:
        print(f"❌ Error parseando JSON: {e}")
        return jsonify({'error': 'JSON inválido'}), 400
    
    if not data:
        print("❌ No hay datos JSON")
        return jsonify({'error': 'No JSON enviado'}), 400

    nombre = data.get('nombre', 'Anonimo')
    respuestas = data.get('respuestas', [])
    print(f"👤 Nombre: {nombre}, Respuestas: {len(respuestas)}")
    # === FIN DEBUG ===

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    puntaje = 0
    tiempo_total = 0.0

    for r in respuestas:
        qid = int(r.get('pregunta_id'))
        opcion = int(r.get('opcion'))
        tiempo = float(r.get('tiempo', 0.0))
        tiempo_total += tiempo

        cur.execute("SELECT correcta FROM preguntas WHERE id = %s", (qid,))
        row = cur.fetchone()
        if row and row.get('correcta') == opcion:
            puntaje += 10

    cur.execute(
        "INSERT INTO ranking (nombre, puntaje, tiempo, fecha) VALUES (%s, %s, %s, %s)",
        (nombre, puntaje, tiempo_total, datetime.now())
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'status': 'ok', 'puntaje': puntaje, 'tiempo_total': tiempo_total})

@app.route('/ranking')
def ranking():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT nombre, puntaje, tiempo, fecha
        FROM ranking
        ORDER BY puntaje DESC, tiempo ASC, fecha ASC
        LIMIT 50;
    """)
    resultados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('ranking.html', resultados=resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)