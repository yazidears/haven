const socket = io();

const queuePage = document.getElementById('queue-page');
const queuePosition = document.getElementById('queue-position');
const estimatedTime = document.getElementById('estimated-time');

let aliveInterval; // Variable to store the interval reference

socket.on('connect', () => {
    console.log('Connected to server');
    // Clear any existing interval before creating a new one
    if (aliveInterval) {
        clearInterval(aliveInterval);
    }
    aliveInterval = setInterval(() => {
        socket.emit('alive', { user_id: socket.id });
    }, 500); 
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    // Clear the interval when disconnected to avoid unnecessary requests
    clearInterval(aliveInterval);
});

socket.on('queue_update', (data) => {
    queuePosition.textContent = data.position + 1;
    estimatedTime.textContent = formatTime(data.eta);
});

socket.on('enter_haven', () => {
    window.location.href = '/haven'; 
});

// Modified check with a timeout
setTimeout(() => {
    if (!socket.connected) {
        window.location.href = '/'; 
    }
}, 1000); // Wait for 1 second before checking the connection

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
}

// haven.html specific JavaScript
const timeRemaining = document.getElementById('time-remaining');

function startHavenTimer() {
    let secondsLeft = 120; 
    timeRemaining.textContent = formatTime(secondsLeft);
    const timerInterval = setInterval(() => {
        secondsLeft--;
        timeRemaining.textContent = formatTime(secondsLeft);
        if (secondsLeft <= 0) {
            clearInterval(timerInterval);
            // Handle haven timeout (server should kick you out)
        }
    }, 1000);
}

startHavenTimer(); // Start the timer when haven.html loads

setInterval(() => {
    socket.emit('alive', { user_id: socket.id });
}, 1000); 
