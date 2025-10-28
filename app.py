from flask import Flask, render_template, request, jsonify
import sqlite3
import mysql.connector
from datetime import datetime
import os

app = Flask(__name__)

# --- CONFIGURACIÓN DUAL: SQLite en Render, MySQL local ---
def get_db():
    # Si estamos en Render, usar SQLite
    if 'RENDER' in os.environ:
        conn = sqlite3.connect('juego_seguro.db')
        conn.row_factory = sqlite3.Row  # Para que se comporte como MySQL
        return conn
    else:
        # Local - MySQL
        DB_CONFIG = {
            'host': 'localhost',
            'user': 'root',
            'password': 'AnnaKarenina2925',
            'database': 'juego_seguro',
            'autocommit': True
        }
        return mysql.connector.connect(**DB_CONFIG)

def init_db():
    """Crear tablas si no existen (solo para SQLite)"""
    if 'RENDER' in os.environ:
        conn = sqlite3.connect('juego_seguro.db')
        cur = conn.cursor()
        
        # Tabla preguntas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS preguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pregunta TEXT NOT NULL,
                opcion1 TEXT,
                opcion2 TEXT,
                opcion3 TEXT,
                opcion4 TEXT,
                correcta INTEGER
            )
        ''')
        
        # Tabla ranking
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ranking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                puntaje INTEGER NOT NULL,
                tiempo REAL NOT NULL,
                fecha TEXT NOT NULL
            )
        ''')
        
        # Insertar preguntas de ejemplo si no existen
        cur.execute("SELECT COUNT(*) FROM preguntas")
        if cur.fetchone()[0] == 0:
            preguntas_ejemplo = [
                ("¿Cuál es la capital de Francia?", "Londres", "Berlín", "París", "Madrid", 3),
                ("¿2 + 2 = ?", "3", "4", "5", "6", 2),
                ("¿El sol es...?", "Una estrella", "Un planeta", "Un satélite", "Un cometa", 1)
            ]
            cur.executemany(
                "INSERT INTO preguntas (pregunta, opcion1, opcion2, opcion3, opcion4, correcta) VALUES (?, ?, ?, ?, ?, ?)",
                preguntas_ejemplo
            )
        
        conn.commit()
        conn.close()

# Inicializar BD al inicio
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play', methods=['GET', 'POST'])
def play():
    nombre = request.form.get('nombre', 'Anónimo')
    conn = get_db()
    
    if 'RENDER' in os.environ:
        # SQLite
        cur = conn.cursor()
        cur.execute("SELECT * FROM preguntas ORDER BY id ASC;")
        preguntas = [dict(row) for row in cur.fetchall()]
    else:
        # MySQL
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM preguntas ORDER BY id ASC;")
        preguntas = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('play.html', nombre=nombre, preguntas=preguntas)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON enviado'}), 400

        nombre = data.get('nombre', 'Anónimo')
        respuestas = data.get('respuestas', [])
        
        conn = get_db()
        
        if 'RENDER' in os.environ:
            cur = conn.cursor()  # SQLite
        else:
            cur = conn.cursor(dictionary=True)  # MySQL

        puntaje = 0
        tiempo_total = 0.0

        for r in respuestas:
            qid = int(r.get('pregunta_id'))
            opcion = int(r.get('opcion'))
            tiempo = float(r.get('tiempo', 0.0))
            tiempo_total += tiempo

            if 'RENDER' in os.environ:
                # SQLite
                cur.execute("SELECT correcta FROM preguntas WHERE id = ?", (qid,))
                row = cur.fetchone()
                if row and row[0] == opcion:  # row[0] para SQLite
                    puntaje += 10
            else:
                # MySQL
                cur.execute("SELECT correcta FROM preguntas WHERE id = %s", (qid,))
                row = cur.fetchone()
                if row and row.get('correcta') == opcion:
                    puntaje += 10

        # Insertar en ranking
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'RENDER' in os.environ:
            cur.execute(
                "INSERT INTO ranking (nombre, puntaje, tiempo, fecha) VALUES (?, ?, ?, ?)",
                (nombre, puntaje, tiempo_total, fecha_actual)
            )
        else:
            cur.execute(
                "INSERT INTO ranking (nombre, puntaje, tiempo, fecha) VALUES (%s, %s, %s, %s)",
                (nombre, puntaje, tiempo_total, fecha_actual)
            )
        
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'status': 'ok', 
            'puntaje': puntaje, 
            'tiempo_total': round(tiempo_total, 2)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ranking')
def ranking():
    conn = get_db()
    
    if 'RENDER' in os.environ:
        cur = conn.cursor()
        cur.execute("""
            SELECT nombre, puntaje, tiempo, fecha
            FROM ranking
            ORDER BY puntaje DESC, tiempo ASC, fecha ASC
            LIMIT 50;
        """)
        resultados = [dict(row) for row in cur.fetchall()]
    else:
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
    app.run(host='0.0.0.0', port=port)