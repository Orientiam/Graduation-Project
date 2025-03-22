from app import app,socketio
socketio.run(app, debug=True, host='127.0.0.1', port=5000)
app.run()

