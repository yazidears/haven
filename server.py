from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Queue and user data
queue = []
user_activity = {}
in_haven = None 
average_wait_time = 0 

# Timeouts
QUEUE_TIMEOUT = 5  
HAVEN_TIMEOUT = 120  
QUEUE_ALIVE_INTERVAL = 0.5 
HAVEN_ALIVE_INTERVAL = 1 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/haven')
def haven():
    return render_template('haven.html')

@socketio.on('connect')
def handle_connect():
    user_id = request.sid
    if in_haven is not None:  # Check if haven is occupied
        socketio.emit('redirect_to_queue', to=user_id)  # Redirect if occupied
    else:
        queue.append(user_id)
        user_activity[user_id] = time.time()
        if len(queue) == 1:  # If the user is the first and haven is empty, admit
            admit_to_haven(user_id)
        else:
            update_queue_status()



@socketio.on('alive')
def handle_alive(data):
    user_id = data['user_id']
    if user_id in user_activity:
        user_activity[user_id] = time.time()
        if user_id == in_haven:
            if time.time() - user_activity[user_id] > HAVEN_TIMEOUT:
                kick_from_haven(user_id)
        else:
            if time.time() - user_activity[user_id] > QUEUE_TIMEOUT:
                remove_from_queue(user_id)
            elif in_haven is None and queue[0] == user_id:
                admit_to_haven(user_id)

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id == in_haven:
        kick_from_haven(user_id)
    else:
        remove_from_queue(user_id)

def update_queue_status():
    for i, user_id in enumerate(queue):
        eta = estimate_eta(i)
        socketio.emit('queue_update', {'position': i, 'eta': eta}, to=user_id)

def estimate_eta(position):
    return average_wait_time * position 

def admit_to_haven(user_id):
    global in_haven
    if in_haven is None:
        in_haven = user_id
        queue.pop(0)
        print(f"User {user_id} admitted to haven")
        socketio.emit('enter_haven', to=user_id)
        update_queue_status()
    else:
        print(f"Attempted to admit {user_id} but haven is occupied")  # Debugging statement



def kick_from_haven(user_id):
    global in_haven
    in_haven = None
    if queue:
        admit_to_haven(queue[0])
    else:
        update_queue_status()

def remove_from_queue(user_id):
    if user_id in queue:
        queue.remove(user_id)
        del user_activity[user_id]
        update_queue_status()

def queue_management_task():
    while True:
        socketio.sleep(0.3)
        current_time = time.time()
        for user_id in list(user_activity.keys()):
            if current_time - user_activity[user_id] > QUEUE_TIMEOUT:
                remove_from_queue(user_id)
        if in_haven is not None and current_time - user_activity[in_haven] > HAVEN_TIMEOUT:
            kick_from_haven(in_haven)
        update_queue_status()

socketio.start_background_task(queue_management_task)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=2345, debug=True)
