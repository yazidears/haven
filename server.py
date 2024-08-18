from flask import Flask, render_template, request, jsonify
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Data structures
waiting_room = {} 
haven_keys = {} 
current_user_id = 0
average_time_in_haven = 0

# Timeouts
WAITING_ROOM_TIMEOUT = 1.5 
HAVEN_TIMEOUT = 120 

# Lock for synchronizing access
lock = threading.Lock()
user_id_lock = threading.Lock()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/haven.html')
def haven():
    return render_template('haven.html')

@app.route('/hi', methods=['GET'])
def assign_user_id():
    global current_user_id
    with user_id_lock:  # Acquire the lock before modifying current_user_id
        current_user_id += 1
        user_id = f"User{current_user_id}"
        waiting_room[user_id] = time.time()
        print(f"Assigned new user ID: {user_id}")
        return jsonify({'user_id': user_id})
@app.route('/alive', methods=['POST'])
def handle_alive():
    user_id = request.json.get('user_id')
    print(f"Received 'alive' from {user_id}")

    with lock:
        if user_id in waiting_room:
            waiting_room[user_id] = time.time()
        else:
            return jsonify({'status': 300}) 

    return jsonify({'status': 200})

@app.route('/pos', methods=['POST'])
def get_position():
    user_id = request.json.get('user_id')
    if user_id not in waiting_room:
        return jsonify({'status': 300})

    position = list(waiting_room.keys()).index(user_id) + 1
    estimated_wait = estimate_wait_time(position)

    waiting_list = list(waiting_room.keys())

    return jsonify({
        'position': position,
        'total': len(waiting_room),
        'ahead': position - 1,
        'estimated_wait': estimated_wait,
        'waiting_list': waiting_list
    })

@app.route('/haven', methods=['POST'])
def enter_haven():
    user_id = request.json.get('user_id')
    with lock:
        if waiting_room and list(waiting_room.keys())[0] == user_id:
            haven_key = generate_haven_key()
            haven_keys[haven_key] = (user_id, time.time())
            del waiting_room[user_id]
            print(f"User {user_id} admitted to haven with key {haven_key}")
            return jsonify({'status': 200, 'haven_key': haven_key})
        else:
            return jsonify({'status': 403})

@app.route('/haven_alive', methods=['POST'])
def handle_haven_alive():
    haven_key = request.json.get('haven_key')
    print(f"Received 'haven_alive' from haven_key {haven_key}")

    with lock:
        if haven_key in haven_keys:
            user_id, start_time = haven_keys[haven_key]
            haven_keys[haven_key] = (user_id, time.time())
            time_left = max(0, HAVEN_TIMEOUT - (time.time() - start_time))
            return jsonify({'status': 200, 'time_left': time_left})
        else:
            return jsonify({'status': 300})  # Haven key not valid

def generate_haven_key():
    import uuid
    return str(uuid.uuid4())

def estimate_wait_time(position):
    return max(0, (position - 1) * average_time_in_haven)

def kick_from_haven(user_id):
    global in_haven, average_time_in_haven

    with lock:
        for key, (u_id, start_time) in haven_keys.items():
            if u_id == user_id:
                time_spent = time.time() - start_time
                average_time_in_haven = (average_time_in_haven + time_spent) / 2
                del haven_keys[key]
                in_haven = None
                print(f"User {user_id} kicked from haven after {time_spent:.2f} seconds")
                break 

        if waiting_room:
            admit_to_haven(waiting_room[0])

def remove_from_waiting_room(user_id):
    if user_id in waiting_room:
        del waiting_room[user_id]
        print(f"User {user_id} removed from waiting room")

def update_waiting_room_status():
    print("Updating waiting room status")
    for user_id in waiting_room:
        if user_id in socketio.server.rooms('/'): # This line was causing issues
            position = list(waiting_room.keys()).index(user_id) + 1
            estimated_wait = estimate_wait_time(position)
            socketio.emit('waiting_room_update', {
                'position': position,
                'total': len(waiting_room),
                'ahead': position - 1,
                'estimated_wait': estimated_wait,
                'waiting_list': list(waiting_room.keys())
            }, to=user_id)


def queue_management_task():
    while True:
        time.sleep(0.5)
        current_time = time.time()
        with lock:
            for user_id in list(waiting_room.keys()):
                if current_time - waiting_room[user_id] > WAITING_ROOM_TIMEOUT:
                    remove_from_waiting_room(user_id)

            # Check if haven is empty and there are users waiting
            if in_haven is None and waiting_room: 
                admit_to_haven(list(waiting_room.keys())[0]) # Admit the first user

            # Check for timeout or disconnection in the haven
            if in_haven is not None and (current_time - user_activity[in_haven] > HAVEN_TIMEOUT or in_haven not in socketio.server.rooms('/')):
                kick_from_haven(in_haven)

        update_waiting_room_status()

if __name__ == '__main__':
    background_thread = threading.Thread(target=queue_management_task)
    background_thread.daemon = True
    background_thread.start()
    app.run(host='0.0.0.0', port=2345, debug=True)